import customtkinter as ctk

from ..core.rules import (
    FACTORS,
    RuleError,
    RuleEngineConfig,
    build_rule,
    validate_score_split,
)
from . import theme
from .widgets import show_prompt


class RuleEngineScreen:
    """
    The 'Rule Engine' setup screen.

    Lets the professor set a Minimum/Maximum range per metadata
    factor and choose how the total 100 points split between System
    and Human grading. Calls `on_continue(config)` with a
    RuleEngineConfig once the input validates.

    Also offers a Skip option for a professor who wants to grade
    entirely manually -- calls `on_skip()` directly, with no Rule
    Engine validation at all.

    `presets` is a {name: RuleEngineConfig} dict the caller already
    loaded from storage.rule_presets -- this screen only renders it
    and lets the professor load one into the form. Saving a new
    preset reuses the exact same validation as Continue (via
    build_config()) and calls `on_save_preset(name, config)`;
    persisting it and refreshing the list is the caller's job.
    """

    def __init__(
        self,
        parent,
        on_continue,
        on_skip=None,
        on_save_preset=None,
        presets=None,
        banner_text=None,
    ):

        self.on_continue = on_continue
        self.on_skip = on_skip
        self.on_save_preset = on_save_preset
        self.presets = presets or {}
        self.factor_entries = {}

        self.container = theme.page(parent)

        if banner_text:
            # Shown once, above the title, right after a class has
            # just been created and saved.
            banner = ctk.CTkFrame(
                self.container,
                fg_color=theme.TINTS[theme.SUCCESS],
                corner_radius=10
            )

            banner.pack(
                fill="x",
                pady=(0, 14)
            )

            theme.label(
                banner,
                f"✓  {banner_text}",
                size=13,
                weight="bold",
                color=theme.SUCCESS,
                anchor="w"
            ).pack(
                anchor="w",
                padx=16,
                pady=9
            )

        theme.screen_header(
            self.container,
            "Rule Engine",
            subtitle=(
                "Set a valid range for each factor. Leave both fields "
                "blank to skip grading that factor."
            )
        )

        # Footer is packed first (side="bottom") so the buttons stay
        # visible however small the window is; the scrollable form
        # takes whatever space remains.
        self.create_footer()

        self.scroll_frame = ctk.CTkScrollableFrame(
            self.container,
            fg_color="transparent"
        )

        self.scroll_frame.pack(
            fill="both",
            expand=True
        )

        self.create_factor_rows()
        self.create_score_split_row()
        self.create_presets_section()

    # -----------------------------------------
    # FACTOR RANGES
    # -----------------------------------------

    def create_factor_rows(self):

        card = theme.card(self.scroll_frame)

        card.pack(
            fill="x",
            pady=(0, 14),
            padx=(0, 6)
        )

        theme.label(
            card,
            "Technical ranges",
            size=16,
            weight="bold"
        ).pack(
            anchor="w",
            padx=22,
            pady=(18, 8)
        )

        for factor, info in FACTORS.items():

            row = ctk.CTkFrame(
                card,
                fg_color=theme.SURFACE_ALT,
                corner_radius=10
            )

            row.pack(
                fill="x",
                padx=16,
                pady=4
            )

            row.grid_columnconfigure(3, weight=1)

            theme.label(
                row,
                info["label"],
                size=14,
                weight="bold",
                width=210,
                anchor="w"
            ).grid(
                row=0,
                column=0,
                padx=(16, 10),
                pady=12,
                sticky="w"
            )

            min_entry = theme.text_entry(
                row,
                width=110,
                placeholder_text="Minimum"
            )

            min_entry.grid(
                row=0,
                column=1,
                padx=(0, 10)
            )

            max_entry = theme.text_entry(
                row,
                width=110,
                placeholder_text="Maximum"
            )

            max_entry.grid(
                row=0,
                column=2,
                padx=(0, 14)
            )

            theme.muted(
                row,
                (
                    f"allowed {info['valid_min']:.5f}".rstrip("0").rstrip(".")
                    + f" – {info['valid_max']:g}"
                ),
                anchor="w"
            ).grid(
                row=0,
                column=3,
                sticky="w"
            )

            self.factor_entries[factor] = (min_entry, max_entry)

        # bottom spacing inside the card
        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()

    # -----------------------------------------
    # SCORE SPLIT
    # -----------------------------------------

    def create_score_split_row(self):

        card = theme.card(self.scroll_frame)

        card.pack(
            fill="x",
            pady=(0, 14),
            padx=(0, 6)
        )

        theme.label(
            card,
            "Score split",
            size=16,
            weight="bold"
        ).pack(
            anchor="w",
            padx=22,
            pady=(18, 2)
        )

        theme.muted(
            card,
            (
                "System points are graded automatically from the ranges "
                "above. Human points are the ones you assign per photo."
            ),
            size=13,
            anchor="w",
            justify="left",
            wraplength=700
        ).pack(
            anchor="w",
            padx=22,
            pady=(0, 12)
        )

        row = ctk.CTkFrame(card, fg_color="transparent")

        row.pack(
            fill="x",
            padx=22,
            pady=(0, 8)
        )

        theme.label(
            row,
            "System Score (0-100):",
            size=14,
            weight="bold",
            width=190,
            anchor="w"
        ).pack(
            side="left",
            padx=(0, 10)
        )

        self.system_score_entry = theme.text_entry(
            row,
            width=100,
            placeholder_text="e.g. 40"
        )

        self.system_score_entry.pack(side="left")

        self.human_score_preview = theme.label(
            row,
            "Human Score: —",
            size=14,
            color=theme.TEXT_MUTED
        )

        self.human_score_preview.pack(
            side="left",
            padx=(18, 0)
        )

        self.split_bar = theme.progress_bar(card, 0.0, width=400)

        self.split_bar.pack(
            anchor="w",
            fill="x",
            padx=22,
            pady=(4, 20)
        )

        self.system_score_entry.bind(
            "<KeyRelease>",
            lambda event: self.update_human_score_preview()
        )

    def update_human_score_preview(self):

        value = self.system_score_entry.get().strip()

        if value.isdigit() and 0 <= int(value) <= 100:
            self.human_score_preview.configure(
                text=f"Human Score: {100 - int(value)}",
                text_color=theme.ACCENT
            )
            self.split_bar.set(int(value) / 100)
        else:
            self.human_score_preview.configure(
                text="Human Score: —",
                text_color=theme.TEXT_MUTED
            )
            self.split_bar.set(0)

    # -----------------------------------------
    # FOOTER ACTIONS
    # -----------------------------------------

    def create_footer(self):

        footer = ctk.CTkFrame(self.container, fg_color="transparent")

        footer.pack(
            side="bottom",
            fill="x",
            pady=(10, 0)
        )

        self.error_label = theme.error_label(footer)

        self.error_label.pack(
            anchor="w",
            pady=(0, 6)
        )

        self.create_action_buttons(footer)

    def create_action_buttons(self, parent):

        button_row = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )

        button_row.pack(fill="x")

        theme.primary_button(
            button_row,
            "Continue  →",
            self.handle_continue,
            width=160,
            height=42
        ).pack(side="left")

        theme.secondary_button(
            button_row,
            "Skip (Manual Grading Only)",
            self.handle_skip,
            width=230,
            height=42
        ).pack(
            side="left",
            padx=(10, 0)
        )

    # -----------------------------------------
    # SAVED PRESETS
    # -----------------------------------------

    def create_presets_section(self):

        card = theme.card(self.scroll_frame)

        card.pack(
            fill="x",
            pady=(0, 14),
            padx=(0, 6)
        )

        theme.label(
            card,
            "Saved presets",
            size=16,
            weight="bold"
        ).pack(
            anchor="w",
            padx=22,
            pady=(18, 10)
        )

        row = ctk.CTkFrame(card, fg_color="transparent")

        row.pack(
            fill="x",
            padx=22,
            pady=(0, 20)
        )

        preset_names = list(self.presets.keys())

        self.preset_menu = ctk.CTkOptionMenu(
            row,
            values=preset_names or ["No saved presets"],
            width=230,
            height=36,
            corner_radius=8,
            font=theme.font(13),
            dropdown_font=theme.font(13),
            fg_color=theme.SURFACE_ALT,
            button_color=theme.SURFACE_HOVER,
            button_hover_color=theme.BORDER,
            dropdown_fg_color=theme.SURFACE_ALT,
            dropdown_hover_color=theme.SURFACE_HOVER,
            text_color=theme.TEXT
        )

        self.preset_menu.pack(
            side="left",
            padx=(0, 10)
        )

        if not preset_names:
            self.preset_menu.configure(state="disabled")

        theme.secondary_button(
            row,
            "Load Selected Preset",
            self.handle_load_preset,
            width=170,
            height=36
        ).pack(
            side="left",
            padx=(0, 10)
        )

        theme.secondary_button(
            row,
            "Save Current as Preset",
            self.handle_save_preset,
            width=180,
            height=36
        ).pack(side="left")

    def handle_load_preset(self):
        """
        Loads the selected preset straight into the existing
        Minimum/Maximum/System Score fields -- the professor can
        still edit anything after loading it, same as if they'd
        typed it in by hand.
        """

        self.error_label.configure(text="")

        if not self.presets:
            return

        config = self.presets.get(self.preset_menu.get())

        if config is None:
            return

        rules_by_factor = {rule.factor: rule for rule in config.rules}

        for factor, (min_entry, max_entry) in self.factor_entries.items():

            min_entry.delete(0, "end")
            max_entry.delete(0, "end")

            rule = rules_by_factor.get(factor)

            if rule:
                min_entry.insert(0, f"{rule.minimum:g}")
                max_entry.insert(0, f"{rule.maximum:g}")

        self.system_score_entry.delete(0, "end")
        self.system_score_entry.insert(0, f"{config.system_score:g}")

        self.update_human_score_preview()

    def handle_save_preset(self):
        """
        Validates the current form with the exact same rules as
        Continue (build_config()) before asking for a preset name --
        a saved preset should never contain something the Rule
        Engine itself wouldn't accept.
        """

        self.error_label.configure(text="")

        config, error = self.build_config()

        if error:
            self.error_label.configure(text=error)
            return

        if not self.on_save_preset:
            return

        show_prompt(
            self.container,
            "Save Preset",
            "Preset name:",
            on_submit=lambda name: self.on_save_preset(name, config)
        )

    # -----------------------------------------
    # VALIDATION / SUBMIT
    # -----------------------------------------

    def build_config(self):
        """
        Validate the on-screen fields and build a RuleEngineConfig
        from them. The single place that turns form input into a
        RuleEngineConfig -- both Continue and Save Preset call this
        instead of each re-validating the same fields.

        Returns (config, None) on success, or (None, error_message)
        if the form is invalid.
        """

        rules = []

        for factor, (min_entry, max_entry) in self.factor_entries.items():

            min_text = min_entry.get().strip()
            max_text = max_entry.get().strip()

            if not min_text and not max_text:
                continue

            if not min_text or not max_text:
                return None, (
                    f"{FACTORS[factor]['label']}: fill in both "
                    f"Minimum and Maximum, or leave both blank."
                )

            try:
                minimum = float(min_text)
                maximum = float(max_text)
            except ValueError:
                return None, f"{FACTORS[factor]['label']}: values must be numbers."

            try:
                rules.append(build_rule(factor, minimum, maximum))
            except RuleError as error:
                return None, str(error)

        system_text = self.system_score_entry.get().strip()

        if not system_text.isdigit():
            return None, "System Score must be a whole number between 0 and 100."

        system_score = int(system_text)
        human_score = 100 - system_score

        try:
            validate_score_split(system_score, human_score)
        except RuleError as error:
            return None, str(error)

        config = RuleEngineConfig(
            system_score=system_score,
            human_score=human_score,
            rules=rules,
        )

        return config, None

    def handle_continue(self):

        self.error_label.configure(text="")

        config, error = self.build_config()

        if error:
            self.error_label.configure(text=error)
            return

        self.on_continue(config)

    def handle_skip(self):
        """
        Rule Engine Skip. No validation at all -- the professor is
        choosing to grade entirely manually, so
        app.py.on_rules_skipped() sets every photo's Teacher max
        score to 100 and leaves Rule Engine grading off.
        """

        if self.on_skip:
            self.on_skip()

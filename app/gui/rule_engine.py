import customtkinter as ctk

from ..core.rules import (
    FACTORS,
    RuleError,
    RuleEngineConfig,
    build_rule,
    validate_score_split,
)
from .widgets import show_prompt


class RuleEngineScreen:
    """
    The 'Rule Engine' setup screen (spec sections 1-3).

    Lets the professor set a Minimum/Maximum range per metadata
    factor and choose how the total 100 points split between System
    and Human grading. Calls `on_continue(config)` with a
    RuleEngineConfig once the input validates.

    Also offers a Skip option (new feature: Rule Engine Skip) for a
    professor who wants to grade entirely manually -- calls
    `on_skip()` directly, with no Rule Engine validation at all.

    New feature: Rule Engine Presets. `presets` is a
    {name: RuleEngineConfig} dict the caller already loaded from
    storage.rule_presets -- this screen only renders it and lets the
    professor load one into the form above. Saving a new preset
    reuses the exact same validation as Continue (via build_config())
    and calls `on_save_preset(name, config)`; persisting it and
    refreshing the list is the caller's job (same "screen renders,
    App persists" split used everywhere else in the app).

    New feature: Settings defaults. `default_system_score` pre-fills
    the System Score box, and `default_tolerance_percent` (a
    percentage like 15) is the tolerance given to every NEW Rule
    this screen builds. Both only affect configurations created
    here -- a preset that is loaded keeps its own saved tolerance.
    """

    def __init__(
        self,
        parent,
        on_continue,
        on_skip=None,
        on_save_preset=None,
        presets=None,
        banner_text=None,
        default_system_score=None,
        default_tolerance_percent=None,
    ):

        self.on_continue = on_continue
        self.on_skip = on_skip
        self.on_save_preset = on_save_preset
        self.presets = presets or {}
        self.default_tolerance_percent = default_tolerance_percent
        self.factor_entries = {}

        # {factor: tolerance fraction} for rules loaded from a
        # preset, so they keep the tolerance they were saved with
        # instead of being re-stamped with today's default.
        self.loaded_tolerance = {}

        self.container = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )

        self.container.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=30
        )

        if banner_text:
            # New feature: Class Management -- shown once, right
            # above the Rule Engine title, after a class has just
            # been created and saved (spec section 5).
            ctk.CTkLabel(
                self.container,
                text=f"✅ {banner_text}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#7CFFB2"
            ).pack(pady=(0, 10))

        ctk.CTkLabel(
            self.container,
            text="Rule Engine",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#7CFFB2"
        ).pack(pady=(0, 5))

        ctk.CTkLabel(
            self.container,
            text=(
                "Set a valid range for each factor. Leave both fields "
                "blank to skip grading that factor."
            ),
            text_color="gray60"
        ).pack(pady=(0, 15))

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

        if default_system_score is not None:
            self.system_score_entry.insert(0, str(int(default_system_score)))
            self.update_human_score_preview()

        self.error_label = ctk.CTkLabel(
            self.container,
            text="",
            text_color="#FF6B6B"
        )

        self.error_label.pack(pady=(10, 5))

        self.create_action_buttons()
        self.create_presets_section()

    # -----------------------------------------
    # ROWS
    # -----------------------------------------

    def create_factor_rows(self):

        for factor, info in FACTORS.items():

            row = ctk.CTkFrame(
                self.scroll_frame,
                fg_color="transparent"
            )

            row.pack(
                fill="x",
                pady=8
            )

            ctk.CTkLabel(
                row,
                text=info["label"],
                width=200,
                anchor="w",
                font=ctk.CTkFont(size=14, weight="bold")
            ).pack(
                side="left",
                padx=(0, 10)
            )

            min_entry = ctk.CTkEntry(
                row,
                width=100,
                placeholder_text="Minimum"
            )

            min_entry.pack(
                side="left",
                padx=(0, 10)
            )

            max_entry = ctk.CTkEntry(
                row,
                width=100,
                placeholder_text="Maximum"
            )

            max_entry.pack(side="left")

            self.factor_entries[factor] = (min_entry, max_entry)

    def create_score_split_row(self):

        row = ctk.CTkFrame(
            self.container,
            fg_color="transparent"
        )

        row.pack(
            fill="x",
            pady=(15, 0)
        )

        ctk.CTkLabel(
            row,
            text="System Score (0-100):",
            width=200,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(
            side="left",
            padx=(0, 10)
        )

        self.system_score_entry = ctk.CTkEntry(
            row,
            width=100,
            placeholder_text="e.g. 40"
        )

        self.system_score_entry.pack(side="left")

        self.human_score_preview = ctk.CTkLabel(
            row,
            text="Human Score: —",
            text_color="gray60"
        )

        self.human_score_preview.pack(
            side="left",
            padx=(15, 0)
        )

        self.system_score_entry.bind(
            "<KeyRelease>",
            lambda event: self.update_human_score_preview()
        )

    def update_human_score_preview(self):

        value = self.system_score_entry.get().strip()

        if value.isdigit() and 0 <= int(value) <= 100:
            self.human_score_preview.configure(
                text=f"Human Score: {100 - int(value)}"
            )
        else:
            self.human_score_preview.configure(
                text="Human Score: —"
            )

    def create_action_buttons(self):

        button_row = ctk.CTkFrame(
            self.container,
            fg_color="transparent"
        )

        button_row.pack(pady=(10, 0))

        ctk.CTkButton(
            button_row,
            text="Continue",
            width=150,
            height=40,
            fg_color="#1F8F4C",
            hover_color="#27AE60",
            command=self.handle_continue
        ).pack(
            side="left",
            padx=(0, 10)
        )

        ctk.CTkButton(
            button_row,
            text="Skip (Manual Grading Only)",
            width=220,
            height=40,
            fg_color="transparent",
            hover_color="#123f2c",
            border_color="#2ECC71",
            border_width=1,
            text_color="#7CFFB2",
            command=self.handle_skip
        ).pack(side="left")

    # -----------------------------------------
    # SAVED PRESETS (new feature: Rule Engine Presets)
    # -----------------------------------------

    def create_presets_section(self):

        ctk.CTkFrame(
            self.container,
            height=2,
            fg_color="gray30"
        ).pack(
            fill="x",
            pady=(20, 15)
        )

        ctk.CTkLabel(
            self.container,
            text="Saved Presets",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#7CFFB2"
        ).pack(
            anchor="w",
            pady=(0, 10)
        )

        row = ctk.CTkFrame(
            self.container,
            fg_color="transparent"
        )

        row.pack(fill="x")

        preset_names = list(self.presets.keys())

        self.preset_menu = ctk.CTkOptionMenu(
            row,
            values=preset_names or ["No saved presets"],
            width=220
        )

        self.preset_menu.pack(
            side="left",
            padx=(0, 10)
        )

        if not preset_names:
            self.preset_menu.configure(state="disabled")

        ctk.CTkButton(
            row,
            text="Load Selected Preset",
            width=170,
            fg_color="transparent",
            hover_color="#123f2c",
            border_color="#2ECC71",
            border_width=1,
            text_color="#7CFFB2",
            command=self.handle_load_preset
        ).pack(
            side="left",
            padx=(0, 10)
        )

        ctk.CTkButton(
            row,
            text="Save Preset",
            width=140,
            fg_color="#1F8F4C",
            hover_color="#27AE60",
            command=self.handle_save_preset
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

        # Remember each loaded rule's own tolerance (None for presets
        # saved before tolerance was stored per rule -- those fall
        # back to the default in build_config()).
        self.loaded_tolerance = {
            rule.factor: rule.tolerance_percent
            for rule in config.rules
            if rule.tolerance_percent is not None
        }

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

    def tolerance_for(self, factor):
        """
        The tolerance fraction a Rule built for `factor` should get:
        the one it was loaded with from a preset, else the Settings
        default, else None (the Rule Engine's built-in 15%).
        """

        loaded = self.loaded_tolerance.get(factor)

        if loaded is not None:
            return loaded

        if self.default_tolerance_percent is not None:
            return self.default_tolerance_percent / 100

        return None

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
                rules.append(
                    build_rule(
                        factor,
                        minimum,
                        maximum,
                        tolerance_percent=self.tolerance_for(factor)
                    )
                )
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
        New feature: Rule Engine Skip. No validation at all -- the
        professor is choosing to grade entirely manually, so
        app.py.on_rules_skipped() sets every photo's Teacher max
        score to 100 and leaves Rule Engine grading off.
        """

        if self.on_skip:
            self.on_skip()
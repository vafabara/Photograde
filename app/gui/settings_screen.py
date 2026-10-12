import customtkinter as ctk

from ..core.rules import RuleError, validate_score_split
from ..storage.settings_storage import (
    AppSettings,
    EXPORT_FORMATS,
    MAX_TOLERANCE_SETTING,
    MIN_TOLERANCE_PERCENT,
)
from . import theme


class SettingsScreen:
    """
    The Settings screen. Same pattern as the other screens: takes a
    parent frame, renders `settings` (an AppSettings that App already
    loaded) and reports back through callbacks -- it never touches
    storage itself.

    Nothing is applied until Save is pressed, because the weights and
    tolerance need validating first. `on_save(new_settings)` is only
    called with fully valid values; it returns False if saving failed
    (App shows the error), in which case no success message is shown.

    There is deliberately no Theme control here (out of scope for the
    redesign). The stored `theme` value is passed through untouched
    so saving never changes it.
    """

    def __init__(self, parent, settings, on_save, on_back):

        self.settings = settings
        self.on_save = on_save

        self.container = theme.page(parent)

        theme.screen_header(
            self.container,
            "Settings",
            subtitle="Defaults and preferences. They never change existing classes.",
            on_back=on_back
        )

        # Footer first so Save stays visible however small the window is.
        footer = ctk.CTkFrame(self.container, fg_color="transparent")

        footer.pack(
            side="bottom",
            fill="x",
            pady=(12, 0)
        )

        self.message_label = theme.label(
            footer,
            "",
            size=13,
            anchor="w"
        )

        self.message_label.pack(
            anchor="w",
            pady=(0, 6)
        )

        theme.primary_button(
            footer,
            "Save Settings",
            self.handle_save,
            width=170,
            height=42
        ).pack(anchor="w")

        self.scroll = ctk.CTkScrollableFrame(
            self.container,
            fg_color="transparent"
        )

        self.scroll.pack(
            fill="both",
            expand=True
        )

        self.create_grading_card(settings)
        self.create_export_card(settings)
        self.create_behavior_card(settings)

    # -----------------------------------------
    # LAYOUT HELPERS
    # -----------------------------------------

    def create_card(self, title):

        card = theme.card(self.scroll)

        card.pack(
            fill="x",
            pady=(0, 14),
            padx=(0, 6)
        )

        theme.label(
            card,
            title,
            size=16,
            weight="bold",
            anchor="w"
        ).pack(
            anchor="w",
            padx=22,
            pady=(18, 6)
        )

        return card

    def create_row(self, card, label_text, description):
        """
        One setting: a bold label with a grey explanation underneath
        on the left, and its control on the right. Returns the
        right-hand frame for the caller to put the control in.
        """

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

        row.grid_columnconfigure(0, weight=1)

        text_column = ctk.CTkFrame(row, fg_color="transparent")

        text_column.grid(
            row=0,
            column=0,
            sticky="w",
            padx=(16, 10),
            pady=12
        )

        theme.label(
            text_column,
            label_text,
            size=14,
            weight="bold",
            anchor="w"
        ).pack(anchor="w")

        theme.muted(
            text_column,
            description,
            size=12,
            anchor="w",
            justify="left",
            wraplength=480
        ).pack(
            anchor="w",
            pady=(2, 0)
        )

        control_frame = ctk.CTkFrame(row, fg_color="transparent")

        control_frame.grid(
            row=0,
            column=1,
            padx=(0, 16)
        )

        return control_frame

    def create_note(self, card, text):

        theme.muted(
            card,
            text,
            size=12,
            anchor="w",
            justify="left",
            wraplength=640
        ).pack(
            anchor="w",
            padx=22,
            pady=(2, 16)
        )

    def create_option_menu(self, parent, values):

        return ctk.CTkOptionMenu(
            parent,
            values=values,
            width=140,
            height=34,
            corner_radius=8,
            font=theme.font(13),
            dropdown_font=theme.font(13),
            fg_color=theme.SURFACE,
            button_color=theme.SURFACE_HOVER,
            button_hover_color=theme.BORDER,
            dropdown_fg_color=theme.SURFACE_ALT,
            dropdown_hover_color=theme.SURFACE_HOVER,
            text_color=theme.TEXT
        )

    def create_switch(self, parent):

        return ctk.CTkSwitch(
            parent,
            text="",
            fg_color=theme.BORDER,
            progress_color=theme.ACCENT,
            button_color=theme.TEXT,
            button_hover_color=theme.TEXT_MUTED
        )

    # -----------------------------------------
    # CARDS
    # -----------------------------------------

    def create_grading_card(self, settings):

        card = self.create_card("Grading")

        control = self.create_row(
            card,
            "Default System Weight",
            "Points (out of 100) given to the Rule Engine when you "
            "configure a new class. Teacher weight fills in the rest."
        )

        self.system_entry = theme.text_entry(control, width=80)
        self.system_entry.insert(0, str(settings.system_weight))
        self.system_entry.pack()

        control = self.create_row(
            card,
            "Default Teacher Weight",
            "Points (out of 100) for your own grading. Must add up to "
            "100 together with the System weight."
        )

        self.teacher_entry = theme.text_entry(control, width=80)
        self.teacher_entry.insert(0, str(settings.teacher_weight))
        self.teacher_entry.pack()

        # Typing in one box fills the other, the same way the Rule
        # Engine screen shows the Human score.
        self.system_entry.bind(
            "<KeyRelease>",
            lambda event: self.fill_complement(self.system_entry, self.teacher_entry)
        )
        self.teacher_entry.bind(
            "<KeyRelease>",
            lambda event: self.fill_complement(self.teacher_entry, self.system_entry)
        )

        control = self.create_row(
            card,
            "Default Tolerance (%)",
            "How far outside a Min/Max range a value can be and still "
            "count as Yellow instead of Red. Applies to new Rule Engine "
            "configurations only."
        )

        self.tolerance_entry = theme.text_entry(control, width=80)
        self.tolerance_entry.insert(0, f"{settings.tolerance_percent:g}")
        self.tolerance_entry.pack()

        self.create_note(
            card,
            "Existing classes and saved presets keep the values they "
            "were created with."
        )

    def create_export_card(self, settings):

        card = self.create_card("Export")

        control = self.create_row(
            card,
            "Default Export Format",
            "Excel is the only format available right now. CSV and JSON "
            "can be selected, but exporting still produces an Excel file "
            "until they are implemented."
        )

        self.export_menu = self.create_option_menu(control, list(EXPORT_FORMATS))
        self.export_menu.set(settings.export_format)
        self.export_menu.pack()

        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()

    def create_behavior_card(self, settings):

        card = self.create_card("Behavior")

        control = self.create_row(
            card,
            "Confirm before deleting",
            "Ask Yes/No before deleting a class or removing a student."
        )

        self.confirm_switch = self.create_switch(control)
        self.confirm_switch.pack()

        if settings.confirm_delete:
            self.confirm_switch.select()

        control = self.create_row(
            card,
            "Show EXIF information",
            "Show the Camera Information section while grading photos. "
            "Turning it off also hides the Green/Yellow/Red colors, "
            "which are drawn on those fields."
        )

        self.exif_switch = self.create_switch(control)
        self.exif_switch.pack()

        if settings.show_exif:
            self.exif_switch.select()

        ctk.CTkFrame(card, height=10, fg_color="transparent").pack()

    # -----------------------------------------
    # VALIDATION / SAVE
    # -----------------------------------------

    def fill_complement(self, source_entry, target_entry):

        text = source_entry.get().strip()

        if text.isdigit() and 0 <= int(text) <= 100:
            target_entry.delete(0, "end")
            target_entry.insert(0, str(100 - int(text)))

    def show_message(self, text, color):
        self.message_label.configure(text=text, text_color=color)

    def handle_save(self):

        system_text = self.system_entry.get().strip()
        teacher_text = self.teacher_entry.get().strip()

        if not system_text.isdigit() or not teacher_text.isdigit():
            self.show_message(
                "Weights must be whole numbers between 0 and 100.",
                theme.DANGER
            )
            return

        system_weight = int(system_text)
        teacher_weight = int(teacher_text)

        try:
            validate_score_split(system_weight, teacher_weight)
        except RuleError as error:
            self.show_message(str(error), theme.DANGER)
            return

        try:
            tolerance = float(self.tolerance_entry.get().strip())
        except ValueError:
            self.show_message("Tolerance must be a number.", theme.DANGER)
            return

        if not MIN_TOLERANCE_PERCENT <= tolerance <= MAX_TOLERANCE_SETTING:
            self.show_message(
                f"Tolerance must be between {MIN_TOLERANCE_PERCENT} and "
                f"{MAX_TOLERANCE_SETTING} %.",
                theme.DANGER
            )
            return

        saved = self.on_save(
            AppSettings(
                theme=self.settings.theme,
                system_weight=system_weight,
                teacher_weight=teacher_weight,
                tolerance_percent=tolerance,
                export_format=self.export_menu.get(),
                confirm_delete=bool(self.confirm_switch.get()),
                show_exif=bool(self.exif_switch.get()),
            )
        )

        if saved is False:
            return

        self.show_message("Settings saved.", theme.SUCCESS)

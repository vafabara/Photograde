import customtkinter as ctk

from ..core.rules import RuleError, validate_score_split
from ..storage.settings_storage import (
    AppSettings,
    EXPORT_FORMATS,
    MAX_TOLERANCE_SETTING,
    MIN_TOLERANCE_PERCENT,
    THEMES,
)


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
    """

    def __init__(self, parent, settings, on_save, on_back):

        self.on_save = on_save

        self.container = ctk.CTkFrame(parent, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=40, pady=30)

        self.create_header(on_back)

        self.scroll = ctk.CTkScrollableFrame(
            self.container,
            fg_color="transparent"
        )
        self.scroll.pack(fill="both", expand=True)

        self.create_appearance_card(settings)
        self.create_grading_card(settings)
        self.create_export_card(settings)
        self.create_behavior_card(settings)

        self.message_label = ctk.CTkLabel(self.container, text="")
        self.message_label.pack(pady=(10, 5))

        ctk.CTkButton(
            self.container,
            text="Save Settings",
            width=170,
            height=40,
            fg_color="#1F8F4C",
            hover_color="#27AE60",
            command=self.handle_save
        ).pack()

    # -----------------------------------------
    # LAYOUT HELPERS
    # -----------------------------------------

    def create_header(self, on_back):

        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))

        ctk.CTkButton(
            header,
            text="← Back",
            width=90,
            height=32,
            fg_color="transparent",
            hover_color="#123f2c",
            border_color="#2ECC71",
            text_color="#7CFFB2",
            border_width=1,
            command=on_back
        ).pack(side="left", padx=(0, 15))

        ctk.CTkLabel(
            header,
            text="Settings",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#7CFFB2"
        ).pack(side="left")

    def create_card(self, title):

        card = ctk.CTkFrame(self.scroll, corner_radius=12)
        card.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#7CFFB2"
        ).pack(anchor="w", padx=20, pady=(15, 5))

        return card

    def create_row(self, card, label_text, description):
        """
        One setting: a bold label with its control on the right, and
        a grey one-line explanation underneath. Returns the right-hand
        frame for the caller to put the control in.
        """

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(8, 0))

        ctk.CTkLabel(
            row,
            text=label_text,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        control_frame = ctk.CTkFrame(row, fg_color="transparent")
        control_frame.pack(side="right")

        ctk.CTkLabel(
            card,
            text=description,
            anchor="w",
            justify="left",
            wraplength=560,
            text_color="gray60",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=20, pady=(0, 8))

        return control_frame

    # -----------------------------------------
    # CARDS
    # -----------------------------------------

    def create_appearance_card(self, settings):

        card = self.create_card("Appearance")

        control = self.create_row(
            card,
            "Theme",
            "Dark, Light, or follow your operating system's setting."
        )

        self.theme_menu = ctk.CTkOptionMenu(
            control,
            values=list(THEMES),
            width=140
        )
        self.theme_menu.set(settings.theme)
        self.theme_menu.pack()

    def create_grading_card(self, settings):

        card = self.create_card("Grading")

        control = self.create_row(
            card,
            "Default System Weight",
            "Points (out of 100) given to the Rule Engine when you "
            "configure a new class. Teacher weight fills in the rest."
        )

        self.system_entry = ctk.CTkEntry(control, width=80)
        self.system_entry.insert(0, str(settings.system_weight))
        self.system_entry.pack()

        control = self.create_row(
            card,
            "Default Teacher Weight",
            "Points (out of 100) for your own grading. Must add up to "
            "100 together with the System weight."
        )

        self.teacher_entry = ctk.CTkEntry(control, width=80)
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

        self.tolerance_entry = ctk.CTkEntry(control, width=80)
        self.tolerance_entry.insert(0, f"{settings.tolerance_percent:g}")
        self.tolerance_entry.pack()

        ctk.CTkLabel(
            card,
            text="Existing classes and saved presets keep the values they "
                 "were created with.",
            anchor="w",
            text_color="gray60",
            font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=20, pady=(0, 12))

    def create_export_card(self, settings):

        card = self.create_card("Export")

        control = self.create_row(
            card,
            "Default Export Format",
            "Excel is the only format available right now. CSV and JSON "
            "can be selected, but exporting still produces an Excel file "
            "until they are implemented."
        )

        self.export_menu = ctk.CTkOptionMenu(
            control,
            values=list(EXPORT_FORMATS),
            width=140
        )
        self.export_menu.set(settings.export_format)
        self.export_menu.pack()

    def create_behavior_card(self, settings):

        card = self.create_card("Behavior")

        control = self.create_row(
            card,
            "Confirm before deleting",
            "Ask Yes/No before deleting a class or removing a student."
        )

        self.confirm_switch = ctk.CTkSwitch(control, text="")
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

        self.exif_switch = ctk.CTkSwitch(control, text="")
        self.exif_switch.pack()

        if settings.show_exif:
            self.exif_switch.select()

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
                "#FF6B6B"
            )
            return

        system_weight = int(system_text)
        teacher_weight = int(teacher_text)

        try:
            validate_score_split(system_weight, teacher_weight)
        except RuleError as error:
            self.show_message(str(error), "#FF6B6B")
            return

        try:
            tolerance = float(self.tolerance_entry.get().strip())
        except ValueError:
            self.show_message("Tolerance must be a number.", "#FF6B6B")
            return

        if not MIN_TOLERANCE_PERCENT <= tolerance <= MAX_TOLERANCE_SETTING:
            self.show_message(
                f"Tolerance must be between {MIN_TOLERANCE_PERCENT} and "
                f"{MAX_TOLERANCE_SETTING} %.",
                "#FF6B6B"
            )
            return

        saved = self.on_save(
            AppSettings(
                theme=self.theme_menu.get(),
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

        self.show_message("Settings saved.", "#7CFFB2")
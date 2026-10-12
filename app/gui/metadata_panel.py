import customtkinter as ctk

from ..core.converters import exif_value
from ..core.scoring import GREEN, YELLOW, RED, MISSING
from . import theme
from .teacher_grading import TeacherGradingPanel

# Colors for each Rule status. A factor with no rule defined for it
# stays NO_RULE_COLOR, per the Rule Engine spec.
STATUS_COLORS = {
    GREEN: theme.SUCCESS,
    YELLOW: theme.WARNING,
    RED: theme.DANGER,
    MISSING: theme.TEXT_MUTED,
}

# Words next to the colour so status never relies on colour alone.
STATUS_TEXT = {
    GREEN: "In range",
    YELLOW: "Near",
    RED: "Out of range",
    MISSING: "No data",
}

NO_RULE_COLOR = theme.TEXT

# Maps a Rule Engine factor key to the value label that displays it,
# so update() can color the right label.
FACTOR_LABEL_ATTRS = {
    "iso": "iso_label",
    "aperture": "aperture_label",
    "shutter_speed": "shutter_label",
    "focal_length": "focal_label",
}


class MetadataPanel:
    """
    Right side of the grading screen: scoring on top, then the
    graded camera settings (coloured by Rule status), the remaining
    camera info, and file information.

    Same public contract as before: `MetadataPanel(parent,
    on_teacher_confirm)`, `.update(data, image_record)`,
    `.status_color(grading, factor)`, `.teacher_grading_panel`.
    """

    def __init__(self, parent, on_teacher_confirm=None):

        self.on_teacher_confirm = on_teacher_confirm
        self.badges = {}

        self.frame = ctk.CTkScrollableFrame(
            parent,
            width=360,
            corner_radius=12,
            fg_color=theme.SURFACE,
            border_width=1,
            border_color=theme.BORDER
        )

        self.frame.pack(
            side="right",
            fill="y",
            padx=(12, 0)
        )

        self.create_score_section()
        self.create_settings_section()
        self.create_camera_section()
        self.create_file_section()

    # -----------------------------------------
    # BUILDING BLOCKS
    # -----------------------------------------

    def section(self, title):

        card = ctk.CTkFrame(
            self.frame,
            fg_color=theme.SURFACE_ALT,
            corner_radius=10
        )

        card.pack(
            fill="x",
            padx=6,
            pady=6
        )

        theme.label(
            card,
            title.upper(),
            size=11,
            weight="bold",
            color=theme.TEXT_FAINT,
            anchor="w"
        ).pack(
            anchor="w",
            padx=16,
            pady=(12, 6)
        )

        return card

    def info_row(self, card, key, with_badge=False):
        """Key on the left, value on the right. Returns (value, badge)."""

        row = ctk.CTkFrame(card, fg_color="transparent")

        row.pack(
            fill="x",
            padx=16,
            pady=3
        )

        row.grid_columnconfigure(1, weight=1)

        theme.muted(
            row,
            key,
            size=13
        ).grid(
            row=0,
            column=0,
            sticky="nw"
        )

        value = theme.label(
            row,
            "—",
            size=13,
            weight="bold",
            anchor="e",
            justify="right",
            wraplength=190
        )

        value.grid(
            row=0,
            column=1,
            sticky="e",
            padx=(10, 0)
        )

        badge = None

        if with_badge:
            badge = theme.pill(row, "")
            badge.grid(
                row=0,
                column=2,
                padx=(8, 0)
            )
            badge.grid_remove()

        return value, badge

    def end_section(self, card):
        ctk.CTkFrame(card, height=8, fg_color="transparent").pack()

    # -----------------------------------------
    # SECTIONS
    # -----------------------------------------

    def create_score_section(self):

        self.score_card = self.section("Scoring")
        self.score_title = self.score_card

        self.teacher_grading_panel = TeacherGradingPanel(
            self.score_card,
            on_confirm=self.on_teacher_confirm
        )

    def create_settings_section(self):

        card = self.section("Exposure settings")

        self.iso_label, self.badges["iso"] = self.info_row(card, "ISO", True)
        self.aperture_label, self.badges["aperture"] = self.info_row(card, "Aperture", True)
        self.shutter_label, self.badges["shutter_speed"] = self.info_row(card, "Shutter speed", True)
        self.focal_label, self.badges["focal_length"] = self.info_row(card, "Focal length", True)

        self.end_section(card)

    def create_camera_section(self):

        card = self.section("Camera")

        self.make_label, _ = self.info_row(card, "Make")
        self.model_label, _ = self.info_row(card, "Model")
        self.lens_model_label, _ = self.info_row(card, "Lens")
        self.date_label, _ = self.info_row(card, "Date taken")
        self.flash_label, _ = self.info_row(card, "Flash")
        self.white_balance_label, _ = self.info_row(card, "White balance")

        self.end_section(card)

    def create_file_section(self):

        card = self.section("File")

        self.filename_label, _ = self.info_row(card, "Filename")
        self.format_label, _ = self.info_row(card, "Format")
        self.filesize_label, _ = self.info_row(card, "File size")
        self.width_label, _ = self.info_row(card, "Width")
        self.height_label, _ = self.info_row(card, "Height")
        self.mode_label, _ = self.info_row(card, "Color mode")

        self.end_section(card)

    # -----------------------------------------
    # UPDATE
    # -----------------------------------------

    def update(self, data, image_record):
        """
        `image_record` is a core.student.ImageRecord for the photo
        currently on screen. Camera-setting fields are colored by
        the Rule status in image_record.grading_result (default
        colour if there's no grading yet, or no rule was set for that
        factor), and the Teacher Grading panel is refreshed to show
        this photo's Rule Engine / Teacher / Total numbers.
        """

        grading = image_record.grading_result

        size = data["size"]

        self.filename_label.configure(text=data["path"].name)
        self.format_label.configure(text=str(data["format"]))
        self.filesize_label.configure(text=f"{data['file_size_mb']:.2f} MB")
        self.width_label.configure(text=f"{size[0]} PX")
        self.height_label.configure(text=f"{size[1]} PX")
        self.mode_label.configure(text=str(data["mode"]))

        self.make_label.configure(text=exif_value(data["make"]))
        self.model_label.configure(text=exif_value(data["model"]))
        self.lens_model_label.configure(text=exif_value(data["lens_model"]))
        self.date_label.configure(text=exif_value(data["date"]))
        self.flash_label.configure(text=exif_value(data["flash"]))
        self.white_balance_label.configure(text=exif_value(data["white_balance"]))

        graded_values = {
            "iso": data["iso"],
            "aperture": data["fnum"],
            "shutter_speed": data["exposure_time"],
            "focal_length": data["focal"],
        }

        for factor, raw_value in graded_values.items():

            label = getattr(self, FACTOR_LABEL_ATTRS[factor])

            label.configure(
                text=exif_value(raw_value),
                text_color=self.status_color(grading, factor)
            )

            self.update_badge(grading, factor)

        self.teacher_grading_panel.update(image_record)

    def find_status(self, grading, factor):

        if grading is None:
            return None

        for result in grading.rule_results:
            if result.factor == factor:
                return result.status

        return None

    def update_badge(self, grading, factor):

        badge = self.badges[factor]
        status = self.find_status(grading, factor)

        if status is None:
            badge.grid_remove()
            return

        color = STATUS_COLORS.get(status, NO_RULE_COLOR)

        badge.configure(
            text=f"  {STATUS_TEXT.get(status, status)}  ",
            text_color=color,
            fg_color=theme.TINTS.get(color, theme.SURFACE_ALT)
        )

        badge.grid()

    def status_color(self, grading, factor):
        """
        Look up this factor's Rule status in `grading` (a
        core.scoring.GradingResult) and return the color to display
        it in. NO_RULE_COLOR if there's no grading yet, or no rule
        was set for this factor.
        """

        status = self.find_status(grading, factor)

        if status is None:
            return NO_RULE_COLOR

        return STATUS_COLORS.get(status, NO_RULE_COLOR)

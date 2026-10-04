import customtkinter as ctk

from ..core.converters import exif_value
from ..core.scoring import GREEN, YELLOW, RED, MISSING
from .teacher_grading import TeacherGradingPanel
from .widgets import create_info_label

# Colors for each Rule status. A factor with no rule defined for it
# stays NO_RULE_COLOR (white), per spec section 10.
STATUS_COLORS = {
    GREEN: "#7CFFB2",
    YELLOW: "#F5D76E",
    RED: "#FF6B6B",
    MISSING: "#AAAAAA",
}

NO_RULE_COLOR = "white"

# Maps a Rule Engine factor key to the CTkLabel attribute that
# displays it, so update() can color the right label.
FACTOR_LABEL_ATTRS = {
    "iso": "iso_label",
    "aperture": "aperture_label",
    "shutter_speed": "shutter_label",
    "focal_length": "focal_label",
}


class MetadataPanel:
    """
    `show_exif` (Settings: "Show EXIF information") controls whether
    the Camera Information section is displayed. The section is
    always built and still updated -- it's just not packed onto the
    screen when show_exif is False -- so nothing else in this class
    needs to know about the setting.
    """

    def __init__(self, parent, on_teacher_confirm=None, show_exif=True):

        self.on_teacher_confirm = on_teacher_confirm
        self.show_exif = show_exif

        self.frame = ctk.CTkScrollableFrame(
            parent,
            corner_radius=12
        )

        self.frame.pack(
            side="right",
            fill="both",
            expand=True,
            padx=(10, 0)
        )

        self.create_score_section()
        self.create_file_section()
        self.create_camera_section()

    def create_score_section(self):
        # NOTE: the spec asks for this "under the photo" — that's
        # image_viewer.py, which wasn't shared with me. I put it here
        # instead so it still works; move it if you'd rather it sat
        # under the image.

        self.score_title = ctk.CTkLabel(
            self.frame,
            text="🏆  Scoring",
            font=ctk.CTkFont(
                size=20,
                weight="bold"
            )
        )

        self.score_title.pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        self.teacher_grading_panel = TeacherGradingPanel(
            self.frame,
            on_confirm=self.on_teacher_confirm
        )

        self.score_separator = ctk.CTkFrame(
            self.frame,
            height=2,
            fg_color="gray30"
        )

        self.score_separator.pack(
            fill="x",
            padx=20,
            pady=(10, 20)
        )

    def create_file_section(self):

        self.file_title = ctk.CTkLabel(
            self.frame,
            text="🗂️  File Information",
            font=ctk.CTkFont(
                size=20,
                weight="bold"
            )
        )

        self.file_title.pack(
            anchor="w",
            padx=20,
            pady=(20, 15)
        )

        self.filename_label = create_info_label(
            self.frame,
            "Filename: —"
        )

        self.format_label = create_info_label(
            self.frame,
            "Format: —"
        )

        self.filesize_label = create_info_label(
            self.frame,
            "File Size: —"
        )

        self.width_label = create_info_label(
            self.frame,
            "Width: —"
        )

        self.height_label = create_info_label(
            self.frame,
            "Height: —"
        )

        self.mode_label = create_info_label(
            self.frame,
            "Color Mode: —"
        )

        self.separator = ctk.CTkFrame(
            self.frame,
            height=2,
            fg_color="gray30"
        )

        self.separator.pack(
            fill="x",
            padx=20,
            pady=20
        )

    def create_camera_section(self):

        # Everything in the Camera Information section lives in its
        # own frame so the whole section can be hidden at once
        # (Settings: Show EXIF information).
        self.camera_frame = ctk.CTkFrame(
            self.frame,
            fg_color="transparent"
        )

        if self.show_exif:
            self.camera_frame.pack(fill="x")

        self.camera_title = ctk.CTkLabel(
            self.camera_frame,
            text="📸  Camera Information",
            font=ctk.CTkFont(
                size=20,
                weight="bold"
            )
        )

        self.camera_title.pack(
            anchor="w",
            padx=20,
            pady=(0, 15)
        )

        self.make_label = create_info_label(
            self.camera_frame,
            "Make: —"
        )

        self.model_label = create_info_label(
            self.camera_frame,
            "Model: —"
        )

        self.lens_model_label = create_info_label(
            self.camera_frame,
            "Lens Model: —"
        )

        self.iso_label = create_info_label(
            self.camera_frame,
            "ISO: —"
        )

        self.aperture_label = create_info_label(
            self.camera_frame,
            "Aperture: —"
        )

        self.shutter_label = create_info_label(
            self.camera_frame,
            "Shutter Speed: —"
        )

        self.focal_label = create_info_label(
            self.camera_frame,
            "Focal Length: —"
        )

        self.date_label = create_info_label(
            self.camera_frame,
            "Date Taken: —"
        )

        self.flash_label = create_info_label(
            self.camera_frame,
            "Flash: —"
        )

        self.white_balance_label = create_info_label(
            self.camera_frame,
            "White Balance: —"
        )

    def update(self, data, image_record):
        """
        `image_record` is a core.student.ImageRecord for the photo
        currently on screen. Camera-setting fields are colored by
        the Rule status in image_record.grading_result (white if
        there's no grading yet, or no rule was set for that factor),
        and the Teacher Grading panel is refreshed to show this
        photo's Rule Engine / Teacher / Total numbers.
        """

        grading = image_record.grading_result

        size = data["size"]

        self.filename_label.configure(
            text=f"Filename: {data['path'].name}"
        )

        self.format_label.configure(
            text=f"Format: {data['format']}"
        )

        self.filesize_label.configure(
            text=f"File Size: {data['file_size_mb']:.2f} MB"
        )

        self.width_label.configure(
            text=f"Width: {size[0]} PX"
        )

        self.height_label.configure(
            text=f"Height: {size[1]} PX"
        )

        self.mode_label.configure(
            text=f"Color Mode: {data['mode']}"
        )

        self.make_label.configure(
            text=f"Make: {exif_value(data['make'])}"
        )

        self.model_label.configure(
            text=f"Model: {exif_value(data['model'])}"
        )

        self.lens_model_label.configure(
            text=f"Lens Model: {exif_value(data['lens_model'])}"
        )

        self.iso_label.configure(
            text=f"ISO: {exif_value(data['iso'])}",
            text_color=self.status_color(grading, "iso")
        )

        self.aperture_label.configure(
            text=f"Aperture: {exif_value(data['fnum'])}",
            text_color=self.status_color(grading, "aperture")
        )

        self.shutter_label.configure(
            text=f"Shutter Speed: {exif_value(data['exposure_time'])}",
            text_color=self.status_color(grading, "shutter_speed")
        )

        self.focal_label.configure(
            text=f"Focal Length: {exif_value(data['focal'])}",
            text_color=self.status_color(grading, "focal_length")
        )

        self.date_label.configure(
            text=f"Date Taken: {exif_value(data['date'])}"
        )

        self.flash_label.configure(
            text=f"Flash: {exif_value(data['flash'])}"
        )

        self.white_balance_label.configure(
            text=f"White Balance: {exif_value(data['white_balance'])}"
        )

        self.teacher_grading_panel.update(image_record)

    def status_color(self, grading, factor):
        """
        Look up this factor's Rule status in `grading` (a
        core.scoring.GradingResult) and return the color to display
        it in. NO_RULE_COLOR (white) if there's no grading yet, or
        no rule was set for this factor.
        """

        if grading is None:
            return NO_RULE_COLOR

        for result in grading.rule_results:
            if result.factor == factor:
                return STATUS_COLORS.get(result.status, NO_RULE_COLOR)

        return NO_RULE_COLOR
import customtkinter as ctk

from ..core.rules import FACTORS
from ..core.scoring import MISSING
from ..core.teacher_scoring import (
    validate_teacher_score,
    compute_total_score,
    TeacherScoreError,
)
from . import theme


class TeacherGradingPanel:
    """
    Renders the Rule Engine / Teacher Grading / Total Score
    breakdown for whichever photo is currently on screen. Lives
    inside MetadataPanel's score section, the same way HistogramPanel
    lives inside ImageViewer.

    The System/Human split always comes from whatever is already set
    on the ImageRecord passed to update() (rule_engine_max_score /
    teacher_max_score, which app.py fills in from the existing
    RuleEngineConfig) -- nothing here is hard-coded to a specific
    weighting, so 40/60 and 30/70 both just work.

    Calls `on_confirm(image_record)` once the professor enters a
    valid score and presses Confirm (or Enter).
    """

    def __init__(self, parent, on_confirm=None):

        self.on_confirm = on_confirm
        self.image_record = None

        self.frame = ctk.CTkFrame(
            parent,
            fg_color="transparent"
        )

        self.frame.pack(
            fill="x",
            padx=16,
            pady=(0, 14)
        )

        self.create_exif_warning()

        # Rule Engine (automatic) score
        engine_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.engine_row = engine_row

        engine_row.pack(
            fill="x",
            pady=(0, 10)
        )

        theme.muted(
            engine_row,
            "Rule Engine",
            size=13
        ).pack(side="left")

        self.rule_engine_label = theme.label(
            engine_row,
            "—",
            size=13,
            weight="bold",
            anchor="e"
        )

        self.rule_engine_label.pack(side="right")

        self.create_teacher_row()

        self.error_label = theme.error_label(
            self.frame,
            wraplength=300,
            justify="left"
        )

        self.error_label.pack(
            anchor="w",
            pady=(4, 6)
        )

        self.total_separator = theme.divider(self.frame)

        self.total_separator.pack(
            fill="x",
            pady=(0, 10)
        )

        total_row = ctk.CTkFrame(self.frame, fg_color="transparent")

        total_row.pack(fill="x")

        theme.muted(
            total_row,
            "Total Score",
            size=13
        ).pack(side="left")

        self.total_label = theme.label(
            total_row,
            "— / 100",
            size=20,
            weight="bold",
            color=theme.ACCENT,
            anchor="e"
        )

        self.total_label.pack(side="right")

    def create_exif_warning(self):
        """
        Banner shown only while Rule Engine grading is skipped for the
        photo on screen because required EXIF data is missing. Built
        here but not packed -- update_exif_warning() shows/hides it.
        """

        self.exif_warning = ctk.CTkFrame(
            self.frame,
            fg_color=theme.TINTS[theme.WARNING],
            corner_radius=8
        )

        theme.label(
            self.exif_warning,
            "⚠  EXIF data missing",
            size=12,
            weight="bold",
            color=theme.WARNING,
            anchor="w"
        ).pack(
            anchor="w",
            padx=10,
            pady=(8, 2)
        )

        self.exif_warning_text = theme.label(
            self.exif_warning,
            "",
            size=12,
            color=theme.TEXT,
            anchor="w",
            justify="left",
            wraplength=250
        )

        self.exif_warning_text.pack(
            anchor="w",
            padx=10,
            pady=(0, 8)
        )

    def update_exif_warning(self, image_record):
        """
        Derived from this photo's own grading_result on every update(),
        so a previous photo's warning can never show on another photo.
        """

        grading = image_record.grading_result

        if grading is None or not grading.exif_missing:
            self.exif_warning.pack_forget()
            return

        missing = ", ".join(
            FACTORS[result.factor]["label"]
            for result in grading.rule_results
            if result.status == MISSING
        )

        self.exif_warning_text.configure(
            text=(
                "This photo is missing required EXIF metadata "
                f"(or has none): {missing}.\n"
                "Rule Engine grading was skipped. Please review the "
                "photo and assign its score out of 100."
            )
        )

        self.exif_warning.pack(
            fill="x",
            pady=(0, 10),
            before=self.engine_row
        )

    def create_teacher_row(self):

        row = ctk.CTkFrame(
            self.frame,
            fg_color="transparent"
        )

        row.pack(
            fill="x",
            pady=(0, 4)
        )

        theme.muted(
            row,
            "Teacher grading",
            size=13
        ).pack(side="left")

        self.confirm_button = theme.primary_button(
            row,
            "Confirm",
            self.handle_confirm,
            width=84,
            height=32
        )

        self.confirm_button.pack(side="right")

        self.teacher_max_label = theme.muted(
            row,
            "/ —",
            size=13
        )

        self.teacher_max_label.pack(
            side="right",
            padx=(6, 10)
        )

        self.teacher_entry = theme.text_entry(
            row,
            width=64,
            height=32,
            placeholder_text="?",
            justify="center"
        )

        self.teacher_entry.pack(side="right")

        self.teacher_entry.bind("<Return>", lambda event: self.handle_confirm())

    # -----------------------------------------
    # RENDER
    # -----------------------------------------

    def update(self, image_record):
        """
        `image_record` -- a core.student.ImageRecord for the photo
        currently on screen. Resets the input box for a fresh photo,
        or re-shows an already-confirmed Teacher score if this exact
        photo was graded before.
        """

        self.image_record = image_record
        self.error_label.configure(text="")

        grading = image_record.grading_result

        if grading is not None and grading.exif_missing:
            self.rule_engine_label.configure(
                text="Skipped (EXIF missing)",
                text_color=theme.WARNING
            )
        elif image_record.rule_engine_score is None:
            self.rule_engine_label.configure(
                text="— (no rules configured)",
                text_color=theme.TEXT_MUTED
            )
        else:
            self.rule_engine_label.configure(
                text=(
                    f"{image_record.rule_engine_score:g} "
                    f"/ {image_record.rule_engine_max_score:g}"
                ),
                text_color=theme.TEXT
            )

        self.update_exif_warning(image_record)

        teacher_max = image_record.teacher_max_score

        self.teacher_max_label.configure(
            text=f"/ {teacher_max:g}" if teacher_max is not None else "/ —"
        )

        self.teacher_entry.delete(0, "end")

        if image_record.teacher_score is not None:
            self.teacher_entry.insert(0, f"{image_record.teacher_score:g}")

        self.render_total()

    def render_total(self):

        record = self.image_record

        if record is None or record.total_score is None:
            self.total_label.configure(text="— / 100")
            return

        total_max = (record.rule_engine_max_score or 0) + (record.teacher_max_score or 0)

        self.total_label.configure(
            text=f"{record.total_score:g} / {total_max:g}"
        )

    # -----------------------------------------
    # CONFIRM
    # -----------------------------------------

    def handle_confirm(self):

        if self.image_record is None:
            return

        self.error_label.configure(text="")

        record = self.image_record

        if record.teacher_max_score is None:
            self.error_label.configure(
                text="Configure the Rule Engine score split before grading."
            )
            return

        try:
            teacher_score = validate_teacher_score(
                self.teacher_entry.get(),
                record.teacher_max_score
            )
        except TeacherScoreError as error:
            self.error_label.configure(text=str(error))
            return

        record.teacher_score = teacher_score

        rule_engine_score = record.rule_engine_score or 0.0

        record.total_score = compute_total_score(
            rule_engine_score,
            teacher_score
        )

        self.render_total()

        if self.on_confirm:
            self.on_confirm(record)
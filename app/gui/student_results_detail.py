import math
from pathlib import Path

import customtkinter as ctk

from . import theme


def format_score(value):
    """A score for display: "—" if the photo isn't graded, else 84.2 -> "84.2"."""

    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"

    return f"{value:g}"


class StudentResultsDetailScreen:
    """
    Per-student details opened from the Class Results screen's
    "Details" button. A read-only view over one
    core.class_model.ClassStudentEntry: the student's average and
    photo count, then one card per photo with its Rule Engine /
    Teacher / Total Score and its saved note.

    Everything shown is read straight from ClassStudentEntry /
    ClassPhotoEntry -- notes come from ClassPhotoEntry.note, the same
    field the Photo Note dialog writes -- so there's no second copy
    of any score or note. Takes a parent frame, a student and an
    on_back callback (App returns to the Class Results screen).

    This is a separate screen from StudentDetailScreen on purpose:
    that one is the Class Screen's DataFrame table (back goes to the
    Class Screen, no notes).
    """

    def __init__(self, parent, student, on_back):

        self.container = theme.page(parent)

        self.create_header(student, on_back)
        self.create_photo_list(student)

    # -----------------------------------------
    # HEADER
    # -----------------------------------------

    def create_header(self, student, on_back):

        # Same rule as the Class Results table: a Pending student's
        # average is shown as "—", not a partial number.
        average = student.average_total_score

        if student.is_completed and not math.isnan(average):
            average_text = f"{average:g} / 100"
        else:
            average_text = "—"

        status_text = "Completed" if student.is_completed else "Pending"

        header = theme.screen_header(
            self.container,
            student.name,
            subtitle=(
                f"Average: {average_text} • "
                f"{student.photo_count} Photos • "
                f"{status_text}"
            ),
            on_back=on_back,
            back_text="Back to Results",
            back_width=160
        )

        theme.pill(
            header,
            status_text,
            theme.SUCCESS if student.is_completed else theme.WARNING
        ).pack(side="right")

    # -----------------------------------------
    # PHOTO CARDS
    # -----------------------------------------

    def create_photo_list(self, student):

        # Scrollable so a student with many photos (up to the
        # 20-photo folder limit, and more if photos are added later)
        # stays usable.
        photo_list = ctk.CTkScrollableFrame(
            self.container,
            fg_color="transparent"
        )

        photo_list.pack(
            fill="both",
            expand=True
        )

        if not student.photos:

            theme.muted(
                photo_list,
                "No photos for this student.",
                size=14
            ).pack(pady=30)

            return

        for index, photo in enumerate(student.photos, start=1):
            self.create_photo_card(photo_list, index, photo)

    def create_photo_card(self, parent, index, photo):
        """
        `photo` is a core.class_model.ClassPhotoEntry. "Pic N" matches
        the label the Student DataFrame and the Excel export use for
        the same photo, with the filename alongside it.
        """

        card = theme.card(parent)

        card.pack(
            fill="x",
            padx=(0, 6),
            pady=6
        )

        title_row = ctk.CTkFrame(card, fg_color="transparent")

        title_row.pack(
            fill="x",
            padx=18,
            pady=(14, 8)
        )

        theme.label(
            title_row,
            f"Pic {index}",
            size=15,
            weight="bold",
            color=theme.ACCENT
        ).pack(side="left")

        theme.muted(
            title_row,
            Path(photo.path).name,
            size=13
        ).pack(
            side="left",
            padx=(10, 0)
        )

        scores_row = ctk.CTkFrame(card, fg_color="transparent")

        scores_row.pack(
            fill="x",
            padx=18
        )

        scores = [
            ("Rule Engine Score", photo.rule_engine_score, False),
            ("Teacher Score", photo.teacher_score, False),
            ("Total Score", photo.total_score, True),
        ]

        for column, (caption, value, highlight) in enumerate(scores):

            scores_row.grid_columnconfigure(column, weight=1, uniform="scores")

            theme.stat_tile(
                scores_row,
                caption,
                format_score(value),
                highlight=highlight
            ).grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else 8, 0)
            )

        note = (photo.note or "").strip()

        theme.label(
            card,
            "NOTE",
            size=11,
            weight="bold",
            color=theme.TEXT_FAINT,
            anchor="w"
        ).pack(
            fill="x",
            padx=18,
            pady=(12, 2)
        )

        # wraplength keeps a long note inside the card instead of
        # running off the right edge.
        theme.label(
            card,
            note if note else "No note",
            size=13,
            color=theme.TEXT if note else theme.TEXT_FAINT,
            wraplength=640,
            justify="left",
            anchor="w"
        ).pack(
            fill="x",
            padx=18,
            pady=(0, 16)
        )

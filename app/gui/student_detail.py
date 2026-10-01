from pathlib import Path

import customtkinter as ctk
import pandas as pd

from ..core.student_dataframe import build_student_dataframe
from .widgets import show_confirm, show_error


class StudentDetailScreen:
    """
    The Student Detail Screen (spec section 10), now rendering the
    Student DataFrame (new feature, spec section 6): one row per
    photo ("Pic 1", "Pic 2", ...) with its Rule Engine / Teacher /
    Total Score, plus a bold "Average" row. Sourced entirely from
    `student.photos` (core.class_model.ClassPhotoEntry) -- the same
    data the Class Screen's Avg Total column reads -- no second
    scoring system, and no grading is triggered from here.

    New feature: each photo row has a delete button. It asks for
    confirmation and then calls `on_delete_photo(photo_index)` --
    App removes that one photo from the class record and persists
    it; this screen never touches storage (same rule as ClassScreen).
    """

    def __init__(self, parent, student, on_back, on_delete_photo=None):

        self.student = student
        self.on_delete_photo = on_delete_photo

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

        self.create_header(student, on_back)
        self.create_dataframe_table(student)

    def create_header(self, student, on_back):

        header = ctk.CTkFrame(
            self.container,
            fg_color="transparent"
        )

        header.pack(
            fill="x",
            pady=(0, 20)
        )

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
        ).pack(
            side="left",
            padx=(0, 15)
        )

        ctk.CTkLabel(
            header,
            text=student.name,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#7CFFB2"
        ).pack(side="left")

    def create_dataframe_table(self, student):

        card = ctk.CTkFrame(
            self.container,
            corner_radius=12
        )

        card.pack(
            fill="both",
            expand=True
        )

        if not student.photos:

            ctk.CTkLabel(
                card,
                text="No grading data available yet.",
                font=ctk.CTkFont(size=16),
                text_color="gray60"
            ).pack(expand=True)

            return

        dataframe = build_student_dataframe(student)

        table_frame = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )

        table_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        columns = list(dataframe.columns)

        for col_index, column_name in enumerate(columns):

            ctk.CTkLabel(
                table_frame,
                text=column_name,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#7CFFB2"
            ).grid(
                row=0,
                column=col_index,
                padx=15,
                pady=(0, 10),
                sticky="w"
            )

        last_row_index = len(dataframe) - 1

        for row_index, row in enumerate(dataframe.itertuples(index=False), start=1):

            is_average_row = (row_index - 1) == last_row_index

            row_font = ctk.CTkFont(
                size=13,
                weight="bold" if is_average_row else "normal"
            )

            for col_index, value in enumerate(row):

                ctk.CTkLabel(
                    table_frame,
                    text=self.format_value(value),
                    font=row_font,
                    text_color="#7CFFB2" if is_average_row else "white"
                ).grid(
                    row=row_index,
                    column=col_index,
                    padx=15,
                    pady=4,
                    sticky="w"
                )

            # Photo rows only (the Average row isn't a photo). The
            # DataFrame lists photos in student.photos order, so grid
            # row N is photo index N - 1.
            if not is_average_row and self.on_delete_photo:

                ctk.CTkButton(
                    table_frame,
                    text="🗑",
                    width=32,
                    height=28,
                    fg_color="transparent",
                    hover_color="#3a1f1f",
                    text_color="#FF6B6B",
                    command=lambda i=row_index - 1: self.handle_delete_photo(i)
                ).grid(
                    row=row_index,
                    column=len(columns),
                    padx=15,
                    pady=4,
                    sticky="w"
                )

    def handle_delete_photo(self, index):
        """
        Confirms, then reports the deletion to App. Only removes the
        photo from this student's record in PhotoGrade -- the image
        file on disk is never touched. The last remaining photo
        can't be removed: a student with no photos can't be graded
        (the review flow has nothing to show), and there's no way to
        get a photo-less student into a class today, so the way to
        drop them entirely is the existing Delete Student action.
        """

        if len(self.student.photos) <= 1:
            show_error(
                self.container,
                "A student must keep at least one photo. "
                "To remove them completely, delete the student "
                "from the class instead."
            )
            return

        photo = self.student.photos[index]

        show_confirm(
            self.container,
            f'Remove Pic {index + 1} ({Path(photo.path).name}) '
            f'from this student?\n(The file on disk is not deleted.)',
            on_yes=lambda: self.on_delete_photo(index)
        )

    def format_value(self, value):

        if isinstance(value, str):
            return value

        if pd.isna(value):
            return "NaN"

        return f"{value:g}"

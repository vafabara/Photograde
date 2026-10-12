import customtkinter as ctk
import pandas as pd

from ..core.student_dataframe import build_student_dataframe
from . import theme

FIRST_COL_WIDTH = 160
SCORE_COL_WIDTH = 150


class StudentDetailScreen:
    """
    The Student Detail Screen: renders the Student DataFrame -- one
    row per photo ("Pic 1", "Pic 2", ...) with its Rule Engine /
    Teacher / Total Score, plus a highlighted "Average" row.
    Sourced entirely from `student.photos`
    (core.class_model.ClassPhotoEntry) -- the same data the Class
    Screen's Avg Total column reads -- no second scoring system, and
    no grading is triggered from here.
    """

    def __init__(self, parent, student, on_back):

        self.container = theme.page(parent)

        self.create_header(student, on_back)
        self.create_dataframe_table(student)

    def create_header(self, student, on_back):

        theme.screen_header(
            self.container,
            student.name,
            subtitle=f"{len(student.photos)} photos • score breakdown",
            on_back=on_back
        )

    def create_dataframe_table(self, student):

        card = theme.card(self.container)

        card.pack(
            fill="both",
            expand=True
        )

        if not student.photos:

            theme.label(
                card,
                "No grading data available yet.",
                size=15,
                color=theme.TEXT_MUTED
            ).pack(expand=True)

            return

        dataframe = build_student_dataframe(student)

        columns = list(dataframe.columns)

        header_row = ctk.CTkFrame(card, fg_color="transparent")

        header_row.pack(
            fill="x",
            padx=28,
            pady=(18, 4)
        )

        for col_index, column_name in enumerate(columns):

            theme.label(
                header_row,
                column_name.upper(),
                size=11,
                weight="bold",
                color=theme.TEXT_FAINT,
                width=FIRST_COL_WIDTH if col_index == 0 else SCORE_COL_WIDTH,
                anchor="w" if col_index == 0 else "e"
            ).grid(
                row=0,
                column=col_index,
                padx=6
            )

        table_frame = ctk.CTkScrollableFrame(
            card,
            fg_color="transparent"
        )

        table_frame.pack(
            fill="both",
            expand=True,
            padx=14,
            pady=(0, 14)
        )

        last_row_index = len(dataframe) - 1

        for row_index, row in enumerate(dataframe.itertuples(index=False)):

            is_average_row = row_index == last_row_index

            row_frame = ctk.CTkFrame(
                table_frame,
                fg_color=theme.TINTS[theme.ACCENT] if is_average_row else (
                    theme.SURFACE_ALT if row_index % 2 == 0 else "transparent"
                ),
                corner_radius=8
            )

            row_frame.pack(
                fill="x",
                pady=2,
                padx=(0, 4)
            )

            for col_index, value in enumerate(row):

                theme.label(
                    row_frame,
                    self.format_value(value),
                    size=13,
                    weight="bold" if is_average_row else "normal",
                    color=theme.ACCENT if is_average_row else theme.TEXT,
                    width=FIRST_COL_WIDTH if col_index == 0 else SCORE_COL_WIDTH,
                    anchor="w" if col_index == 0 else "e"
                ).grid(
                    row=0,
                    column=col_index,
                    padx=6,
                    pady=8
                )

    def format_value(self, value):

        if isinstance(value, str):
            return value

        if pd.isna(value):
            return "—"

        return f"{value:g}"

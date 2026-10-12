import math
from tkinter import filedialog

import customtkinter as ctk

from ..storage.export import default_export_filename, export_class_to_excel
from . import theme
from .widgets import show_error, show_info

COL_NAME = 300
COL_PHOTOS = 90
COL_AVERAGE = 110
COL_STATUS = 130


class ClassResultsScreen:
    """
    The Class Results page: shown at the end of the review flow.
    Purely a *view* over the already-persisted
    core.class_model.ClassRecord -- the same ClassStudentEntry /
    ClassPhotoEntry data that already powers the Class Screen's Avg
    Total column and the Student DataFrame. No score is computed,
    recalculated, or duplicated here:

        Photos -> Rule Engine -> Teacher Grading -> ClassRecord
               -> Student DataFrame -> Class Results (this screen)

    Takes a parent frame and a ClassRecord, and calls back into App
    for navigation (Home / Review / a student's details) -- this
    screen never touches class storage itself. Export is the one
    action it handles directly: it asks where to save, then hands
    the ClassRecord to storage.export, which builds the workbook.
    """

    def __init__(self, parent, class_record, on_home, on_review, on_student_details):

        self.class_record = class_record
        self.on_home = on_home
        self.on_review = on_review
        self.on_student_details = on_student_details

        self.container = theme.page(parent)

        self.create_header()
        self.create_completion_message()
        self.create_summary()
        self.create_bottom_bar()
        self.create_student_table()

    # -----------------------------------------
    # HEADER
    # -----------------------------------------

    def create_header(self):

        theme.label(
            self.container,
            "CLASS RESULTS",
            size=12,
            weight="bold",
            color=theme.ACCENT,
            anchor="w"
        ).pack(anchor="w")

        theme.label(
            self.container,
            self.class_record.class_name,
            size=26,
            weight="bold",
            anchor="w"
        ).pack(
            anchor="w",
            pady=(0, 12)
        )

    # -----------------------------------------
    # COMPLETION MESSAGE
    # -----------------------------------------

    def create_completion_message(self):
        """
        Short status banner. The "grading completed" wording is only
        shown when it's actually true (every student Completed) --
        this page is also reached after grading a single student,
        when others may still be Pending.
        """

        if not self.class_record.students:
            return

        pending = self.class_record.pending_student_count

        if pending == 0:
            text = (
                "Grading completed successfully. "
                "All student results are ready to review."
            )
            color = theme.SUCCESS
        else:
            noun = "student" if pending == 1 else "students"
            text = f"Grading in progress. {pending} {noun} still pending."
            color = theme.WARNING

        banner = ctk.CTkFrame(
            self.container,
            fg_color=theme.TINTS[color],
            corner_radius=10
        )

        banner.pack(
            fill="x",
            pady=(0, 16)
        )

        theme.label(
            banner,
            text,
            size=13,
            color=color,
            anchor="w"
        ).pack(
            anchor="w",
            padx=16,
            pady=10
        )

    # -----------------------------------------
    # SUMMARY (Class Average + counts)
    # -----------------------------------------

    def create_summary(self):
        """
        Reads ClassRecord.average_total_score -- the mean of every
        graded *photo's* Total Score in the class, not the mean of
        the student averages -- shown exactly as computed.
        """

        record = self.class_record

        average = record.average_total_score
        graded = record.graded_photo_count
        total = record.total_photo_count

        average_text = "—" if math.isnan(average) else f"{average:g} / 100"

        # True when the average is built from only part of the class.
        is_partial = 0 < graded < total

        row = ctk.CTkFrame(self.container, fg_color="transparent")

        row.pack(
            fill="x",
            pady=(0, 18)
        )

        for column in range(5):
            row.grid_columnconfigure(column, weight=1 if column == 0 else 0)

        average_card = ctk.CTkFrame(
            row,
            fg_color=theme.SURFACE,
            border_width=1,
            border_color=theme.BORDER,
            corner_radius=12
        )

        average_card.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 10)
        )

        theme.muted(
            average_card,
            "Class Average",
            size=13
        ).pack(
            anchor="w",
            padx=22,
            pady=(14, 0)
        )

        theme.label(
            average_card,
            average_text,
            size=32,
            weight="bold",
            color=theme.ACCENT,
            anchor="w"
        ).pack(
            anchor="w",
            padx=22,
            pady=(0, 2 if is_partial else 14)
        )

        if is_partial:
            theme.muted(
                average_card,
                f"Based on {graded} of {total} photos graded"
            ).pack(
                anchor="w",
                padx=22,
                pady=(0, 14)
            )

        tiles = [
            ("Students", str(record.student_count)),
            ("Photos", str(record.total_photo_count)),
            ("Completed", str(record.completed_student_count)),
            ("Pending", str(record.pending_student_count)),
        ]

        for column, (caption, value) in enumerate(tiles, start=1):
            theme.stat_tile(row, caption, value).grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0 if column == 1 else 8, 0)
            )

    # -----------------------------------------
    # STUDENT RESULTS TABLE
    # -----------------------------------------

    def create_student_table(self):

        card = theme.card(self.container)

        card.pack(
            fill="both",
            expand=True,
            pady=(0, 16)
        )

        if not self.class_record.students:

            theme.label(
                card,
                "No students in this class.",
                size=14,
                color=theme.TEXT_MUTED
            ).pack(expand=True)

            return

        header_row = ctk.CTkFrame(card, fg_color="transparent")

        header_row.pack(
            fill="x",
            padx=28,
            pady=(14, 2)
        )

        headers = [
            ("STUDENT", COL_NAME),
            ("PHOTOS", COL_PHOTOS),
            ("AVERAGE", COL_AVERAGE),
            ("STATUS", COL_STATUS),
        ]

        for col_index, (text, width) in enumerate(headers):
            theme.label(
                header_row,
                text,
                size=11,
                weight="bold",
                color=theme.TEXT_FAINT,
                width=width,
                anchor="w"
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
            pady=(0, 12)
        )

        for row_index, student in enumerate(self.class_record.students, start=1):
            self.create_student_row(table_frame, row_index, student)

    def create_student_row(self, table_frame, row_index, student):
        """
        `student` is a core.class_model.ClassStudentEntry. Average
        and completion status are read straight off it
        (average_total_score / is_completed) -- both already power
        the Class Screen, so nothing here is a second calculation.
        A Pending student always shows "—" for Average, even if a
        partial average could technically be computed.

        The name cell also holds the "Details" button, which opens
        that student's per-photo details via
        on_student_details(class_record, student_index). Rows are
        numbered from 1, so the student's index in
        class_record.students is row_index - 1.
        """

        completed = student.is_completed

        if completed:
            avg_score = student.average_total_score
            average_text = "—" if math.isnan(avg_score) else f"{avg_score:g}"
        else:
            average_text = "—"

        row = ctk.CTkFrame(
            table_frame,
            fg_color=theme.SURFACE_ALT if row_index % 2 else "transparent",
            corner_radius=8
        )

        row.pack(
            fill="x",
            pady=2,
            padx=(0, 4)
        )

        name_cell = ctk.CTkFrame(
            row,
            fg_color="transparent",
            width=COL_NAME,
            height=40
        )

        name_cell.grid(
            row=0,
            column=0,
            padx=6,
            pady=4,
            sticky="w"
        )

        name_cell.grid_propagate(False)
        name_cell.grid_columnconfigure(0, weight=1)

        theme.label(
            name_cell,
            student.name,
            size=13,
            weight="bold",
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=6
        )

        theme.ghost_button(
            name_cell,
            "Details",
            lambda i=row_index - 1: self.on_student_details(
                self.class_record, i
            ),
            width=64,
            height=26
        ).grid(
            row=0,
            column=1,
            sticky="e"
        )

        theme.muted(
            row,
            str(student.photo_count),
            size=13,
            width=COL_PHOTOS,
            anchor="w"
        ).grid(
            row=0,
            column=1,
            padx=6
        )

        theme.label(
            row,
            average_text,
            size=13,
            weight="bold",
            color=theme.TEXT if completed else theme.TEXT_FAINT,
            width=COL_AVERAGE,
            anchor="w"
        ).grid(
            row=0,
            column=2,
            padx=6
        )

        status_cell = ctk.CTkFrame(
            row,
            fg_color="transparent",
            width=COL_STATUS,
            height=30
        )

        status_cell.grid(
            row=0,
            column=3,
            padx=6,
            sticky="w"
        )

        status_cell.grid_propagate(False)

        theme.pill(
            status_cell,
            "Completed" if completed else "Pending",
            theme.SUCCESS if completed else theme.WARNING
        ).place(
            x=0,
            rely=0.5,
            anchor="w"
        )

    # -----------------------------------------
    # BOTTOM ACTIONS — Home / Review / Export
    # -----------------------------------------

    def create_bottom_bar(self):

        bottom_frame = ctk.CTkFrame(
            self.container,
            fg_color="transparent"
        )

        # Packed before the table so it always stays visible.
        bottom_frame.pack(
            side="bottom",
            fill="x"
        )

        theme.secondary_button(
            bottom_frame,
            "Home",
            self.on_home,
            width=120,
            height=40
        ).pack(side="left")

        theme.secondary_button(
            bottom_frame,
            "Review",
            self.on_review,
            width=120,
            height=40
        ).pack(
            side="left",
            padx=(10, 0)
        )

        theme.primary_button(
            bottom_frame,
            "Export to Excel",
            self.handle_export,
            width=160,
            height=40
        ).pack(side="right")

    def handle_export(self):
        """
        Ask where to save, then export the class to an .xlsx
        workbook via storage.export.export_class_to_excel. Failures
        are shown as plain messages -- never a traceback.
        """

        file_path = filedialog.asksaveasfilename(
            title="Export Class Results",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
            initialfile=default_export_filename(self.class_record.class_name)
        )

        if not file_path:
            return

        # defaultextension isn't applied on every platform.
        if not file_path.lower().endswith(".xlsx"):
            file_path += ".xlsx"

        try:
            export_class_to_excel(self.class_record, file_path)

        except ImportError:
            show_error(
                self.container,
                "Excel export needs the 'openpyxl' package.\n"
                "Install it with: pip install openpyxl"
            )

        except OSError:
            show_error(
                self.container,
                "Could not save the file. Make sure it isn't open in "
                "another program and that you can write to that location."
            )

        except Exception:
            # Last-resort guard at the GUI boundary (e.g. openpyxl
            # rejecting an unusual character in a note): the teacher
            # gets a message instead of a silent failure.
            show_error(
                self.container,
                "Could not export the results."
            )

        else:
            show_info(
                self.container,
                "Export",
                "Results exported successfully."
            )

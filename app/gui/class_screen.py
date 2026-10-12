import math

import customtkinter as ctk
from tkinter import filedialog

from ..core.image import scan_student_folder, validate_selected_files, FolderValidationError
from . import theme
from .widgets import create_modal, show_error, show_confirm

# Fixed pixel widths for the table columns, shared by the header row
# and every student row so they line up.
COL_AVG = 90
COL_PHOTOS = 70
COL_GRADED = 140
COL_ACTIONS = 340


class ClassScreen:
    """
    The Class Screen: shows one persisted class's students with
    their photo counts, grading progress and average Total Score, and
    lets the professor start grading, add photos (folder or
    individual files), add a new student, or delete a student.

    Same contract as before -- takes a parent frame and a
    core.class_model.ClassRecord and renders straight from it; every
    change is handed back to App through a callback (this screen
    never touches storage):

        ClassScreen  ->  App  ->  class_storage  ->  classes/<id>/class.json
    """

    def __init__(
        self,
        parent,
        class_record,
        on_back,
        on_open_student,
        on_add_student,
        on_add_photos,
        on_delete_student,
        on_start_grading,
    ):

        self.class_record = class_record
        self.on_back = on_back
        self.on_open_student = on_open_student
        self.on_add_student = on_add_student
        self.on_add_photos = on_add_photos
        self.on_delete_student = on_delete_student
        self.on_start_grading = on_start_grading

        self.container = theme.page(parent)

        self.create_header()
        self.create_student_list()
        self.create_add_student_button()

    # -----------------------------------------
    # HEADER
    # -----------------------------------------

    def create_header(self):

        record = self.class_record

        self.header = theme.screen_header(
            self.container,
            record.class_name,
            subtitle=(
                f"{record.student_count} Students • "
                f"{record.total_photo_count} Photos • "
                f"{record.completed_student_count} Completed"
            ),
            on_back=self.on_back
        )

    def create_add_student_button(self):

        theme.primary_button(
            self.header,
            "+  Add Student",
            self.open_add_student_dialog,
            width=150,
            height=38
        ).pack(side="right")

    # -----------------------------------------
    # STUDENT LIST
    # -----------------------------------------

    def configure_columns(self, frame):
        """Same column geometry for the header row and every student row."""

        frame.grid_columnconfigure(0, weight=1, minsize=140)
        frame.grid_columnconfigure(1, weight=0, minsize=COL_AVG)
        frame.grid_columnconfigure(2, weight=0, minsize=COL_PHOTOS)
        frame.grid_columnconfigure(3, weight=0, minsize=COL_GRADED)
        frame.grid_columnconfigure(4, weight=0, minsize=COL_ACTIONS)

    def create_student_list(self):

        card = theme.card(self.container)

        card.pack(
            fill="both",
            expand=True
        )

        if not self.class_record.students:

            theme.label(
                card,
                "No students yet",
                size=16,
                weight="bold"
            ).pack(pady=(60, 4))

            theme.muted(
                card,
                "Use “Add Student” to add the first one.",
                size=13
            ).pack()

            return

        header_row = ctk.CTkFrame(card, fg_color="transparent")

        header_row.pack(
            fill="x",
            padx=28,
            pady=(16, 4)
        )

        self.configure_columns(header_row)

        for column, (text, anchor) in enumerate(
            [("STUDENT", "w"), ("AVG TOTAL", "w"), ("PHOTOS", "w"), ("GRADED", "w")]
        ):
            theme.label(
                header_row,
                text,
                size=11,
                weight="bold",
                color=theme.TEXT_FAINT,
                anchor=anchor
            ).grid(
                row=0,
                column=column,
                sticky="w",
                padx=(0, 6)
            )

        self.student_list_frame = ctk.CTkScrollableFrame(
            card,
            fg_color="transparent"
        )

        self.student_list_frame.pack(
            fill="both",
            expand=True,
            padx=14,
            pady=(0, 14)
        )

        for index, student in enumerate(self.class_record.students):
            self.create_student_row(index, student)

    def create_student_row(self, index, student):

        row = ctk.CTkFrame(
            self.student_list_frame,
            fg_color=theme.SURFACE_ALT,
            corner_radius=10
        )

        row.pack(
            fill="x",
            pady=3
        )

        inner = ctk.CTkFrame(row, fg_color="transparent")

        inner.pack(
            fill="x",
            padx=14,
            pady=10
        )

        self.configure_columns(inner)

        name_label = theme.label(
            inner,
            student.name,
            size=14,
            weight="bold",
            color=theme.TEXT,
            anchor="w",
            cursor="hand2"
        )

        name_label.grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 6)
        )

        theme.make_clickable(
            [name_label],
            lambda i=index: self.on_open_student(self.class_record, i),
            target=row
        )

        # Avg Total Score, from the same per-photo total_score data
        # that powers the Student DataFrame -- no second calculation.
        avg_score = student.average_total_score

        if math.isnan(avg_score):
            avg_pill = theme.pill(inner, "—", theme.TEXT_MUTED)
        else:
            avg_pill = theme.pill(inner, f"{avg_score:g}", theme.ACCENT)

        avg_pill.grid(
            row=0,
            column=1,
            sticky="w"
        )

        theme.muted(
            inner,
            str(student.photo_count),
            size=13
        ).grid(
            row=0,
            column=2,
            sticky="w"
        )

        # Grading progress for this student: photos with a Total
        # Score out of photos in the class record.
        total = len(student.photos)
        graded = sum(1 for photo in student.photos if photo.total_score is not None)

        progress_cell = ctk.CTkFrame(inner, fg_color="transparent")

        progress_cell.grid(
            row=0,
            column=3,
            sticky="w"
        )

        if total:
            theme.progress_bar(
                progress_cell,
                graded / total,
                width=70,
                color=theme.SUCCESS if graded == total else theme.ACCENT
            ).pack(side="left")

            theme.muted(
                progress_cell,
                f"{graded}/{total}",
                size=12
            ).pack(
                side="left",
                padx=(8, 0)
            )
        else:
            theme.muted(progress_cell, "—", size=13).pack(side="left")

        actions = ctk.CTkFrame(inner, fg_color="transparent")

        actions.grid(
            row=0,
            column=4,
            sticky="e"
        )

        theme.secondary_button(
            actions,
            "Start Grading",
            lambda i=index: self.handle_start_grading(i),
            width=112,
            height=30
        ).pack(side="left")

        theme.ghost_button(
            actions,
            "+ Folder",
            lambda i=index: self.handle_add_photos_folder(i),
            width=68
        ).pack(
            side="left",
            padx=(6, 0)
        )

        theme.ghost_button(
            actions,
            "+ Files",
            lambda i=index: self.handle_add_photos_files(i),
            width=62
        ).pack(
            side="left",
            padx=(2, 0)
        )

        theme.danger_button(
            actions,
            "Remove",
            lambda i=index: self.handle_delete_student(i),
            width=64
        ).pack(
            side="left",
            padx=(2, 0)
        )

    # -----------------------------------------
    # START GRADING
    # -----------------------------------------

    def handle_start_grading(self, index):
        self.on_start_grading(self.class_record, index)

    # -----------------------------------------
    # ADD PHOTOS
    # -----------------------------------------

    def handle_add_photos_folder(self, index):

        folder_path = filedialog.askdirectory(
            title="Select a photo folder"
        )

        if not folder_path:
            return

        try:
            image_paths = scan_student_folder(folder_path)
        except FolderValidationError as error:
            show_error(self.container, str(error))
            return

        self.on_add_photos(
            self.class_record,
            index,
            image_paths,
            folder_path
        )

    def handle_add_photos_files(self, index):

        file_paths = filedialog.askopenfilenames(
            title="Select photo file(s)"
        )

        if not file_paths:
            return

        try:
            image_paths = validate_selected_files(file_paths)
        except FolderValidationError as error:
            show_error(self.container, str(error))
            return

        self.on_add_photos(
            self.class_record,
            index,
            image_paths,
            None
        )

    # -----------------------------------------
    # DELETE STUDENT
    # -----------------------------------------

    def handle_delete_student(self, index):

        student = self.class_record.students[index]

        show_confirm(
            self.container,
            f'Are you sure you want to remove "{student.name}"?',
            on_yes=lambda: self.on_delete_student(self.class_record, index)
        )

    # -----------------------------------------
    # ADD NEW STUDENT
    # -----------------------------------------

    def open_add_student_dialog(self):

        dialog = create_modal(
            self.container,
            "Add New Student",
            480,
            430,
            accent=theme.ACCENT
        )

        theme.label(
            dialog,
            "Add new student",
            size=18,
            weight="bold"
        ).pack(
            anchor="w",
            padx=26,
            pady=(22, 16)
        )

        theme.label(
            dialog,
            "Student name",
            size=12,
            weight="bold",
            color=theme.TEXT_MUTED
        ).pack(
            anchor="w",
            padx=26
        )

        name_entry = theme.text_entry(
            dialog,
            placeholder_text="Enter student name"
        )

        name_entry.pack(
            fill="x",
            padx=26,
            pady=(6, 16)
        )

        theme.label(
            dialog,
            "Photos",
            size=12,
            weight="bold",
            color=theme.TEXT_MUTED
        ).pack(
            anchor="w",
            padx=26
        )

        selected = {"image_paths": None, "folder_path": None}

        status_label = theme.label(
            dialog,
            "No photos selected",
            size=13,
            color=theme.TEXT_MUTED,
            anchor="w",
            wraplength=400,
            justify="left"
        )

        def select_folder():

            folder_path = filedialog.askdirectory(
                title="Select a photo folder"
            )

            if not folder_path:
                return

            try:
                image_paths = scan_student_folder(folder_path)
            except FolderValidationError as error:
                status_label.configure(
                    text=f"⚠ {error}",
                    text_color=theme.DANGER
                )
                return

            selected["image_paths"] = image_paths
            selected["folder_path"] = folder_path

            status_label.configure(
                text=f"✓ {len(image_paths)} image(s) from folder",
                text_color=theme.SUCCESS
            )

        def select_files():

            file_paths = filedialog.askopenfilenames(
                title="Select photo file(s)"
            )

            if not file_paths:
                return

            try:
                image_paths = validate_selected_files(file_paths)
            except FolderValidationError as error:
                status_label.configure(
                    text=f"⚠ {error}",
                    text_color=theme.DANGER
                )
                return

            selected["image_paths"] = image_paths
            selected["folder_path"] = None

            status_label.configure(
                text=f"✓ {len(image_paths)} image(s) selected",
                text_color=theme.SUCCESS
            )

        button_frame = ctk.CTkFrame(
            dialog,
            fg_color="transparent"
        )

        button_frame.pack(
            anchor="w",
            padx=26,
            pady=(6, 8)
        )

        theme.secondary_button(
            button_frame,
            "Select Folder",
            select_folder,
            width=140,
            height=36
        ).pack(
            side="left",
            padx=(0, 10)
        )

        theme.secondary_button(
            button_frame,
            "Select Files",
            select_files,
            width=140,
            height=36
        ).pack(side="left")

        status_label.pack(
            anchor="w",
            padx=26,
            pady=(0, 6)
        )

        error_label = theme.error_label(dialog)

        error_label.pack(
            anchor="w",
            padx=26
        )

        def handle_add():

            name = name_entry.get().strip()
            image_paths = selected["image_paths"]

            if not name:
                error_label.configure(text="Please enter a student name.")
                return

            if not image_paths:
                error_label.configure(text="Please select a photo folder or file(s).")
                return

            dialog.destroy()

            self.on_add_student(
                self.class_record,
                name,
                image_paths,
                selected["folder_path"]
            )

        button_row = ctk.CTkFrame(
            dialog,
            fg_color="transparent"
        )

        button_row.pack(pady=(14, 0))

        theme.secondary_button(
            button_row,
            "Cancel",
            dialog.destroy,
            width=110,
            height=38
        ).pack(
            side="left",
            padx=8
        )

        theme.primary_button(
            button_row,
            "Add Student",
            handle_add,
            width=140,
            height=38
        ).pack(
            side="left",
            padx=8
        )

        name_entry.bind("<Return>", lambda event: handle_add())

        dialog.after(200, name_entry.focus)

import math

import customtkinter as ctk
from tkinter import filedialog

from ..core.image import scan_student_folder, validate_selected_files, FolderValidationError
from .widgets import show_error, show_confirm


class ClassScreen:
    """
    The Class Screen (spec sections 8, 9, 11, 12, 14, 15): shows one
    persisted class's students with their photo counts and average
    Total Score, and lets the professor add photos (folder or
    individual files), add a new student, or delete a student.

    Takes a parent frame and a core.class_model.ClassRecord, and
    renders straight from it -- this screen never touches storage
    directly (spec section 17). Folder/file picking + scanning
    happens here (the same way student_setup.py already does it --
    spec section 13, no parallel logic), but every resulting change
    is handed back to App through a callback, which persists it via
    storage.class_storage and re-renders this screen with the fresh
    ClassRecord:

        ClassScreen  ->  App  ->  class_storage  ->  classes/<id>/class.json

    `confirm_delete` (Settings: "Confirm before deleting") controls
    whether removing a student asks Yes/No first.

    New feature: Student Search. A search field above the student
    list filters the rows by student name as the professor types
    (case-insensitive). It only changes which rows are displayed --
    class_record.students is never modified, and every row keeps its
    real index in that list, so open/delete/add-photos/start-grading
    always act on the right student even while a filter is active.
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
        confirm_delete=True,
    ):

        self.class_record = class_record
        self.on_back = on_back
        self.on_open_student = on_open_student
        self.on_add_student = on_add_student
        self.on_add_photos = on_add_photos
        self.on_delete_student = on_delete_student
        self.on_start_grading = on_start_grading
        self.confirm_delete = confirm_delete

        # Widgets currently shown inside the student list (student
        # rows or an empty-state message), so a re-render can remove
        # exactly those and nothing else.
        self.row_widgets = []

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

        self.create_header()
        self.create_student_list()
        self.create_add_student_button()

    # -----------------------------------------
    # HEADER
    # -----------------------------------------

    def create_header(self):

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
            command=self.on_back
        ).pack(
            side="left",
            padx=(0, 15)
        )

        ctk.CTkLabel(
            header,
            text=self.class_record.class_name,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#7CFFB2"
        ).pack(side="left")

    # -----------------------------------------
    # STUDENT LIST
    # -----------------------------------------

    def create_student_list(self):

        card = ctk.CTkFrame(
            self.container,
            corner_radius=12
        )

        card.pack(
            fill="both",
            expand=True,
            pady=(0, 20)
        )

        ctk.CTkLabel(
            card,
            text="Students",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#7CFFB2"
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        # Student search (new feature). Packed before the list so it
        # sits above it. Every key release re-filters the list.
        self.student_search_entry = ctk.CTkEntry(
            card,
            placeholder_text="Search students..."
        )

        self.student_search_entry.pack(
            fill="x",
            padx=20,
            pady=(0, 10)
        )

        self.student_search_entry.bind(
            "<KeyRelease>",
            lambda event: self.render_student_list()
        )

        self.student_list_frame = ctk.CTkScrollableFrame(
            card,
            fg_color="transparent"
        )

        self.student_list_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 15)
        )

        self.render_student_list()

    def render_student_list(self):
        """
        (Re)builds the student rows from class_record.students,
        showing only students whose name contains the search text
        (case-insensitive). An empty search shows every student, in
        the original order. Never modifies class_record.students.

        Each row is created with the student's index in the *full*
        list (not its position among the filtered rows), because
        every row callback uses that index to find the student in
        class_record.students.
        """

        for widget in self.row_widgets:
            widget.destroy()

        self.row_widgets = []

        if not self.class_record.students:
            self.show_empty_message("No students yet.")
            return

        query = self.student_search_entry.get().strip().lower()

        matches = [
            (index, student)
            for index, student in enumerate(self.class_record.students)
            if query in student.name.lower()
        ]

        if not matches:
            self.show_empty_message("No matching students.")
            return

        for index, student in matches:
            self.create_student_row(index, student)

    def show_empty_message(self, text):

        label = ctk.CTkLabel(
            self.student_list_frame,
            text=text,
            text_color="gray60"
        )

        label.pack(pady=20)

        self.row_widgets.append(label)

    def create_student_row(self, index, student):

        row = ctk.CTkFrame(
            self.student_list_frame,
            fg_color="transparent"
        )

        row.pack(
            fill="x",
            pady=4
        )

        self.row_widgets.append(row)

        name_label = ctk.CTkLabel(
            row,
            text=student.name,
            anchor="w",
            width=140,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#7CFFB2",
            cursor="hand2"
        )

        name_label.pack(
            side="left",
            padx=(10, 10)
        )

        name_label.bind(
            "<Button-1>",
            lambda event, i=index: self.on_open_student(self.class_record, i)
        )

        # New feature: Avg Total Score, sourced from the same
        # per-photo total_score data that powers the Student
        # DataFrame -- no second calculation.
        avg_score = student.average_total_score
        avg_text = "NaN" if math.isnan(avg_score) else f"{avg_score:g}"

        ctk.CTkLabel(
            row,
            text=f"Avg Total: {avg_text}",
            text_color="gray60",
            width=140,
            anchor="w"
        ).pack(
            side="left",
            padx=(0, 10)
        )

        ctk.CTkLabel(
            row,
            text=f"{student.photo_count} photos",
            text_color="gray60"
        ).pack(
            side="left",
            fill="x",
            expand=True
        )

        ctk.CTkButton(
            row,
            text="🗑",
            width=32,
            height=28,
            fg_color="transparent",
            hover_color="#3a1f1f",
            text_color="#FF6B6B",
            command=lambda i=index: self.handle_delete_student(i)
        ).pack(side="right")

        ctk.CTkButton(
            row,
            text="📁+",
            width=40,
            height=28,
            fg_color="transparent",
            hover_color="#123f2c",
            border_color="#2ECC71",
            border_width=1,
            text_color="#7CFFB2",
            command=lambda i=index: self.handle_add_photos_folder(i)
        ).pack(
            side="right",
            padx=(0, 8)
        )

        ctk.CTkButton(
            row,
            text="🖼+",
            width=40,
            height=28,
            fg_color="transparent",
            hover_color="#123f2c",
            border_color="#2ECC71",
            border_width=1,
            text_color="#7CFFB2",
            command=lambda i=index: self.handle_add_photos_files(i)
        ).pack(
            side="right",
            padx=(0, 8)
        )

        ctk.CTkButton(
            row,
            text="Start Grading",
            width=110,
            height=28,
            fg_color="transparent",
            hover_color="#123f2c",
            border_color="#2ECC71",
            border_width=1,
            text_color="#7CFFB2",
            command=lambda i=index: self.handle_start_grading(i)
        ).pack(
            side="right",
            padx=(0, 8)
        )

    # -----------------------------------------
    # START GRADING (new feature -- inactive for now: the student
    # is added to the class, but running them through the Rule
    # Engine / Teacher Grading review flow is a later feature)
    # -----------------------------------------

    def handle_start_grading(self, index):
        self.on_start_grading(self.class_record, index)

    # -----------------------------------------
    # ADD PHOTOS (spec section 14, extended with file selection)
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
    # DELETE STUDENT (spec section 15)
    # -----------------------------------------

    def handle_delete_student(self, index):

        # "Confirm before deleting" off in Settings -> delete right
        # away, same as before confirmations existed.
        if not self.confirm_delete:
            self.on_delete_student(self.class_record, index)
            return

        student = self.class_record.students[index]

        show_confirm(
            self.container,
            f'Are you sure you want to remove "{student.name}"?',
            on_yes=lambda: self.on_delete_student(self.class_record, index)
        )

    # -----------------------------------------
    # ADD NEW STUDENT (spec section 12, extended with file selection)
    # -----------------------------------------

    def create_add_student_button(self):

        ctk.CTkButton(
            self.container,
            text="+ Add New Student",
            width=200,
            height=40,
            fg_color="#1F8F4C",
            hover_color="#27AE60",
            command=self.open_add_student_dialog
        ).pack(anchor="w")

    def open_add_student_dialog(self):

        dialog = ctk.CTkToplevel(self.container)

        dialog.title("Add New Student")
        dialog.geometry("440x360")
        dialog.resizable(False, False)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Add New Student",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#7CFFB2"
        ).pack(pady=(20, 15))

        ctk.CTkLabel(
            dialog,
            text="Student Name",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(
            anchor="w",
            padx=20
        )

        name_entry = ctk.CTkEntry(
            dialog,
            placeholder_text="Enter student name"
        )

        name_entry.pack(
            fill="x",
            padx=20,
            pady=(5, 15)
        )

        ctk.CTkLabel(
            dialog,
            text="Photos",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(
            anchor="w",
            padx=20
        )

        selected = {"image_paths": None, "folder_path": None}

        status_label = ctk.CTkLabel(
            dialog,
            text="No photos selected",
            text_color="gray60"
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
                    text=f"⚠️ {error}",
                    text_color="#FF6B6B"
                )
                return

            selected["image_paths"] = image_paths
            selected["folder_path"] = folder_path

            status_label.configure(
                text=f"✅ {len(image_paths)} image(s) from folder",
                text_color="#7CFFB2"
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
                    text=f"⚠️ {error}",
                    text_color="#FF6B6B"
                )
                return

            selected["image_paths"] = image_paths
            selected["folder_path"] = None

            status_label.configure(
                text=f"✅ {len(image_paths)} image(s) selected",
                text_color="#7CFFB2"
            )

        button_frame = ctk.CTkFrame(
            dialog,
            fg_color="transparent"
        )

        button_frame.pack(
            anchor="w",
            padx=20,
            pady=(5, 5)
        )

        ctk.CTkButton(
            button_frame,
            text="Select Folder",
            width=130,
            command=select_folder
        ).pack(
            side="left",
            padx=(0, 10)
        )

        ctk.CTkButton(
            button_frame,
            text="Select Files",
            width=130,
            command=select_files
        ).pack(side="left")

        status_label.pack(
            anchor="w",
            padx=20,
            pady=(0, 10)
        )

        error_label = ctk.CTkLabel(
            dialog,
            text="",
            text_color="#FF6B6B"
        )

        error_label.pack(
            anchor="w",
            padx=20
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

        button_row.pack(pady=(15, 0))

        ctk.CTkButton(
            button_row,
            text="Cancel",
            width=100,
            fg_color="transparent",
            hover_color="#3a1f1f",
            border_color="#FF6B6B",
            border_width=1,
            text_color="#FF6B6B",
            command=dialog.destroy
        ).pack(
            side="left",
            padx=10
        )

        ctk.CTkButton(
            button_row,
            text="Add Student",
            width=140,
            fg_color="#1F8F4C",
            hover_color="#27AE60",
            command=handle_add
        ).pack(
            side="left",
            padx=10
        )
import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path

from ..core.image import scan_student_folder, validate_selected_files, FolderValidationError
from ..core.student import Student, ImageRecord
from . import theme


class StudentFoldersScreen:
    """
    Setup step 3. Takes a parent frame and an on_continue callback,
    the same pattern as RuleEngineScreen/HomeScreen.

    For each student, the professor picks a folder OR one/more
    individual image files. Every valid image is discovered and
    validated against the same limits (max images / max total size)
    before the professor can continue -- a bad selection shows its
    error right on that student's row instead of crashing or silently
    dropping images.

    Calls `on_continue(students)` with a list of fully-populated
    core.student.Student objects -- each with its `images` list
    already built as one ImageRecord per discovered photo.
    """

    def __init__(self, parent, students, on_continue):

        self.on_continue = on_continue

        # One Student per name from the previous (names) screen.
        # folder_path/images get filled in as folders/files are picked.
        self.class_students = [
            Student(name=entry["name"])
            for entry in students
        ]

        self.container = theme.page(parent)

        theme.setup_steps(self.container, current=3)

        theme.screen_header(
            self.container,
            "Select photos for each student",
            subtitle="Pick a folder, or choose one or more image files, for every student."
        )

        # Footer first so the Start button never gets pushed off screen.
        footer = ctk.CTkFrame(self.container, fg_color="transparent")

        footer.pack(
            side="bottom",
            fill="x",
            pady=(12, 0)
        )

        self.error_label = theme.error_label(footer)

        self.error_label.pack(
            anchor="w",
            pady=(0, 6)
        )

        theme.primary_button(
            footer,
            "Start Review  →",
            self.handle_continue,
            width=180,
            height=42
        ).pack(anchor="w")

        self.scroll_frame = ctk.CTkScrollableFrame(
            self.container,
            fg_color="transparent"
        )

        self.scroll_frame.pack(
            fill="both",
            expand=True
        )

        self.status_labels = []

        self.create_student_rows()

    # -----------------------------------------
    # ROWS
    # -----------------------------------------

    def create_student_rows(self):

        for index, student in enumerate(self.class_students):

            row = theme.card(self.scroll_frame)

            row.pack(
                fill="x",
                pady=5,
                padx=(0, 6)
            )

            row.grid_columnconfigure(3, weight=1)

            theme.label(
                row,
                student.name,
                size=14,
                weight="bold",
                width=190,
                anchor="w"
            ).grid(
                row=0,
                column=0,
                padx=(18, 10),
                pady=14,
                sticky="w"
            )

            theme.secondary_button(
                row,
                "Select Folder",
                lambda i=index: self.select_folder(i),
                width=120,
                height=34
            ).grid(
                row=0,
                column=1,
                padx=(0, 8)
            )

            theme.secondary_button(
                row,
                "Select Files",
                lambda i=index: self.select_files(i),
                width=120,
                height=34
            ).grid(
                row=0,
                column=2,
                padx=(0, 14)
            )

            status_label = theme.label(
                row,
                "No photos selected",
                size=13,
                color=theme.TEXT_FAINT,
                anchor="w",
                justify="left",
                wraplength=360
            )

            status_label.grid(
                row=0,
                column=3,
                sticky="w",
                padx=(0, 16)
            )

            self.status_labels.append(status_label)

    # -----------------------------------------
    # FOLDER SELECTION
    # -----------------------------------------

    def select_folder(self, index):

        folder_path = filedialog.askdirectory(
            title="Select a photo folder"
        )

        if not folder_path:
            return

        student = self.class_students[index]
        status_label = self.status_labels[index]

        try:
            image_paths = scan_student_folder(folder_path)

        except FolderValidationError as error:

            student.folder_path = None
            student.images = []

            status_label.configure(
                text=f"⚠ {error}",
                text_color=theme.DANGER
            )

            return

        student.folder_path = Path(folder_path)

        student.images = [
            ImageRecord(
                student_name=student.name,
                image_path=image_path
            )
            for image_path in image_paths
        ]

        status_label.configure(
            text=f"✓ {len(image_paths)} image(s) found",
            text_color=theme.SUCCESS
        )

    # -----------------------------------------
    # FILE SELECTION
    # -----------------------------------------

    def select_files(self, index):

        file_paths = filedialog.askopenfilenames(
            title="Select photo file(s)"
        )

        if not file_paths:
            return

        student = self.class_students[index]
        status_label = self.status_labels[index]

        try:
            image_paths = validate_selected_files(file_paths)

        except FolderValidationError as error:

            student.folder_path = None
            student.images = []

            status_label.configure(
                text=f"⚠ {error}",
                text_color=theme.DANGER
            )

            return

        # No single common folder for individually-selected files.
        student.folder_path = None

        student.images = [
            ImageRecord(
                student_name=student.name,
                image_path=image_path
            )
            for image_path in image_paths
        ]

        status_label.configure(
            text=f"✓ {len(image_paths)} image(s) selected",
            text_color=theme.SUCCESS
        )

    # -----------------------------------------
    # VALIDATION / SUBMIT
    # -----------------------------------------

    def handle_continue(self):

        self.error_label.configure(text="")

        if any(not student.images for student in self.class_students):
            self.error_label.configure(
                text="Please select photos (folder or files) for every student."
            )
            return

        self.on_continue(self.class_students)

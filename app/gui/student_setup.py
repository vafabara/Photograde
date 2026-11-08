import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path

from ..core.image import (
    MAX_IMAGES_PER_STUDENT,
    FolderValidationError,
    merge_student_photos,
    scan_student_folder,
    validate_selected_files,
)
from ..core.clipboard import ClipboardError
from ..core.student import Student, ImageRecord
from ..storage.pasted_images import paste_from_clipboard
from . import theme
from .paste import PasteShortcut


class StudentFoldersScreen:
    """
    Setup step 3. Takes a parent frame and an on_continue callback,
    the same pattern as RuleEngineScreen/HomeScreen.

    For each student, the professor picks a folder and/or one or more
    individual image files, as many times as they like. Every
    selection is ADDED to what the student already has -- it never
    replaces it -- and is validated against the same limits (max
    photos per student / max total size) and checked for duplicates
    (core.image.merge_student_photos). A bad selection shows its
    error right on that student's row and leaves their existing
    photos untouched. "Clear" empties one student's photos.

    "Paste" (or Ctrl+V) adds an image from the clipboard to the
    highlighted student -- the last one whose row was used or
    clicked (see core.clipboard / storage.pasted_images). Like
    storage.export for the Results screen, saving the pasted image
    is the one storage call this screen makes itself.

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
            subtitle=(
                f"Add up to {MAX_IMAGES_PER_STUDENT} photos per student: pick a folder or "
                "choose image files or paste with Ctrl+V. You can add photos "
                "in several steps."
            )
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
        self.name_labels = []

        # The student Ctrl+V pastes into: the last row that was used
        # or clicked (highlighted). With a single student there is no
        # ambiguity, so that student is the target from the start.
        self.active_index = 0 if len(self.class_students) == 1 else None

        self.create_student_rows()

        self.set_active(self.active_index)

        self.paste_shortcut = PasteShortcut(self.container, self.handle_paste_shortcut)

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

            row.grid_columnconfigure(4, weight=1)

            name_label = theme.label(
                row,
                student.name,
                size=14,
                weight="bold",
                width=190,
                anchor="w"
            )

            name_label.grid(
                row=0,
                column=0,
                padx=(18, 10),
                pady=14,
                sticky="w"
            )

            self.name_labels.append(name_label)

            # Clicking the row (or the name) makes it the Ctrl+V target.
            for clickable in (row, name_label):
                clickable.bind(
                    "<Button-1>",
                    lambda event, i=index: self.set_active(i)
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
                padx=(0, 8)
            )

            theme.secondary_button(
                row,
                "Paste",
                lambda i=index: self.paste_photos(i),
                width=80,
                height=34
            ).grid(
                row=0,
                column=3,
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
                column=4,
                sticky="w",
                padx=(0, 16)
            )

            self.status_labels.append(status_label)

            theme.ghost_button(
                row,
                "Clear",
                lambda i=index: self.clear_photos(i),
                width=56
            ).grid(
                row=0,
                column=5,
                padx=(0, 14)
            )

    # -----------------------------------------
    # ADDING PHOTOS
    # -----------------------------------------

    def select_folder(self, index):

        self.set_active(index)

        folder_path = filedialog.askdirectory(
            title="Select a photo folder"
        )

        if not folder_path:
            return

        try:
            image_paths = scan_student_folder(folder_path)

        except FolderValidationError as error:
            self.show_rejected(index, error)
            return

        self.add_photos(index, image_paths, Path(folder_path))

    def select_files(self, index):

        self.set_active(index)

        file_paths = filedialog.askopenfilenames(
            title="Select photo file(s)"
        )

        if not file_paths:
            return

        try:
            image_paths = validate_selected_files(file_paths)

        except FolderValidationError as error:
            self.show_rejected(index, error)
            return

        self.add_photos(index, image_paths, None)

    def add_photos(self, index, image_paths, folder_path):
        """
        Adds already-validated `image_paths` to this student's photos
        (after the duplicate / limit check). `folder_path` is set only
        when they came from a folder; adding individual files leaves
        the student's folder as it was.
        """

        student = self.class_students[index]

        try:
            to_add, duplicates = merge_student_photos(
                [record.image_path for record in student.images],
                image_paths
            )

        except FolderValidationError as error:
            self.show_rejected(index, error)
            return

        student.images += [
            ImageRecord(
                student_name=student.name,
                image_path=image_path
            )
            for image_path in to_add
        ]

        if folder_path is not None:
            student.folder_path = folder_path

        self.show_status(index, added=len(to_add), duplicates=len(duplicates))

    def set_active(self, index):
        """Highlights the Ctrl+V target row (None = no target yet)."""

        self.active_index = index

        for position, name_label in enumerate(self.name_labels):
            name_label.configure(
                text_color=theme.ACCENT if position == index else theme.TEXT
            )

    def paste_photos(self, index, in_text_input=False):
        """
        Adds the clipboard's image (or copied image files) to this
        student. A clipboard with something else in it is reported on
        the row -- except when the focus is in a text field, where
        Ctrl+V is just a normal text paste.
        """

        self.set_active(index)

        student = self.class_students[index]

        try:
            paths = paste_from_clipboard(student.name, len(student.images))

        except (ClipboardError, FolderValidationError) as error:
            self.show_rejected(index, error)
            return

        if paths is None:

            if not in_text_input:
                self.show_rejected(
                    index,
                    "The clipboard does not contain an image. Copy an "
                    "image first, then paste."
                )

            return

        self.add_photos(index, paths, None)

    def handle_paste_shortcut(self, in_text_input):

        if self.active_index is None:

            if not in_text_input:
                self.error_label.configure(
                    text="Click a student's row (or its Paste button) first, "
                         "then press Ctrl+V."
                )

            return

        self.error_label.configure(text="")

        self.paste_photos(self.active_index, in_text_input)

    def clear_photos(self, index):

        self.set_active(index)

        student = self.class_students[index]

        student.images = []
        student.folder_path = None

        self.status_labels[index].configure(
            text="No photos selected",
            text_color=theme.TEXT_FAINT
        )

    def show_status(self, index, added=0, duplicates=0):

        total = len(self.class_students[index].images)

        text = f"✓ {total} of {MAX_IMAGES_PER_STUDENT} photos"

        if added:
            text += f"  (+{added} added)"

        if duplicates:
            text += f"  •  {duplicates} duplicate(s) skipped"

        self.status_labels[index].configure(
            text=text,
            text_color=theme.SUCCESS
        )

    def show_rejected(self, index, error):
        """
        A selection was refused. The student's existing photos are
        kept -- the message just says why nothing was added.
        """

        kept = len(self.class_students[index].images)

        text = f"⚠ {error}"

        if kept:
            text += f"  ({kept} photo(s) kept.)"

        self.status_labels[index].configure(
            text=text,
            text_color=theme.DANGER
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

import customtkinter as ctk
from tkinter import filedialog
from tkinterdnd2 import TkinterDnD
from tkinter import TclError

from pathlib import Path
from PIL import UnidentifiedImageError

from ..core.image import load_image
from ..core.converters import exif_value
from ..core.scoring import grade_student
from ..core.student import ImageRecord
from ..core.rules import RuleEngineConfig
from ..core.class_model import (
    build_class_record,
    validate_new_student_name,
    image_records_from_student,
    ClassError,
    ClassStudentEntry,
    ClassPhotoEntry,
)
from ..storage.class_storage import save_class, load_all_classes, load_class, delete_class
from ..storage.rule_presets import load_presets, save_preset
from ..storage.settings_storage import (
    SettingsStorageError,
    load_settings,
    save_settings,
)

from . import theme
from .class_screen import ClassScreen
from .help import HelpScreen
from .home_screen import HomeScreen
from .image_viewer import ImageViewer
from .metadata_panel import MetadataPanel
from .results_screen import ClassResultsScreen
from .rule_engine import RuleEngineScreen
from .settings_screen import SettingsScreen
from .student_detail import StudentDetailScreen
from .student_results_detail import StudentResultsDetailScreen
from .student_setup import StudentFoldersScreen
from .widgets import show_error


class App(ctk.CTk, TkinterDnD.DnDWrapper):

    def __init__(self):
        theme.apply_theme()

        super().__init__()

        self.TkdndVersion = TkinterDnD._require(self)

        self.title("PhotoGrade")
        self.geometry("1180x760")
        self.minsize(980, 640)

        self.configure(fg_color=theme.BG)

        # Current image
        self.current_image = None
        self.current_data = None

        # Class / student workflow
        self.class_name = None
        self.student_count = 0
        self.students = []

        # Populated once folders/files are selected (student_setup.py):
        # one core.student.Student per name, each with its own
        # core.student.ImageRecord list. image_records is the same
        # ImageRecords flattened into the single ordered sequence
        # the review flow steps through.
        self.class_students = []
        self.image_records = []
        self.current_image_index = 0

        # The persisted ClassRecord created for the class currently
        # being reviewed (per-photo scores/notes are written back into
        # this and saved as they're confirmed).
        self.class_record = None

        # Rule Engine
        self.rule_config = None

        # Main frame
        self.main_frame = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=theme.BG
        )

        self.main_frame.pack(
            fill="both",
            expand=True
        )

        self.show_setup_count_screen()

    # -----------------------------------------
    # HELPERS
    # -----------------------------------------

    def clear_main_frame(self):

        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def find_photo_entry(self, image_record):
        """
        Locate the core.class_model.ClassPhotoEntry that corresponds
        to `image_record` inside self.class_record, by matching
        image path. Returns None if there's no class currently being
        reviewed, or no matching photo (e.g. Open Image / drag & drop
        outside the review flow).
        """

        if self.class_record is None:
            return None

        target_path = str(image_record.image_path)

        for student in self.class_record.students:
            for photo in student.photos:
                if photo.path == target_path:
                    return photo

        return None

    # -----------------------------------------
    # SETUP STEP 1 — HOME PAGE
    # -----------------------------------------

    def show_setup_count_screen(self):
        """
        Home page: Previous Classes (backed by real, persisted
        classes) + New Class form. Kept under the original method
        name so nothing else in the app has to change how it starts
        the setup flow or returns to Home.
        """

        self.clear_main_frame()

        classes = load_all_classes()

        HomeScreen(
            self.main_frame,
            classes=classes,
            on_continue=self.on_home_continue,
            on_open_class=self.on_open_class,
            on_delete_class=self.on_delete_class,
            on_settings=self.show_settings_screen,
            on_help=self.show_help_screen
        )

    def show_settings_screen(self):
        """
        Settings page, opened from the Home Screen. Settings are
        loaded fresh from storage each time it opens; Back returns to
        Home through show_setup_count_screen like every other screen.
        """

        self.clear_main_frame()

        SettingsScreen(
            self.main_frame,
            settings=load_settings(),
            on_save=self.on_save_settings,
            on_back=self.show_setup_count_screen
        )

    def on_save_settings(self, settings):
        """
        Called by SettingsScreen with fully validated AppSettings.
        Persists them; returns False (after showing the error) if
        saving failed, so the screen doesn't report success.
        """

        try:
            save_settings(settings)
        except SettingsStorageError as error:
            show_error(self, str(error))
            return False

        return True

    def show_help_screen(self):
        """
        How to Use page, opened from the Home Screen. Static content;
        Back returns to Home through show_setup_count_screen.
        """

        self.clear_main_frame()

        HelpScreen(
            self.main_frame,
            on_back=self.show_setup_count_screen
        )

    def on_home_continue(self, class_name, student_count):
        """
        Called by HomeScreen once the New Class form validates.
        Stores class_name for later use and continues the existing
        student-count workflow unchanged.
        """

        self.class_name = class_name
        self.student_count = student_count

        self.show_setup_names_screen()

    # -----------------------------------------
    # SETUP STEP 2
    # -----------------------------------------

    def show_setup_names_screen(self):

        self.clear_main_frame()

        container = theme.page(self.main_frame)

        theme.setup_steps(container, current=2)

        theme.screen_header(
            container,
            "Enter student names",
            subtitle=f"{self.class_name} • {self.student_count} students"
        )

        footer = ctk.CTkFrame(container, fg_color="transparent")

        footer.pack(
            side="bottom",
            fill="x",
            pady=(12, 0)
        )

        error_label = theme.error_label(footer)

        error_label.pack(
            anchor="w",
            pady=(0, 6)
        )

        scroll_frame = ctk.CTkScrollableFrame(
            container,
            fg_color="transparent"
        )

        scroll_frame.pack(
            fill="both",
            expand=True
        )

        name_entries = []

        for i in range(self.student_count):

            row = theme.card(scroll_frame)

            row.pack(
                fill="x",
                pady=4,
                padx=(0, 6)
            )

            theme.label(
                row,
                f"Student {i + 1}",
                size=13,
                color=theme.TEXT_MUTED,
                width=100,
                anchor="w"
            ).pack(
                side="left",
                padx=(18, 10),
                pady=10
            )

            entry = theme.text_entry(
                row,
                width=320,
                placeholder_text="Full name"
            )

            entry.pack(
                side="left",
                pady=10
            )

            name_entries.append(entry)

        def on_continue():

            names = [
                entry.get().strip()
                for entry in name_entries
            ]

            if any(not name for name in names):
                error_label.configure(
                    text="Please fill in a name for every student."
                )
                return

            self.students = [
                {"name": name}
                for name in names
            ]

            self.show_setup_photos_screen()

        theme.primary_button(
            footer,
            "Continue  →",
            on_continue,
            width=160,
            height=42
        ).pack(anchor="w")

        # Enter moves to the next name; Enter on the last one continues.
        for position, entry in enumerate(name_entries):

            if position + 1 < len(name_entries):
                entry.bind(
                    "<Return>",
                    lambda event, nxt=name_entries[position + 1]: nxt.focus()
                )
            else:
                entry.bind("<Return>", lambda event: on_continue())

        if name_entries:
            name_entries[0].focus()

    # -----------------------------------------
    # SETUP STEP 3 — SELECT FOLDER/FILES PER STUDENT
    # -----------------------------------------

    def show_setup_photos_screen(self):
        """
        Kept under the original method name so nothing else in the
        app has to change how it continues the setup flow. Delegates
        to StudentFoldersScreen (Select Folder or Select Files, one
        or more photos per student).
        """

        self.clear_main_frame()

        StudentFoldersScreen(
            self.main_frame,
            students=self.students,
            on_continue=self.on_folders_selected
        )

    def on_folders_selected(self, class_students):
        """
        Called by StudentFoldersScreen once every student has a
        valid photo selection. `class_students` is a list of
        core.student.Student, each already holding one ImageRecord
        per discovered photo.

        This is also the point where the Class actually gets created
        and persisted -- Rule Engine is NOT a condition for the class
        to exist. The resulting ClassRecord is kept on
        self.class_record so later Rule Engine / Teacher Grading
        confirmations and photo notes can be written back into it and
        saved.
        """

        self.class_students = class_students

        self.image_records = [
            image_record
            for student in class_students
            for image_record in student.images
        ]

        try:
            class_record = build_class_record(self.class_name, class_students)
        except ClassError as error:
            show_error(self, str(error))
            self.show_setup_names_screen()
            return

        save_class(class_record)
        self.class_record = class_record

        self.show_rule_engine_screen(
            on_continue=self.on_rules_configured,
            on_skip=self.on_rules_skipped,
            banner_text=f'Class "{class_record.class_name}" created'
        )

    # -----------------------------------------
    # RULE ENGINE
    # -----------------------------------------

    def show_rule_engine_screen(self, on_continue, on_skip, banner_text=None):
        """
        `on_continue`/`on_skip` are supplied by the caller rather
        than hard-coded so this one screen can serve two different
        flows without a second Rule Engine implementation: the
        initial class-creation flow (on_rules_configured /
        on_rules_skipped below) and "Start Grading" on a class that
        was never configured, which needs to route back into grading
        a specific student afterward instead of the usual full-queue
        review.

        Presets are loaded fresh from storage every time this screen
        opens. Saving a new preset re-opens this same screen (with
        the same on_continue/on_skip/banner_text it was already
        showing) so the preset list reflects the save immediately.
        """

        self.clear_main_frame()

        presets = load_presets()

        def handle_save_preset(name, config):
            save_preset(name, config)
            self.show_rule_engine_screen(on_continue, on_skip, banner_text)

        RuleEngineScreen(
            self.main_frame,
            on_continue=on_continue,
            on_skip=on_skip,
            on_save_preset=handle_save_preset,
            presets=presets,
            banner_text=banner_text
        )

    def on_rules_configured(self, config):
        """
        Applies the professor's System/Human score split to every
        photo in the review queue. The split itself always comes
        from `config` -- nothing here hard-codes a specific
        weighting -- so 40/60, 30/70, etc. all just work.

        Also persists `config` onto self.class_record (the class's
        active Rule Engine configuration) so reopening this class
        later -- to grade a student added afterward, or after an app
        restart -- knows which configuration to reuse instead of
        asking the professor to reconfigure from scratch.
        """

        self.rule_config = config

        for image_record in self.image_records:
            image_record.rule_engine_max_score = config.system_score
            image_record.teacher_max_score = config.human_score

        if self.class_record is not None:
            self.class_record.rule_config = config.to_dict()
            save_class(self.class_record)

        self.start_review()

    def on_rules_skipped(self):
        """
        Rule Engine Skip. The professor wants to grade entirely
        manually -- no Rule Engine grading runs at all
        (self.rule_config stays None, so load_and_display never
        calls grade_student), and every photo's Teacher Grading max
        becomes the full 100 points.

        Persisted as {"skipped": True} rather than a real
        RuleEngineConfig, since "no Rule Engine at all" isn't a
        config with zero rules -- it's a distinct choice that
        reopening this class must also remember and repeat, not
        re-ask for.
        """

        self.rule_config = None

        for image_record in self.image_records:
            image_record.teacher_max_score = 100

        if self.class_record is not None:
            self.class_record.rule_config = {"skipped": True}
            save_class(self.class_record)

        self.start_review()

    # -----------------------------------------
    # CLASS SCREEN / STUDENT DETAIL
    # -----------------------------------------

    def on_open_class(self, class_id):
        """
        Called by HomeScreen when a Previous Classes row is clicked.
        """

        self.open_class_screen(class_id)

    def open_class_screen(self, class_id):
        """
        Loads a ClassRecord fresh from storage and shows it -- every
        mutation (add/remove student, add photos) re-enters here
        instead of reusing an in-memory copy, so the screen always
        reflects what's actually on disk.
        """

        class_record = load_class(class_id)

        if class_record is None:
            show_error(self, "This class could not be found.")
            self.show_setup_count_screen()
            return

        self.show_class_screen(class_record)

    def show_class_screen(self, class_record):

        self.clear_main_frame()

        ClassScreen(
            self.main_frame,
            class_record=class_record,
            on_back=self.show_setup_count_screen,
            on_open_student=self.on_open_student,
            on_add_student=self.on_add_student_to_class,
            on_add_photos=self.on_add_photos_to_class,
            on_delete_student=self.on_delete_student_from_class,
            on_start_grading=self.on_start_grading
        )

    def on_delete_class(self, class_id):
        """
        Called by HomeScreen only after the professor confirms the
        Yes/No dialog. Deletes just this class's storage folder --
        never the student photo folders on disk -- then refreshes
        Home.
        """

        delete_class(class_id)
        self.show_setup_count_screen()

    def on_open_student(self, class_record, student_index):

        student = class_record.students[student_index]

        self.clear_main_frame()

        StudentDetailScreen(
            self.main_frame,
            student=student,
            on_back=lambda: self.open_class_screen(class_record.class_id)
        )

    def on_start_grading(self, class_record, student_index):
        """
        "Start Grading" next to a student in the Class Screen.
        Routes that student's already-persisted photos into the
        existing Rule Engine / Teacher Grading review flow via
        begin_grading()/begin_grading_skipped() below -- reusing this
        class's already-saved rule_config if there is one, or asking
        the professor to configure/skip the Rule Engine first (the
        exact same RuleEngineScreen used for a brand-new class) if
        this class has never been configured, including every class
        saved before rule_config existed.
        """

        self.class_record = class_record

        rule_config_data = class_record.rule_config

        if rule_config_data is None:
            self.show_rule_engine_screen(
                on_continue=lambda config: self.begin_grading(
                    class_record, student_index, config
                ),
                on_skip=lambda: self.begin_grading_skipped(
                    class_record, student_index
                ),
            )
            return

        if rule_config_data.get("skipped"):
            self.begin_grading_skipped(class_record, student_index)
            return

        config = RuleEngineConfig.from_dict(rule_config_data)
        self.begin_grading(class_record, student_index, config)

    def begin_grading(self, class_record, student_index, config):
        """
        Shared by on_start_grading (class already has a rule_config)
        and the Rule Engine screen's Continue button when a class
        had none yet. Persists `config` onto the class, rebuilds the
        runtime ImageRecords for this one student straight from
        their persisted ClassPhotoEntry data
        (core.class_model.image_records_from_student -- previously
        confirmed scores/notes come along with them), and hands them
        to the existing start_review() flow exactly the way a brand
        new class's photos already are.
        """

        class_record.rule_config = config.to_dict()
        save_class(class_record)

        student_entry = class_record.students[student_index]
        image_records = image_records_from_student(student_entry)

        for image_record in image_records:
            image_record.rule_engine_max_score = config.system_score
            image_record.teacher_max_score = config.human_score

        self.rule_config = config
        self.image_records = image_records

        self.start_review()

    def begin_grading_skipped(self, class_record, student_index):
        """
        Shared by on_start_grading (class was already configured to
        Skip) and the Rule Engine screen's Skip button when a class
        had no configuration yet. Same as begin_grading() above but
        for manual-only grading -- see on_rules_skipped for why this
        is stored as {"skipped": True} rather than a RuleEngineConfig.
        """

        class_record.rule_config = {"skipped": True}
        save_class(class_record)

        student_entry = class_record.students[student_index]
        image_records = image_records_from_student(student_entry)

        for image_record in image_records:
            image_record.teacher_max_score = 100

        self.rule_config = None
        self.image_records = image_records

        self.start_review()

    def on_add_student_to_class(self, class_record, name, image_paths, source_folder):
        """
        Called by ClassScreen's Add New Student dialog once photos
        have already been picked and validated (folder or individual
        files). Validates the name is non-blank and not a duplicate
        before persisting -- ClassScreen itself never writes storage.
        """

        try:
            name = validate_new_student_name(class_record, name)
        except ClassError as error:
            show_error(self, str(error))
            return

        class_record.students.append(
            ClassStudentEntry(
                name=name,
                folder_path=source_folder or "",
                photo_count=len(image_paths),
                photos=[
                    ClassPhotoEntry(path=str(path)) for path in image_paths
                ],
            )
        )

        save_class(class_record)
        self.open_class_screen(class_record.class_id)

    def on_add_photos_to_class(self, class_record, student_index, image_paths, source_folder):
        """
        Called by ClassScreen after new photos have been picked and
        validated for an existing student (folder or individual
        files). Selecting the exact same folder again re-scans it
        instead of doubling the count/photos, as a simple guard
        against double counting; individually-selected files always
        add to the existing set.
        """

        student = class_record.students[student_index]

        new_photos = [
            ClassPhotoEntry(path=str(path)) for path in image_paths
        ]

        if source_folder is not None and source_folder == student.folder_path:
            student.photo_count = len(image_paths)
            student.photos = new_photos
        else:
            student.photo_count += len(image_paths)
            student.photos += new_photos

            if source_folder is not None:
                student.folder_path = source_folder

        save_class(class_record)
        self.open_class_screen(class_record.class_id)

    def on_delete_student_from_class(self, class_record, student_index):
        """
        Called by ClassScreen only after the professor confirms the
        Yes/No dialog. Removes the student from the class only --
        never touches their photo folder on disk.
        """

        del class_record.students[student_index]

        save_class(class_record)
        self.open_class_screen(class_record.class_id)

    # -----------------------------------------
    # REVIEW
    # -----------------------------------------

    def start_review(self):

        self.current_image_index = 0

        self.clear_main_frame()

        self.create_student_bar()
        self.create_bottom_bar()
        self.create_content()

        self.load_current_image()

    def create_student_bar(self):
        """Top bar of the grading screen: who is being graded + progress."""

        self.student_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=theme.SURFACE,
            corner_radius=0,
            border_width=0
        )

        self.student_frame.pack(fill="x")

        inner = ctk.CTkFrame(self.student_frame, fg_color="transparent")

        inner.pack(
            fill="x",
            padx=28,
            pady=14
        )

        left = ctk.CTkFrame(inner, fg_color="transparent")

        left.pack(side="left")

        theme.label(
            left,
            "GRADING",
            size=11,
            weight="bold",
            color=theme.ACCENT,
            anchor="w"
        ).pack(anchor="w")

        self.student_label = theme.label(
            left,
            "—",
            size=20,
            weight="bold",
            anchor="w"
        )

        self.student_label.pack(anchor="w")

        right = ctk.CTkFrame(inner, fg_color="transparent")

        right.pack(side="right")

        self.progress_label = theme.muted(
            right,
            "",
            size=13,
            anchor="e"
        )

        self.progress_label.pack(anchor="e")

        self.progress_bar = theme.progress_bar(right, 0.0, width=220)

        self.progress_bar.pack(
            anchor="e",
            pady=(6, 0)
        )

        theme.divider(self.main_frame).pack(fill="x")

    def load_current_image(self):
        """
        Loads and displays the ImageRecord at current_image_index
        (the queue is photos, not one-per-student).
        """

        image_record = self.image_records[self.current_image_index]

        self.student_label.configure(
            text=image_record.student_name
        )

        total = len(self.image_records)
        position = self.current_image_index + 1

        self.progress_label.configure(
            text=f"Photo {position} of {total}"
        )

        self.progress_bar.set(position / total)

        self.next_button.configure(
            text="Finish" if position == total else "Next  →"
        )

        self.load_and_display(
            str(image_record.image_path),
            image_record=image_record
        )

    def next_image(self):

        self.current_image_index += 1

        if self.current_image_index >= len(self.image_records):
            self.show_results_screen()
        else:
            self.load_current_image()

    def show_results_screen(self):
        """
        Class Results page, shown at the end of the review flow.
        Reloads the ClassRecord fresh from storage -- same pattern as
        open_class_screen -- so the page reflects exactly what's
        persisted, even though self.class_record has already been
        kept up to date via on_teacher_confirm/on_note_save. Falls
        back to the in-memory copy if the reload fails for any
        reason, since it's still the most accurate data we have.
        """

        self.clear_main_frame()

        class_record = load_class(self.class_record.class_id)

        if class_record is not None:
            self.class_record = class_record

        ClassResultsScreen(
            self.main_frame,
            class_record=self.class_record,
            on_home=self.show_setup_count_screen,
            on_review=self.start_review,
            on_student_details=self.on_open_results_student
        )

    def on_open_results_student(self, class_record, student_index):
        """
        Called by ClassResultsScreen's "Details" button. Shows that
        student's per-photo scores and notes; Back to Results goes
        through show_results_screen, so the Results page is rebuilt
        fresh from storage like always.
        """

        student = class_record.students[student_index]

        self.clear_main_frame()

        StudentResultsDetailScreen(
            self.main_frame,
            student=student,
            on_back=self.show_results_screen
        )

    # -----------------------------------------
    # CONTENT
    # -----------------------------------------

    def create_content(self):

        self.content = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent"
        )

        self.content.pack(
            fill="both",
            expand=True,
            padx=24,
            pady=16
        )

        self.image_viewer = ImageViewer(
            self.content,
            on_drop=self.on_drop,
            on_note_save=self.on_note_save
        )

        self.metadata_panel = MetadataPanel(
            self.content,
            on_teacher_confirm=self.on_teacher_confirm
        )

    # -----------------------------------------
    # TEACHER GRADING
    # -----------------------------------------

    def on_teacher_confirm(self, image_record):
        """
        Called by TeacherGradingPanel once a Teacher Grading score is
        confirmed for the photo on screen. Writes the confirmed
        Rule Engine / Teacher / Total scores back into the matching
        core.class_model.ClassPhotoEntry and persists them, so the
        Class Screen's Avg Total and the Student DataFrame both pick
        them up.
        """

        photo_entry = self.find_photo_entry(image_record)

        if photo_entry is None:
            return

        photo_entry.rule_engine_score = image_record.rule_engine_score
        photo_entry.teacher_score = image_record.teacher_score
        photo_entry.total_score = image_record.total_score

        save_class(self.class_record)

    # -----------------------------------------
    # PHOTO NOTES
    # -----------------------------------------

    def on_note_save(self, image_record, note_text):
        """
        Called by ImageViewer once the professor saves a note for
        the photo on screen. Persists it into the matching
        core.class_model.ClassPhotoEntry.note -- notes are stored
        per photo, not per student.
        """

        photo_entry = self.find_photo_entry(image_record)

        if photo_entry is None:
            return

        photo_entry.note = note_text

        save_class(self.class_record)

    # -----------------------------------------
    # BOTTOM BAR
    # -----------------------------------------

    def create_bottom_bar(self):

        self.bottom_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=theme.SURFACE,
            corner_radius=0
        )

        # Packed before the content so it always stays on screen.
        self.bottom_frame.pack(
            side="bottom",
            fill="x"
        )

        inner = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")

        inner.pack(
            fill="x",
            padx=28,
            pady=12
        )

        self.open_button = theme.secondary_button(
            inner,
            "Open Image",
            self.open_image,
            width=130,
            height=40
        )

        self.open_button.pack(side="left")

        self.copy_button = theme.secondary_button(
            inner,
            "Copy Info",
            self.copy_info_to_clipboard,
            width=120,
            height=40
        )

        self.copy_button.pack(
            side="left",
            padx=(10, 0)
        )

        self.next_button = theme.primary_button(
            inner,
            "Next  →",
            self.next_image,
            width=130,
            height=40
        )

        self.next_button.pack(side="right")

        self.exit_button = theme.ghost_button(
            inner,
            "Exit",
            self.destroy,
            width=80,
            height=40
        )

        self.exit_button.pack(
            side="right",
            padx=(0, 10)
        )

    # -----------------------------------------
    # IMAGE HANDLING
    # -----------------------------------------

    def open_image(self):

        file_path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[
                (
                    "Image files",
                    "*.jpg *.jpeg *.png *.webp *.bmp *.tiff"
                ),
                (
                    "All files",
                    "*.*"
                )
            ]
        )

        if file_path:
            self.load_and_display(file_path)

    def on_drop(self, event):

        file_path = event.data.strip("{}")

        self.load_and_display(file_path)

    def load_and_display(self, file_path, image_record=None):
        """
        Loads `file_path` and renders it. `image_record` is the
        core.student.ImageRecord this photo belongs to during the
        official review flow (student/photo already known, Teacher
        Grading state and note preserved across re-renders).

        When called without one -- Open Image or drag & drop, both
        of which can point at any photo outside the review queue --
        a scratch ImageRecord is created just so MetadataPanel /
        Teacher Grading has something to render. It isn't added to
        self.image_records, so it never affects the Next button or
        the official per-student results.
        """

        try:

            data = load_image(file_path)

            self.current_image = data["image"]
            self.current_data = data

            grading = None

            if self.rule_config is not None:
                grading = grade_student(
                    data,
                    self.rule_config.rules,
                    self.rule_config.system_score
                )

            if image_record is None:
                image_record = ImageRecord(
                    student_name="",
                    image_path=Path(file_path)
                )

            image_record.grading_result = grading

            if grading is not None:
                image_record.rule_engine_score = grading.technical_score
                image_record.rule_engine_max_score = grading.system_score

            if self.rule_config is not None:
                image_record.teacher_max_score = self.rule_config.human_score

            self.image_viewer.update(
                self.current_image,
                image_record
            )

            self.metadata_panel.update(data, image_record)

        except FileNotFoundError:

            show_error(
                self,
                "File not found."
            )

        except UnidentifiedImageError:

            show_error(
                self,
                "This file is not a valid image."
            )

        except OSError:

            show_error(
                self,
                "Could not open this file."
            )

    # -----------------------------------------
    # COPY INFO
    # -----------------------------------------

    def copy_info_to_clipboard(self):

        if not self.current_data:
            return

        data = self.current_data

        lines = [
            f"Filename: {data['path'].name}",
            f"Format: {data['format']}",
            f"File Size: {data['file_size_mb']:.2f} MB",
            f"Width: {data['size'][0]} PX",
            f"Height: {data['size'][1]} PX",
            f"Color Mode: {data['mode']}",
            f"Make: {exif_value(data['make'])}",
            f"Model: {exif_value(data['model'])}",
            f"Lens Model: {exif_value(data['lens_model'])}",
            f"ISO: {exif_value(data['iso'])}",
            f"Aperture: {exif_value(data['fnum'])}",
            f"Shutter Speed: {exif_value(data['exposure_time'])}",
            f"Focal Length: {exif_value(data['focal'])}",
            f"Date Taken: {exif_value(data['date'])}",
            f"Flash: {exif_value(data['flash'])}",
            f"White Balance: {exif_value(data['white_balance'])}",
        ]

        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
        self.update()


if __name__ == "__main__":

    app = App()
    app.mainloop()

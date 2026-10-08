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
from ..storage.grading_session import (
    GradingSessionError,
    delete_session,
    find_conflict,
    load_active_session,
    save_session,
)

from .class_screen import ClassScreen
from .home_screen import HomeScreen
from .image_viewer import ImageViewer
from .metadata_panel import MetadataPanel
from .results_screen import ClassResultsScreen
from .rule_engine import RuleEngineScreen
from .student_detail import StudentDetailScreen
from .student_results_detail import StudentResultsDetailScreen
from .student_setup import StudentFoldersScreen
from .widgets import show_error, show_confirm


class App(ctk.CTk, TkinterDnD.DnDWrapper):

    def __init__(self):
        super().__init__()

        self.TkdndVersion = TkinterDnD._require(self)

        self.title("Image Metadata")
        self.geometry("1050x700")
        self.minsize(900, 600)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # Closing the window with the X button goes through the same
        # unsaved-progress check as the Exit button.
        self.protocol("WM_DELETE_WINDOW", self.exit_app)

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
        # being reviewed (new feature: per-photo scores/notes are
        # written back into this and saved as they're confirmed).
        self.class_record = None

        # Rule Engine
        self.rule_config = None

        # Grading Progress, Save & Continue (new feature).
        #
        # grading_student_name: which queue is being graded -- None
        # means the whole class (the queue built right after a class
        # is created), a name means only that one student (started
        # with "Start Grading" on the Class Screen). It is saved into
        # the checkpoint so Continue can rebuild the same queue, and
        # so one student's checkpoint is never overwritten by
        # another's. The name is used rather than the student's list
        # position because positions shift when a student is deleted.
        #
        # grading_dirty: True when something changed since the last
        # Save (a confirmed score, a note, or moving to another
        # photo). Drives the "unsaved progress" warning.
        #
        # in_grading: True only while the grading screen is showing.
        self.grading_student_name = None
        self.grading_dirty = False
        self.in_grading = False

        # Main frame
        self.main_frame = ctk.CTkFrame(
            self,
            corner_radius=15
        )

        self.main_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        self.show_setup_count_screen()

    # -----------------------------------------
    # HELPERS
    # -----------------------------------------

    def clear_main_frame(self):

        # Every screen change goes through here, so this is the one
        # place that knows the grading screen is no longer showing.
        # start_review() switches it back on after clearing.
        self.in_grading = False

        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def find_photo_entry(self, image_record):
        """
        Locate the core.class_model.ClassPhotoEntry that corresponds
        to `image_record` inside self.class_record, by matching
        image path (new feature: persisting per-photo scores/notes).
        Returns None if there's no class currently being reviewed,
        or no matching photo (e.g. Open Image / drag & drop outside
        the review flow).
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
        Home page: Welcome + Previous Classes (backed by real,
        persisted classes -- Class Management) + New Class form.
        Kept under the original method name so nothing else in the
        app has to change how it starts the setup flow or returns to
        Home.

        Also checks for an unfinished grading session (new feature:
        Grading Progress, Save & Continue) so the Home Page can offer
        "Continue (ClassName) Grading".
        """

        self.clear_main_frame()

        classes = load_all_classes()
        active_session = load_active_session()

        HomeScreen(
            self.main_frame,
            classes=classes,
            on_continue=self.on_home_continue,
            on_open_class=self.on_open_class,
            on_delete_class=self.on_delete_class,
            active_session=active_session,
            on_continue_grading=self.on_continue_grading
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

        container = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent"
        )

        container.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=30
        )

        ctk.CTkLabel(
            container,
            text="Enter Student Names",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#7CFFB2"
        ).pack(pady=(0, 15))

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

            row = ctk.CTkFrame(
                scroll_frame,
                fg_color="transparent"
            )

            row.pack(
                fill="x",
                pady=5
            )

            ctk.CTkLabel(
                row,
                text=f"Student {i + 1} name:",
                width=140,
                anchor="w"
            ).pack(
                side="left",
                padx=(0, 10)
            )

            entry = ctk.CTkEntry(
                row,
                width=250
            )

            entry.pack(side="left")

            name_entries.append(entry)

        error_label = ctk.CTkLabel(
            container,
            text="",
            text_color="#FF6B6B"
        )

        error_label.pack(pady=(10, 5))

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

        ctk.CTkButton(
            container,
            text="Continue",
            width=150,
            height=40,
            fg_color="#1F8F4C",
            hover_color="#27AE60",
            command=on_continue
        ).pack(pady=(10, 0))

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
        and persisted (Class Management, spec section 3) -- Rule
        Engine is NOT a condition for the class to exist. The
        resulting ClassRecord is kept on self.class_record so later
        Rule Engine / Teacher Grading confirmations and photo notes
        can be written back into it and saved.
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
        was never configured (on_start_grading), which needs to
        route back into grading a specific student afterward instead
        of the usual full-queue review.

        New feature: Rule Engine Presets. Presets are loaded fresh
        from storage every time this screen opens. Saving a new
        preset re-opens this same screen (with the same
        on_continue/on_skip/banner_text it was already showing) so
        the preset list reflects the save immediately.
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

        Also persists `config` onto self.class_record (new feature:
        class's active Rule Engine configuration) so reopening this
        class later -- to grade a student added afterward, or after
        an app restart -- knows which configuration to reuse instead
        of asking the professor to reconfigure from scratch.

        New feature (Grading Progress): if an unfinished saved
        grading session already exists for another queue, grading
        can't start yet. The class itself was already created, so
        the professor simply goes back Home and can grade it later.
        """

        if self.class_record is not None and self.session_conflicts(
            self.class_record.class_id, None
        ):
            self.show_setup_count_screen()
            return

        self.rule_config = config

        for image_record in self.image_records:
            image_record.rule_engine_max_score = config.system_score
            image_record.teacher_max_score = config.human_score

        if self.class_record is not None:
            self.class_record.rule_config = config.to_dict()
            save_class(self.class_record)

        # Whole-class queue (not a single student's).
        self.grading_student_name = None

        self.start_review()

    def on_rules_skipped(self):
        """
        New feature: Rule Engine Skip. The professor wants to grade
        entirely manually -- no Rule Engine grading runs at all
        (self.rule_config stays None, so load_and_display never
        calls grade_student), and every photo's Teacher Grading max
        becomes the full 100 points.

        Persisted as {"skipped": True} rather than a real
        RuleEngineConfig, since "no Rule Engine at all" isn't a
        config with zero rules -- it's a distinct choice that
        reopening this class must also remember and repeat, not
        re-ask for.

        Same unfinished-session check as on_rules_configured.
        """

        if self.class_record is not None and self.session_conflicts(
            self.class_record.class_id, None
        ):
            self.show_setup_count_screen()
            return

        self.rule_config = None

        for image_record in self.image_records:
            image_record.teacher_max_score = 100

        if self.class_record is not None:
            self.class_record.rule_config = {"skipped": True}
            save_class(self.class_record)

        # Whole-class queue (not a single student's).
        self.grading_student_name = None

        self.start_review()

    # -----------------------------------------
    # CLASS SCREEN / STUDENT DETAIL
    # (Class Management, spec sections 8-16)
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
        reflects what's actually on disk (spec section 7/17).
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
        never the student photo folders on disk (spec section 11) --
        then refreshes Home.

        Also removes this class's saved grading session, if it has
        one -- otherwise Home would offer to continue grading a class
        that no longer exists, and the leftover file would block
        every other class from being graded.
        """

        delete_class(class_id)
        self.remove_session(class_id)
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
        "Start Grading" next to a student in the Class Screen (new
        feature). Routes that student's already-persisted photos
        into the existing Rule Engine / Teacher Grading review flow
        via begin_grading()/begin_grading_skipped() below --
        reusing this class's already-saved rule_config if there is
        one, or asking the professor to configure/skip the Rule
        Engine first (the exact same RuleEngineScreen used for a
        brand-new class) if this class has never been configured,
        including every class saved before rule_config existed.

        New feature (Grading Progress): refuses to start if an
        unfinished saved grading session exists for a different
        class, or for a different student of this class.
        """

        student_name = class_record.students[student_index].name

        if self.session_conflicts(class_record.class_id, student_name):
            return

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

        # Queue is this one student only (saved into the checkpoint).
        self.grading_student_name = student_entry.name

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

        # Queue is this one student only (saved into the checkpoint).
        self.grading_student_name = student_entry.name

        self.start_review()

    def on_add_student_to_class(self, class_record, name, image_paths, source_folder):
        """
        Called by ClassScreen's Add New Student dialog once photos
        have already been picked and validated (folder or individual
        files). Validates the name is non-blank and not a duplicate
        (spec section 20) before persisting -- ClassScreen itself
        never writes storage.
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
        files, spec section 14). Selecting the exact same folder
        again re-scans it instead of doubling the count/photos, as a
        simple guard against double counting; individually-selected
        files always add to the existing set.
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
        never touches their photo folder on disk (spec section 15).
        """

        del class_record.students[student_index]

        save_class(class_record)
        self.open_class_screen(class_record.class_id)

    # -----------------------------------------
    # GRADING SESSION — SAVE & CONTINUE
    # (new feature: Grading Progress, Save & Continue)
    #
    # The checkpoint file (storage.grading_session) only remembers
    # *where the teacher stopped*. The scores and notes themselves
    # already live in class.json (on_teacher_confirm / on_note_save
    # save them as they happen), so this is a checkpoint on top of
    # the existing class storage, not a second storage system.
    # -----------------------------------------

    def session_conflicts(self, class_id, student_name):
        """
        True (after showing an error) if an unfinished saved grading
        session already exists for a different class, or for a
        different queue in this class (another student, or the whole
        class). `student_name` is None for a whole-class queue.
        """

        message = find_conflict(class_id, student_name)

        if message:
            show_error(self, message)
            return True

        return False

    def remove_session(self, class_id):
        """
        Deletes the saved grading session of `class_id` (if any).
        A failure is shown to the teacher instead of crashing.
        """

        try:
            delete_session(class_id)
        except GradingSessionError as error:
            show_error(self, str(error))

    def drop_unusable_session(self, class_id, message):
        """
        A saved session that can no longer be applied (the class is
        gone, or its photos changed) would otherwise sit there
        forever and block every other class. So it is removed, the
        teacher is told why, and Home is shown again. Nothing real is
        lost: every confirmed score and note is still in class.json.
        """

        self.remove_session(class_id)

        show_error(
            self,
            message + " The saved progress was removed; scores you "
            "already confirmed are still in the class."
        )

        self.show_setup_count_screen()

    def queue_students(self, class_record, student_name):
        """
        The ClassStudentEntry objects that make up a review queue:
        every student for a whole-class queue (student_name None),
        or just the one student with that name. None if no such
        student exists any more.
        """

        if student_name is None:
            return list(class_record.students)

        for student in class_record.students:
            if student.name == student_name:
                return [student]

        return None

    def build_session_data(self):
        """
        The dict written to classes/grading(<class name>).json: which
        class and queue, the photo the teacher is on, the Rule Engine
        configuration, and a snapshot of every queued photo's
        confirmed scores and note. The photos come from the
        ClassPhotoEntry objects (the same data class.json holds), in
        review-queue order.
        """

        class_record = self.class_record

        students = self.queue_students(class_record, self.grading_student_name)

        return {
            "class_id": class_record.class_id,
            "class_name": class_record.class_name,
            "student_name": self.grading_student_name,
            "current_index": self.current_image_index,
            "rule_config": class_record.rule_config,
            "photos": [
                photo.to_dict()
                for student in students
                for photo in student.photos
            ],
        }

    def all_photos_graded(self):
        """True once every photo in the review queue has a Total Score."""

        return bool(self.image_records) and all(
            image_record.total_score is not None
            for image_record in self.image_records
        )

    def finish_session_if_complete(self):
        """
        When every photo in the queue is graded, the grading session
        is finished: delete its checkpoint file (the class data in
        class.json stays untouched). Returns True if it was complete.
        """

        if not self.all_photos_graded():
            return False

        self.remove_session(self.class_record.class_id)
        self.grading_dirty = False
        self.set_save_status("", "gray60")

        return True

    def save_grading_progress(self):
        """
        The Save button (also used by the unsaved-exit dialog).
        Returns True if the progress was saved -- or if there was
        nothing left to save because grading is already complete --
        and False if saving failed or was blocked.
        """

        if self.class_record is None:
            return False

        # A fully graded queue has nothing to resume. Writing a
        # checkpoint for it would only leave a stale file that blocks
        # every other class.
        if self.finish_session_if_complete():
            return True

        try:
            save_session(self.build_session_data())
        except GradingSessionError as error:
            show_error(self, str(error))
            return False

        self.grading_dirty = False
        self.set_save_status("✓ Saved", "#7CFFB2")

        return True

    def mark_dirty(self):
        """
        Something changed since the last Save. Ignored once the whole
        queue is graded, because a finished session has nothing to
        checkpoint.
        """

        if self.all_photos_graded():
            return

        self.grading_dirty = True
        self.set_save_status("Unsaved changes", "#F5D76E")

    def leave_grading(self, proceed):
        """
        Runs `proceed()` to leave the grading screen -- but first, if
        there are unsaved changes, asks whether to save:

          Yes -> save, then leave (stays put if the save fails)
          No  -> leave without saving the latest changes
          X   -> closes the dialog and stays on the grading screen
        """

        if not (self.in_grading and self.grading_dirty):
            proceed()
            return

        def save_then_leave():
            if self.save_grading_progress():
                proceed()

        show_confirm(
            self,
            "You have unsaved grading progress. "
            "Do you want to save before leaving?",
            on_yes=save_then_leave,
            on_no=proceed
        )

    def exit_app(self):
        """Exit button / window X button: close the app, with the unsaved check."""

        self.leave_grading(self.destroy)

    def on_continue_grading(self):
        """
        Called by HomeScreen's "Continue (ClassName) Grading" button.
        Loads the saved session and the class it belongs to, then
        hands both to resume_grading().
        """

        session = load_active_session()

        if session is None:
            show_error(self, "No saved grading session was found.")
            self.show_setup_count_screen()
            return

        class_record = load_class(session["class_id"])

        if class_record is None:
            self.drop_unusable_session(
                session["class_id"],
                "The class for this saved grading session no longer exists."
            )
            return

        self.resume_grading(class_record, session)

    def resume_grading(self, class_record, session):
        """
        Rebuilds the review queue exactly as it was when the teacher
        pressed Save, restores every photo's saved scores and note,
        and opens the grading screen on the photo they stopped at.

        The saved photo list must match the class's current photos
        (same paths, same order). If photos were added or removed
        since the save, the session can't be applied safely -- it is
        dropped (see drop_unusable_session) instead of risking
        putting scores on the wrong photos.
        """

        student_name = session.get("student_name")
        students = self.queue_students(class_record, student_name)

        entries = (
            [photo for student in students for photo in student.photos]
            if students is not None
            else []
        )

        saved_photos = session["photos"]

        if not entries or [entry.path for entry in entries] != [
            saved.get("path") for saved in saved_photos
        ]:
            self.drop_unusable_session(
                class_record.class_id,
                "The photos in this class changed after the grading "
                "progress was saved, so it can't be resumed."
            )
            return

        config_data = session.get("rule_config") or class_record.rule_config

        if config_data is None:
            self.drop_unusable_session(
                class_record.class_id,
                "The saved grading progress has no Rule Engine settings."
            )
            return

        # Restore the saved scores and notes onto the class's photos.
        for entry, saved in zip(entries, saved_photos):

            restored = ClassPhotoEntry.from_dict(saved)

            entry.rule_engine_score = restored.rule_engine_score
            entry.teacher_score = restored.teacher_score
            entry.total_score = restored.total_score
            entry.note = restored.note

        class_record.rule_config = config_data
        save_class(class_record)

        # Rebuild the runtime queue from the restored entries.
        image_records = [
            image_record
            for student in students
            for image_record in image_records_from_student(student)
        ]

        if config_data.get("skipped"):

            self.rule_config = None

            for image_record in image_records:
                image_record.teacher_max_score = 100

        else:

            config = RuleEngineConfig.from_dict(config_data)
            self.rule_config = config

            for image_record in image_records:
                image_record.rule_engine_max_score = config.system_score
                image_record.teacher_max_score = config.human_score

        self.class_record = class_record
        self.image_records = image_records
        self.grading_student_name = student_name

        # Land on the exact photo the teacher stopped at.
        start_index = max(
            0,
            min(int(session["current_index"]), len(image_records) - 1)
        )

        self.start_review(start_index=start_index)

    # -----------------------------------------
    # REVIEW
    # -----------------------------------------

    def start_review(self, start_index=0):
        """
        Opens the grading screen. `start_index` is 0 for a normal
        start (and for the Results screen's Review button, which
        calls this with no arguments); Continue passes the saved
        position instead.
        """

        self.current_image_index = start_index
        self.grading_dirty = False

        self.clear_main_frame()

        self.in_grading = True

        self.create_student_bar()
        self.create_header()
        self.create_progress_bar()
        self.create_content()
        self.create_bottom_bar()

        self.load_current_image()

    def create_student_bar(self):

        self.student_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent"
        )

        self.student_frame.pack(
            fill="x",
            padx=25,
            pady=(20, 0)
        )

        self.student_label = ctk.CTkLabel(
            self.student_frame,
            text="Student: —",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#7CFFB2"
        )

        self.student_label.pack(side="left")

    def load_current_image(self):
        """
        Loads and displays the ImageRecord at current_image_index
        (renamed from load_current_student now that the queue is
        photos, not one-per-student).
        """

        image_record = self.image_records[self.current_image_index]

        self.student_label.configure(
            text=f"Student: {image_record.student_name}"
        )

        self.load_and_display(
            str(image_record.image_path),
            image_record=image_record
        )

        self.refresh_progress()

    def next_image(self):
        """
        Moves to the next photo. On the last photo there is no next
        one, so this finishes grading instead (see finish_grading).
        """

        if self.current_image_index + 1 >= len(self.image_records):
            self.finish_grading()
            return

        self.current_image_index += 1

        # The position is part of the saved progress.
        self.mark_dirty()

        self.load_current_image()

    def finish_grading(self):
        """
        Next was pressed on the last photo.

        If every photo is graded, the session is finished: its
        checkpoint is deleted and the Results screen opens. If some
        photos were skipped, the session is NOT finished -- any
        saved checkpoint stays, and unsaved changes get the usual
        save-before-leaving question first.
        """

        if self.finish_session_if_complete():
            self.show_results_screen()
            return

        self.leave_grading(self.show_results_screen)

    def show_results_screen(self):
        """
        New feature: Class Results page, replacing the old "Done"
        screen. Reloads the ClassRecord fresh from storage -- same
        pattern as open_class_screen -- so the page reflects exactly
        what's persisted, even though self.class_record has already
        been kept up to date via on_teacher_confirm/on_note_save.
        Falls back to the in-memory copy if the reload fails for any
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
        Called by ClassResultsScreen's "ⓘ" button (new feature:
        Student Details). Shows that student's per-photo scores and
        notes; Back to Results goes through show_results_screen, so
        the Results page is rebuilt fresh from storage like always.
        """

        student = class_record.students[student_index]

        self.clear_main_frame()

        StudentResultsDetailScreen(
            self.main_frame,
            student=student,
            on_back=self.show_results_screen
        )

    # -----------------------------------------
    # HEADER
    # -----------------------------------------

    def create_header(self):

        self.header = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent"
        )

        self.header.pack(
            fill="x",
            padx=25,
            pady=(10, 10)
        )

        ctk.CTkLabel(
            self.header,
            text="📷  Image Metadata",
            font=ctk.CTkFont(
                size=28,
                weight="bold"
            ),
            text_color="#7CFFB2"
        ).pack(side="left")

        ctk.CTkLabel(
            self.header,
            text="View image information and EXIF metadata",
            text_color="gray60",
            font=ctk.CTkFont(size=13)
        ).pack(
            side="left",
            padx=15
        )

    # -----------------------------------------
    # PROGRESS BAR (new feature: Grading Progress, Save & Continue)
    # -----------------------------------------

    def create_progress_bar(self):
        """
        One row above the grading area:

            [ Save ]  status   ==========----------   23/37

        The bar shows how many photos are actually graded; the
        counter shows which photo the teacher is on.
        """

        self.progress_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent"
        )

        self.progress_frame.pack(
            fill="x",
            padx=25,
            pady=(0, 5)
        )

        self.save_button = ctk.CTkButton(
            self.progress_frame,
            text="💾  Save",
            width=90,
            height=28,
            fg_color="transparent",
            hover_color="#123f2c",
            border_color="#2ECC71",
            text_color="#7CFFB2",
            border_width=1,
            command=self.save_grading_progress
        )

        self.save_button.pack(side="left")

        self.save_status_label = ctk.CTkLabel(
            self.progress_frame,
            text="",
            width=120,
            anchor="w",
            text_color="gray60",
            font=ctk.CTkFont(size=12)
        )

        self.save_status_label.pack(
            side="left",
            padx=(8, 8)
        )

        # Packed before the bar so the bar is the part that stretches.
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="0/0",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#7CFFB2"
        )

        self.progress_label.pack(
            side="right",
            padx=(10, 0)
        )

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            height=6,
            progress_color="#2ECC71"
        )

        self.progress_bar.pack(
            side="left",
            fill="x",
            expand=True
        )

        self.progress_bar.set(0)

    def refresh_progress(self):
        """
        Updates the bar and the counter from the real grading state:
        the bar = photos with a confirmed Total Score / total photos
        in the queue; the counter = current position / total.
        """

        total = len(self.image_records)
        graded = sum(
            1 for image_record in self.image_records
            if image_record.total_score is not None
        )

        self.progress_bar.set(graded / total if total else 0)

        self.progress_label.configure(
            text=f"{self.current_image_index + 1}/{total}"
        )

    def set_save_status(self, text, color):

        self.save_status_label.configure(
            text=text,
            text_color=color
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
            padx=25,
            pady=10
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

        New feature (Grading Progress): also marks the session as
        having unsaved changes, advances the progress bar, and --
        if that was the last ungraded photo -- finishes the session
        by deleting its checkpoint file.
        """

        photo_entry = self.find_photo_entry(image_record)

        if photo_entry is None:
            return

        photo_entry.rule_engine_score = image_record.rule_engine_score
        photo_entry.teacher_score = image_record.teacher_score
        photo_entry.total_score = image_record.total_score

        save_class(self.class_record)

        self.mark_dirty()
        self.refresh_progress()
        self.finish_session_if_complete()

    # -----------------------------------------
    # PHOTO NOTES (new feature)
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

        self.mark_dirty()

    # -----------------------------------------
    # BOTTOM BAR
    # -----------------------------------------

    def create_bottom_bar(self):

        self.bottom_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color="transparent"
        )

        self.bottom_frame.pack(
            fill="x",
            padx=25,
            pady=(10, 20)
        )

        self.open_button = ctk.CTkButton(
            self.bottom_frame,
            text="📂  Open Image",
            width=150,
            height=40,
            fg_color="#1F8F4C",
            hover_color="#27AE60",
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            ),
            command=self.open_image
        )

        self.open_button.pack(side="left")

        self.copy_button = ctk.CTkButton(
            self.bottom_frame,
            text="📋  Copy Info",
            width=140,
            height=40,
            fg_color="transparent",
            hover_color="#123f2c",
            border_color="#2ECC71",
            text_color="#7CFFB2",
            border_width=1,
            command=self.copy_info_to_clipboard
        )

        self.copy_button.pack(
            side="left",
            padx=(10, 0)
        )

        self.next_button = ctk.CTkButton(
            self.bottom_frame,
            text="➡️  Next",
            width=120,
            height=40,
            fg_color="#1F8F4C",
            hover_color="#27AE60",
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            ),
            command=self.next_image
        )

        self.next_button.pack(
            side="left",
            padx=(10, 0)
        )

        self.exit_button = ctk.CTkButton(
            self.bottom_frame,
            text="✕  Exit",
            width=100,
            height=40,
            fg_color="transparent",
            hover_color="#123f2c",
            border_color="#2ECC71",
            text_color="#7CFFB2",
            border_width=1,
            command=self.exit_app
        )

        self.exit_button.pack(side="right")

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
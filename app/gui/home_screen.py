import customtkinter as ctk

from .widgets import show_confirm


class HomeScreen:
    """
    The Home Page (spec: Welcome + Previous Classes + New Class).

    Follows the same pattern as RuleEngineScreen: takes a parent
    frame, builds its own widgets into it, and calls
    `on_continue(class_name, student_count)` once the New Class
    form validates.

    Previous Classes is now backed by real, persisted classes (new
    feature: Class Management) -- `classes` is a list of
    core.class_model.ClassRecord that App already loaded from
    storage.class_storage. This screen only renders them and reports
    back what the professor clicked; it never touches storage or
    JSON itself (spec section 17):

      - clicking a class name calls `on_open_class(class_id)`
      - clicking Delete asks for confirmation right here, and only
        calls `on_delete_class(class_id)` if the professor picks Yes

    New feature: Grading Progress, Save & Continue. `active_session`
    is the saved grading session dict App loaded from
    storage.grading_session (or None). When there is one, a
    "Continue (ClassName) Grading" card is shown at the top of the
    left column; clicking it calls `on_continue_grading()`.
    """

    def __init__(
        self,
        parent,
        classes,
        on_continue,
        on_open_class,
        on_delete_class,
        active_session=None,
        on_continue_grading=None,
    ):

        self.classes = classes
        self.on_continue = on_continue
        self.on_open_class = on_open_class
        self.on_delete_class = on_delete_class
        self.active_session = active_session
        self.on_continue_grading = on_continue_grading

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

        # Two-column layout: left column (Welcome + Previous Classes)
        # and right column (New Class form).
        self.left_column = ctk.CTkFrame(
            self.container,
            fg_color="transparent"
        )

        self.left_column.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 15)
        )

        self.right_column = ctk.CTkFrame(
            self.container,
            fg_color="transparent"
        )

        self.right_column.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(15, 0)
        )

        if self.active_session:
            self.create_continue_card()

        self.create_welcome_card()
        self.create_previous_classes_card()
        self.create_new_class_card()

    # -----------------------------------------
    # LEFT — CONTINUE GRADING CARD
    # (new feature: Grading Progress, Save & Continue)
    # -----------------------------------------

    def create_continue_card(self):

        class_name = self.active_session["class_name"]
        position = self.active_session["current_index"] + 1
        total = len(self.active_session["photos"])

        card = ctk.CTkFrame(
            self.left_column,
            corner_radius=12
        )

        card.pack(
            fill="x",
            pady=(0, 15)
        )

        ctk.CTkLabel(
            card,
            text="Unfinished Grading",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#7CFFB2"
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 5)
        )

        ctk.CTkLabel(
            card,
            text=f"Saved at photo {position}/{total}",
            text_color="gray60",
            font=ctk.CTkFont(size=13)
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 10)
        )

        ctk.CTkButton(
            card,
            text=f"Continue ({class_name}) Grading",
            height=36,
            fg_color="#1F8F4C",
            hover_color="#27AE60",
            command=self.handle_continue_grading
        ).pack(
            fill="x",
            padx=20,
            pady=(0, 20)
        )

    def handle_continue_grading(self):

        if self.on_continue_grading:
            self.on_continue_grading()

    # -----------------------------------------
    # LEFT — WELCOME CARD
    # -----------------------------------------

    def create_welcome_card(self):

        card = ctk.CTkFrame(
            self.left_column,
            corner_radius=12
        )

        card.pack(
            fill="x",
            pady=(0, 15)
        )

        ctk.CTkLabel(
            card,
            text="Welcome to PhotoGrade",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#7CFFB2"
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        ctk.CTkLabel(
            card,
            text=(
                "PhotoGrade helps photography instructors evaluate "
                "students' photos using image metadata and technical "
                "grading rules. Create a new class to get started."
            ),
            text_color="gray60",
            font=ctk.CTkFont(size=13),
            justify="left",
            wraplength=380
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 20)
        )

    # -----------------------------------------
    # LEFT — PREVIOUS CLASSES CARD
    # -----------------------------------------

    def create_previous_classes_card(self):

        card = ctk.CTkFrame(
            self.left_column,
            corner_radius=12
        )

        card.pack(
            fill="both",
            expand=True
        )

        ctk.CTkLabel(
            card,
            text="Previous Classes",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#7CFFB2"
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        # Scrollable list so it works the same way once real
        # classes are loaded in later (same pattern used elsewhere
        # in the app for lists, e.g. RuleEngineScreen's factor list).
        self.previous_classes_frame = ctk.CTkScrollableFrame(
            card,
            fg_color="transparent"
        )

        self.previous_classes_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=(0, 15)
        )

        if not self.classes:

            ctk.CTkLabel(
                self.previous_classes_frame,
                text="No classes yet",
                text_color="gray60"
            ).pack(pady=20)

            return

        for class_record in self.classes:
            self.create_previous_class_row(class_record)

    def create_previous_class_row(self, class_record):
        """
        One row in the Previous Classes list: class name + a
        "N Students • M Photos" subtitle + a Delete icon. Clicking
        the name/subtitle opens the class (on_open_class); clicking
        Delete asks for confirmation before removing anything.
        """

        row = ctk.CTkFrame(
            self.previous_classes_frame,
            fg_color="transparent"
        )

        row.pack(
            fill="x",
            pady=4
        )

        text_column = ctk.CTkFrame(
            row,
            fg_color="transparent",
            cursor="hand2"
        )

        text_column.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(10, 10)
        )

        name_label = ctk.CTkLabel(
            text_column,
            text=class_record.class_name,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold")
        )

        name_label.pack(
            anchor="w",
            fill="x"
        )

        subtitle_label = ctk.CTkLabel(
            text_column,
            text=(
                f"{class_record.student_count} Students • "
                f"{class_record.total_photo_count} Photos"
            ),
            anchor="w",
            text_color="gray60",
            font=ctk.CTkFont(size=12)
        )

        subtitle_label.pack(
            anchor="w",
            fill="x"
        )

        def handle_open(event=None):
            self.on_open_class(class_record.class_id)

        text_column.bind("<Button-1>", handle_open)
        name_label.bind("<Button-1>", handle_open)
        subtitle_label.bind("<Button-1>", handle_open)

        ctk.CTkButton(
            row,
            text="🗑️",
            width=32,
            height=28,
            fg_color="transparent",
            hover_color="#3a1f1f",
            text_color="#FF6B6B",
            command=lambda: self.handle_delete_class(class_record)
        ).pack(side="right")

    def handle_delete_class(self, class_record):
        """
        Shows a Yes/No confirmation (spec section 11) and only calls
        on_delete_class -- App's job, not this screen's, to actually
        touch storage -- if the professor confirms.
        """

        show_confirm(
            self.previous_classes_frame,
            f'Are you sure you want to delete\n"{class_record.class_name}"?',
            on_yes=lambda: self.on_delete_class(class_record.class_id)
        )

    # -----------------------------------------
    # RIGHT — NEW CLASS CARD
    # -----------------------------------------

    def create_new_class_card(self):

        card = ctk.CTkFrame(
            self.right_column,
            corner_radius=12
        )

        card.pack(
            fill="both",
            expand=True
        )

        ctk.CTkLabel(
            card,
            text="New Class",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#7CFFB2"
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 15)
        )

        ctk.CTkLabel(
            card,
            text="Class Name",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(
            anchor="w",
            padx=20
        )

        self.class_name_entry = ctk.CTkEntry(
            card,
            placeholder_text="Enter class name"
        )

        self.class_name_entry.pack(
            fill="x",
            padx=20,
            pady=(5, 15)
        )

        ctk.CTkLabel(
            card,
            text="Number of Students",
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(
            anchor="w",
            padx=20
        )

        self.student_count_entry = ctk.CTkEntry(
            card,
            placeholder_text="Enter number of students"
        )

        self.student_count_entry.pack(
            fill="x",
            padx=20,
            pady=(5, 15)
        )

        self.error_label = ctk.CTkLabel(
            card,
            text="",
            text_color="#FF6B6B"
        )

        self.error_label.pack(
            anchor="w",
            padx=20,
            pady=(0, 5)
        )

        ctk.CTkButton(
            card,
            text="Next",
            width=150,
            height=40,
            fg_color="#1F8F4C",
            hover_color="#27AE60",
            command=self.handle_next
        ).pack(
            anchor="w",
            padx=20,
            pady=(5, 20)
        )

    # -----------------------------------------
    # VALIDATION / SUBMIT
    # -----------------------------------------

    def handle_next(self):

        self.error_label.configure(text="")

        class_name = self.class_name_entry.get().strip()
        count_value = self.student_count_entry.get().strip()

        if not class_name:
            self.error_label.configure(
                text="Please enter a class name."
            )
            return

        if not count_value.isdigit() or int(count_value) <= 0:
            self.error_label.configure(
                text="Please enter a positive whole number of students."
            )
            return

        self.on_continue(class_name, int(count_value))
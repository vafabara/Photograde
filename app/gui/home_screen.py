import customtkinter as ctk

from . import theme
from .widgets import show_confirm


class HomeScreen:
    """
    The Home Page: Previous Classes + New Class form.

    Same contract as before: takes a parent frame and builds into it.
    `classes` is a list of core.class_model.ClassRecord that App
    already loaded from storage; this screen only renders them and
    reports back what the professor did (it never touches storage):

      - New Class form validates, then calls
        `on_continue(class_name, student_count)`
      - clicking a class calls `on_open_class(class_id)`
      - clicking Delete asks for confirmation here, and only calls
        `on_delete_class(class_id)` if the professor picks Yes
    """

    def __init__(
        self,
        parent,
        classes,
        on_continue,
        on_open_class,
        on_delete_class,
        on_settings=None,
        on_help=None
    ):

        self.classes = classes
        self.on_continue = on_continue
        self.on_open_class = on_open_class
        self.on_delete_class = on_delete_class
        self.on_settings = on_settings
        self.on_help = on_help

        # Set in create_previous_classes_card (only when there is at
        # least one class to search).
        self.search_entry = None
        self.count_label = None

        self.container = theme.page(parent)

        self.create_hero()

        body = ctk.CTkFrame(self.container, fg_color="transparent")

        body.pack(
            fill="both",
            expand=True
        )

        # Previous Classes gets the larger share; New Class is a
        # fixed-feeling form column that still resizes gracefully.
        body.grid_columnconfigure(0, weight=3, uniform="home")
        body.grid_columnconfigure(1, weight=2, uniform="home")
        body.grid_rowconfigure(0, weight=1)

        self.left_column = ctk.CTkFrame(body, fg_color="transparent")
        self.left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.right_column = ctk.CTkFrame(body, fg_color="transparent")
        self.right_column.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        self.create_previous_classes_card()
        self.create_new_class_card()

    # -----------------------------------------
    # HERO
    # -----------------------------------------

    def create_hero(self):

        hero = ctk.CTkFrame(self.container, fg_color="transparent")

        hero.pack(
            fill="x",
            pady=(0, 22)
        )

        title_row = ctk.CTkFrame(hero, fg_color="transparent")

        title_row.pack(fill="x")

        theme.label(
            title_row,
            "PhotoGrade",
            size=32,
            weight="bold",
            color=theme.ACCENT,
            anchor="w"
        ).pack(side="left")

        # Settings is packed first so it ends up rightmost; Help sits
        # just to its left.
        if self.on_settings:
            theme.secondary_button(
                title_row,
                "Settings",
                self.on_settings,
                width=100,
                height=34
            ).pack(side="right")

        if self.on_help:
            theme.secondary_button(
                title_row,
                "How to Use",
                self.on_help,
                width=110,
                height=34
            ).pack(
                side="right",
                padx=(0, 10)
            )

        theme.muted(
            hero,
            (
                "PhotoGrade helps photography instructors evaluate "
                "students' photos using image metadata and technical "
                "grading rules. Create a new class to get started."
            ),
            size=13,
            anchor="w",
            justify="left",
            wraplength=760
        ).pack(
            anchor="w",
            pady=(4, 0)
        )

    # -----------------------------------------
    # LEFT — PREVIOUS CLASSES
    # -----------------------------------------

    def create_previous_classes_card(self):

        card = theme.card(self.left_column)

        card.pack(
            fill="both",
            expand=True
        )

        header = ctk.CTkFrame(card, fg_color="transparent")

        header.pack(
            fill="x",
            padx=22,
            pady=(20, 10)
        )

        theme.label(
            header,
            "Previous classes",
            size=18,
            weight="bold"
        ).pack(side="left")

        if self.classes:
            self.count_label = theme.muted(
                header,
                str(len(self.classes)),
                size=13
            )

            self.count_label.pack(
                side="left",
                padx=(10, 0)
            )

            # Search only filters what is displayed -- self.classes
            # itself is never changed.
            self.search_entry = theme.text_entry(
                card,
                placeholder_text="Search classes..."
            )

            self.search_entry.pack(
                fill="x",
                padx=22,
                pady=(0, 10)
            )

            self.search_entry.bind(
                "<KeyRelease>",
                lambda event: self.render_class_rows()
            )

        self.previous_classes_frame = ctk.CTkScrollableFrame(
            card,
            fg_color="transparent"
        )

        self.previous_classes_frame.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=(0, 14)
        )

        if not self.classes:
            self.create_empty_state()
            return

        self.render_class_rows()

    def render_class_rows(self):
        """
        (Re)draws the class rows for the current search text: a
        case-insensitive, partial match on the class name. An empty
        search matches everything, so clearing the field restores the
        full list. Only the displayed rows change -- self.classes and
        storage are never touched.
        """

        for widget in self.previous_classes_frame.winfo_children():
            widget.destroy()

        query = self.search_entry.get().strip()

        matches = [
            class_record
            for class_record in self.classes
            if query.casefold() in class_record.class_name.casefold()
        ]

        if query:
            self.count_label.configure(
                text=f"{len(matches)} of {len(self.classes)}"
            )
        else:
            self.count_label.configure(text=str(len(self.classes)))

        if not matches:
            self.create_no_results_state(query)
            return

        for class_record in matches:
            self.create_previous_class_row(class_record)

    def create_no_results_state(self, query):

        empty = ctk.CTkFrame(
            self.previous_classes_frame,
            fg_color="transparent"
        )

        empty.pack(pady=40)

        theme.label(
            empty,
            "No classes found",
            size=16,
            weight="bold"
        ).pack()

        theme.muted(
            empty,
            f"No class name matches “{query}”. Try a different search.",
            size=13,
            wraplength=360,
            justify="center"
        ).pack(pady=(4, 0))

    def create_empty_state(self):

        empty = ctk.CTkFrame(
            self.previous_classes_frame,
            fg_color="transparent"
        )

        empty.pack(pady=40)

        theme.label(
            empty,
            "No classes yet",
            size=16,
            weight="bold"
        ).pack()

        theme.muted(
            empty,
            "Create your first class using the form on the right.",
            size=13
        ).pack(pady=(4, 0))

    def create_previous_class_row(self, class_record):
        """
        One row: class name, "N Students • M Photos", a grading
        progress bar (students completed / total) and a Delete
        button. Clicking anywhere on the text area opens the class;
        Delete asks for confirmation before removing anything.
        """

        row = ctk.CTkFrame(
            self.previous_classes_frame,
            fg_color=theme.SURFACE_ALT,
            corner_radius=10
        )

        row.pack(
            fill="x",
            pady=4
        )

        row.grid_columnconfigure(0, weight=1)

        text_column = ctk.CTkFrame(
            row,
            fg_color="transparent",
            cursor="hand2"
        )

        text_column.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(16, 8),
            pady=12
        )

        name_label = theme.label(
            text_column,
            class_record.class_name,
            size=15,
            weight="bold",
            anchor="w",
            cursor="hand2"
        )

        name_label.pack(
            anchor="w",
            fill="x"
        )

        subtitle_label = theme.muted(
            text_column,
            (
                f"{class_record.student_count} Students • "
                f"{class_record.total_photo_count} Photos"
            ),
            anchor="w",
            cursor="hand2"
        )

        subtitle_label.pack(
            anchor="w",
            fill="x"
        )

        clickable = [row, text_column, name_label, subtitle_label]

        if class_record.student_count:

            done = class_record.completed_student_count
            total = class_record.student_count

            progress_row = ctk.CTkFrame(
                text_column,
                fg_color="transparent",
                cursor="hand2"
            )

            progress_row.pack(
                anchor="w",
                fill="x",
                pady=(8, 0)
            )

            bar = theme.progress_bar(
                progress_row,
                done / total,
                width=160,
                color=theme.SUCCESS if done == total else theme.ACCENT
            )

            bar.pack(side="left")

            progress_text = theme.muted(
                progress_row,
                f"{done} of {total} graded",
                cursor="hand2"
            )

            progress_text.pack(
                side="left",
                padx=(10, 0)
            )

            clickable += [progress_row, progress_text]

        def handle_open(event=None):
            self.on_open_class(class_record.class_id)

        theme.make_clickable(clickable, handle_open, target=row)

        theme.danger_button(
            row,
            "Delete",
            lambda: self.handle_delete_class(class_record)
        ).grid(
            row=0,
            column=1,
            padx=(0, 12)
        )

    def handle_delete_class(self, class_record):
        """
        Shows a Yes/No confirmation and only calls on_delete_class --
        App's job, not this screen's, to actually touch storage -- if
        the professor confirms.
        """

        show_confirm(
            self.container,
            f'Are you sure you want to delete\n"{class_record.class_name}"?',
            on_yes=lambda: self.on_delete_class(class_record.class_id)
        )

    # -----------------------------------------
    # RIGHT — NEW CLASS
    # -----------------------------------------

    def create_new_class_card(self):

        card = theme.card(self.right_column)

        card.pack(
            fill="both",
            expand=True
        )

        theme.label(
            card,
            "New class",
            size=18,
            weight="bold"
        ).pack(
            anchor="w",
            padx=22,
            pady=(20, 4)
        )

        theme.muted(
            card,
            "You'll add student names and photos next.",
            size=13
        ).pack(
            anchor="w",
            padx=22,
            pady=(0, 18)
        )

        theme.label(
            card,
            "Class name",
            size=12,
            weight="bold",
            color=theme.TEXT_MUTED,
            anchor="w"
        ).pack(
            anchor="w",
            padx=22
        )

        self.class_name_entry = theme.text_entry(
            card,
            placeholder_text="e.g. Photography 101"
        )

        self.class_name_entry.pack(
            fill="x",
            padx=22,
            pady=(6, 16)
        )

        theme.label(
            card,
            "Number of students",
            size=12,
            weight="bold",
            color=theme.TEXT_MUTED,
            anchor="w"
        ).pack(
            anchor="w",
            padx=22
        )

        self.student_count_entry = theme.text_entry(
            card,
            placeholder_text="e.g. 12"
        )

        self.student_count_entry.pack(
            fill="x",
            padx=22,
            pady=(6, 12)
        )

        self.error_label = theme.error_label(card, wraplength=320, justify="left")

        self.error_label.pack(
            anchor="w",
            padx=22,
            pady=(0, 6)
        )

        theme.primary_button(
            card,
            "Continue  →",
            self.handle_next,
            width=170,
            height=42
        ).pack(
            anchor="w",
            padx=22,
            pady=(4, 22)
        )

        self.class_name_entry.bind("<Return>", lambda event: self.student_count_entry.focus())
        self.student_count_entry.bind("<Return>", lambda event: self.handle_next())

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
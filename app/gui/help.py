import customtkinter as ctk

from . import theme


# -----------------------------------------------------------------
# HELP CONTENT
#
# Sections 1-14 are the provided Help content, unchanged. Section 15
# was added to describe Save & Continue, search and Settings. It is
# split into blocks so the screen can lay it out with headings, body
# text, bullet lists and highlighted lines. Each section is
# (heading, [blocks]); a block is:
#
#   ("p", text)       a body paragraph
#   ("list", items)   a bullet list (one string per bullet)
#   ("lines", lines)  short highlighted lines (workflow, example values)
# -----------------------------------------------------------------

PAGE_TITLE = "How to use PhotoGrade"

SECTIONS = [
    (
        "What is PhotoGrade?",
        [
            ("p", "PhotoGrade is a desktop application designed to help photography teachers evaluate and organize student photography assignments."),
            ("p", "Instead of manually checking every photo, calculating scores, and organizing the results, PhotoGrade lets you create a class, add students and their photos, configure grading rules, review automatic scores, add teacher scores and notes, and export the final results."),
            ("p", "PhotoGrade works locally on your computer, so your class data and photos remain under your control."),
        ],
    ),
    (
        "1. BASIC WORKFLOW",
        [
            ("p", "The typical PhotoGrade workflow is:"),
            ("lines", ["Create a Class → Add Students → Add Photos → Configure Grading Rules → Review Scores → Add Teacher Scores → Review Results → Export"]),
            ("p", "You can also return to previously saved classes from the Home Screen."),
        ],
    ),
    (
        "2. CREATE A NEW CLASS",
        [
            ("p", "From the Home Screen, select New Class."),
            ("p", "Enter the required class information and add your students."),
            ("p", "Each student can have one or more photos associated with their work."),
            ("p", "After the class is created, you can add photos and configure the grading system."),
        ],
    ),
    (
        "3. ADD PHOTOS",
        [
            ("p", "Photos can be added individually or from a folder."),
            ("p", "PhotoGrade reads available photo metadata such as:"),
            ("list", ["ISO", "Aperture (F-number)", "Shutter Speed"]),
            ("p", "These values can be used by the Rule Engine when grading photos."),
            ("p", "Make sure the photos contain the metadata required by the rules you plan to use."),
        ],
    ),
    (
        "4. CONFIGURE THE RULE ENGINE",
        [
            ("p", "The Rule Engine allows you to define technical requirements for the assignment."),
            ("p", "For example, you can create rules for:"),
            ("list", ["ISO", "Aperture", "Shutter Speed"]),
            ("p", "For each factor, you can define an acceptable range."),
            ("p", "The Rule Engine calculates a technical score based on how well the photo follows the configured rules."),
            ("p", "You can also choose how the final grade is divided between the automatic Rule Engine score and the teacher's manual score."),
            ("p", "For example:"),
            ("lines", ["Rule Engine: 40 points", "Teacher: 60 points"]),
            ("p", "The Rule Engine starts from a full score and adjusts the score according to the configured rules."),
            ("p", "A tolerance can also be used so that small deviations do not immediately result in a large score reduction."),
        ],
    ),
    (
        "5. MISSING PHOTO METADATA",
        [
            ("p", "If a rule requires information that is not available in a photo's metadata, PhotoGrade does not treat the missing information as a successful result."),
            ("p", "The affected factor is shown as:"),
            ("lines", ["EXIF Missing"]),
            ("p", "When required information is missing, the teacher can determine the appropriate result manually."),
            ("p", "This prevents a photo from receiving a full technical score simply because its required metadata is unavailable."),
        ],
    ),
    (
        "6. TEACHER GRADING",
        [
            ("p", "The teacher can manually evaluate each photo in addition to the automatic Rule Engine score."),
            ("p", "The teacher score is useful for aspects that cannot be reliably evaluated from metadata, such as:"),
            ("list", ["Composition", "Creativity", "Subject", "Lighting", "Artistic decisions", "Assignment-specific requirements"]),
            ("p", "The final score combines the automatic and teacher portions according to the configured grading weights."),
            ("p", "If the Rule Engine is skipped, the teacher can use the manual grading path instead."),
        ],
    ),
    (
        "7. REVIEW PHOTO SCORES",
        [
            ("p", "After grading, you can review the results for each student's photos."),
            ("p", "The photo information can include:"),
            ("list", ["Rule Engine score", "Teacher score", "Total score", "Notes"]),
            ("p", "Use the photo information view to inspect individual results and understand how each photo was graded."),
        ],
    ),
    (
        "8. ADD NOTES",
        [
            ("p", "Notes can be attached to photo results."),
            ("p", "Use notes to record useful feedback or explain grading decisions."),
            ("p", "For example:"),
            ("list", [
                "Good composition",
                "Correct exposure",
                "Creative use of depth of field",
                "ISO was higher than the requested range",
                "Missing EXIF information",
            ]),
            ("p", "Notes help keep the reasoning behind a grade together with the student's result."),
        ],
    ),
    (
        "9. VIEW CLASS RESULTS",
        [
            ("p", "After grading, PhotoGrade provides an overview of the class results."),
            ("p", "You can review:"),
            ("list", ["Individual student results", "Individual photo scores", "Total scores", "Class average", "Notes"]),
            ("p", "The Results screen allows you to inspect the grading information before exporting it."),
        ],
    ),
    (
        "10. EXPORT RESULTS",
        [
            ("p", "PhotoGrade can export class results to an Excel file."),
            ("p", "The exported file can be used for further processing, record keeping, or sharing."),
            ("p", "Before exporting, review the Results screen to make sure the grading information is correct."),
        ],
    ),
    (
        "11. PREVIOUS CLASSES",
        [
            ("p", "Previously saved classes can be accessed from the Previous Classes section on the Home Screen."),
            ("p", "This allows you to return to existing class data without creating the class again."),
            ("p", "You can open a saved class and continue reviewing its results or working with its stored information."),
        ],
    ),
    (
        "12. EXAMPLE WORKFLOW",
        [
            ("p", "Imagine a photography teacher creates an assignment requiring students to use:"),
            ("lines", ["ISO: 100–400", "Aperture: f/4–f/8", "Shutter Speed: 1/125–1/500"]),
            ("p", "The teacher creates a new class and adds the students' photos."),
            ("p", "PhotoGrade reads the available EXIF data from each photo and evaluates the configured technical requirements."),
            ("p", "The teacher then reviews the automatic scores, adds a manual score based on the artistic quality of each photo, and writes notes where necessary."),
            ("p", "After reviewing all students, the teacher opens the Results screen, checks the class average and individual results, and exports the final results to Excel."),
        ],
    ),
    (
        "13. TIPS",
        [
            ("list", [
                "Make sure your photos contain the EXIF information required by your rules.",
                "Review automatic scores before assigning the final teacher score.",
                "Use notes to explain important grading decisions.",
                "Always review the Results screen before exporting.",
                "Keep your class data organized so previous classes are easy to find.",
            ]),
        ],
    ),
    (
        "14. GETTING STARTED",
        [
            ("p", "If this is your first time using PhotoGrade, start by creating a New Class."),
            ("p", "Add your students and their photos, configure the grading rules if you want to use automatic technical grading, then review and complete the results."),
            ("p", "PhotoGrade is designed to make the technical and organizational parts of photography grading easier, while keeping the final evaluation in the teacher's hands."),
        ],
    ),
    (
        "15. SAVE & CONTINUE, SEARCH AND SETTINGS",
        [
            ("p", "While grading, the bar above the photo shows how many photos in the current queue already have a confirmed Total Score. Press Save to keep your place."),
            ("p", "The next time you open PhotoGrade, the Home Screen shows Continue (Class Name) Grading so you can resume where you stopped."),
            ("list", [
                "Only one saved grading session can exist at a time. Finish it before saving progress for a different class or a different student.",
                "The saved progress is removed automatically once every photo in the queue has a confirmed score.",
                "If you exit with unsaved progress, PhotoGrade asks you to confirm first.",
            ]),
            ("p", "Use the search field above the class list (Home Screen) or the student list (Class Screen) to filter by name. Clear the field to see everything again."),
            ("p", "Settings (Home Screen) lets you choose the default System/Teacher weights for new classes, whether deleting asks for confirmation, and whether EXIF information is shown while grading."),
        ],
    ),
]

# Wide enough to use the space, narrow enough to fit inside the
# window at its minimum size once padding and the scrollbar are
# accounted for.
TEXT_WRAP = 720


class HelpScreen:
    """
    The "How to Use" Help screen: takes a parent frame, builds its own
    widgets into it, and calls `on_back()` when the user presses Back.

    Purely static content -- it never touches grading, storage or
    class data. The header (Back button + title) stays fixed and only
    the sections below it scroll.
    """

    def __init__(self, parent, on_back):

        self.container = theme.page(parent)

        theme.screen_header(
            self.container,
            PAGE_TITLE,
            subtitle="A short guide to the PhotoGrade workflow and its main features.",
            on_back=on_back
        )

        self.create_sections()

    # -----------------------------------------
    # SECTIONS
    # -----------------------------------------

    def create_sections(self):

        scroll_frame = ctk.CTkScrollableFrame(
            self.container,
            fg_color="transparent"
        )

        scroll_frame.pack(
            fill="both",
            expand=True
        )

        for heading, blocks in SECTIONS:
            self.create_section(scroll_frame, heading, blocks)

    def create_section(self, parent, heading, blocks):

        card = theme.card(parent)

        card.pack(
            fill="x",
            padx=(0, 8),
            pady=(0, 14)
        )

        theme.label(
            card,
            heading,
            size=16,
            weight="bold",
            color=theme.ACCENT,
            anchor="w"
        ).pack(
            fill="x",
            padx=22,
            pady=(18, 8)
        )

        for kind, content in blocks:

            if kind == "p":
                self.create_paragraph(card, content)
            elif kind == "list":
                self.create_bullet_list(card, content)
            elif kind == "lines":
                self.create_highlight(card, content)

        # Bottom breathing room inside the card.
        ctk.CTkFrame(
            card,
            height=10,
            fg_color="transparent"
        ).pack()

    def create_paragraph(self, card, text):

        theme.label(
            card,
            text,
            size=14,
            wraplength=TEXT_WRAP,
            justify="left",
            anchor="w"
        ).pack(
            fill="x",
            padx=22,
            pady=(0, 8)
        )

    def create_bullet_list(self, card, items):

        for item in items:

            theme.label(
                card,
                f"•  {item}",
                size=14,
                color=theme.TEXT,
                wraplength=TEXT_WRAP - 25,
                justify="left",
                anchor="w"
            ).pack(
                fill="x",
                padx=(42, 22),
                pady=(0, 3)
            )

        # Small gap after the list, before the next block.
        ctk.CTkFrame(
            card,
            height=5,
            fg_color="transparent"
        ).pack()

    def create_highlight(self, card, lines):
        """
        Short lines that should stand out from body text (the
        workflow chain, example rule values) in a tinted box using
        the app's amber accent.
        """

        box = ctk.CTkFrame(
            card,
            corner_radius=8,
            fg_color=theme.TINTS[theme.ACCENT]
        )

        box.pack(
            fill="x",
            padx=22,
            pady=(0, 10)
        )

        for line in lines:

            theme.label(
                box,
                line,
                size=14,
                weight="bold",
                color=theme.ACCENT,
                wraplength=TEXT_WRAP - 30,
                justify="left",
                anchor="w"
            ).pack(
                fill="x",
                padx=15,
                pady=6
            )

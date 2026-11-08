"""
Data model for the Class -> Student -> Image relationship
(new feature: Teacher Grading + multiple photos per student).

A "Class" isn't its own object yet -- app.py just keeps a list of
Student objects, since class_name is the only other thing tracked
per-class right now. Each Student owns the folder it was assigned
and every ImageRecord discovered inside that folder.

Keeping this as one small module -- rather than spreading these
fields across app.py as loose variables -- is what makes the *next*
step (average score per student -> DataFrame) simple later: every
number scoring needs already hangs off Student.images.

No CustomTkinter or GUI dependency here (spec section 8) -- same
rule as core/rules.py and core/scoring.py.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ImageRecord:
    """
    One graded photo belonging to one student. Independent scoring
    state per photo -- a student with 3 photos has 3 of these, and
    grading one never touches the others.
    """

    student_name: str
    image_path: Path

    # Filled in once the Rule Engine grades this photo
    # (core.scoring.grade_student). None until then.
    # rule_engine_score is always the score that counts toward
    # total_score: the automatic result, or the teacher's manual
    # override when rule_engine_overridden is True. The automatic
    # result is kept separately in rule_engine_auto_score so the two
    # can always be told apart (see core.teacher_scoring).
    rule_engine_score: float | None = None
    rule_engine_max_score: float | None = None
    rule_engine_auto_score: float | None = None
    rule_engine_overridden: bool = False

    # Filled in only after the professor presses Confirm on the
    # Teacher Grading panel. None before that -- see is_finalized().
    teacher_score: float | None = None
    teacher_max_score: float | None = None

    # None until Confirm is pressed for this photo.
    total_score: float | None = None

    # The core.scoring.GradingResult for this photo, kept around so
    # the GUI can re-render the per-factor GREEN/YELLOW/RED colors
    # without re-running the Rule Engine every time this photo is
    # shown again.
    grading_result: object = None

    # Optional teacher note for this specific photo (new feature:
    # Photo Notes). Mirrored into the matching
    # core.class_model.ClassPhotoEntry.note by gui/app.py so it
    # survives an app restart.
    note: str = ""

    def is_finalized(self):
        """
        True once the professor has confirmed a Teacher Grading
        score for this photo. `total_score` should not be treated as
        an official final grade before this is True.
        """

        return self.teacher_score is not None


@dataclass
class Student:
    """
    One student in the class. `images` stays empty until their
    folder/files have been scanned by core.image.scan_student_folder()
    / core.image.validate_selected_files() and turned into
    ImageRecords.
    """

    name: str
    folder_path: Path | None = None
    images: list = field(default_factory=list)
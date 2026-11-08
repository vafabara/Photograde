"""
Data model for a persisted Class (new feature: Class Management,
extended with per-photo data -- Rule Engine / Teacher / Total Score
and Photo Notes).

This is deliberately a *separate* concept from core.student.Student:

  - core.student.Student / ImageRecord hold live, in-memory review
    state (scanned ImageRecord objects, Rule Engine / Teacher scores)
    for whatever review flow is currently on screen.

  - ClassRecord / ClassStudentEntry / ClassPhotoEntry hold the
    lightweight, JSON-safe summary of a class (name, students,
    photos, and each photo's persisted scores/note) that gets
    written to disk via storage.class_storage so it survives an app
    restart. Nothing here is CustomTkinter-aware or scans folders
    itself -- that stays in core.image / student_setup.py / the
    Class Screen, which pass already-known photo paths in here.

No CustomTkinter dependency here (spec section 8) -- same rule as
core/rules.py and core/scoring.py.
"""

import math
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .student import ImageRecord


class ClassError(ValueError):
    """Raised when a Class or Student fails validation."""


def _is_valid_score(value):
    """
    True for a real, usable score -- a number that isn't NaN.
    None (not graded yet), NaN, and anything non-numeric are all
    treated as "no score" so they can never distort an average.
    """

    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and not math.isnan(value)
    )


@dataclass
class ClassPhotoEntry:
    """
    One persisted photo belonging to one student in a Class
    (new feature: Student DataFrame / Photo Notes). Scores start as
    None (-> NaN in the Student DataFrame) until that photo is
    actually graded through the existing Rule Engine / Teacher
    Grading flow -- nothing here computes a score itself.
    """

    path: str
    rule_engine_score: float | None = None
    teacher_score: float | None = None
    total_score: float | None = None
    note: str = ""

    # Teacher override of the Rule Engine score (new feature).
    # rule_engine_score above is always the score that counts (the
    # manual one when rule_engine_overridden is True);
    # rule_engine_auto_score keeps what the Rule Engine itself
    # calculated, so the two stay distinguishable. Old saved classes
    # have neither key and load as "not overridden".
    rule_engine_auto_score: float | None = None
    rule_engine_overridden: bool = False

    def to_dict(self):
        return {
            "path": self.path,
            "rule_engine_score": self.rule_engine_score,
            "teacher_score": self.teacher_score,
            "total_score": self.total_score,
            "note": self.note,
            "rule_engine_auto_score": self.rule_engine_auto_score,
            "rule_engine_overridden": self.rule_engine_overridden,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            path=data["path"],
            rule_engine_score=data.get("rule_engine_score"),
            teacher_score=data.get("teacher_score"),
            total_score=data.get("total_score"),
            note=data.get("note", ""),
            rule_engine_auto_score=data.get("rule_engine_auto_score"),
            rule_engine_overridden=bool(data.get("rule_engine_overridden", False)),
        )


@dataclass
class ClassStudentEntry:
    """One student's persisted info within a Class."""

    name: str
    folder_path: str
    photo_count: int
    photos: list = field(default_factory=list)  # list[ClassPhotoEntry]

    @property
    def average_total_score(self):
        """
        Average Total Score across this student's photos (new
        feature: student list Avg Total column). Reads the exact
        same `total_score` values the Student DataFrame uses -- this
        is not a second, independent calculation. Returns float("nan")
        if no photo has a Total Score yet, never 0.
        """

        scores = [
            photo.total_score
            for photo in self.photos
            if photo.total_score is not None
        ]

        if not scores:
            return float("nan")

        return round(sum(scores) / len(scores), 1)

    @property
    def is_completed(self):
        """
        True once every one of this student's photos has a Total
        Score (new feature: Class Results page). Reads the exact
        same `total_score` values as average_total_score -- not a
        second calculation. A student with no photos yet is never
        considered completed.
        """

        return bool(self.photos) and all(
            photo.total_score is not None for photo in self.photos
        )


@dataclass
class ClassRecord:
    """
    One persisted Class. `class_id` is a UUID generated once and
    never derived from `class_name` (spec section 19) -- so renaming
    a class later won't need to touch its storage folder.
    """

    class_id: str
    class_name: str
    students: list = field(default_factory=list)  # list[ClassStudentEntry]

    # The RuleEngineConfig this class was actually graded with, as a
    # plain dict (core.rules.RuleEngineConfig.to_dict()) -- new
    # feature: reopening a class for grading needs to know which
    # configuration to reuse. None means "never configured yet"
    # (including every class saved before this field existed --
    # spec: must load safely as None, not crash). The professor
    # choosing "Skip" is stored as {"skipped": True} rather than a
    # real config, since Skip means no Rule Engine grading at all.
    #
    # Deliberately the *actual* configuration, not just a preset
    # name -- storage.rule_presets entries can be renamed/deleted
    # later without changing what an already-graded class remembers.
    rule_config: dict | None = None

    @property
    def student_count(self):
        return len(self.students)

    @property
    def total_photo_count(self):
        return sum(student.photo_count for student in self.students)

    @property
    def completed_student_count(self):
        """
        Number of students whose every photo has a Total Score
        (new feature: Class Results page). Sourced from
        ClassStudentEntry.is_completed -- not a second calculation.
        """

        return sum(1 for student in self.students if student.is_completed)

    @property
    def pending_student_count(self):
        return self.student_count - self.completed_student_count

    def _graded_total_scores(self):
        """
        Every valid photo-level Total Score in the whole class, in
        one flat list (new feature: Class Average). Reads the same
        `total_score` values as ClassStudentEntry.average_total_score
        -- just pooled across students instead of averaged per
        student.
        """

        return [
            photo.total_score
            for student in self.students
            for photo in student.photos
            if _is_valid_score(photo.total_score)
        ]

    @property
    def graded_photo_count(self):
        """Number of photos in the class that have a valid Total Score."""

        return len(self._graded_total_scores())

    @property
    def average_total_score(self):
        """
        Class Average (new feature): the mean of every graded
        photo's Total Score across the whole class -- deliberately
        NOT the mean of the per-student averages, so a student with
        10 photos counts for more than a student with 2. Returns
        NaN if nothing has been graded yet, never 0.
        """

        scores = self._graded_total_scores()

        if not scores:
            return float("nan")

        return round(sum(scores) / len(scores), 2)

    def to_dict(self):
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "student_count": self.student_count,
            "rule_config": self.rule_config,
            "students": [
                {
                    "name": student.name,
                    "folder_path": student.folder_path,
                    "photo_count": student.photo_count,
                    "photos": [
                        photo.to_dict() for photo in student.photos
                    ],
                }
                for student in self.students
            ],
        }

    @classmethod
    def from_dict(cls, data):

        students = [
            ClassStudentEntry(
                name=entry["name"],
                folder_path=entry["folder_path"],
                photo_count=entry["photo_count"],
                photos=[
                    ClassPhotoEntry.from_dict(photo_data)
                    for photo_data in entry.get("photos", [])
                ],
            )
            for entry in data.get("students", [])
        ]

        return cls(
            class_id=data["class_id"],
            class_name=data["class_name"],
            # .get() -- old saved classes never had this key, and
            # must still load with rule_config=None rather than
            # raising KeyError (spec: backward compatibility).
            rule_config=data.get("rule_config"),
            students=students,
        )


def new_class_id():
    return str(uuid.uuid4())


def build_class_record(class_name, class_students):
    """
    Build a ClassRecord from a list of core.student.Student objects
    -- the objects StudentFoldersScreen hands back once every
    student has a validated photo folder/file selection (spec
    section 3). Each discovered image becomes a ClassPhotoEntry with
    no score yet -- scores get filled in later as photos are graded
    (see gui/app.py on_teacher_confirm).

    Raises ClassError if two students share the same name, case
    insensitively (spec section 20).
    """

    class_name = class_name.strip()

    if not class_name:
        raise ClassError("Class name is required.")

    seen_names = set()
    entries = []

    for student in class_students:

        name = student.name.strip()

        if name.lower() in seen_names:
            raise ClassError(f"Duplicate student name: {name}")

        seen_names.add(name.lower())

        entries.append(
            ClassStudentEntry(
                name=name,
                folder_path=str(student.folder_path or ""),
                photo_count=len(student.images),
                photos=[
                    ClassPhotoEntry(path=str(image.image_path))
                    for image in student.images
                ],
            )
        )

    return ClassRecord(
        class_id=new_class_id(),
        class_name=class_name,
        students=entries,
    )


def validate_new_student_name(class_record, name):
    """
    Raise ClassError if `name` is blank or already used (case
    insensitively) by another student in `class_record` (spec
    section 20). Returns the stripped name on success.
    """

    name = name.strip()

    if not name:
        raise ClassError("Please enter a student name.")

    existing = {student.name.lower() for student in class_record.students}

    if name.lower() in existing:
        raise ClassError(f'A student named "{name}" already exists in this class.')

    return name


def image_records_from_student(student_entry):
    """
    Rebuild the runtime core.student.ImageRecord objects for one
    persisted ClassStudentEntry -- the missing bridge between saved
    class data and the existing Rule Engine / Teacher Grading review
    flow (new feature: "Start Grading" / reopening a class).

    Each photo's already-confirmed Rule Engine / Teacher / Total
    score and note are restored straight from its ClassPhotoEntry,
    so re-entering the review flow never loses previously-graded
    work. EXIF/technical metadata isn't restored here -- it's
    re-read from disk the same way it already is for any photo the
    review flow displays (core.image.load_image, called from
    gui/app.py.load_and_display), so there's nothing to duplicate.
    """

    return [
        ImageRecord(
            student_name=student_entry.name,
            image_path=Path(photo.path),
            rule_engine_score=photo.rule_engine_score,
            teacher_score=photo.teacher_score,
            total_score=photo.total_score,
            note=photo.note,
            rule_engine_auto_score=photo.rule_engine_auto_score,
            rule_engine_overridden=photo.rule_engine_overridden,
        )
        for photo in student_entry.photos
    ]
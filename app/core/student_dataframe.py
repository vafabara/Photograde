"""
Student DataFrame (new feature, spec section 6).

Builds a simple, per-photo pandas DataFrame for one student, read
straight from the already-persisted per-photo scores in
core.class_model.ClassStudentEntry/ClassPhotoEntry -- the same data
that powers the Class Screen's Avg Total column. This module does
not compute or invent any score itself; it only shapes existing
scores into a table.

Also holds the class-level frame (build_class_dataframe) used by the
Excel export -- one row per student, shaped from the same
ClassStudentEntry properties the Class Results screen displays.

No CustomTkinter dependency here (spec section 8) -- same rule as
core/rules.py and core/scoring.py. gui/student_detail.py renders
whatever this returns.
"""

import pandas as pd

COLUMNS = ["Photo", "Rule Engine Score", "Teacher Score", "Total Score"]
NOTE_COLUMN = "Note"
SOURCE_COLUMN = "Rule Engine Source"
AUTO_COLUMN = "Automatic Rule Score"

CLASS_COLUMNS = ["Student", "Photos", "Average", "Status"]


def build_student_dataframe(student_entry, include_notes=False, include_override=False):
    """
    `student_entry` -- a core.class_model.ClassStudentEntry.

    Returns a pandas DataFrame with one row per photo ("Pic 1",
    "Pic 2", ...) followed by a trailing "Average" row. Missing
    scores are NaN (never 0) -- both for individual photos that
    haven't been graded yet, and for the Average of an empty/entirely
    ungraded column.

    `include_notes` (default False, so the Student Detail screen's
    table is unchanged) adds a trailing "Note" column read straight
    from ClassPhotoEntry.note -- used by the Excel export. The
    Average row has no note.

    `include_override` (default False, same reason) adds two columns
    placed before the note: "Rule Engine Source" ("Automatic" or
    "Manual override") and "Automatic Rule Score" (what the Rule
    Engine itself calculated). "Rule Engine Score" always stays the
    score that counts toward the Total. Used by the Excel export.
    """

    rows = [
        {
            "Photo": f"Pic {index}",
            "Rule Engine Score": photo.rule_engine_score,
            "Teacher Score": photo.teacher_score,
            "Total Score": photo.total_score,
            SOURCE_COLUMN: (
                "Manual override" if photo.rule_engine_overridden else "Automatic"
            ),
            AUTO_COLUMN: photo.rule_engine_auto_score,
            NOTE_COLUMN: photo.note or "",
        }
        for index, photo in enumerate(student_entry.photos, start=1)
    ]

    columns = list(COLUMNS)

    if include_override:
        columns += [SOURCE_COLUMN, AUTO_COLUMN]

    if include_notes:
        columns.append(NOTE_COLUMN)

    dataframe = pd.DataFrame(rows, columns=columns)

    numeric_columns = ["Rule Engine Score", "Teacher Score", "Total Score"]

    average_row = {"Photo": "Average"}

    if include_override:
        average_row[SOURCE_COLUMN] = ""
        average_row[AUTO_COLUMN] = float("nan")

    if include_notes:
        average_row[NOTE_COLUMN] = ""

    for column in numeric_columns:
        average_row[column] = dataframe[column].mean() if not dataframe.empty else float("nan")

    dataframe = pd.concat(
        [dataframe, pd.DataFrame([average_row])],
        ignore_index=True
    )

    return dataframe


def build_class_dataframe(class_record):
    """
    `class_record` -- a core.class_model.ClassRecord.

    Returns a pandas DataFrame with one row per student -- the same
    Student / Photos / Average / Status columns the Class Results
    screen shows -- followed by a trailing "Class Average" row that
    mirrors the Class Average card. Every value is read from
    ClassStudentEntry / ClassRecord properties (average_total_score,
    is_completed), so nothing is recalculated here.

    Same rule as the Results screen: a Pending student's Average is
    NaN (blank in Excel), never a partial number and never 0.
    """

    rows = [
        {
            "Student": student.name,
            "Photos": student.photo_count,
            "Average": (
                student.average_total_score
                if student.is_completed
                else float("nan")
            ),
            "Status": "Completed" if student.is_completed else "Pending",
        }
        for student in class_record.students
    ]

    rows.append(
        {
            "Student": "Class Average",
            "Photos": class_record.total_photo_count,
            "Average": class_record.average_total_score,
            "Status": "",
        }
    )

    return pd.DataFrame(rows, columns=CLASS_COLUMNS)

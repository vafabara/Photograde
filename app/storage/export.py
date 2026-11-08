import csv
import json
import re

import pandas as pd

from app.core.converters import exif_value
from app.core.student_dataframe import (
    build_class_dataframe,
    build_student_dataframe,
)


def build_export_data(data):
    return {
        "filename": data["path"].name,
        "format": data["format"],
        "file_size_mb": round(data["file_size_mb"], 2),
        "width": data["size"][0],
        "height": data["size"][1],
        "color_mode": data["mode"],
        "make": exif_value(data["make"]),
        "model": exif_value(data["model"]),
        "lens_model": exif_value(data["lens_model"]),
        "iso": exif_value(data["iso"]),
        "aperture": exif_value(data["fnum"]),
        "shutter_speed": str(exif_value(data["exposure_time"])),
        "focal_length": exif_value(data["focal"]),
        "date_taken": exif_value(data["date"]),
        "flash": exif_value(data["flash"]),
        "white_balance": exif_value(data["white_balance"]),
    }


def export_to_json(data, path):
    export_data = build_export_data(data)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)


def export_to_csv(data, path):
    export_data = build_export_data(data)

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(export_data.keys())
        writer.writerow(export_data.values())


# -----------------------------------------------------------------
# EXCEL EXPORT (new feature: Class Results -> Export)
# -----------------------------------------------------------------
# Workbook layout:
#   Sheet 1        "Class Results"  -- build_class_dataframe()
#   One per student (named after them) -- build_student_dataframe(
#                                         include_notes=True,
#                                         include_override=True)
#
# Everything is read through the existing DataFrame builders, so
# nothing here computes or stores a score. Sheet names are only
# sanitized for Excel's rules -- the student's real name in the
# ClassRecord is never changed.

CLASS_SHEET_NAME = "Class Results"

MAX_SHEET_NAME_LENGTH = 31
MAX_COLUMN_WIDTH = 60

# Characters Excel forbids in a sheet name.
INVALID_SHEET_CHARS = re.compile(r"[:\\/?*\[\]]")

# Characters Windows forbids in a filename (used for the default
# name suggested in the Save dialog).
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')


def _clean_sheet_name(text):
    """
    Excel also rejects sheet names that start or end with an
    apostrophe, and blank names, so trim those too.
    """

    return text.strip().strip("'").strip()


def make_sheet_name(name, used_names):
    """
    Turn a student name into a valid, unique Excel sheet name.

    - invalid characters (: \\ / ? * [ ]) become "_"
    - trimmed to 31 characters
    - unique *case-insensitively* (Excel treats "ali" and "Ali" as
      the same sheet): a clash gets a numeric suffix -- Ali, Ali_2,
      Ali_3 -- and the base is shortened so the suffix still fits
      inside 31 characters

    `used_names` is a set of lowercase names already taken in this
    workbook; the returned name is added to it.
    """

    base = _clean_sheet_name(INVALID_SHEET_CHARS.sub("_", str(name)))
    base = _clean_sheet_name(base[:MAX_SHEET_NAME_LENGTH]) or "Student"

    candidate = base
    counter = 2

    while candidate.lower() in used_names:
        suffix = f"_{counter}"
        room = MAX_SHEET_NAME_LENGTH - len(suffix)
        candidate = _clean_sheet_name(base[:room]) + suffix
        counter += 1

    used_names.add(candidate.lower())

    return candidate


def default_export_filename(class_name):
    """
    Suggested filename for the Save dialog: "<ClassName>_Results.xlsx",
    with any characters Windows forbids in filenames replaced by "_".
    """

    safe_name = INVALID_FILENAME_CHARS.sub("_", class_name).strip() or "Class"

    return f"{safe_name}_Results.xlsx"


def _autofit_columns(worksheet):
    """Widen each column to fit its longest value (capped), so names
    and notes are readable without the teacher resizing by hand."""

    for column_cells in worksheet.columns:

        longest = max(
            (len(str(cell.value)) for cell in column_cells if cell.value is not None),
            default=0
        )

        worksheet.column_dimensions[column_cells[0].column_letter].width = min(
            longest + 2,
            MAX_COLUMN_WIDTH
        )


def export_class_to_excel(class_record, path):
    """
    Write `class_record` (a core.class_model.ClassRecord) to an
    .xlsx workbook at `path`: a "Class Results" sheet followed by
    one sheet per student with that student's per-photo scores and
    notes.

    Raises whatever pandas/openpyxl/the OS raises (ImportError if
    openpyxl isn't installed, OSError if the file can't be written)
    -- the caller (gui/results_screen.py) turns those into messages.
    """

    # "history" is a name Excel reserves for its own use.
    used_names = {CLASS_SHEET_NAME.lower(), "history"}

    with pd.ExcelWriter(path, engine="openpyxl") as writer:

        build_class_dataframe(class_record).to_excel(
            writer,
            sheet_name=CLASS_SHEET_NAME,
            index=False
        )

        for student in class_record.students:

            sheet_name = make_sheet_name(student.name, used_names)

            build_student_dataframe(
                student,
                include_notes=True,
                include_override=True
            ).to_excel(
                writer,
                sheet_name=sheet_name,
                index=False
            )

        for worksheet in writer.sheets.values():
            _autofit_columns(worksheet)

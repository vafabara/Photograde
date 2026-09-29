"""
Persistence for Class records (new feature: Class Management).

Mirrors storage/recent_files.py: plain JSON on disk, no database.
Each class gets its own folder so future per-class data (Rule
Engine results, grading, DataFrame, student averages, final grades
-- spec section 23) has somewhere to live without another storage
rewrite:

    classes/
    ├── <class_id>/
    │   └── class.json
    └── ...

GUI code never touches this module's file paths or JSON directly --
only App (the controller) calls save_class / load_all_classes /
load_class / delete_class and hands the resulting ClassRecord
objects to the GUI screens to render (spec section 17):

    HomeScreen / ClassScreen  ->  App  ->  class_storage  ->  classes/<id>/class.json

Deleting a class only ever removes classes/<class_id>/ -- it never
touches folder_path, which points at the professor's own photos
(spec section 11).
"""

import json
import os
import shutil
from pathlib import Path

from ..core.class_model import ClassRecord

CLASSES_DIR = Path(__file__).resolve().parents[2] / "classes"


class ClassStorageError(Exception):
    """Raised when a class storage operation fails."""


def _class_dir(class_id):
    return CLASSES_DIR / class_id


def _class_file(class_id):
    return _class_dir(class_id) / "class.json"


def save_class(class_record):
    """
    Write `class_record` to classes/<class_id>/class.json, creating
    the class's folder if needed. Used for both the initial save
    (spec section 3) and every later update -- add/remove student,
    add photos (spec sections 12, 14, 15).
    """

    try:
        class_dir = _class_dir(class_record.class_id)
        class_dir.mkdir(parents=True, exist_ok=True)

        class_file = _class_file(class_record.class_id)
        temp_file = class_file.with_name(class_file.name + ".tmp")

        # Write to a temp file in the same folder first, then swap it
        # in with os.replace() (atomic) -- so a crash mid-write can
        # never leave class.json half-written.
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(class_record.to_dict(), f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_file, class_file)

    except OSError as error:
        raise ClassStorageError(f"Could not save class: {error}")


def load_all_classes():
    """
    Load every persisted Class for the Home Page's Previous Classes
    list. Skips (rather than crashes on) any class folder with a
    missing or invalid class.json -- spec section 21.
    """

    if not CLASSES_DIR.exists():
        return []

    classes = []

    for class_dir in CLASSES_DIR.iterdir():

        if not class_dir.is_dir():
            continue

        class_file = class_dir / "class.json"

        if not class_file.exists():
            continue

        try:
            with open(class_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            classes.append(ClassRecord.from_dict(data))

        except (json.JSONDecodeError, OSError, KeyError):
            # Corrupt or incomplete class folder -- skip it rather
            # than crashing the whole Home Page (spec section 21).
            continue

    return classes


def load_class(class_id):
    """
    Load one Class by id. Returns None if it doesn't exist or its
    JSON is invalid, rather than raising -- callers (App) decide
    what to show the user in that case.
    """

    class_file = _class_file(class_id)

    if not class_file.exists():
        return None

    try:
        with open(class_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        return ClassRecord.from_dict(data)

    except (json.JSONDecodeError, OSError, KeyError):
        return None


def delete_class(class_id):
    """
    Delete a class's storage folder only (spec section 11) -- the
    student photo folders on disk are never touched. A missing
    folder is treated as already-deleted rather than an error.
    """

    class_dir = _class_dir(class_id)

    if not class_dir.exists():
        return

    try:
        shutil.rmtree(class_dir)
    except OSError as error:
        raise ClassStorageError(f"Could not delete class: {error}")

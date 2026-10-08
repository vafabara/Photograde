"""
Persistence for the Grading Session checkpoint (new feature:
Grading Progress, Save & Continue).

A checkpoint is a small JSON file written next to the class folders:

    classes/
    ├── <class_id>/
    │   └── class.json
    └── grading(<class name>).json     <- this module

It is NOT a replacement for class.json. class.json is still the
permanent record of a class (and still receives every confirmed score
and note immediately, exactly as before). The checkpoint only
remembers where the teacher stopped -- which class, which queue,
which photo -- plus a snapshot of the per-photo grading data, so the
session can be resumed later.

A checkpoint is identified by its *scope*: the class (class_id) and
which queue it covers -- the whole class (student_name is None) or
one named student. Rules enforced here:
  - only ONE checkpoint may exist at a time, across all classes
  - within a class, one student's checkpoint can never be overwritten
    by another student's (or by a whole-class one)
  - a checkpoint is deleted once its grading session is finished

Like class_storage.py, this module has no GUI code. App (the
controller) calls it and shows any error message itself.
"""

import json
import re

from . import class_storage

BLOCKED_MESSAGE = (
    "Another class currently has unfinished grading progress. "
    "Please finish or discard that grading session before starting a new one."
)

BLOCKED_STUDENT_MESSAGE = (
    "Another student in this class currently has unfinished grading progress. "
    "Please finish that grading session before starting a new one."
)

# Windows forbids these characters in filenames, and a class name
# can contain them (e.g. "Intro: Lighting / Portraits").
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')

SESSION_PATTERN = "grading(*).json"

# A checkpoint missing any of these is treated as unusable.
# ("student_name" is optional: it is None/absent for a whole-class queue.)
REQUIRED_KEYS = ("class_id", "class_name", "current_index", "photos")


class GradingSessionError(Exception):
    """Raised when a grading session operation fails or is not allowed."""


def _session_file(class_name):
    """classes/grading(<class name>).json, with forbidden characters replaced."""

    safe_name = INVALID_FILENAME_CHARS.sub("_", class_name).strip() or "Class"

    return class_storage.CLASSES_DIR / f"grading({safe_name}).json"


def _read_sessions():
    """
    Returns a list of (path, data) for every readable, valid
    checkpoint file. Corrupt or incomplete files are skipped rather
    than crashing the Home Page -- same tolerance class_storage has
    for a bad class.json.
    """

    classes_dir = class_storage.CLASSES_DIR

    if not classes_dir.exists():
        return []

    sessions = []

    for path in sorted(classes_dir.glob(SESSION_PATTERN)):

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

        except (json.JSONDecodeError, OSError):
            continue

        if not isinstance(data, dict):
            continue

        if not all(key in data for key in REQUIRED_KEYS):
            continue

        if not isinstance(data["photos"], list):
            continue

        sessions.append((path, data))

    return sessions


def load_active_session():
    """
    Returns the saved grading session as a dict, or None if there
    isn't one. Used by the Home Page to decide whether to show the
    "Continue (ClassName) Grading" option.
    """

    sessions = _read_sessions()

    if not sessions:
        return None

    return sessions[0][1]


def find_conflict(class_id, student_name):
    """
    Checks whether saving/starting grading for this scope would clash
    with an existing checkpoint. `student_name` is None for a
    whole-class queue.

    Returns an error message to show the teacher, or None if it is
    fine to go ahead (no checkpoint exists, or the existing one is
    for this very same class and queue).
    """

    for _, existing in _read_sessions():

        if existing["class_id"] != class_id:
            return BLOCKED_MESSAGE

        if existing.get("student_name") != student_name:
            return BLOCKED_STUDENT_MESSAGE

    return None


def save_session(session_data):
    """
    Write `session_data` (a dict built by App) to
    classes/grading(<class name>).json.

    Raises GradingSessionError if a checkpoint for a different class
    or a different student queue already exists (see find_conflict),
    or if the file can't be written.
    """

    conflict = find_conflict(
        session_data["class_id"],
        session_data.get("student_name")
    )

    if conflict:
        raise GradingSessionError(conflict)

    target = _session_file(session_data["class_name"])

    try:
        class_storage.CLASSES_DIR.mkdir(parents=True, exist_ok=True)

        with open(target, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        # If the class was saved earlier under a different name, that
        # older file is now stale -- remove it so there is never more
        # than one checkpoint file.
        for path, _ in _read_sessions():
            if path != target:
                path.unlink(missing_ok=True)

    except OSError as error:
        raise GradingSessionError(f"Could not save grading progress: {error}")


def delete_session(class_id):
    """
    Delete the checkpoint that belongs to `class_id`, if there is
    one. A missing file is not an error. Matches by class_id (not by
    filename) so it still works if the class name has changed.
    """

    for path, data in _read_sessions():

        if data["class_id"] != class_id:
            continue

        try:
            path.unlink(missing_ok=True)

        except OSError as error:
            raise GradingSessionError(
                f"Could not remove the saved grading progress: {error}"
            )
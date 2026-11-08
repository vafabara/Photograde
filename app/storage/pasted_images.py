"""
Saving images pasted from the clipboard (new feature: Ctrl+V when
adding a student's photos).

A pasted bitmap has no file, so it is written once to a folder next
to the class folders:

    classes/
    ├── pasted_photos/
    │   └── <student>_pasted_<YYYYMMDD_HHMMSS>.png     <- this module
    └── <class_id>/class.json

From then on it is an ordinary photo file: its path is stored in
ClassPhotoEntry.path exactly like a photo chosen with Select Files,
so grading, notes, persistence and export treat it the same way.
(load_all_classes() only looks at folders containing class.json, so
pasted_photos/ is never mistaken for a class.)

PNG is used because it is lossless -- the pasted pixels are kept
exactly. A pasted bitmap carries no EXIF data, so the Rule Engine
reports "EXIF missing" for it and the teacher scores it out of 100,
as for any photo without metadata.

Like class_storage.py, this module has no GUI code.
"""

import re
from datetime import datetime

from ..core.clipboard import ClipboardError, grab_clipboard_photos
from ..core.image import (
    IMAGE_EXTENSIONS,
    FolderValidationError,
    ensure_photo_slots,
    validate_selected_files,
)
from . import class_storage

PASTED_DIR_NAME = "pasted_photos"

# Same set of forbidden filename characters the rest of the app
# replaces (export file names, grading checkpoint names).
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')


def _pasted_dir():
    """Read at call time so tests can point CLASSES_DIR elsewhere."""

    return class_storage.CLASSES_DIR / PASTED_DIR_NAME


def save_pasted_image(image, student_name):
    """
    Write a pasted PIL image to pasted_photos/ and return its Path.
    The name is "<student>_pasted_<timestamp>.png"; a counter is
    added if that name is already taken, so nothing is overwritten.
    """

    safe_name = INVALID_FILENAME_CHARS.sub("_", student_name or "").strip() or "student"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        folder = _pasted_dir()
        folder.mkdir(parents=True, exist_ok=True)

        path = folder / f"{safe_name}_pasted_{stamp}.png"
        counter = 2

        while path.exists():
            path = folder / f"{safe_name}_pasted_{stamp}_{counter}.png"
            counter += 1

        if image.mode not in ("RGB", "RGBA", "L"):
            image = image.convert("RGB")

        image.save(path, "PNG")

    except (OSError, ValueError) as error:
        raise ClipboardError(f"Could not save the pasted image: {error}")

    return path


def paste_from_clipboard(student_name, existing_count):
    """
    Turn the clipboard into photo files for one student who already
    has `existing_count` photos.

    Returns a list of Paths ready to add -- or None if the clipboard
    holds no image or image files (so the caller can say so).

    Raises ClipboardError / FolderValidationError, with a message
    ready to show, if the clipboard can't be read, the student has no
    room left, or copied files are not supported images. The limit is
    checked BEFORE a pasted bitmap is saved, so a refused paste never
    leaves a stray file behind.
    """

    content = grab_clipboard_photos()

    if content is None:
        return None

    kind, value = content

    if kind == "image":
        ensure_photo_slots(existing_count, 1)
        return [save_pasted_image(value, student_name)]

    # Files copied in the file manager: used where they are, exactly
    # like Select Files. Anything that isn't a supported image makes
    # the whole paste fail rather than adding some and skipping others.
    if any(path.suffix.lower() not in IMAGE_EXTENSIONS for path in value):
        raise FolderValidationError(
            "The clipboard contains files that are not supported images."
        )

    paths = validate_selected_files(value)
    ensure_photo_slots(existing_count, len(paths))

    return paths

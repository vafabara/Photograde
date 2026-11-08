import os
from pathlib import Path
from PIL import Image

from .metadata import extract_metadata


def load_image(loc):
    """
    Load an image and return image-related information
    together with its EXIF metadata.
    """

    loc = loc.strip().strip('"').strip("'")

    path = Path(loc)

    # -----------------------------------------
    # OPEN IMAGE
    # -----------------------------------------

    image = Image.open(path)

    # -----------------------------------------
    # BASIC IMAGE INFORMATION
    # -----------------------------------------

    image_format = image.format
    size = image.size
    mode = image.mode

    # -----------------------------------------
    # FILE SIZE
    # -----------------------------------------

    file_size = path.stat().st_size
    file_size_mb = file_size / (1024 ** 2)

    # -----------------------------------------
    # EXIF METADATA
    # -----------------------------------------

    metadata = extract_metadata(path)

    # -----------------------------------------
    # RETURN DATA
    # -----------------------------------------

    return {
        "image": image,
        "path": path,
        "format": image_format,
        "size": size,
        "mode": mode,
        "file_size_mb": file_size_mb,

        # EXIF metadata
        **metadata,
    }


# -----------------------------------------------------------------
# STUDENT PHOTO DISCOVERY (Select Folder, and now also Select
# Files -- new feature: single/multiple individual image selection
# so a one-photo student doesn't need a whole folder just for one
# image). Both entry points share the same extension/count/size
# limits so neither path is more permissive than the other.
# -----------------------------------------------------------------

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

MAX_IMAGES_PER_STUDENT = 6
MAX_FOLDER_SIZE_MB = 100


class FolderValidationError(ValueError):
    """Raised when a student's photo folder/selection fails validation."""


class PhotoLimitError(FolderValidationError):
    """
    Raised when adding photos would push a student past
    MAX_IMAGES_PER_STUDENT. A subclass of FolderValidationError so
    every existing `except FolderValidationError` handler already
    shows its message.
    """


def discover_images(folder_path):
    """
    Return every valid image file directly inside `folder_path`,
    sorted by filename. Only files whose extension is in
    IMAGE_EXTENSIONS are counted -- anything else (a stray .txt,
    .psd, folder, etc.) is ignored rather than crashing the scan.
    """

    folder_path = Path(folder_path)

    return sorted(
        path for path in folder_path.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def scan_student_folder(folder_path):
    """
    Discover and validate the images inside one student's folder.

    Returns the list of image Paths on success.

    Raises FolderValidationError (with a message ready to show
    directly in the GUI) if:
      - the folder has no supported images at all
      - the folder has more than MAX_IMAGES_PER_STUDENT images
      - the images inside total more than MAX_FOLDER_SIZE_MB

    This runs before any Rule Engine / Teacher Grading processing
    starts, so a bad folder never gets partway into the review flow.
    """

    images = discover_images(folder_path)

    if not images:
        raise FolderValidationError(
            "This folder does not contain any supported image files."
        )

    if len(images) > MAX_IMAGES_PER_STUDENT:
        raise FolderValidationError(
            f"This folder contains more than {MAX_IMAGES_PER_STUDENT} images."
        )

    total_size_mb = sum(
        path.stat().st_size for path in images
    ) / (1024 ** 2)

    if total_size_mb > MAX_FOLDER_SIZE_MB:
        raise FolderValidationError(
            f"The total image size exceeds the {MAX_FOLDER_SIZE_MB} MB limit."
        )

    return images


def validate_selected_files(file_paths):
    """
    Validate a list of individually-selected image files (new
    feature: Select Files, as an alternative to Select Folder).
    Enforces the same limits as scan_student_folder so neither
    selection path is more permissive than the other.

    Returns the sorted list of image Paths on success. Raises
    FolderValidationError on the same conditions scan_student_folder
    does (no valid images, too many images, total size too large),
    plus rejecting any file whose extension isn't supported.
    """

    paths = [Path(file_path) for file_path in file_paths]

    if not paths:
        raise FolderValidationError(
            "Please select at least one image file."
        )

    unsupported = [
        path for path in paths
        if path.suffix.lower() not in IMAGE_EXTENSIONS
    ]

    if unsupported:
        raise FolderValidationError(
            "One or more selected files are not supported image files."
        )

    if len(paths) > MAX_IMAGES_PER_STUDENT:
        raise FolderValidationError(
            f"You can select at most {MAX_IMAGES_PER_STUDENT} images."
        )

    total_size_mb = sum(
        path.stat().st_size for path in paths
    ) / (1024 ** 2)

    if total_size_mb > MAX_FOLDER_SIZE_MB:
        raise FolderValidationError(
            f"The total image size exceeds the {MAX_FOLDER_SIZE_MB} MB limit."
        )

    return sorted(paths)


# -----------------------------------------------------------------
# ADDING PHOTOS TO A STUDENT THAT ALREADY HAS SOME
#
# validate_selected_files / scan_student_folder only validate the
# *new* selection on its own. This is the one place that checks a
# selection against what the student already has, so every entry
# point (class setup, Class Screen, Add Student dialog, clipboard
# paste) applies the same duplicate and limit rules and none of
# them ever replaces existing photos.
# -----------------------------------------------------------------

def _path_key(path):
    """
    Identity of a photo file for duplicate detection: its absolute,
    normalised path (case-insensitive on Windows). Deliberately NOT
    the file name -- "IMG_001.jpg" from two different folders are
    two different photographs.
    """

    return os.path.normcase(os.path.abspath(str(path)))


def ensure_photo_slots(existing_count, needed=1):
    """
    Raise PhotoLimitError unless a student who already has
    `existing_count` photos has room for `needed` more. Checked
    before anything is written (e.g. before a pasted image is saved
    to disk), and by merge_student_photos for every other way of
    adding photos, so the message is the same everywhere.
    """

    remaining = max(0, MAX_IMAGES_PER_STUDENT - existing_count)

    if needed <= remaining:
        return

    if remaining == 0:
        raise PhotoLimitError(
            f"This student already has the maximum of "
            f"{MAX_IMAGES_PER_STUDENT} photos. No photos were added."
        )

    raise PhotoLimitError(
        f"You selected {needed} new photos, but only "
        f"{remaining} more can be added (maximum "
        f"{MAX_IMAGES_PER_STUDENT} per student). No photos were "
        f"added -- please select {remaining} or fewer."
    )


def merge_student_photos(existing_paths, new_paths):
    """
    Work out which of `new_paths` can be added to a student who
    already has `existing_paths`.

    Returns (to_add, duplicates):
      to_add      -- new Paths, in the order given, that are not
                     already present (and not repeated inside
                     `new_paths` itself)
      duplicates  -- Paths that were skipped because that exact file
                     is already there

    Raises PhotoLimitError -- adding nothing at all -- if the
    non-duplicate photos would not fit in the student's remaining
    slots, or FolderValidationError if the student's photos would
    exceed the total size limit. Refusing the whole selection (instead
    of quietly keeping "the first N") means the teacher decides which
    photos to leave out.

    The caller keeps `existing_paths` as they are and appends
    `to_add`, so existing photos, their order and their scores are
    never touched.
    """

    seen = {_path_key(path) for path in existing_paths}

    to_add = []
    duplicates = []

    for path in new_paths:

        key = _path_key(path)

        if key in seen:
            duplicates.append(Path(path))
            continue

        seen.add(key)
        to_add.append(Path(path))

    ensure_photo_slots(len(existing_paths), len(to_add))

    if to_add:

        total_bytes = 0

        for path in list(existing_paths) + to_add:
            try:
                total_bytes += Path(path).stat().st_size
            except OSError:
                # A photo that moved or was deleted since it was added
                # must not stop the teacher adding new ones.
                continue

        if total_bytes / (1024 ** 2) > MAX_FOLDER_SIZE_MB:
            raise FolderValidationError(
                f"The total image size exceeds the {MAX_FOLDER_SIZE_MB} MB limit."
            )

    return to_add, duplicates


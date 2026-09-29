import piexif
import pytest
from PIL import Image, UnidentifiedImageError

from app.core import image as image_module
from app.core.image import (
    MAX_IMAGES_PER_STUDENT,
    FolderValidationError,
    discover_images,
    load_image,
    scan_student_folder,
    validate_selected_files,
)


# -----------------------------------------
# HELPERS
# -----------------------------------------

def make_jpeg(path, with_exif=False, size=(20, 10)):
    """Create a small real JPEG on disk, optionally with EXIF data."""

    image = Image.new("RGB", size, (200, 50, 50))

    if with_exif:
        exif_dict = {
            "0th": {
                piexif.ImageIFD.Make: b"Canon",
                piexif.ImageIFD.Model: b"EOS R5",
            },
            "Exif": {
                piexif.ExifIFD.ISOSpeedRatings: 400,
                piexif.ExifIFD.FNumber: (28, 10),
                piexif.ExifIFD.ExposureTime: (1, 125),
                piexif.ExifIFD.FocalLength: (50, 1),
            },
            "GPS": {},
            "1st": {},
            "thumbnail": None,
        }
        image.save(path, "JPEG", exif=piexif.dump(exif_dict))
    else:
        image.save(path, "JPEG")

    return path


def make_fake_files(folder, names, content=b"x"):
    """Create placeholder files (not real images) -- enough for the
    discovery/validation functions, which only look at names/sizes."""

    paths = []

    for name in names:
        path = folder / name
        path.write_bytes(content)
        paths.append(path)

    return paths


# -----------------------------------------
# load_image
# -----------------------------------------

class TestLoadImage:

    def test_returns_basic_image_information(self, tmp_path):

        path = make_jpeg(tmp_path / "photo.jpg", size=(20, 10))

        data = load_image(str(path))

        try:
            assert data["path"] == path
            assert data["format"] == "JPEG"
            assert data["size"] == (20, 10)
            assert data["mode"] == "RGB"
            assert data["file_size_mb"] == pytest.approx(path.stat().st_size / (1024 ** 2))
            assert data["image"].size == (20, 10)
        finally:
            data["image"].close()

    def test_includes_the_metadata_keys_from_extract_metadata(self, tmp_path):

        path = make_jpeg(tmp_path / "photo.jpg")

        data = load_image(str(path))

        try:
            for key in ("make", "model", "lens_model", "focal", "fnum",
                        "exposure_time", "iso", "flash", "white_balance",
                        "date", "exif"):
                assert key in data
        finally:
            data["image"].close()

    def test_exif_values_are_merged_into_the_result(self, tmp_path):

        path = make_jpeg(tmp_path / "photo.jpg", with_exif=True)

        data = load_image(str(path))

        try:
            assert data["make"] == "Canon"
            assert data["model"] == "EOS R5"
            assert data["iso"] == 400
            assert data["fnum"] == pytest.approx(2.8)
            assert data["exposure_time"] == "1/125"
            assert data["focal"] == 50.0
        finally:
            data["image"].close()

    def test_image_without_exif_still_loads_with_none_values(self, tmp_path):

        path = make_jpeg(tmp_path / "plain.jpg")

        data = load_image(str(path))

        try:
            assert data["make"] is None
            assert data["iso"] is None
            assert data["exposure_time"] is None
        finally:
            data["image"].close()

    def test_png_without_exif_is_supported(self, tmp_path):

        path = tmp_path / "shot.png"
        Image.new("RGB", (8, 8)).save(path, "PNG")

        data = load_image(str(path))

        try:
            assert data["format"] == "PNG"
            assert data["iso"] is None
        finally:
            data["image"].close()

    def test_surrounding_quotes_and_spaces_in_the_path_are_stripped(self, tmp_path):

        # Drag & drop / copy-as-path often wraps the path in quotes.
        path = make_jpeg(tmp_path / "photo.jpg")

        data = load_image(f'  "{path}"  ')

        try:
            assert data["path"] == path
        finally:
            data["image"].close()

    def test_missing_file_raises_file_not_found(self, tmp_path):

        with pytest.raises(FileNotFoundError):
            load_image(str(tmp_path / "does_not_exist.jpg"))

    def test_non_image_file_raises_unidentified_image_error(self, tmp_path):

        path = tmp_path / "notes.jpg"
        path.write_text("this is not an image", encoding="utf-8")

        with pytest.raises(UnidentifiedImageError):
            load_image(str(path))


# -----------------------------------------
# discover_images
# -----------------------------------------

class TestDiscoverImages:

    def test_returns_only_supported_image_files_sorted_by_name(self, tmp_path):

        make_fake_files(tmp_path, ["b.jpg", "a.png", "c.webp", "notes.txt", "raw.psd"])

        found = discover_images(tmp_path)

        assert [p.name for p in found] == ["a.png", "b.jpg", "c.webp"]

    def test_extension_check_is_case_insensitive(self, tmp_path):

        make_fake_files(tmp_path, ["A.JPG", "b.PnG"])

        assert [p.name for p in discover_images(tmp_path)] == ["A.JPG", "b.PnG"]

    def test_subfolders_are_ignored_even_if_named_like_images(self, tmp_path):

        (tmp_path / "folder.jpg").mkdir()
        make_fake_files(tmp_path, ["real.jpg"])

        assert [p.name for p in discover_images(tmp_path)] == ["real.jpg"]

    def test_empty_folder_returns_an_empty_list(self, tmp_path):

        assert discover_images(tmp_path) == []


# -----------------------------------------
# scan_student_folder
# -----------------------------------------

class TestScanStudentFolder:

    def test_returns_the_images_for_a_valid_folder(self, tmp_path):

        make_fake_files(tmp_path, ["1.jpg", "2.jpg"])

        assert [p.name for p in scan_student_folder(tmp_path)] == ["1.jpg", "2.jpg"]

    def test_folder_with_no_supported_images_raises(self, tmp_path):

        make_fake_files(tmp_path, ["notes.txt"])

        with pytest.raises(FolderValidationError):
            scan_student_folder(tmp_path)

    def test_exactly_the_max_number_of_images_is_allowed(self, tmp_path):

        make_fake_files(tmp_path, [f"{i}.jpg" for i in range(MAX_IMAGES_PER_STUDENT)])

        assert len(scan_student_folder(tmp_path)) == MAX_IMAGES_PER_STUDENT

    def test_more_than_the_max_number_of_images_raises(self, tmp_path):

        make_fake_files(tmp_path, [f"{i}.jpg" for i in range(MAX_IMAGES_PER_STUDENT + 1)])

        with pytest.raises(FolderValidationError):
            scan_student_folder(tmp_path)

    def test_total_size_over_the_limit_raises(self, tmp_path, monkeypatch):

        # Shrink the limit instead of writing 100 MB to disk.
        monkeypatch.setattr(image_module, "MAX_FOLDER_SIZE_MB", 0.001)  # ~1 KB
        make_fake_files(tmp_path, ["big.jpg"], content=b"x" * 2000)

        with pytest.raises(FolderValidationError):
            scan_student_folder(tmp_path)


# -----------------------------------------
# validate_selected_files
# -----------------------------------------

class TestValidateSelectedFiles:

    def test_returns_sorted_paths_for_valid_files(self, tmp_path):

        paths = make_fake_files(tmp_path, ["b.jpg", "a.png"])

        result = validate_selected_files([str(p) for p in paths])

        assert [p.name for p in result] == ["a.png", "b.jpg"]

    def test_empty_selection_raises(self):

        with pytest.raises(FolderValidationError):
            validate_selected_files([])

    def test_unsupported_extension_raises(self, tmp_path):

        paths = make_fake_files(tmp_path, ["a.jpg", "notes.txt"])

        with pytest.raises(FolderValidationError):
            validate_selected_files([str(p) for p in paths])

    def test_more_than_the_max_number_of_files_raises(self, tmp_path):

        paths = make_fake_files(tmp_path, [f"{i}.jpg" for i in range(MAX_IMAGES_PER_STUDENT + 1)])

        with pytest.raises(FolderValidationError):
            validate_selected_files([str(p) for p in paths])

    def test_total_size_over_the_limit_raises(self, tmp_path, monkeypatch):

        monkeypatch.setattr(image_module, "MAX_FOLDER_SIZE_MB", 0.001)
        paths = make_fake_files(tmp_path, ["big.jpg"], content=b"x" * 2000)

        with pytest.raises(FolderValidationError):
            validate_selected_files([str(p) for p in paths])

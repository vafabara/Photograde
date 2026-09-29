import piexif
import pytest
from PIL import Image

from app.core.metadata import extract_metadata

EXPECTED_KEYS = {
    "make", "model", "lens_model",
    "focal", "fnum", "exposure_time", "iso", "flash", "white_balance",
    "date", "exif",
}

VALUE_KEYS = EXPECTED_KEYS - {"exif"}


# -----------------------------------------
# HELPERS
# -----------------------------------------

def make_jpeg(path, zeroth=None, exif=None):
    """Create a small real JPEG containing the given EXIF entries."""

    exif_dict = {
        "0th": zeroth or {},
        "Exif": exif or {},
        "GPS": {},
        "1st": {},
        "thumbnail": None,
    }

    Image.new("RGB", (8, 8)).save(path, "JPEG", exif=piexif.dump(exif_dict))

    return path


# -----------------------------------------
# NO / BROKEN EXIF
# -----------------------------------------

class TestMissingExif:

    def test_jpeg_without_exif_returns_all_none(self, tmp_path):

        path = tmp_path / "plain.jpg"
        Image.new("RGB", (8, 8)).save(path, "JPEG")

        metadata = extract_metadata(path)

        assert set(metadata.keys()) == EXPECTED_KEYS
        assert all(metadata[key] is None for key in VALUE_KEYS)

    def test_png_is_handled_without_raising(self, tmp_path):

        # piexif can't read PNG -- extract_metadata must swallow that
        # and behave as "no EXIF", not crash.
        path = tmp_path / "shot.png"
        Image.new("RGB", (8, 8)).save(path, "PNG")

        metadata = extract_metadata(path)

        assert all(metadata[key] is None for key in VALUE_KEYS)
        assert metadata["exif"] == {}

    def test_garbage_file_is_handled_without_raising(self, tmp_path):

        path = tmp_path / "broken.jpg"
        path.write_bytes(b"definitely not an image")

        metadata = extract_metadata(path)

        assert all(metadata[key] is None for key in VALUE_KEYS)

    def test_missing_file_raises_os_error(self, tmp_path):

        # Only invalid *image data* is tolerated; a path that doesn't
        # exist is a real error the caller should see.
        with pytest.raises(OSError):
            extract_metadata(tmp_path / "nope.jpg")


# -----------------------------------------
# CAMERA INFORMATION
# -----------------------------------------

class TestCameraInformation:

    def test_make_model_and_lens_are_decoded_to_clean_strings(self, tmp_path):

        path = make_jpeg(
            tmp_path / "cam.jpg",
            zeroth={
                piexif.ImageIFD.Make: b"Canon",
                piexif.ImageIFD.Model: b"EOS R5",
            },
            exif={piexif.ExifIFD.LensModel: b"RF 24-70mm F2.8"},
        )

        metadata = extract_metadata(path)

        assert metadata["make"] == "Canon"
        assert metadata["model"] == "EOS R5"
        assert metadata["lens_model"] == "RF 24-70mm F2.8"


# -----------------------------------------
# CAMERA SETTINGS
# -----------------------------------------

class TestCameraSettings:

    def test_aperture_and_focal_length_become_floats(self, tmp_path):

        path = make_jpeg(
            tmp_path / "settings.jpg",
            exif={
                piexif.ExifIFD.FNumber: (28, 10),
                piexif.ExifIFD.FocalLength: (50, 1),
            },
        )

        metadata = extract_metadata(path)

        assert metadata["fnum"] == pytest.approx(2.8)
        assert metadata["focal"] == 50.0

    def test_fast_shutter_speed_is_a_fraction_string(self, tmp_path):

        path = make_jpeg(tmp_path / "fast.jpg", exif={piexif.ExifIFD.ExposureTime: (1, 125)})

        assert extract_metadata(path)["exposure_time"] == "1/125"

    def test_long_shutter_speed_is_a_seconds_string(self, tmp_path):

        path = make_jpeg(tmp_path / "slow.jpg", exif={piexif.ExifIFD.ExposureTime: (2, 1)})

        assert extract_metadata(path)["exposure_time"] == "2s"

    def test_iso_is_kept_as_a_number(self, tmp_path):

        path = make_jpeg(tmp_path / "iso.jpg", exif={piexif.ExifIFD.ISOSpeedRatings: 400})

        assert extract_metadata(path)["iso"] == 400

    def test_flash_and_white_balance_are_read(self, tmp_path):

        path = make_jpeg(
            tmp_path / "flash.jpg",
            exif={
                piexif.ExifIFD.Flash: 16,
                piexif.ExifIFD.WhiteBalance: 1,
            },
        )

        metadata = extract_metadata(path)

        assert metadata["flash"] == 16
        assert metadata["white_balance"] == 1

    def test_settings_that_are_absent_stay_none(self, tmp_path):

        # Only ISO is present; everything else must be None, not
        # missing keys or zeros.
        path = make_jpeg(tmp_path / "partial.jpg", exif={piexif.ExifIFD.ISOSpeedRatings: 200})

        metadata = extract_metadata(path)

        assert metadata["iso"] == 200
        assert metadata["fnum"] is None
        assert metadata["focal"] is None
        assert metadata["exposure_time"] is None


# -----------------------------------------
# DATE
# -----------------------------------------

class TestDate:

    def test_date_time_original_is_used_when_present(self, tmp_path):

        path = make_jpeg(
            tmp_path / "date.jpg",
            zeroth={piexif.ImageIFD.DateTime: b"2020:05:05 10:00:00"},
            exif={piexif.ExifIFD.DateTimeOriginal: b"2024:01:01 12:00:00"},
        )

        assert extract_metadata(path)["date"] == "2024:01:01 12:00:00"

    def test_falls_back_to_the_general_date_time(self, tmp_path):

        path = make_jpeg(
            tmp_path / "date_fallback.jpg",
            zeroth={piexif.ImageIFD.DateTime: b"2020:05:05 10:00:00"},
        )

        assert extract_metadata(path)["date"] == "2020:05:05 10:00:00"


# -----------------------------------------
# RAW EXIF
# -----------------------------------------

class TestRawExif:

    def test_raw_exif_dict_is_kept_for_later_use(self, tmp_path):

        path = make_jpeg(tmp_path / "raw.jpg", exif={piexif.ExifIFD.ISOSpeedRatings: 100})

        raw = extract_metadata(path)["exif"]

        assert raw["Exif"][piexif.ExifIFD.ISOSpeedRatings] == 100

    def test_accepts_str_and_path_objects(self, tmp_path):

        path = make_jpeg(tmp_path / "either.jpg", exif={piexif.ExifIFD.ISOSpeedRatings: 100})

        assert extract_metadata(path)["iso"] == extract_metadata(str(path))["iso"] == 100

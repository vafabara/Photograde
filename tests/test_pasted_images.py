from pathlib import Path

import pytest
from PIL import Image, ImageGrab

from app.core import clipboard as clipboard_module
from app.core.clipboard import ClipboardError, grab_clipboard_photos
from app.core.image import FolderValidationError, PhotoLimitError, load_image
from app.storage import class_storage, pasted_images
from app.storage.pasted_images import paste_from_clipboard, save_pasted_image


@pytest.fixture(autouse=True)
def isolated_classes_dir(tmp_path, monkeypatch):
    """Pasted images must never be written to the real classes/ folder."""

    monkeypatch.setattr(class_storage, "CLASSES_DIR", tmp_path)
    return tmp_path


def fake_clipboard(monkeypatch, content=None, error=None):

    def grab():
        if error:
            raise error
        return content

    monkeypatch.setattr(ImageGrab, "grabclipboard", grab)


class TestGrabClipboardPhotos:

    def test_bitmap(self, monkeypatch):

        image = Image.new("RGB", (4, 4))
        fake_clipboard(monkeypatch, image)

        assert grab_clipboard_photos() == ("image", image)

    def test_copied_files(self, monkeypatch):

        fake_clipboard(monkeypatch, ["/a/1.jpg", "/a/2.jpg"])

        assert grab_clipboard_photos() == ("files", [Path("/a/1.jpg"), Path("/a/2.jpg")])

    def test_empty_or_text_clipboard_is_none(self, monkeypatch):

        fake_clipboard(monkeypatch, None)
        assert grab_clipboard_photos() is None

        fake_clipboard(monkeypatch, [])
        assert grab_clipboard_photos() is None

    def test_unsupported_platform_gives_a_friendly_error(self, monkeypatch):

        fake_clipboard(monkeypatch, error=NotImplementedError())

        with pytest.raises(ClipboardError) as error:
            grab_clipboard_photos()

        assert "xclip" in str(error.value)

    def test_other_failures_give_a_friendly_error(self, monkeypatch):

        fake_clipboard(monkeypatch, error=OSError("boom"))

        with pytest.raises(ClipboardError):
            grab_clipboard_photos()


class TestSavePastedImage:

    def test_saved_as_a_normal_loadable_png_under_pasted_photos(self, isolated_classes_dir):

        path = save_pasted_image(Image.new("RGB", (30, 20), (1, 2, 3)), "Alice")

        assert path.parent == isolated_classes_dir / "pasted_photos"
        assert path.suffix == ".png"
        assert path.name.startswith("Alice_pasted_")

        data = load_image(str(path))
        try:
            assert data["size"] == (30, 20)
            assert data["iso"] is None   # no EXIF -> teacher grades out of 100
        finally:
            data["image"].close()

    def test_pixels_are_kept_exactly(self):

        path = save_pasted_image(Image.new("RGB", (3, 3), (12, 34, 56)), "Alice")

        with Image.open(path) as saved:
            assert saved.getpixel((1, 1)) == (12, 34, 56)

    def test_two_pastes_in_the_same_second_never_overwrite_each_other(self):

        first = save_pasted_image(Image.new("RGB", (2, 2)), "Alice")
        second = save_pasted_image(Image.new("RGB", (2, 2)), "Alice")

        assert first != second
        assert first.exists() and second.exists()

    def test_forbidden_filename_characters_in_the_student_name_are_replaced(self):

        path = save_pasted_image(Image.new("RGB", (2, 2)), 'A/B:C*"D')

        assert path.exists()
        assert not any(char in path.name for char in '/:*"')

    def test_blank_name_still_works(self):

        assert save_pasted_image(Image.new("RGB", (2, 2)), "  ").name.startswith("student_pasted_")

    def test_unusual_modes_are_converted(self):

        path = save_pasted_image(Image.new("CMYK", (2, 2)), "Alice")

        assert path.exists()


class TestPasteFromClipboard:

    def test_bitmap_becomes_one_saved_file(self, monkeypatch):

        fake_clipboard(monkeypatch, Image.new("RGB", (5, 5)))

        paths = paste_from_clipboard("Alice", existing_count=0)

        assert len(paths) == 1 and paths[0].exists()

    def test_nothing_usable_returns_none(self, monkeypatch):

        fake_clipboard(monkeypatch, None)

        assert paste_from_clipboard("Alice", 0) is None

    def test_full_student_is_refused_and_nothing_is_saved(self, monkeypatch, isolated_classes_dir):

        fake_clipboard(monkeypatch, Image.new("RGB", (5, 5)))

        with pytest.raises(PhotoLimitError):
            paste_from_clipboard("Alice", existing_count=6)

        assert not (isolated_classes_dir / "pasted_photos").exists()

    def test_copied_image_files_are_used_where_they_are(self, monkeypatch, tmp_path):

        photo = tmp_path / "shot.jpg"
        Image.new("RGB", (4, 4)).save(photo)
        fake_clipboard(monkeypatch, [str(photo)])

        assert paste_from_clipboard("Alice", 0) == [photo]

    def test_copied_files_that_are_not_images_are_refused(self, monkeypatch, tmp_path):

        document = tmp_path / "notes.txt"
        document.write_text("hi")
        fake_clipboard(monkeypatch, [str(document)])

        with pytest.raises(FolderValidationError):
            paste_from_clipboard("Alice", 0)

    def test_too_many_copied_files_for_the_remaining_slots_are_refused(self, monkeypatch, tmp_path):

        files = []
        for i in range(3):
            photo = tmp_path / f"{i}.jpg"
            Image.new("RGB", (2, 2)).save(photo)
            files.append(str(photo))

        fake_clipboard(monkeypatch, files)

        with pytest.raises(PhotoLimitError):
            paste_from_clipboard("Alice", existing_count=4)  # 2 slots left

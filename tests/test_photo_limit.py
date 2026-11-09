from pathlib import Path

import pytest

from app.core import image as image_module
from app.core.image import (
    MAX_IMAGES_PER_STUDENT,
    FolderValidationError,
    PhotoLimitError,
    merge_student_photos,
)


def make_files(folder, names):

    folder.mkdir(exist_ok=True)
    paths = []

    for name in names:
        path = folder / name
        path.write_bytes(b"x")
        paths.append(path)

    return paths


def test_limit_is_six_photos_per_student():

    assert MAX_IMAGES_PER_STUDENT == 6


class TestMergeStudentPhotos:

    def test_adding_one_at_a_time_keeps_every_earlier_photo(self, tmp_path):

        files = make_files(tmp_path, [f"{i}.jpg" for i in range(3)])

        existing = []

        for path in files:
            to_add, duplicates = merge_student_photos(existing, [path])
            existing += to_add

        assert existing == files

    def test_many_at_once_are_all_added_in_order(self, tmp_path):

        files = make_files(tmp_path, ["b.jpg", "a.jpg", "c.jpg"])

        to_add, duplicates = merge_student_photos([], files)

        assert to_add == files
        assert duplicates == []

    def test_same_file_is_a_duplicate(self, tmp_path):

        files = make_files(tmp_path, ["a.jpg", "b.jpg"])

        to_add, duplicates = merge_student_photos([files[0]], [files[0], files[1]])

        assert to_add == [files[1]]
        assert duplicates == [files[0]]

    def test_same_file_selected_twice_in_one_selection_is_added_once(self, tmp_path):

        files = make_files(tmp_path, ["a.jpg"])

        to_add, duplicates = merge_student_photos([], [files[0], files[0]])

        assert to_add == files
        assert len(duplicates) == 1

    def test_same_file_name_in_different_folders_is_not_a_duplicate(self, tmp_path):

        first = make_files(tmp_path / "one", ["IMG_001.jpg"])
        second = make_files(tmp_path / "two", ["IMG_001.jpg"])

        to_add, duplicates = merge_student_photos(first, second)

        assert to_add == second
        assert duplicates == []

    def test_path_written_differently_is_still_a_duplicate(self, tmp_path):

        files = make_files(tmp_path, ["a.jpg"])
        roundabout = tmp_path / "sub" / ".." / "a.jpg"

        to_add, duplicates = merge_student_photos(files, [roundabout])

        assert to_add == []
        assert len(duplicates) == 1

    def test_exactly_filling_the_last_slots_is_allowed(self, tmp_path):

        files = make_files(tmp_path, [f"{i}.jpg" for i in range(6)])

        to_add, _ = merge_student_photos(files[:4], files[4:])

        assert len(to_add) == 2

    def test_too_many_new_photos_are_refused_without_adding_any(self, tmp_path):

        files = make_files(tmp_path, [f"{i}.jpg" for i in range(8)])

        with pytest.raises(PhotoLimitError) as error:
            merge_student_photos(files[:4], files[4:])  # 4 new, only 2 slots

        assert "2 more" in str(error.value)

    def test_full_student_refuses_more(self, tmp_path):

        files = make_files(tmp_path, [f"{i}.jpg" for i in range(7)])

        with pytest.raises(PhotoLimitError):
            merge_student_photos(files[:6], files[6:])

    def test_duplicates_do_not_count_against_the_limit(self, tmp_path):

        files = make_files(tmp_path, [f"{i}.jpg" for i in range(6)])

        to_add, duplicates = merge_student_photos(files, files[:2])

        assert to_add == []
        assert len(duplicates) == 2

    def test_student_already_over_the_limit_can_still_re_select_existing(self, tmp_path):

        # A class saved when the limit was 20 must not break.
        files = make_files(tmp_path, [f"{i}.jpg" for i in range(9)])

        to_add, duplicates = merge_student_photos(files, files[:3])

        assert to_add == []

    def test_limit_error_is_a_folder_validation_error(self):

        assert issubclass(PhotoLimitError, FolderValidationError)

    def test_total_size_limit_is_checked_across_existing_and_new(self, tmp_path, monkeypatch):

        monkeypatch.setattr(image_module, "MAX_FOLDER_SIZE_MB", 0.001)  # ~1 KB
        first = tmp_path / "a.jpg"
        second = tmp_path / "b.jpg"
        first.write_bytes(b"x" * 800)
        second.write_bytes(b"x" * 800)

        with pytest.raises(FolderValidationError):
            merge_student_photos([first], [second])

    def test_missing_existing_file_does_not_block_adding(self, tmp_path):

        files = make_files(tmp_path, ["new.jpg"])

        to_add, _ = merge_student_photos([tmp_path / "gone.jpg"], files)

        assert to_add == files

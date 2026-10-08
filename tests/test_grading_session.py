import json

import pytest

from app.storage import class_storage
from app.storage.grading_session import (
    BLOCKED_MESSAGE,
    BLOCKED_STUDENT_MESSAGE,
    GradingSessionError,
    delete_session,
    find_conflict,
    load_active_session,
    save_session,
)


@pytest.fixture(autouse=True)
def isolated_classes_dir(tmp_path, monkeypatch):
    """
    Redirect class_storage.CLASSES_DIR to a temporary directory for
    every test in this file, so nothing here ever reads or writes
    the project's real classes/ folder. grading_session reads
    class_storage.CLASSES_DIR at call time, so this covers it too.
    """

    monkeypatch.setattr(class_storage, "CLASSES_DIR", tmp_path)
    return tmp_path


def make_session(
    class_id="class-1",
    class_name="Photography 101",
    student_name=None,
    current_index=2,
):

    return {
        "class_id": class_id,
        "class_name": class_name,
        "student_name": student_name,
        "current_index": current_index,
        "rule_config": {"skipped": True},
        "photos": [
            {
                "path": "/photos/alice/1.jpg",
                "rule_engine_score": 35.0,
                "teacher_score": 50.0,
                "total_score": 85.0,
                "note": "Great composition",
            },
            {
                "path": "/photos/alice/2.jpg",
                "rule_engine_score": None,
                "teacher_score": None,
                "total_score": None,
                "note": "",
            },
        ],
    }


def session_files(directory):

    return sorted(path.name for path in directory.glob("grading(*).json"))


# -----------------------------------------
# SAVE / LOAD
# -----------------------------------------

class TestSaveAndLoad:

    def test_round_trip_preserves_everything(self):

        session = make_session()
        save_session(session)

        assert load_active_session() == session

    def test_load_returns_none_when_nothing_was_saved(self):

        assert load_active_session() is None

    def test_load_returns_none_when_classes_dir_does_not_exist(self, tmp_path, monkeypatch):

        monkeypatch.setattr(class_storage, "CLASSES_DIR", tmp_path / "missing")

        assert load_active_session() is None

    def test_file_is_named_after_the_class(self, isolated_classes_dir):

        save_session(make_session(class_name="Photography 101"))

        assert session_files(isolated_classes_dir) == ["grading(Photography 101).json"]

    def test_forbidden_filename_characters_are_replaced(self, isolated_classes_dir):

        save_session(make_session(class_name="Intro: Light/Portraits"))

        assert session_files(isolated_classes_dir) == ["grading(Intro_ Light_Portraits).json"]

    def test_saving_the_same_session_again_overwrites_it(self, isolated_classes_dir):

        save_session(make_session(current_index=2))
        save_session(make_session(current_index=7))

        assert len(session_files(isolated_classes_dir)) == 1
        assert load_active_session()["current_index"] == 7

    def test_renaming_the_class_does_not_leave_a_stale_file(self, isolated_classes_dir):

        save_session(make_session(class_name="Old Name"))
        save_session(make_session(class_name="New Name"))

        assert session_files(isolated_classes_dir) == ["grading(New Name).json"]

    def test_corrupt_file_is_ignored(self, isolated_classes_dir):

        (isolated_classes_dir / "grading(Bad).json").write_text(
            "{not valid json", encoding="utf-8"
        )

        assert load_active_session() is None

    def test_file_missing_required_keys_is_ignored(self, isolated_classes_dir):

        (isolated_classes_dir / "grading(Incomplete).json").write_text(
            json.dumps({"class_id": "x"}), encoding="utf-8"
        )

        assert load_active_session() is None


# -----------------------------------------
# ONE ACTIVE SESSION (class + student scope)
# -----------------------------------------

class TestConflicts:

    def test_no_conflict_when_nothing_is_saved(self):

        assert find_conflict("class-1", None) is None
        assert find_conflict("class-1", "Alice") is None

    def test_a_different_class_is_blocked(self):

        save_session(make_session(class_id="class-1"))

        assert find_conflict("class-2", None) == BLOCKED_MESSAGE

    def test_saving_a_different_class_raises_and_keeps_the_first_session(self, isolated_classes_dir):

        save_session(make_session(class_id="class-1", class_name="Class A", current_index=4))

        with pytest.raises(GradingSessionError) as error:
            save_session(make_session(class_id="class-2", class_name="Class B"))

        assert str(error.value) == BLOCKED_MESSAGE
        assert session_files(isolated_classes_dir) == ["grading(Class A).json"]
        assert load_active_session()["current_index"] == 4

    def test_a_different_student_in_the_same_class_is_blocked(self):

        save_session(make_session(student_name="Alice"))

        assert find_conflict("class-1", "Bob") == BLOCKED_STUDENT_MESSAGE

    def test_saving_another_students_session_never_overwrites_the_first(self):

        save_session(make_session(student_name="Alice", current_index=5))

        with pytest.raises(GradingSessionError) as error:
            save_session(make_session(student_name="Bob", current_index=0))

        assert str(error.value) == BLOCKED_STUDENT_MESSAGE

        saved = load_active_session()
        assert saved["student_name"] == "Alice"
        assert saved["current_index"] == 5

    def test_whole_class_and_single_student_queues_block_each_other(self):

        save_session(make_session(student_name=None))
        assert find_conflict("class-1", "Alice") == BLOCKED_STUDENT_MESSAGE

        # Start over with a student-scoped session instead.
        delete_session("class-1")
        save_session(make_session(student_name="Alice"))
        assert find_conflict("class-1", None) == BLOCKED_STUDENT_MESSAGE

    def test_the_same_class_and_same_student_is_allowed(self):

        save_session(make_session(student_name="Alice", current_index=1))

        assert find_conflict("class-1", "Alice") is None

        save_session(make_session(student_name="Alice", current_index=3))

        assert load_active_session()["current_index"] == 3

    def test_a_file_without_student_name_counts_as_whole_class(self, isolated_classes_dir):

        data = make_session()
        del data["student_name"]

        (isolated_classes_dir / "grading(Photography 101).json").write_text(
            json.dumps(data), encoding="utf-8"
        )

        assert find_conflict("class-1", None) is None
        assert find_conflict("class-1", "Alice") == BLOCKED_STUDENT_MESSAGE


# -----------------------------------------
# DELETE
# -----------------------------------------

class TestDeleteSession:

    def test_delete_removes_the_checkpoint(self, isolated_classes_dir):

        save_session(make_session())

        delete_session("class-1")

        assert session_files(isolated_classes_dir) == []
        assert load_active_session() is None

    def test_delete_matches_by_class_id_not_by_filename(self, isolated_classes_dir):

        save_session(make_session(class_name="Some Class"))

        # Looked up by id even though the caller doesn't know the name.
        delete_session("class-1")

        assert session_files(isolated_classes_dir) == []

    def test_delete_only_removes_the_matching_class(self, isolated_classes_dir):

        # Written by hand: save_session would refuse a second class.
        for class_id, name in (("a-id", "A"), ("b-id", "B")):
            (isolated_classes_dir / f"grading({name}).json").write_text(
                json.dumps(make_session(class_id=class_id, class_name=name)),
                encoding="utf-8",
            )

        delete_session("a-id")

        assert session_files(isolated_classes_dir) == ["grading(B).json"]

    def test_delete_when_nothing_exists_does_not_raise(self):

        delete_session("never-existed")  # should not raise
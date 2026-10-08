"""
Tests for the Grading Progress / Save & Continue logic that lives on
App (app/gui/app.py): building and restoring a checkpoint, the
progress/dirty state, and the one-session-at-a-time checks.

Same approach as test_photo_entry_lookup.py: App is never
instantiated (App() would build real Tk windows). Instead the real
App methods are bound onto a lightweight stand-in object that carries
only the attributes those methods read, so the exact production code
is exercised. The few GUI-only hooks (show_error, set_save_status,
start_review, drop_unusable_session) are replaced by recorders.
"""

import types
from pathlib import Path

import pytest

from app.core.class_model import ClassPhotoEntry, ClassRecord, ClassStudentEntry
from app.core.student import ImageRecord
from app.gui import app as app_module
from app.gui.app import App
from app.storage import class_storage
from app.storage.class_storage import load_class
from app.storage.grading_session import (
    BLOCKED_MESSAGE,
    BLOCKED_STUDENT_MESSAGE,
    load_active_session,
    save_session,
)


@pytest.fixture(autouse=True)
def isolated_classes_dir(tmp_path, monkeypatch):
    """Never touch the project's real classes/ folder."""

    monkeypatch.setattr(class_storage, "CLASSES_DIR", tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def errors(monkeypatch):
    """
    Replace app.gui.app.show_error (which would open a real window)
    with a recorder. Tests can assert on the messages it collected.
    """

    messages = []

    monkeypatch.setattr(
        app_module,
        "show_error",
        lambda parent, message: messages.append(message),
    )

    return messages


# -----------------------------------------
# HELPERS
# -----------------------------------------

def make_class_record(rule_config=None):

    return ClassRecord(
        class_id="class-1",
        class_name="Photography 101",
        rule_config=rule_config if rule_config is not None else {"skipped": True},
        students=[
            ClassStudentEntry(
                name="Alice",
                folder_path="/photos/alice",
                photo_count=2,
                photos=[
                    ClassPhotoEntry(path="/photos/alice/1.jpg"),
                    ClassPhotoEntry(path="/photos/alice/2.jpg"),
                ],
            ),
            ClassStudentEntry(
                name="Bob",
                folder_path="/photos/bob",
                photo_count=1,
                photos=[ClassPhotoEntry(path="/photos/bob/1.jpg")],
            ),
        ],
    )


def make_session_for(record, student_name=None, current_index=1, rule_config="default"):
    """A checkpoint dict for `record`, built the same way App builds one."""

    students = App.queue_students(None, record, student_name)

    return {
        "class_id": record.class_id,
        "class_name": record.class_name,
        "student_name": student_name,
        "current_index": current_index,
        "rule_config": (
            record.rule_config if rule_config == "default" else rule_config
        ),
        "photos": [
            photo.to_dict()
            for student in students
            for photo in student.photos
        ],
    }


def make_fake_app(record, student_name=None, current_index=0):
    """
    A stand-in for App carrying only what the grading-session methods
    use, with the real methods bound to it.
    """

    students = App.queue_students(None, record, student_name)

    fake = types.SimpleNamespace(
        class_record=record,
        grading_student_name=student_name,
        current_image_index=current_index,
        image_records=[
            ImageRecord(
                student_name=student.name,
                image_path=Path(photo.path),
                total_score=photo.total_score,
            )
            for student in students
            for photo in student.photos
        ],
        grading_dirty=False,
        in_grading=True,
        rule_config=None,
        status_calls=[],
        dropped=[],
        started=[],
    )

    for method_name in (
        "queue_students",
        "build_session_data",
        "all_photos_graded",
        "finish_session_if_complete",
        "save_grading_progress",
        "mark_dirty",
        "remove_session",
        "session_conflicts",
        "resume_grading",
    ):
        setattr(
            fake,
            method_name,
            types.MethodType(getattr(App, method_name), fake),
        )

    # GUI-only hooks replaced by recorders.
    fake.set_save_status = lambda text, color: fake.status_calls.append(text)
    fake.drop_unusable_session = lambda class_id, message: fake.dropped.append(
        (class_id, message)
    )
    fake.start_review = lambda start_index=0: fake.started.append(start_index)

    return fake


def grade_everything(fake):

    for image_record in fake.image_records:
        image_record.total_score = 90.0


# -----------------------------------------
# QUEUE / SNAPSHOT
# -----------------------------------------

class TestQueueStudents:

    def test_none_means_every_student(self):

        record = make_class_record()

        students = App.queue_students(None, record, None)

        assert [s.name for s in students] == ["Alice", "Bob"]

    def test_a_name_selects_only_that_student(self):

        record = make_class_record()

        students = App.queue_students(None, record, "Bob")

        assert [s.name for s in students] == ["Bob"]

    def test_an_unknown_name_returns_none(self):

        record = make_class_record()

        assert App.queue_students(None, record, "Nobody") is None


class TestBuildSessionData:

    def test_whole_class_session_holds_every_photo_in_queue_order(self):

        record = make_class_record()
        fake = make_fake_app(record, student_name=None, current_index=2)

        data = fake.build_session_data()

        assert data["class_id"] == "class-1"
        assert data["class_name"] == "Photography 101"
        assert data["student_name"] is None
        assert data["current_index"] == 2
        assert data["rule_config"] == {"skipped": True}
        assert [p["path"] for p in data["photos"]] == [
            "/photos/alice/1.jpg",
            "/photos/alice/2.jpg",
            "/photos/bob/1.jpg",
        ]

    def test_single_student_session_holds_only_that_students_photos(self):

        record = make_class_record()
        fake = make_fake_app(record, student_name="Bob")

        data = fake.build_session_data()

        assert data["student_name"] == "Bob"
        assert [p["path"] for p in data["photos"]] == ["/photos/bob/1.jpg"]

    def test_snapshot_carries_confirmed_scores_and_notes(self):

        record = make_class_record()
        photo = record.students[0].photos[0]
        photo.rule_engine_score = 35.0
        photo.teacher_score = 50.0
        photo.total_score = 85.0
        photo.note = "Great composition"

        data = make_fake_app(record).build_session_data()
        saved = data["photos"][0]

        assert saved["rule_engine_score"] == 35.0
        assert saved["teacher_score"] == 50.0
        assert saved["total_score"] == 85.0
        assert saved["note"] == "Great composition"


class TestAllPhotosGraded:

    def test_false_for_an_empty_queue(self):

        fake = make_fake_app(make_class_record())
        fake.image_records = []

        assert fake.all_photos_graded() is False

    def test_false_while_any_photo_is_ungraded(self):

        fake = make_fake_app(make_class_record())
        fake.image_records[0].total_score = 80.0

        assert fake.all_photos_graded() is False

    def test_true_when_every_photo_has_a_total_score(self):

        fake = make_fake_app(make_class_record())
        grade_everything(fake)

        assert fake.all_photos_graded() is True


# -----------------------------------------
# SAVE / DIRTY / COMPLETION
# -----------------------------------------

class TestSaveGradingProgress:

    def test_writes_a_checkpoint_and_clears_the_dirty_flag(self):

        fake = make_fake_app(make_class_record(), current_index=1)
        fake.grading_dirty = True

        assert fake.save_grading_progress() is True

        saved = load_active_session()
        assert saved["class_id"] == "class-1"
        assert saved["current_index"] == 1
        assert saved["student_name"] is None
        assert len(saved["photos"]) == 3

        assert fake.grading_dirty is False
        assert "✓ Saved" in fake.status_calls

    def test_is_blocked_by_another_class_and_stays_dirty(self, errors):

        save_session(
            {
                "class_id": "other-class",
                "class_name": "Other",
                "student_name": None,
                "current_index": 0,
                "photos": [],
            }
        )

        fake = make_fake_app(make_class_record())
        fake.grading_dirty = True

        assert fake.save_grading_progress() is False

        assert errors == [BLOCKED_MESSAGE]
        assert fake.grading_dirty is True
        assert load_active_session()["class_id"] == "other-class"

    def test_is_blocked_by_another_student_and_keeps_their_checkpoint(self, errors):

        record = make_class_record()

        alice = make_fake_app(record, student_name="Alice", current_index=1)
        assert alice.save_grading_progress() is True

        bob = make_fake_app(record, student_name="Bob", current_index=0)
        bob.grading_dirty = True

        assert bob.save_grading_progress() is False

        assert errors == [BLOCKED_STUDENT_MESSAGE]
        assert bob.grading_dirty is True

        saved = load_active_session()
        assert saved["student_name"] == "Alice"
        assert saved["current_index"] == 1

    def test_a_fully_graded_queue_writes_no_checkpoint(self, isolated_classes_dir):

        fake = make_fake_app(make_class_record())
        grade_everything(fake)

        assert fake.save_grading_progress() is True

        assert load_active_session() is None
        assert list(isolated_classes_dir.glob("grading(*).json")) == []


class TestFinishSessionIfComplete:

    def test_incomplete_queue_keeps_the_checkpoint(self):

        fake = make_fake_app(make_class_record())
        fake.save_grading_progress()

        assert fake.finish_session_if_complete() is False
        assert load_active_session() is not None

    def test_complete_queue_deletes_the_checkpoint_and_clears_dirty(self):

        fake = make_fake_app(make_class_record())
        fake.save_grading_progress()
        fake.grading_dirty = True

        grade_everything(fake)

        assert fake.finish_session_if_complete() is True

        assert load_active_session() is None
        assert fake.grading_dirty is False

    def test_completing_does_not_touch_class_json(self):

        record = make_class_record()
        class_storage.save_class(record)

        fake = make_fake_app(record)
        fake.save_grading_progress()
        grade_everything(fake)
        fake.finish_session_if_complete()

        assert load_class("class-1") is not None


class TestMarkDirty:

    def test_marks_unsaved_changes_while_grading_is_unfinished(self):

        fake = make_fake_app(make_class_record())

        fake.mark_dirty()

        assert fake.grading_dirty is True
        assert "Unsaved changes" in fake.status_calls

    def test_ignored_once_everything_is_graded(self):

        fake = make_fake_app(make_class_record())
        grade_everything(fake)

        fake.mark_dirty()

        assert fake.grading_dirty is False


class TestSessionConflicts:

    def test_blocks_a_different_student_and_shows_the_error(self, errors):

        save_session(make_session_for(make_class_record(), student_name="Alice"))

        fake = make_fake_app(make_class_record())

        assert fake.session_conflicts("class-1", "Bob") is True
        assert errors == [BLOCKED_STUDENT_MESSAGE]

    def test_allows_the_same_class_and_student(self, errors):

        save_session(make_session_for(make_class_record(), student_name="Alice"))

        fake = make_fake_app(make_class_record())

        assert fake.session_conflicts("class-1", "Alice") is False
        assert errors == []

    def test_allows_anything_when_no_checkpoint_exists(self, errors):

        fake = make_fake_app(make_class_record())

        assert fake.session_conflicts("class-1", None) is False
        assert errors == []


# -----------------------------------------
# RESUME (Continue)
# -----------------------------------------

class TestResumeGrading:

    def test_restores_scores_and_notes_and_saves_them_to_class_json(self):

        record = make_class_record()
        session = make_session_for(record, current_index=1)
        session["photos"][0].update(
            rule_engine_score=35.0,
            teacher_score=50.0,
            total_score=85.0,
            note="Great composition",
        )

        fake = make_fake_app(record)
        fake.resume_grading(record, session)

        # Restored onto the class's own photo entries...
        restored = record.students[0].photos[0]
        assert restored.rule_engine_score == 35.0
        assert restored.teacher_score == 50.0
        assert restored.total_score == 85.0
        assert restored.note == "Great composition"

        # ...persisted to class.json...
        assert load_class("class-1").students[0].photos[0].total_score == 85.0

        # ...and rebuilt into the runtime review queue.
        assert fake.image_records[0].total_score == 85.0
        assert fake.image_records[0].note == "Great composition"
        assert len(fake.image_records) == 3

    def test_opens_the_grading_screen_on_the_saved_photo(self):

        record = make_class_record()
        session = make_session_for(record, current_index=2)

        fake = make_fake_app(record)
        fake.resume_grading(record, session)

        assert fake.started == [2]
        assert fake.dropped == []

    def test_saved_position_is_clamped_into_the_queue(self):

        record = make_class_record()

        too_far = make_fake_app(record)
        too_far.resume_grading(record, make_session_for(record, current_index=99))
        assert too_far.started == [2]  # last of 3 photos

        negative = make_fake_app(record)
        negative.resume_grading(record, make_session_for(record, current_index=-5))
        assert negative.started == [0]

    def test_single_student_session_rebuilds_only_that_students_queue(self):

        record = make_class_record()
        session = make_session_for(record, student_name="Bob", current_index=0)

        fake = make_fake_app(record)
        fake.resume_grading(record, session)

        assert fake.grading_student_name == "Bob"
        assert [r.student_name for r in fake.image_records] == ["Bob"]
        assert fake.started == [0]

    def test_skipped_rule_engine_gives_teacher_the_full_100_points(self):

        record = make_class_record()
        fake = make_fake_app(record)

        fake.resume_grading(record, make_session_for(record))

        assert fake.rule_config is None
        assert all(r.teacher_max_score == 100 for r in fake.image_records)

    def test_real_rule_engine_config_sets_the_score_split(self):

        config = {
            "system_score": 40,
            "human_score": 60,
            "rules": [{"factor": "iso", "minimum": 100.0, "maximum": 400.0}],
        }

        record = make_class_record()
        fake = make_fake_app(record)

        fake.resume_grading(record, make_session_for(record, rule_config=config))

        assert fake.rule_config.system_score == 40
        assert all(r.rule_engine_max_score == 40 for r in fake.image_records)
        assert all(r.teacher_max_score == 60 for r in fake.image_records)
        assert record.rule_config == config

    def test_falls_back_to_the_classes_own_rule_config(self):

        record = make_class_record(rule_config={"skipped": True})
        fake = make_fake_app(record)

        fake.resume_grading(record, make_session_for(record, rule_config=None))

        assert fake.started == [1]
        assert fake.dropped == []

    def test_session_without_any_rule_config_is_dropped(self):

        record = make_class_record()
        record.rule_config = None
        fake = make_fake_app(record)

        fake.resume_grading(record, make_session_for(record, rule_config=None))

        assert fake.started == []
        assert len(fake.dropped) == 1
        assert fake.dropped[0][0] == "class-1"

    def test_changed_photos_drop_the_session_instead_of_misplacing_scores(self):

        record = make_class_record()
        session = make_session_for(record)
        session["photos"].reverse()  # same photos, different order

        fake = make_fake_app(record)
        fake.resume_grading(record, session)

        assert fake.started == []
        assert len(fake.dropped) == 1
        assert fake.dropped[0][0] == "class-1"

        # Nothing was restored onto the class.
        assert all(
            photo.total_score is None
            for student in record.students
            for photo in student.photos
        )

    def test_a_deleted_student_drops_the_session(self):

        record = make_class_record()
        session = make_session_for(record, student_name="Bob")

        del record.students[1]  # Bob removed after the save

        fake = make_fake_app(record)
        fake.resume_grading(record, session)

        assert fake.started == []
        assert len(fake.dropped) == 1
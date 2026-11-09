import pandas as pd
import pytest

from app.core.class_model import (
    ClassPhotoEntry,
    ClassRecord,
    ClassStudentEntry,
    image_records_from_student,
)
from app.core.student import ImageRecord
from app.core.student_dataframe import COLUMNS, build_student_dataframe
from app.core.teacher_scoring import (
    TeacherScoreError,
    apply_rule_engine_override,
    clear_rule_engine_override,
    compute_total_score,
    sync_automatic_score,
    validate_rule_engine_override,
)


def make_record(**kwargs):

    record = ImageRecord(student_name="Alice", image_path="a.jpg", **kwargs)
    sync_automatic_score(record, 28.0, 40)
    record.teacher_max_score = 60

    return record


class TestValidateOverride:

    def test_accepts_zero_and_the_maximum(self):

        assert validate_rule_engine_override("0", 40) == 0.0
        assert validate_rule_engine_override("40", 40) == 40.0

    def test_can_raise_the_score_above_the_automatic_one(self):

        assert validate_rule_engine_override("38.5", 40) == 38.5

    @pytest.mark.parametrize("bad", ["", "abc", "-1", "40.1"])
    def test_rejects_invalid_input(self, bad):

        with pytest.raises(TeacherScoreError):
            validate_rule_engine_override(bad, 40)


class TestOverrideLifecycle:

    def test_automatic_score_is_used_until_overridden(self):

        record = make_record()

        assert record.rule_engine_score == 28.0
        assert record.rule_engine_auto_score == 28.0
        assert record.rule_engine_overridden is False

    def test_override_keeps_the_automatic_score_separately(self):

        record = make_record()

        apply_rule_engine_override(record, 36.0)

        assert record.rule_engine_score == 36.0
        assert record.rule_engine_auto_score == 28.0
        assert record.rule_engine_overridden is True

    def test_override_survives_the_rule_engine_running_again(self):

        # load_and_display re-runs the Rule Engine every time a photo is shown.
        record = make_record()
        apply_rule_engine_override(record, 36.0)

        sync_automatic_score(record, 28.0, 40)

        assert record.rule_engine_score == 36.0
        assert record.rule_engine_overridden is True

    def test_override_can_lower_the_score_too(self):

        record = make_record()
        apply_rule_engine_override(record, 5.0)

        assert record.rule_engine_score == 5.0

    def test_total_is_not_invented_before_the_teacher_confirms(self):

        record = make_record()
        apply_rule_engine_override(record, 36.0)

        assert record.total_score is None

    def test_total_follows_the_override_once_confirmed(self):

        record = make_record()
        record.teacher_score = 50.0
        record.total_score = compute_total_score(28.0, 50.0)
        assert record.total_score == 78.0

        apply_rule_engine_override(record, 36.0)
        assert record.total_score == 86.0

        clear_rule_engine_override(record)
        assert record.rule_engine_score == 28.0
        assert record.rule_engine_overridden is False
        assert record.total_score == 78.0


class TestPersistence:

    def test_photo_entry_round_trips_the_override(self):

        entry = ClassPhotoEntry(
            path="a.jpg",
            rule_engine_score=36.0,
            rule_engine_auto_score=28.0,
            rule_engine_overridden=True,
            teacher_score=50.0,
            total_score=86.0,
        )

        loaded = ClassPhotoEntry.from_dict(entry.to_dict())

        assert loaded.rule_engine_score == 36.0
        assert loaded.rule_engine_auto_score == 28.0
        assert loaded.rule_engine_overridden is True

    def test_old_saved_photos_load_as_not_overridden(self):

        loaded = ClassPhotoEntry.from_dict(
            {"path": "a.jpg", "rule_engine_score": 35.0, "teacher_score": 50.0,
             "total_score": 85.0, "note": ""}
        )

        assert loaded.rule_engine_overridden is False
        assert loaded.rule_engine_auto_score is None
        assert loaded.total_score == 85.0

    def test_override_is_restored_into_the_review_queue(self):

        student = ClassStudentEntry(
            name="Alice", folder_path="", photo_count=1,
            photos=[ClassPhotoEntry(
                path="a.jpg", rule_engine_score=36.0, rule_engine_auto_score=28.0,
                rule_engine_overridden=True,
            )],
        )

        record = image_records_from_student(student)[0]

        assert record.rule_engine_score == 36.0
        assert record.rule_engine_auto_score == 28.0
        assert record.rule_engine_overridden is True


class TestDataFrame:

    def make_student(self):

        return ClassStudentEntry(
            name="Alice", folder_path="", photo_count=2,
            photos=[
                ClassPhotoEntry(path="a.jpg", rule_engine_score=36.0, rule_engine_auto_score=28.0,
                                rule_engine_overridden=True, teacher_score=50.0, total_score=86.0),
                ClassPhotoEntry(path="b.jpg", rule_engine_score=30.0, rule_engine_auto_score=30.0,
                                teacher_score=40.0, total_score=70.0),
            ],
        )

    def test_default_columns_are_unchanged(self):

        assert list(build_student_dataframe(self.make_student()).columns) == COLUMNS

    def test_averages_use_the_overridden_score(self):

        df = build_student_dataframe(self.make_student())

        assert df.iloc[-1]["Rule Engine Score"] == 33.0
        assert df.iloc[-1]["Total Score"] == 78.0

    def test_export_columns_tell_manual_from_automatic(self):

        df = build_student_dataframe(self.make_student(), include_notes=True, include_override=True)

        assert list(df["Rule Engine Source"][:2]) == ["Manual override", "Automatic"]
        assert df.iloc[0]["Automatic Rule Score"] == 28.0
        assert df.iloc[0]["Rule Engine Score"] == 36.0
        assert list(df.columns)[-1] == "Note"


def test_excel_export_contains_the_override(tmp_path):

    from app.storage.export import export_class_to_excel

    student = TestDataFrame().make_student()
    record = ClassRecord(class_id="c", class_name="Class", students=[student])

    export_class_to_excel(record, tmp_path / "out.xlsx")

    sheet = pd.read_excel(tmp_path / "out.xlsx", sheet_name="Alice")

    assert sheet.iloc[0]["Rule Engine Source"] == "Manual override"
    assert sheet.iloc[0]["Automatic Rule Score"] == 28.0

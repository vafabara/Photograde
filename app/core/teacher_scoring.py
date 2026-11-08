"""
Teacher Grading calculations (new feature: manual professor score
per photo, combined with the Rule Engine score into a Total Score).

This module owns:
  - validating the professor's manual score input for one photo
  - combining Rule Engine + Teacher scores into a Total Score

The System/Human split always comes from the existing
core.rules.RuleEngineConfig (system_score / human_score) that the
professor already set on the Rule Engine screen -- nothing here is
hard-coded to a specific weighting (e.g. 40/60). Whatever split the
professor picked is what image_record.rule_engine_max_score and
image_record.teacher_max_score get set to by app.py.

No CustomTkinter dependency here (spec section 8) -- same rule as
core/rules.py and core/scoring.py. The GUI (gui/teacher_grading.py)
calls into this module and only renders what it returns.
"""


class TeacherScoreError(ValueError):
    """Raised when the professor's manual score input is invalid."""


def validate_teacher_score(raw_value, max_score):
    """
    Validate and parse the professor's manual score input for one
    photo.

    `raw_value` — whatever the professor typed (a string from a
    CTkEntry, in practice).
    `max_score` — this photo's Teacher Grading max score, i.e.
    image_record.teacher_max_score (== rule_config.human_score).

    Returns the parsed float on success.
    Raises TeacherScoreError with a human-readable message if the
    value is missing, not a number, negative, or above `max_score`.
    """

    text = str(raw_value).strip()

    if not text:
        raise TeacherScoreError("Please enter a score.")

    try:
        value = float(text)
    except ValueError:
        raise TeacherScoreError("Score must be a number.")

    if value < 0:
        raise TeacherScoreError("Score cannot be negative.")

    if value > max_score:
        raise TeacherScoreError(f"Score cannot exceed {max_score:g}.")

    return value


def compute_total_score(rule_engine_score, teacher_score):
    """
    Combine an already-graded Rule Engine score with a validated
    Teacher Grading score into the Total Score for one photo.

    Both inputs are expected to already be within their own max
    (the Rule Engine score by construction in core.scoring, the
    Teacher score via validate_teacher_score above) so this is just
    the sum, rounded the same way core.scoring.grade_student rounds
    its final Technical Score.
    """

    return round(rule_engine_score + teacher_score, 1)


# -----------------------------------------------------------------
# RULE ENGINE SCORE OVERRIDE
#
# The teacher can replace the Rule Engine's automatic score for one
# photo. The Rule Engine itself is never bypassed: it still runs for
# every photo and its result is kept in `rule_engine_auto_score`.
# `rule_engine_score` always holds the score that counts -- the
# automatic one, or the manual one while `rule_engine_overridden` is
# True -- so total_score, averages, the Student DataFrame and the
# Excel export all keep reading that one field.
#
# These helpers work on a core.student.ImageRecord (duck-typed, so
# this module still imports nothing from the GUI).
# -----------------------------------------------------------------

def validate_rule_engine_override(raw_value, max_score):
    """
    Validate the teacher's manual Rule Engine score. Same rules as
    validate_teacher_score: a number from 0 up to `max_score` (the
    photo's Rule Engine maximum, image_record.rule_engine_max_score).

    Returns the float, or raises TeacherScoreError with a message
    ready to show.
    """

    return validate_teacher_score(raw_value, max_score)


def _refresh_total(image_record):
    """
    If the teacher has already confirmed a Teacher score for this
    photo, its Total Score must follow the new Rule Engine score.
    Before that, total_score stays None, exactly as it does today.
    """

    if image_record.teacher_score is not None:
        image_record.total_score = compute_total_score(
            image_record.rule_engine_score or 0.0,
            image_record.teacher_score,
        )


def sync_automatic_score(image_record, auto_score, max_score):
    """
    Record the Rule Engine's fresh automatic result for a photo that
    is being displayed. The automatic score and maximum are always
    updated; `rule_engine_score` only follows them while the photo
    is NOT overridden -- this is what stops re-displaying a photo
    from overwriting the teacher's manual score.
    """

    image_record.rule_engine_auto_score = auto_score
    image_record.rule_engine_max_score = max_score

    if not image_record.rule_engine_overridden:
        image_record.rule_engine_score = auto_score


def apply_rule_engine_override(image_record, score):
    """
    Make `score` (already validated) the photo's Rule Engine score,
    flagged as a manual override, and bring its Total Score up to
    date if the photo was already confirmed.
    """

    image_record.rule_engine_score = score
    image_record.rule_engine_overridden = True

    _refresh_total(image_record)


def clear_rule_engine_override(image_record):
    """
    Go back to the Rule Engine's automatic score for this photo.
    """

    image_record.rule_engine_score = image_record.rule_engine_auto_score
    image_record.rule_engine_overridden = False

    _refresh_total(image_record)


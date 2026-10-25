import pytest

from app.core.rules import (
    Rule,
    RuleEngineConfig,
    RuleError,
    build_rule,
    validate_rule,
    validate_score_split,
)
from app.core.scoring import (
    GREEN,
    MISSING,
    RED,
    YELLOW,
    evaluate_rule,
    grade_student,
    split_score,
)
from app.core.tolerance import MAX_TOLERANCE_PERCENT, compute_tolerance, tolerance_bounds


# -----------------------------------------
# RULE VALIDATION (app/core/rules.py)
# -----------------------------------------

class TestRuleValidation:

    def test_build_rule_returns_a_valid_rule(self):

        rule = build_rule("iso", 100, 400)

        assert rule.factor == "iso"
        assert rule.minimum == 100.0
        assert rule.maximum == 400.0

    def test_rejects_minimum_greater_than_maximum(self):

        with pytest.raises(RuleError):
            validate_rule("iso", 400, 100)

    def test_rejects_value_below_factors_valid_min(self):

        # ISO's valid_min is 25.
        with pytest.raises(RuleError):
            validate_rule("iso", 1, 400)

    def test_rejects_value_above_factors_valid_max(self):

        # Aperture's valid_max is 64.
        with pytest.raises(RuleError):
            validate_rule("aperture", 1, 100)

    def test_rejects_unknown_factor(self):

        with pytest.raises(RuleError):
            validate_rule("shutter_count", 1, 2)

    def test_rejects_missing_bounds(self):

        with pytest.raises(RuleError):
            validate_rule("iso", None, 400)


class TestScoreSplitValidation:

    def test_accepts_a_matching_split(self):

        validate_score_split(40, 60)  # should not raise

    def test_rejects_a_split_that_does_not_total_100(self):

        with pytest.raises(RuleError):
            validate_score_split(40, 50)

    def test_rejects_negative_scores(self):

        with pytest.raises(RuleError):
            validate_score_split(-10, 110)

    def test_rejects_missing_scores(self):

        with pytest.raises(RuleError):
            validate_score_split(None, 100)


# -----------------------------------------
# TOLERANCE (app/core/tolerance.py)
# -----------------------------------------

class TestTolerance:

    def test_tolerance_is_a_percentage_of_range_width(self):

        rule = Rule(factor="iso", minimum=100, maximum=500)

        assert compute_tolerance(rule) == pytest.approx((500 - 100) * MAX_TOLERANCE_PERCENT)

    def test_tolerance_bounds_widen_symmetrically(self):

        rule = Rule(factor="iso", minimum=100, maximum=500)
        tolerance = compute_tolerance(rule)

        lower, upper = tolerance_bounds(rule)

        assert lower == pytest.approx(100 - tolerance)
        assert upper == pytest.approx(500 + tolerance)

    def test_zero_width_rule_falls_back_to_value_based_tolerance(self):

        rule = Rule(factor="aperture", minimum=8.0, maximum=8.0)

        tolerance = compute_tolerance(rule)

        assert tolerance == pytest.approx(8.0 * MAX_TOLERANCE_PERCENT)
        assert tolerance > 0

    def test_different_factors_get_tolerance_proportional_to_their_own_range(self):

        narrow_rule = Rule(factor="aperture", minimum=4, maximum=8)
        wide_rule = Rule(factor="iso", minimum=200, maximum=600)

        assert compute_tolerance(narrow_rule) == pytest.approx(4 * MAX_TOLERANCE_PERCENT)
        assert compute_tolerance(wide_rule) == pytest.approx(400 * MAX_TOLERANCE_PERCENT)


# -----------------------------------------
# EVALUATE_RULE (GREEN / YELLOW / RED / MISSING)
# -----------------------------------------

class TestEvaluateRule:

    def test_value_inside_range_is_green(self):

        rule = Rule(factor="iso", minimum=100, maximum=400)

        status, value = evaluate_rule(rule, {"iso": 200})

        assert status == GREEN
        assert value == 200.0

    def test_value_at_minimum_boundary_is_green(self):

        rule = Rule(factor="iso", minimum=100, maximum=400)

        status, value = evaluate_rule(rule, {"iso": 100})

        assert status == GREEN

    def test_value_at_maximum_boundary_is_green(self):

        rule = Rule(factor="iso", minimum=100, maximum=400)

        status, value = evaluate_rule(rule, {"iso": 400})

        assert status == GREEN

    def test_value_in_tolerance_zone_is_yellow(self):

        # width 300 -> tolerance 45 -> yellow zone extends to 445
        rule = Rule(factor="iso", minimum=100, maximum=400)

        status, value = evaluate_rule(rule, {"iso": 420})

        assert status == YELLOW

    def test_value_exactly_at_tolerance_edge_is_yellow(self):

        rule = Rule(factor="iso", minimum=100, maximum=400)
        _, upper = tolerance_bounds(rule)

        status, value = evaluate_rule(rule, {"iso": upper})

        assert status == YELLOW

    def test_value_beyond_tolerance_zone_is_red(self):

        rule = Rule(factor="iso", minimum=100, maximum=400)

        status, value = evaluate_rule(rule, {"iso": 1000})

        assert status == RED

    def test_missing_metadata_value_has_missing_status_and_no_value(self):

        rule = Rule(factor="iso", minimum=100, maximum=400)

        status, value = evaluate_rule(rule, {"iso": None})

        assert status == MISSING
        assert value is None

    def test_absent_metadata_key_is_also_missing(self):

        rule = Rule(factor="iso", minimum=100, maximum=400)

        status, value = evaluate_rule(rule, {})

        assert status == MISSING
        assert value is None

    def test_shutter_speed_fraction_string_is_converted_before_comparing(self):

        rule = Rule(factor="shutter_speed", minimum=0.001, maximum=0.01)

        status, value = evaluate_rule(rule, {"exposure_time": "1/125"})

        assert status == GREEN
        assert value == pytest.approx(1 / 125)


# -----------------------------------------
# SPLIT_SCORE
# -----------------------------------------

class TestSplitScore:

    def test_splits_the_system_score_evenly_across_rules(self):

        rules = [Rule("iso", 100, 400), Rule("aperture", 2, 8)]

        assert split_score(100, rules) == {"iso": 50.0, "aperture": 50.0}

    def test_empty_rules_returns_an_empty_split(self):

        assert split_score(100, []) == {}


# -----------------------------------------
# GRADE_STUDENT (full pipeline / technical score)
# -----------------------------------------

class TestGradeStudent:

    def test_all_green_gives_the_full_system_score(self):

        rules = [Rule("iso", 100, 400), Rule("aperture", 2, 8)]
        metadata = {"iso": 200, "fnum": 4}

        result = grade_student(metadata, rules, 100)

        assert result.technical_score == 100.0
        assert result.system_score == 100

    def test_one_red_rule_loses_its_full_share(self):

        rules = [Rule("iso", 100, 400), Rule("aperture", 2, 8)]
        metadata = {"iso": 5000, "fnum": 4}  # iso far outside range -> RED

        result = grade_student(metadata, rules, 100)

        # Each rule is worth 50; the RED iso rule deducts its full 50.
        assert result.technical_score == 50.0

    def test_one_yellow_rule_loses_half_its_share(self):

        rules = [Rule("iso", 100, 400)]
        metadata = {"iso": 420}  # inside the tolerance zone -> YELLOW

        result = grade_student(metadata, rules, 100)

        assert result.technical_score == 50.0

    def test_missing_metadata_gives_no_technical_score(self):

        rules = [Rule("iso", 100, 400)]
        metadata = {"iso": None}

        result = grade_student(metadata, rules, 100)

        # A configured factor with no EXIF data can't be graded, so the
        # Rule Engine produces no score at all (the caller hands the
        # photo's full 100 points to Teacher Grading instead).
        assert result.technical_score is None
        assert result.exif_missing is True

        # The rule itself is still reported as MISSING, with no
        # deduction of its own.
        assert result.rule_results[0].status == MISSING
        assert result.rule_results[0].deduction == 0.0

    def test_one_missing_rule_invalidates_the_whole_score(self):

        rules = [Rule("iso", 100, 400), Rule("aperture", 2, 8)]
        metadata = {"iso": 200, "fnum": None}  # iso GREEN, aperture MISSING

        result = grade_student(metadata, rules, 100)

        # No partial score, even though the other rule was fine.
        assert result.technical_score is None
        assert result.exif_missing is True

        statuses = {r.factor: r.status for r in result.rule_results}
        assert statuses == {"iso": GREEN, "aperture": MISSING}

    def test_complete_metadata_does_not_flag_exif_missing(self):

        rules = [Rule("iso", 100, 400)]

        result = grade_student({"iso": 200}, rules, 100)

        assert result.exif_missing is False
        assert result.technical_score == 100.0

    def test_no_rules_configured_returns_the_full_system_score_untouched(self):

        result = grade_student({"iso": 200}, [], 60)

        assert result.technical_score == 60.0
        assert result.rule_results == []

    def test_rule_results_contain_one_entry_per_rule(self):

        rules = [Rule("iso", 100, 400), Rule("aperture", 2, 8)]

        result = grade_student({"iso": 200, "fnum": 4}, rules, 100)

        assert len(result.rule_results) == 2
        assert {r.factor for r in result.rule_results} == {"iso", "aperture"}

    def test_mixed_statuses_deduct_correctly_across_three_rules(self):

        # 3 rules of 100/3 points each.
        rules = [
            Rule("iso", 100, 400),          # GREEN  -> 0 deduction
            Rule("aperture", 2, 8),          # YELLOW -> half deduction
            Rule("focal_length", 24, 70),    # RED    -> full deduction
        ]

        metadata = {
            "iso": 200,        # inside range
            "fnum": 8.5,       # width 6, tolerance 0.9 -> yellow zone to 8.9
            "focal": 500,      # way outside 24-70
        }

        result = grade_student(metadata, rules, 99)

        share = 99 / 3
        expected_deduction = 0 + (share / 2) + share
        assert result.technical_score == pytest.approx(round(99 - expected_deduction, 1))


# -----------------------------------------
# RULE / RULE ENGINE CONFIG SERIALIZATION
# (Rule.to_dict/from_dict, RuleEngineConfig.to_dict/from_dict --
# used by storage.rule_presets and ClassRecord.rule_config)
# -----------------------------------------

def test_rule_engine_config_survives_a_to_dict_from_dict_round_trip():

    original = RuleEngineConfig(
        system_score=40,
        human_score=60,
        rules=[
            Rule(factor="iso", minimum=100.0, maximum=400.0),
            Rule(factor="aperture", minimum=2.0, maximum=8.0),
            Rule(factor="focal_length", minimum=24.0, maximum=70.0),
        ],
    )

    reconstructed = RuleEngineConfig.from_dict(original.to_dict())

    # Score split survives.
    assert reconstructed.system_score == original.system_score
    assert reconstructed.human_score == original.human_score

    # Every rule -- factor and its exact min/max range -- survives,
    # in the same order.
    assert len(reconstructed.rules) == len(original.rules)

    for rebuilt_rule, original_rule in zip(reconstructed.rules, original.rules):
        assert rebuilt_rule.factor == original_rule.factor
        assert rebuilt_rule.minimum == original_rule.minimum
        assert rebuilt_rule.maximum == original_rule.maximum

    # The round trip actually goes through plain, JSON-safe data --
    # not just returning the same objects back.
    as_dict = original.to_dict()
    assert as_dict == {
        "system_score": 40,
        "human_score": 60,
        "rules": [
            {"factor": "iso", "minimum": 100.0, "maximum": 400.0},
            {"factor": "aperture", "minimum": 2.0, "maximum": 8.0},
            {"factor": "focal_length", "minimum": 24.0, "maximum": 70.0},
        ],
    }

    # The reconstructed config must be usable by the scoring code
    # exactly like the original -- same grading result either way.
    metadata = {"iso": 200, "fnum": 4.0, "focal": 500}  # focal is RED

    original_result = grade_student(metadata, original.rules, original.system_score)
    reconstructed_result = grade_student(metadata, reconstructed.rules, reconstructed.system_score)

    assert reconstructed_result.technical_score == original_result.technical_score
    assert [r.status for r in reconstructed_result.rule_results] == [
        r.status for r in original_result.rule_results
    ]
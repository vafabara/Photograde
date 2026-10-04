"""
Rule definitions and validation for the PhotoGrade Rule Engine
(spec sections 2 and 3).

This module owns:
  - which metadata factors can be graded, and their metadata.py key
  - the *valid input range* for each factor, so the GUI can reject
    nonsense values (e.g. an ISO of -5, or an Aperture of 10000)
  - the Rule and RuleEngineConfig data structures
  - validation, with no dependency on CustomTkinter (spec section 8)
"""

from dataclasses import dataclass, field


# -----------------------------------------
# FACTOR DEFINITIONS
# -----------------------------------------
# valid_min / valid_max is the range the *professor's input* must
# fall within — not the Rule's own Minimum/Maximum. It's defined per
# factor on purpose: a single shared range (e.g. 0-10000) would let
# someone set an Aperture rule of "0-10000", which is meaningless.

FACTORS = {
    "iso": {
        "label": "ISO",
        "metadata_key": "iso",
        "valid_min": 25,
        "valid_max": 10000,
    },
    "aperture": {
        "label": "Aperture (F-Number)",
        "metadata_key": "fnum",
        "valid_min": 0.5,
        "valid_max": 64,
    },
    "shutter_speed": {
        "label": "Shutter Speed (seconds)",
        "metadata_key": "exposure_time",
        "valid_min": 0.00001,   # 1/100000s
        "valid_max": 30,        # 30s
    },
    "focal_length": {
        "label": "Focal Length (mm)",
        "metadata_key": "focal",
        "valid_min": 1,
        "valid_max": 2000,
    },
}


class RuleError(ValueError):
    """Raised when a Rule or score split fails validation."""


@dataclass
class Rule:
    factor: str        # a key from FACTORS, e.g. "iso"
    minimum: float
    maximum: float

    # New (Settings feature): the tolerance this Rule was created
    # with, as a fraction of its range (0.15 = 15%). None means "use
    # tolerance.MAX_TOLERANCE_PERCENT" -- which is what every Rule
    # saved before this field existed does, so old classes and
    # presets grade exactly as they always did.
    tolerance_percent: float | None = None

    def to_dict(self):
        data = {
            "factor": self.factor,
            "minimum": self.minimum,
            "maximum": self.maximum,
        }

        # Only written when set, so a Rule without a custom
        # tolerance serializes exactly as it did before.
        if self.tolerance_percent is not None:
            data["tolerance_percent"] = self.tolerance_percent

        return data

    @classmethod
    def from_dict(cls, data):
        return cls(
            factor=data["factor"],
            minimum=data["minimum"],
            maximum=data["maximum"],
            tolerance_percent=data.get("tolerance_percent"),
        )


@dataclass
class RuleEngineConfig:
    """
    to_dict()/from_dict() here are the single place a RuleEngineConfig
    is turned into/out of JSON -- both Rule Engine Presets
    (storage.rule_presets) and a class's own persisted configuration
    (ClassRecord.rule_config) reuse these instead of each having
    their own serialization.
    """

    system_score: float
    human_score: float
    rules: list = field(default_factory=list)

    def to_dict(self):
        return {
            "system_score": self.system_score,
            "human_score": self.human_score,
            "rules": [rule.to_dict() for rule in self.rules],
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            system_score=data["system_score"],
            human_score=data["human_score"],
            rules=[Rule.from_dict(rule_data) for rule_data in data.get("rules", [])],
        )


# -----------------------------------------
# VALIDATION
# -----------------------------------------

def validate_rule(factor, minimum, maximum):
    """
    Validate a Minimum/Maximum pair for `factor`.
    Raises RuleError with a human-readable message on failure.
    """

    if factor not in FACTORS:
        raise RuleError(f"Unknown factor: {factor}")

    bounds = FACTORS[factor]

    if minimum is None or maximum is None:
        raise RuleError("Both Minimum and Maximum are required.")

    if minimum > maximum:
        raise RuleError(
            f"{bounds['label']}: Minimum cannot be greater than Maximum."
        )

    valid_min = bounds["valid_min"]
    valid_max = bounds["valid_max"]

    if not (valid_min <= minimum <= valid_max):
        raise RuleError(
            f"{bounds['label']} Minimum must be between "
            f"{valid_min} and {valid_max}."
        )

    if not (valid_min <= maximum <= valid_max):
        raise RuleError(
            f"{bounds['label']} Maximum must be between "
            f"{valid_min} and {valid_max}."
        )


def build_rule(factor, minimum, maximum, tolerance_percent=None):
    """
    Validate and construct a Rule. Raises RuleError on invalid input.

    `tolerance_percent` (optional, a fraction like 0.15) is stored on
    the Rule so it keeps its own tolerance even if the default in
    Settings changes later.
    """

    validate_rule(factor, minimum, maximum)

    return Rule(
        factor=factor,
        minimum=float(minimum),
        maximum=float(maximum),
        tolerance_percent=(
            None if tolerance_percent is None else float(tolerance_percent)
        ),
    )


def validate_score_split(system_score, human_score):
    """
    Validate the System/Human score split (spec section 3).
    The two must be non-negative and add up to exactly 100.
    """

    if system_score is None or human_score is None:
        raise RuleError("Both System Score and Human Score are required.")

    if system_score < 0 or human_score < 0:
        raise RuleError("Scores cannot be negative.")

    if abs((system_score + human_score) - 100) > 1e-9:
        raise RuleError("System Score and Human Score must add up to 100.")
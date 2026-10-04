"""
Automatic tolerance calculation (spec section 6).

The professor never sets Tolerance per Rule directly. For each Rule,
the system widens the Minimum/Maximum range by a percentage of the
range's own width. A value inside that widened range but outside the
original range is YELLOW; anything further out is RED.

The percentage is the Rule's own `tolerance_percent` if it has one
(set from Settings -> Default Tolerance when the Rule was created),
otherwise MAX_TOLERANCE_PERCENT -- so every Rule saved before
Settings existed behaves exactly as before.

Because the widening is a percentage of each Rule's own width, two
different factors (e.g. ISO 200-600 vs. Aperture f/4-f/8) each get a
tolerance proportional to their own range — not one shared constant.
"""

MAX_TOLERANCE_PERCENT = 0.15


def compute_tolerance(rule):
    """
    Return the tolerance amount (in the factor's own units) for a
    single Rule — an absolute value added/subtracted from the range,
    not a percentage.
    """

    percent = (
        MAX_TOLERANCE_PERCENT
        if rule.tolerance_percent is None
        else rule.tolerance_percent
    )

    range_width = rule.maximum - rule.minimum

    if range_width <= 0:
        # A zero-width rule (min == max) would otherwise get zero
        # tolerance, making it impossible to ever score YELLOW.
        # Fall back to a tolerance based on the value itself.
        reference = rule.maximum if rule.maximum else 1
        return abs(reference) * percent

    return range_width * percent


def tolerance_bounds(rule):
    """
    Return the (lower, upper) bounds of the tolerance zone — the
    widened range that separates YELLOW from RED.
    """

    tolerance = compute_tolerance(rule)

    return (
        rule.minimum - tolerance,
        rule.maximum + tolerance,
    )
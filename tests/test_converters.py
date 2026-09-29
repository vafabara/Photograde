import pytest

from app.core.converters import (
    decode_exif_value,
    exif_value,
    rational_to_float,
    rational_to_fraction,
    shutter_speed_to_seconds,
    to_comparable,
)


class TestDecodeExifValue:

    def test_none_stays_none(self):

        assert decode_exif_value(None) is None

    def test_bytes_are_decoded_to_str(self):

        assert decode_exif_value(b"Canon") == "Canon"

    def test_trailing_null_bytes_and_whitespace_are_stripped(self):

        # EXIF text fields are usually null-terminated.
        assert decode_exif_value(b"Canon\x00") == "Canon"
        assert decode_exif_value(b"  EOS R5 \x00") == "EOS R5"

    def test_invalid_bytes_are_ignored_instead_of_raising(self):

        assert decode_exif_value(b"Ca\xffnon") == "Canon"

    def test_non_bytes_values_pass_through_unchanged(self):

        assert decode_exif_value(400) == 400
        assert decode_exif_value("already text") == "already text"


class TestRationalToFloat:

    def test_converts_a_normal_rational(self):

        assert rational_to_float((28, 10)) == pytest.approx(2.8)
        assert rational_to_float((50, 1)) == 50.0

    def test_zero_numerator_gives_zero(self):

        assert rational_to_float((0, 1)) == 0.0

    def test_zero_denominator_returns_none(self):

        assert rational_to_float((5, 0)) is None

    def test_none_or_empty_returns_none(self):

        assert rational_to_float(None) is None
        assert rational_to_float(()) is None


class TestRationalToFraction:

    def test_fast_shutter_speed_is_shown_as_a_fraction(self):

        assert rational_to_fraction((1, 125)) == "1/125"

    def test_one_second_or_longer_is_shown_as_seconds(self):

        assert rational_to_fraction((1, 1)) == "1s"
        assert rational_to_fraction((2, 1)) == "2s"
        assert rational_to_fraction((3, 2)) == "1.5s"

    def test_zero_denominator_returns_none(self):

        assert rational_to_fraction((1, 0)) is None

    def test_none_or_empty_returns_none(self):

        assert rational_to_fraction(None) is None
        assert rational_to_fraction(()) is None


class TestExifValue:

    def test_none_and_empty_string_show_the_placeholder(self):

        assert exif_value(None) == "—"
        assert exif_value("") == "—"

    def test_floats_drop_trailing_zeros(self):

        assert exif_value(50.0) == "50"
        assert exif_value(2.8) == "2.8"

    def test_other_values_become_strings(self):

        assert exif_value(400) == "400"
        assert exif_value("Canon") == "Canon"

    def test_zero_is_a_real_value_not_the_placeholder(self):

        assert exif_value(0) == "0"


class TestShutterSpeedToSeconds:

    def test_fraction_string(self):

        assert shutter_speed_to_seconds("1/125") == pytest.approx(1 / 125)

    def test_seconds_string_with_s_suffix(self):

        assert shutter_speed_to_seconds("2s") == 2.0
        assert shutter_speed_to_seconds("0.5s") == 0.5

    def test_plain_number_string(self):

        assert shutter_speed_to_seconds("0.25") == 0.25

    def test_surrounding_whitespace_is_ignored(self):

        assert shutter_speed_to_seconds("  1/60 ") == pytest.approx(1 / 60)

    def test_none_returns_none(self):

        assert shutter_speed_to_seconds(None) is None

    def test_division_by_zero_returns_none(self):

        assert shutter_speed_to_seconds("1/0") is None

    @pytest.mark.parametrize("bad", ["abc", "a/b", "1/x", "xs", ""])
    def test_unparseable_strings_return_none(self, bad):

        assert shutter_speed_to_seconds(bad) is None

    def test_round_trip_with_rational_to_fraction(self):

        # metadata.py stores the display string; the Rule Engine must
        # be able to turn it back into seconds.
        assert shutter_speed_to_seconds(rational_to_fraction((1, 250))) == pytest.approx(1 / 250)
        assert shutter_speed_to_seconds(rational_to_fraction((2, 1))) == 2.0


class TestToComparable:

    def test_none_returns_none_for_every_factor(self):

        for factor in ("iso", "aperture", "shutter_speed", "focal_length"):
            assert to_comparable(factor, None) is None

    def test_shutter_speed_goes_through_the_string_converter(self):

        assert to_comparable("shutter_speed", "1/125") == pytest.approx(1 / 125)

    def test_numeric_factors_become_floats(self):

        assert to_comparable("iso", 400) == 400.0
        assert isinstance(to_comparable("iso", 400), float)
        assert to_comparable("aperture", 2.8) == 2.8
        assert to_comparable("focal_length", 50.0) == 50.0

    def test_numeric_strings_are_accepted(self):

        assert to_comparable("iso", "400") == 400.0

    def test_unconvertible_values_return_none(self):

        assert to_comparable("iso", "abc") is None
        assert to_comparable("iso", (1, 2)) is None

    def test_unparseable_shutter_speed_returns_none(self):

        assert to_comparable("shutter_speed", "fast") is None

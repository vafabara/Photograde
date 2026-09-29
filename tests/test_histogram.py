from PIL import Image

from app.core.histogram import get_histogram


class TestGetHistogram:

    def test_returns_r_g_b_channels_with_256_bins_each(self):

        histogram = get_histogram(Image.new("RGB", (4, 4), (10, 20, 30)))

        assert set(histogram.keys()) == {"r", "g", "b"}

        for channel in ("r", "g", "b"):
            assert len(histogram[channel]) == 256

    def test_solid_red_image_puts_every_pixel_in_the_expected_bins(self):

        image = Image.new("RGB", (10, 10), (255, 0, 0))

        histogram = get_histogram(image)

        assert histogram["r"][255] == 100
        assert histogram["g"][0] == 100
        assert histogram["b"][0] == 100

    def test_each_channel_counts_every_pixel_exactly_once(self):

        image = Image.new("RGB", (7, 3), (12, 200, 99))

        histogram = get_histogram(image)

        for channel in ("r", "g", "b"):
            assert sum(histogram[channel]) == 7 * 3

    def test_mixed_pixels_are_counted_per_channel(self):

        image = Image.new("RGB", (2, 1))
        image.putpixel((0, 0), (0, 0, 0))
        image.putpixel((1, 0), (255, 128, 0))

        histogram = get_histogram(image)

        assert histogram["r"][0] == 1 and histogram["r"][255] == 1
        assert histogram["g"][0] == 1 and histogram["g"][128] == 1
        assert histogram["b"][0] == 2

    def test_grayscale_image_is_converted_and_channels_match(self):

        image = Image.new("L", (5, 5), 100)

        histogram = get_histogram(image)

        assert histogram["r"] == histogram["g"] == histogram["b"]
        assert histogram["r"][100] == 25

    def test_rgba_image_is_supported(self):

        image = Image.new("RGBA", (4, 4), (255, 0, 0, 128))

        histogram = get_histogram(image)

        assert histogram["r"][255] == 16

    def test_does_not_modify_the_original_image(self):

        image = Image.new("L", (4, 4), 50)

        get_histogram(image)

        assert image.mode == "L"

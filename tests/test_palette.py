"""Palettes taken from pictures: light or dark, readable, colourful."""

import unittest

from qgis.PyQt.QtGui import QColor, QImage

from qrice import palette

BLACK, WHITE = (0, 0, 0), (255, 255, 255)


def picture(*colors):
    """Image of vertical stripes, one per (rgb, width) pair."""
    width = sum(w for _, w in colors)
    image = QImage(width, 20, QImage.Format.Format_ARGB32)
    x = 0
    for rgb, w in colors:
        for dx in range(w):
            for y in range(20):
                image.setPixelColor(x + dx, y, QColor(*rgb))
        x += w
    return image


class ColourMaths(unittest.TestCase):

    def test_contrast_of_black_on_white_is_21(self):
        self.assertAlmostEqual(palette.contrast(BLACK, WHITE), 21, places=1)

    def test_hex_round_trip(self):
        self.assertEqual(palette.parse_hex(palette.hex_color((18, 52, 86))),
                         (18, 52, 86))

    def test_readable_on_reaches_the_contrast(self):
        grey = palette.readable_on((90, 90, 90), (60, 60, 60))
        self.assertGreaterEqual(palette.contrast(grey, (60, 60, 60)),
                                palette.MIN_TEXT_CONTRAST)


class FromPictures(unittest.TestCase):

    def test_median_cut_finds_the_main_colours(self):
        colors = palette.colors_of(picture(((200, 30, 30), 40),
                                           ((30, 30, 200), 20)), 2)
        self.assertEqual(len(colors), 2)
        reddest = max(colors, key=lambda c: c[0][0])[0]
        self.assertGreater(reddest[0], 150)

    def test_dark_picture_gives_a_dark_theme(self):
        result = palette.palette_from_image(
            picture(((15, 15, 25), 50), ((220, 40, 120), 10)))
        bg = palette.parse_hex(result["bg-panel"])
        self.assertLess(palette.luminance(bg), 0.1)

    def test_light_picture_gives_a_light_theme(self):
        result = palette.palette_from_image(
            picture(((240, 240, 230), 50), ((40, 120, 220), 10)))
        bg = palette.parse_hex(result["bg-panel"])
        self.assertGreater(palette.luminance(bg), 0.7)

    def test_accent_is_the_most_saturated_colour(self):
        result = palette.palette_from_image(
            picture(((128, 128, 128), 50), ((20, 200, 40), 10)))
        accent = palette.parse_hex(result["accent"])
        self.assertGreater(accent[1], accent[0] + 60)  # green

    def test_text_reads_on_every_background(self):
        for dark in (True, False):
            result = palette.palette_from_image(
                picture(((250, 200, 0), 30), ((0, 150, 60), 30)), dark)
            text = palette.parse_hex(result["text"])
            for bg in ("bg-window", "bg-panel", "bg-header"):
                self.assertGreaterEqual(
                    palette.contrast(text, palette.parse_hex(result[bg])),
                    palette.MIN_TEXT_CONTRAST, (dark, bg))

    def test_an_unreadable_file_gives_a_grey_palette(self):
        result = palette.palette_from_image("/no/such/picture.png")
        self.assertIn("accent", result)

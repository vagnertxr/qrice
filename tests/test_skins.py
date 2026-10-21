"""Bundled skins: well formed, credited, and their style sheets complete."""

import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from qrice import flags, skins
from qrice.plugin import skin_qss, skin_variables

CREDITS = (skins.BUILTIN / "CREDITS.md").read_text(encoding="utf-8")


class Bundled(unittest.TestCase):

    def setUp(self):
        self.skins = [s for s in skins.list_skins() if s.kind == "builtin"]

    def test_the_default_skin_exists(self):
        self.assertIsNotNone(skins.load_skin(skins.DEFAULT_SKIN))

    def test_every_skin_has_a_licence_layout_and_category(self):
        for skin in self.skins:
            self.assertTrue(skin.license, skin.id)
            self.assertIn(skin.layout, skins.LAYOUTS, skin.id)
            self.assertIn(skin.category, skins.CATEGORIES, skin.id)

    def test_pictures_exist_and_are_credited(self):
        for skin in self.skins:
            for key in ("mascot", "panel_bg"):
                if skin.data.get(key):
                    self.assertIsNotNone(skin.section(key), (skin.id, key))
            pictures = [p for p in skin.path.iterdir()
                        if p.suffix.lower() in skins.PICTURES]
            for path in pictures:
                self.assertIn(path.name, CREDITS, path)

    def test_style_sheets_have_no_unresolved_variables(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
                skins, "user_dir", return_value=Path(tmp)):
            for skin in self.skins:
                qss = skin_qss(skin)
                self.assertEqual(re.findall(r"@[\w-]+", qss), [], skin.id)
                for url in re.findall(r"url\(([^)]+)\)", qss):
                    self.assertTrue(Path(url).exists(), (skin.id, url))


class UserSkins(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(skins, "user_dir",
                                    return_value=Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_skin_from_a_picture_round_trips_through_a_zip(self):
        picture = skins.BUILTIN / "tux" / "tux.png"
        skin = skins.skin_from_picture(picture, "My Tux")
        self.assertEqual(skins.load_skin(skin.id).name, "My Tux")
        self.assertIsNotNone(skin.section("panel_bg"))
        self.assertIsNone(skin.section("mascot"), "no mascot by default")
        archive = Path(self.tmp.name) / "my.zip"
        skins.export_skin(skin, archive)
        copy = skins.import_skin(archive)
        self.assertNotEqual(copy.id, skin.id)
        self.assertTrue((copy.path / "tux.png").exists())
        skins.delete_skin(copy)
        self.assertIsNone(skins.load_skin(copy.id))

    def test_builtin_skins_cannot_be_deleted(self):
        with self.assertRaises(ValueError):
            skins.delete_skin(skins.load_skin(skins.DEFAULT_SKIN))

    def test_dev_skins_need_the_environment_variable(self):
        dev = Path(self.tmp.name) / "dev"
        (dev / "joke").mkdir(parents=True)
        (dev / "joke" / "skin.json").write_text('{"name": "Joke"}')
        self.assertIsNone(skins.load_skin("joke"))
        with mock.patch.dict("os.environ", {skins.DEV_ENV: str(dev)}):
            self.assertEqual(skins.load_skin("joke").kind, "dev")


class ForcedColours(unittest.TestCase):

    def test_club_colours_are_kept_exactly(self):
        skin = skins.Skin("x", skins.BUILTIN, "user", {
            "name": "Club", "dark": True,
            "colors": {"base": "#000000", "accent": "#c8102e",
                       "accent2": "#ffffff"}})
        variables = skin_variables(skin)
        self.assertEqual(variables["accent"], "#c8102e")
        self.assertEqual(variables["accent2"], "#ffffff")
        self.assertEqual(variables["accent2-text"], "#141414")

    def test_no_bundled_skin_puts_a_mascot_over_the_map(self):
        for skin in skins.list_skins():
            if skin.kind == "builtin":
                self.assertIsNone(skin.data.get("mascot"), skin.id)


class Flags(unittest.TestCase):

    def test_every_country_has_a_flag(self):
        for code in flags.countries():
            self.assertIsNotNone(flags.flag_file(code), code)

    def test_flag_skin_uses_the_flag_behind_the_panes(self):
        skin = skins.Skin("x", skins.BUILTIN, "builtin",
                          flags.flag_skin_data("jp"))
        self.assertEqual(skin.section("panel_bg")["file"].name, "jp.svg")
        self.assertIsNone(skin.section("mascot"))
        self.assertEqual(skin.palette_source().name, "jp.svg")

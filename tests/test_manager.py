"""Skin Manager editing: a copy of a skin with fixed colours can be given
another character and take its colours from it."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from qrice import skins
from qrice.manager import SkinManager
from qrice.plugin import skin_variables


class FakePlugin:
    def reapply(self):
        pass

    def switch_skin(self, skin_id):
        pass


class NewCharacter(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(skins, "user_dir",
                                    return_value=Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_colours_from_the_new_picture_replace_the_fixed_ones(self):
        copy = skins.duplicate_skin(skins.load_skin("pro-qgis-tan"), "Mine")
        fixed = skin_variables(copy)["accent"]
        manager = SkinManager(FakePlugin())
        manager.skin = copy
        manager._load_editor()
        shutil.copy2(skins.BUILTIN / "tux" / "tux.png", copy.path)
        manager.picture_name = "tux.png"
        manager.auto_palette.setChecked(True)  # saves through _edited
        saved = skins.load_skin(copy.id)
        self.assertNotIn("colors", saved.data)
        self.assertEqual(saved.layout, "pro")
        self.assertEqual(saved.section("panel_bg")["file"].name, "tux.png")
        self.assertNotEqual(skin_variables(saved)["accent"], fixed)


class Names(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(skins, "user_dir",
                                    return_value=Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.manager = SkinManager(FakePlugin())

    def test_duplicate_asks_for_the_copy_s_name(self):
        self.manager.skin = skins.load_skin("tux")
        with mock.patch.object(self.manager, "_ask_name",
                               return_value="Pinguim"):
            self.manager.duplicate()
        self.assertEqual(self.manager.skin.name, "Pinguim")
        self.assertTrue(self.manager.skin.editable)

    def test_cancelled_duplicate_creates_nothing(self):
        self.manager.skin = skins.load_skin("tux")
        before = len(skins.list_skins())
        with mock.patch.object(self.manager, "_ask_name", return_value=None):
            self.manager.duplicate()
        self.assertEqual(len(skins.list_skins()), before)

    def test_rename_keeps_the_folder(self):
        copy = skins.duplicate_skin(skins.load_skin("tux"), "Old name")
        self.manager.skin = copy
        with mock.patch.object(self.manager, "_ask_name",
                               return_value="New name"):
            self.manager.rename()
        renamed = skins.load_skin(copy.id)
        self.assertEqual(renamed.name, "New name")
        self.assertEqual(renamed.path, copy.path)

    def test_built_in_skins_cannot_be_renamed(self):
        self.manager.skin = skins.load_skin("tux")
        with mock.patch.object(self.manager, "_ask_name",
                               return_value="Nope") as ask:
            self.manager.rename()
        ask.assert_not_called()
        self.assertEqual(skins.load_skin("tux").name, "Tux")


class HandPickedColours(unittest.TestCase):

    def test_derived_colours_follow_swatches_not_the_fixed_palette(self):
        # A copy of Pro QGIS-tan (fixed greens) with reds picked by hand:
        # pressed buttons, hover, selection etc. must not stay green.
        data = dict(skins.load_skin("pro-qgis-tan").data)
        data["variables"] = {"accent": "#e01b24", "accent2": "#ed333b",
                             "bg-panel": "#ffecec", "border": "#ff6262"}
        skin = skins.Skin("asuka", skins.BUILTIN / "pro-qgis-tan", "user",
                          data)
        variables = skin_variables(skin)
        for name in ("pressed", "hover", "accent-dark", "selected-soft",
                     "border-hover", "scrollbar-handle", "border-light"):
            r, g, b = (int(variables[name][i:i + 2], 16) for i in (1, 3, 5))
            self.assertGreaterEqual(r, g, f"{name} {variables[name]}")

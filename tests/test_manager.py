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

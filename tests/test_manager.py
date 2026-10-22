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
        data["variables"]["text"] = "#a51d2d"
        skin = skins.Skin("asuka", skins.BUILTIN / "pro-qgis-tan", "user",
                          data)
        variables = skin_variables(skin)
        for name in ("pressed", "hover", "accent-dark", "selected-soft",
                     "border-hover", "scrollbar-handle", "border-light",
                     "text-emphasis", "text-disabled", "selected-text"):
            r, g, b = (int(variables[name][i:i + 2], 16) for i in (1, 3, 5))
            self.assertGreaterEqual(r, g, f"{name} {variables[name]}")


class PanePictureSize(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(skins, "user_dir",
                                    return_value=Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_size_is_saved_and_the_picture_rendered_at_it(self):
        from qgis.PyQt.QtGui import QImage

        from qrice.panel_bg import render_panel_bg

        copy = skins.duplicate_skin(skins.load_skin("tux"), "Big Tux")
        manager = SkinManager(FakePlugin())
        manager.skin = copy
        manager._load_editor()
        manager.panel_height.setValue(1100)  # bigger than tux.png (900)
        panel = skins.load_skin(copy.id).section("panel_bg")
        self.assertEqual(panel["height"], 1100)
        out = Path(self.tmp.name) / "panel.png"
        render_panel_bg(panel["file"], "#000000", 0.2, panel["height"], out)
        self.assertEqual(QImage(str(out)).height(), 1100)


class OwnSkinsHaveNoCredits(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(skins, "user_dir",
                                    return_value=Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_copies_drop_author_licence_and_source(self):
        copy = skins.duplicate_skin(skins.load_skin("tux"), "Mine")
        for key in skins.CREDIT_KEYS:
            self.assertNotIn(key, skins.load_skin(copy.id).data)

    def test_manager_shows_no_credit_line_for_own_skins(self):
        manager = SkinManager(FakePlugin())
        manager.skin = skins.load_skin("tux")
        manager._load_editor()
        self.assertIn("Larry Ewing", manager.credit.text())
        old_copy = skins.new_skin("Old copy", {"author": "Someone"})
        manager.skin = old_copy
        manager._load_editor()
        self.assertEqual(manager.credit.text(), "")


class PanePicturePosition(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(skins, "user_dir",
                                    return_value=Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_position_and_margin_reach_the_style_sheet_and_picture(self):
        from qgis.PyQt.QtGui import QImage

        from qrice.plugin import skin_qss

        copy = skins.duplicate_skin(skins.load_skin("tux"), "Moved Tux")
        manager = SkinManager(FakePlugin())
        manager.skin = copy
        manager._load_editor()
        manager.panel_height.setValue(200)
        manager.align_x.setCurrentIndex(manager.align_x.findData("left"))
        manager.margin_y.setValue(60)
        saved = skins.load_skin(copy.id)
        qss = skin_qss(saved)
        self.assertIn("background-position: bottom left;", qss)
        picture = QImage(str(skins.cache_dir(copy.id) / "panel.png"))
        self.assertEqual(picture.height(), 260)  # 200 + 60 below it
        # The added strip at the bottom is transparent.
        self.assertEqual(picture.pixelColor(5, 255).alpha(), 0)


class OnOffSwitch(unittest.TestCase):
    """The toolbar button opens the manager, so the manager switches the
    skin on and off, in step with the plugin's action."""

    def test_checkbox_and_plugin_action_follow_each_other(self):
        from qgis.PyQt.QtGui import QAction

        plugin = FakePlugin()
        plugin.action = QAction("QRice skin", checkable=True, checked=True)
        manager = SkinManager(plugin)
        self.assertTrue(manager.enabled.isChecked())
        manager.enabled.setChecked(False)
        self.assertFalse(plugin.action.isChecked())
        plugin.action.setChecked(True)
        self.assertTrue(manager.enabled.isChecked())

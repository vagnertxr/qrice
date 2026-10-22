"""Window chrome: the zen layout's help box."""

import unittest
from unittest import mock

from qgis.PyQt.QtWidgets import QMainWindow

from qrice import chrome
from qrice.util import Changes


class FakeSettings:
    store = {}

    def value(self, key, default=None, type=None):  # noqa: A002 (Qt name)
        return self.store.get(key, default)

    def setValue(self, key, value):  # noqa: N802 (Qt name)
        self.store[key] = value


class ZenHelp(unittest.TestCase):

    def setUp(self):
        FakeSettings.store = {}
        patcher = mock.patch.object(chrome, "QgsSettings", FakeSettings)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.win = QMainWindow()

    def test_box_tells_the_shortcuts_and_closes_with_the_skin(self):
        changes = Changes()
        box = chrome.zen_help(self.win, changes)
        self.assertTrue(box.isVisible())
        self.assertFalse(box.isModal())
        for shortcut in (chrome.ZEN_KEY, chrome.MENUBAR_KEY):
            self.assertIn(shortcut, box.text())
        changes.undo()
        self.assertFalse(box.isVisible())

    def test_dont_show_again(self):
        box = chrome.zen_help(self.win, Changes())
        box.checkBox().setChecked(True)
        self.assertTrue(FakeSettings.store[chrome.ZEN_HELP_KEY])
        self.assertIsNone(chrome.zen_help(self.win, Changes()))

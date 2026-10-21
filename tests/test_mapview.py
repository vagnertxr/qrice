"""Map view helpers that move QGIS's own widgets around."""

import unittest

from qgis.PyQt import sip
from qgis.PyQt.QtWidgets import QFrame, QGridLayout, QWidget

from qrice.mapview import _lower_message_bar
from qrice.util import Changes


class MessageBar(unittest.TestCase):

    def test_qgis_keeps_ownership_of_the_message_bar(self):
        # Python owning the bar after the move would delete it with its
        # wrapper while QGIS still points at it (crash on the next skin).
        central = QWidget()
        grid = QGridLayout(central)
        grid.addWidget(QWidget(), 0, 0)
        bar = QFrame()
        grid.addWidget(bar, 0, 0)
        changes = Changes()
        _lower_message_bar(bar, grid, 30, changes)
        self.assertFalse(sip.ispyowned(bar))
        changes.undo()
        self.assertFalse(sip.ispyowned(bar))
        self.assertEqual(grid.getItemPosition(grid.indexOf(bar))[:2], (0, 0))

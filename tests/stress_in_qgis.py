"""Stress test to run inside QGIS with QRice loaded: switches skins many
times (Pro layout included), moving the focus between panes, then turns
the skin off and on. A crash (signal 11) is written to fault.txt.

    QRICE_SHOTS=/tmp/out QT_QPA_PLATFORM=offscreen \\
        qgis --nologo --code tests/stress_in_qgis.py

SEQ (comma-separated skin ids) and ROUNDS override the defaults.
"""

import faulthandler
import os
import time
import traceback

from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QApplication, QDockWidget, QTreeView
from qgis.utils import iface, plugins

OUT = os.environ["QRICE_SHOTS"]
SEQ = os.environ.get(
    "SEQ", "pro-dark,qgis-tan,pro-qgis-tan,pro-light,zen,pro-dark,"
           "rice-dark,pro-qgis-tan,tux,pro-light").split(",")
ROUNDS = int(os.environ.get("ROUNDS", "2"))

FAULTS = open(os.path.join(OUT, "fault.txt"), "w")
faulthandler.enable(file=FAULTS, all_threads=True)
LOG = open(os.path.join(OUT, "stress.txt"), "w")


def say(*args):
    print(*args, file=LOG, flush=True)


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        QApplication.processEvents()
        time.sleep(0.02)


def move_focus():
    for dock in iface.mainWindow().findChildren(QDockWidget):
        view = dock.findChild(QTreeView) if dock.isVisible() else None
        if view:
            view.setFocus()
            pump(0.2)
    iface.mapCanvas().setFocus()
    pump(0.2)


def run():
    try:
        plugin = plugins["qrice"]
        for round_ in range(ROUNDS):
            for skin_id in SEQ:
                say("switch", round_, skin_id)
                plugin.switch_skin(skin_id)
                pump(0.6)
                move_focus()
            say("toggle off/on")
            plugin.action.setChecked(False)
            pump(0.5)
            plugin.action.setChecked(True)
            pump(0.5)
            move_focus()
        say("DONE")
    except Exception:  # noqa: BLE001 (logged for the reader)
        say(traceback.format_exc())
    os._exit(0)


QTimer.singleShot(4000, run)

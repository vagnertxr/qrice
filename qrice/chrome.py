"""Window composition ricing: gaps, corners, focus frame, bars and layouts.

A skin's ``chrome`` section (all keys optional)::

    {"gaps": 6,               # px between panes (i3-gaps style)
     "radius": 8,             # px, corners of panes and widgets
     "focus_border": 2,       # px, accent frame of the focused pane
     "font": "JetBrains Mono", "font_size": 10,
     "dock_titles": "full",   # full | minimal | hidden
     "menubar": "shown",      # shown | hidden (Ctrl+Alt+M toggles)
     "toolbars": "top",       # top | left | hidden
     "statusbar": "plain",    # plain | polybar
     "bars": "plain",         # plain | accent (menu bar, pane titles and
                              #   status bar in the accent colours)
     "glow": 0,               # px, neon halo around the focused pane
     "glow_pulse": false,     # the halo breathes
     "shine": false,          # glossy gradients on bars, tabs and buttons
     "map_frame": 0}          # px, accent frame around the map
     "opacity": 1.0,          # whole window (needs a compositor)
     "map_background": "keep"}  # keep | theme (map canvas in @bg-window)

and its ``layout``: ``tiling`` (map and a stack of Layers + Browser, the
other panes closed) or ``zen`` (map only; Ctrl+Alt+Z brings the panes and
toolbars back for a moment). Dock and toolbar positions come back with the
window state the plugin saves; everything else goes through ``Changes``.
"""

from qgis.PyQt import sip
from qgis.PyQt.QtCore import QEasingCurve, QObject, Qt, QVariantAnimation
from qgis.PyQt.QtGui import QColor, QFontDatabase, QKeySequence
from qgis.PyQt.QtWidgets import (
    QApplication, QDockWidget, QGraphicsDropShadowEffect, QToolBar, QWidget,
)

try:  # Qt 6
    from qgis.PyQt.QtGui import QShortcut
except ImportError:  # Qt 5
    from qgis.PyQt.QtWidgets import QShortcut

from .panes import ActivePane

LEFT = Qt.DockWidgetArea.LeftDockWidgetArea
DEFAULTS = {"gaps": 6, "radius": 8, "focus_border": 2, "font": None,
            "font_size": None, "dock_titles": "full", "menubar": "shown",
            "toolbars": "top", "statusbar": "plain", "opacity": 1.0,
            "map_background": "keep", "bars": "plain", "glow": 0,
            "glow_pulse": False, "shine": False, "map_frame": 0}
MENUBAR_KEY = "Ctrl+Alt+M"
ZEN_KEY = "Ctrl+Alt+Z"


def settings(chrome):
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in (chrome or {}).items() if v is not None})
    return merged


def font_family(name):
    """``name`` when installed, else the interface's current font."""
    try:
        families = QFontDatabase.families()
    except TypeError:  # Qt 5: not static
        families = QFontDatabase().families()
    if name and name in families:
        return name
    return QApplication.font().family()


def chrome_variables(chrome):
    """Theme variables for the ``chrome`` settings (rice theme names)."""
    c = settings(chrome)
    size = c["font_size"] or QApplication.font().pointSizeF() or 10
    titles = c["dock_titles"]
    return {
        "gaps": f"{int(c['gaps'])}px",
        "radius": f"{int(c['radius'])}px",
        "radius-small": f"{max(int(c['radius']) // 2, 0)}px",
        "focus-border": f"{int(c['focus_border'])}px",
        "font": f'"{font_family(c["font"])}"',
        "font-size": f"{size:g}pt",
        "dock-title-padding": "1px 8px" if titles == "minimal"
        else "5px 10px",
        "dock-title-size": f"{max(size - 1, 7):g}pt" if titles == "minimal"
        else f"{size:g}pt",
        "map-frame": f"{int(c['map_frame'])}px",
    }


POLYBAR_QSS = """
/* Status bar as a polybar: pills on the window colour. QGIS gives its
   status bar labels fixed widths, so the pills add no side padding. */
QStatusBar {
    padding: 2px 4px;
}
QStatusBar QLabel,
QStatusBar QLineEdit,
QStatusBar QToolButton,
QStatusBar QComboBox {
    background-color: @bg-header;
    color: @text;
    border: none;
    border-radius: @radius-small;
    padding: 1px 0;
    margin: 1px 1px;
}
QStatusBar QToolButton:checked,
QStatusBar QToolButton:hover {
    background-color: @accent;
    color: @accent-text;
}
QStatusBar QgsStatusBarCoordinatesWidget QLineEdit,
QStatusBar QgsStatusBarScaleWidget QComboBox {
    background-color: @accent2;
    color: @accent2-text;
}
"""


ACCENT_BARS_QSS = """
/* Bars in the accent colours (a club's or a flag's colours). */
QMenuBar {
    background-color: @accent;
    border-bottom: 3px solid @accent2;
}
QMenuBar::item {
    color: @accent-text;
}
QMenuBar::item:selected {
    background-color: @accent2;
    color: @accent2-text;
}
QToolBar {
    border-bottom: 1px solid @accent;
}
QDockWidget {
    color: @accent-text;
}
QDockWidget::title {
    background-color: @accent;
}
QDockWidget[arcskinActive="true"] {
    color: @accent2-text;
}
QDockWidget[arcskinActive="true"]::title {
    background-color: @accent2;
    border-color: @accent2;
}
QDockWidget[arcskinActive="true"] > QWidget {
    border-color: @accent2;
}
QStatusBar {
    background-color: @accent;
    border-top: 3px solid @accent2;
}
QStatusBar QLabel,
QStatusBar QCheckBox {
    color: @accent-text;
}
"""


# Glossy bars: a light band on top fading into the colour, like the
# shine on an old Aqua / Frutiger Aero button.
SHINE_QSS = """
QDockWidget::title,
QMenuBar,
QStatusBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 @shine-top, stop:0.45 @shine-mid, stop:1 @shine-bottom);
}
QTabBar::tab:selected,
QPushButton:default,
QMenuBar::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 @accent-light, stop:0.5 @accent, stop:1 @accent-dark);
}
QProgressBar::chunk,
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 @accent, stop:1 @accent2);
}
QDockWidget[arcskinActive="true"] {
    color: @accent2-text;
}
QDockWidget[arcskinActive="true"]::title {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 @accent2-light, stop:0.5 @accent2, stop:1 @accent2);
}
"""

MAP_FRAME_QSS = """
QgsMapCanvas {
    border: @map-frame solid @accent;
    border-radius: @radius-small;
}
"""


# The Pro layout's theme has its own shapes; these bring the rice ones to
# it, but only those the skin asks for, so plain Pro stays Pro.
PRO_GAPS_QSS = """
QMainWindow::separator {
    width: @gaps;
    height: @gaps;
    background-color: @bg-window;
}
"""

PRO_RADIUS_QSS = """
QDockWidget::title {
    border-top-left-radius: @radius;
    border-top-right-radius: @radius;
}
QDockWidget > QWidget {
    border-bottom-left-radius: @radius;
    border-bottom-right-radius: @radius;
}
QTabWidget#ArcSkinRibbon::pane,
QPushButton,
QLineEdit,
QComboBox {
    border-radius: @radius-small;
}
"""

PRO_PANEL_BG_QSS = """
QDockWidget#Layers > QWidget {
    background-image: @panel-bg;
    background-position: bottom right;
    background-repeat: no-repeat;
}
QDockWidget QTreeView,
QDockWidget QTreeWidget,
QDockWidget QListView {
    background: transparent;
}
"""

# Accent bars on the Pro layout: its title row, view tabs and map footer
# take the place of the menu bar and status bar.
PRO_ACCENT_BARS_QSS = """
QWidget#ArcSkinTitleRow,
QWidget#ArcSkinMapFooter {
    background-color: @accent;
}
QWidget#ArcSkinTitleRow QLabel,
QWidget#ArcSkinMapFooter QLabel,
QWidget#ArcSkinMapFooter QToolButton {
    color: @accent-text;
}
QTabBar#ArcSkinViewTabs {
    border-bottom: 3px solid @accent2;
}
QToolButton#ArcSkinProjectButton {
    background-color: @accent2;
    color: @accent2-text;
}
"""


def chrome_qss(chrome, pro=False, panel_bg=False):
    """Extra style sheet for the ``chrome`` settings. With ``pro`` (the
    ArcGIS Pro-style layout and theme) gaps and corners apply only when
    the skin sets them."""
    c = settings(chrome)
    qss = ACCENT_BARS_QSS if c["bars"] == "accent" else ""
    if pro:
        own = chrome or {}
        if "gaps" in own:
            qss += PRO_GAPS_QSS
        if "radius" in own:
            qss += PRO_RADIUS_QSS
        if panel_bg:
            qss += PRO_PANEL_BG_QSS
        if c["bars"] == "accent":
            qss += PRO_ACCENT_BARS_QSS
    if c["statusbar"] == "polybar":
        qss += POLYBAR_QSS
    if c["shine"]:
        qss += SHINE_QSS
    if int(c["map_frame"]):
        qss += MAP_FRAME_QSS
    return qss


def _main_docks(win):
    return [d for d in win.findChildren(QDockWidget) if d.parent() is win]


def _main_toolbars(win):
    return [b for b in win.findChildren(QToolBar)
            if b.parent() is win and b.actions()]


def _shortcut(win, changes, key, slot):
    shortcut = QShortcut(QKeySequence(key), win)
    shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
    shortcut.activated.connect(slot)
    changes.add(lambda: sip.isdeleted(shortcut) or shortcut.deleteLater())


def _hide_dock_titles(win, changes):
    for dock in _main_docks(win):
        old = dock.titleBarWidget()
        dock.setTitleBarWidget(QWidget(dock))
        changes.add(lambda d=dock, o=old: sip.isdeleted(d)
                    or d.setTitleBarWidget(o))


def tiling(win):
    """Map plus Layers over Browser on the left; other docked panes closed."""
    docks = {d.objectName(): d for d in _main_docks(win)}
    stack = [docks[n] for n in ("Layers", "Browser") if n in docks]
    for dock in docks.values():
        if dock not in stack and not dock.isFloating():
            dock.hide()
    for dock in stack:
        dock.setFloating(False)
        win.addDockWidget(LEFT, dock)
        dock.show()
    if len(stack) == 2:
        win.splitDockWidget(stack[0], stack[1], Qt.Orientation.Vertical)
    if stack:
        win.resizeDocks(stack[:1], [320], Qt.Orientation.Horizontal)


class Zen:
    """Map only; the shortcut shows the hidden panes and toolbars again
    (and hides them on the next press)."""

    def __init__(self, win, changes):
        self.win = win
        self.hidden = [w for w in _main_docks(win) + _main_toolbars(win)
                       if w.isVisible()]
        self.on = False
        self.toggle()
        _shortcut(win, changes, ZEN_KEY, self.toggle)

    def toggle(self):
        self.on = not self.on
        for widget in self.hidden:
            if not sip.isdeleted(widget):
                widget.setVisible(not self.on)


def _map_background(canvas, changes, color):
    old = canvas.canvasColor()
    canvas.setCanvasColor(QColor(color))
    canvas.refresh()

    def undo():
        if not sip.isdeleted(canvas):
            canvas.setCanvasColor(old)
            canvas.refresh()
    changes.add(undo)


class FocusGlow(QObject):
    """Neon halo around the pane holding the focus: a drop shadow without
    offset, in the accent colour, shown in the gaps between the panes.
    With ``pulse`` it breathes (blur radius going up and down)."""

    def __init__(self, win, changes, radius, color, pulse=False):
        super().__init__(win)
        self.win = win
        self.radius = int(radius)
        self.color = QColor(color)
        self.dock = None
        self.effect = None
        self.animation = None
        if pulse:
            self.animation = QVariantAnimation(
                self, startValue=self.radius * 0.35, endValue=self.radius,
                duration=1600, loopCount=-1,
                easingCurve=QEasingCurve(QEasingCurve.Type.InOutSine))
            self.animation.valueChanged.connect(self._breathe)
        QApplication.instance().focusChanged.connect(self.focus_changed)
        self.attach(win.findChild(QDockWidget, "Layers"))
        changes.add(self.stop)

    def focus_changed(self, _old, new):
        while new is not None and not isinstance(new, QDockWidget):
            new = new.parentWidget()
        if new is not None and new.parent() is self.win:
            self.attach(new)

    def attach(self, dock):
        if dock is self.dock:
            return
        self.detach()
        if dock is None or sip.isdeleted(dock):
            return
        effect = QGraphicsDropShadowEffect(dock)
        effect.setOffset(0, 0)
        effect.setBlurRadius(self.radius)
        effect.setColor(self.color)
        dock.setGraphicsEffect(effect)  # the dock owns it from now on
        self.dock, self.effect = dock, effect
        if self.animation:
            self.animation.start()

    def detach(self):
        if self.animation:
            self.animation.stop()
        if self.dock is not None and not sip.isdeleted(self.dock):
            self.dock.setGraphicsEffect(None)  # deletes the effect
        self.dock = self.effect = None

    def _breathe(self, value):
        if self.effect is not None and not sip.isdeleted(self.effect):
            self.effect.setBlurRadius(value)

    def stop(self):
        QApplication.instance().focusChanged.disconnect(self.focus_changed)
        self.detach()
        self.deleteLater()


def apply_chrome(iface, changes, chrome, layout, variables=None):
    """Window-level parts of the chrome and the layout preset.

    Style sheet parts (gaps, corners, fonts, polybar) come from
    :func:`chrome_variables` and :func:`chrome_qss`.
    """
    c = settings(chrome)
    win = iface.mainWindow()
    if layout != "pro":  # the Pro layout marks the active pane itself
        ActivePane(win, changes)
    if layout == "tiling":
        tiling(win)
    if c["dock_titles"] == "hidden" or layout == "tiling":
        _hide_dock_titles(win, changes)
    if c["toolbars"] in ("left", "hidden") and layout != "pro":
        for bar in _main_toolbars(win):
            if c["toolbars"] == "left":
                win.addToolBar(Qt.ToolBarArea.LeftToolBarArea, bar)
            else:
                bar.hide()
    menubar = win.menuBar()
    if (c["menubar"] == "hidden" or layout == "zen") and layout != "pro":
        changes.set(menubar, "visible", False)
        _shortcut(win, changes, MENUBAR_KEY,
                  lambda: menubar.setVisible(not menubar.isVisible()))
    if float(c["opacity"]) < 1:
        changes.set(win, "windowOpacity", max(float(c["opacity"]), 0.3))
    if c["map_background"] == "theme" and variables:
        _map_background(iface.mapCanvas(), changes,
                        variables.get("bg-window", "#ffffff"))
    if int(c["glow"]) and layout != "zen":
        FocusGlow(win, changes, c["glow"],
                  (variables or {}).get("accent", "#ff79c6"),
                  bool(c["glow_pulse"]))
    if layout == "zen":
        Zen(win, changes)

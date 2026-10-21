"""QRice plugin: skins for QGIS, fully reverted on disable.

A skin (see skins.py) gives the colours (a theme plus its variables, or a
palette taken from a picture), a mascot over the map, a faded picture
behind the panes, the window chrome (gaps, corners, bars, see chrome.py)
and a layout: ``pro`` brings the ArcGIS Pro-style ribbon, panes, icons and
symbology this plugin started from (ArcSkin by EnviroSolutions).

Every change goes into a :class:`~.util.Changes` undo log; switching the
skin off, or to another skin, undoes it and restores the window state.
"""

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QByteArray, QCoreApplication
from qgis.PyQt.QtGui import QAction, QActionGroup, QIcon, QPalette
from qgis.PyQt.QtWidgets import QApplication, QMenu, QToolBar

from . import skins
from .chrome import apply_chrome, chrome_qss, chrome_variables
from .dialogs import WindowDresser
from .icon_theme import apply_icon_theme
from .mapview import frame_map
from .mascot import apply_mascot
from .palette import colors_of, hex_color, mix, palette, parse_hex
from .panel_bg import render_panel_bg
from .panes import arrange_panes
from .progress import Progress
from .ribbon import build_ribbon
from .symbology import ProSymbology
from .theme import (
    PLUGIN_DIR, build_palette, load_qss, recolor_icons, theme_variables,
)
from .util import Changes, tr

MENU_NAME = "&QRice"
THEME = "pro_light"  # theme of the Pro layout
# Window layout before the skin, kept in settings so that disabling the
# skin after a QGIS restart still brings the original toolbars back.
STATE_KEY = "qrice/original_window_state"
SKIN_KEY = "qrice/active_skin"


def skin_variables(skin):
    """All theme variables of ``skin``: theme defaults < palette (from its
    picture and/or its ``colors``) < its own variables < its chrome."""
    variables = theme_variables(skin.theme)
    forced = {key: parse_hex(value)
              for key, value in (skin.data.get("colors") or {}).items()
              if key in ("base", "accent", "accent2")}
    own = skin.variables or {}
    if skin.palette == "auto" or forced:
        source = skin.palette_source() if skin.palette == "auto" else None
        colors = colors_of(source) if source else []
        generated = palette(colors, skin.dark, **forced)
        # Colours only the Pro theme names, from the generated ones.
        generated.update({"selected-soft": generated["hover"],
                          "selected-soft2": generated["hover"],
                          "bg-alt": generated["bg-header"],
                          "table-selection": generated["selected"]})
        variables.update(generated)
    variables.update(own)
    _shine_variables(variables, own, skin.chrome.get("bars", "plain"))
    variables.update(chrome_variables(skin.chrome))
    return variables


def _shine_variables(variables, own, bars="plain"):
    """Lighter and darker tones for the glossy gradients, from the final
    colours (unless the skin sets them itself). The shine on the bars
    follows their colour: the accent with ``bars: accent``, else the
    header colour."""
    def tone(name, toward, t):
        value = variables.get(name, "")
        if not (value.startswith("#") and len(value) == 7):
            return value
        return hex_color(mix(toward, parse_hex(value), t))

    white, black = (255, 255, 255), (0, 0, 0)
    base = "accent" if bars == "accent" else "bg-header"
    derived = {"accent-light": tone("accent", white, 0.35),
               "accent2-light": tone("accent2", white, 0.35),
               "shine-top": tone(base, white, 0.3),
               "shine-mid": variables.get(base, "#808080"),
               "shine-bottom": tone(base, black, 0.15)}
    for name, value in derived.items():
        if name not in own:
            variables[name] = value


def skin_qss(skin):
    """The complete style sheet of ``skin`` (pictures rendered to its
    cache folder)."""
    variables = skin_variables(skin)
    cache = skins.cache_dir(skin.id)
    icons = recolor_icons(variables, cache / "icons")
    panel = skin.section("panel_bg")
    if panel:
        variables["panel-bg"] = render_panel_bg(
            panel["file"], variables.get("bg-panel", "#ffffff"),
            panel.get("opacity", 0.12), panel.get("height", 200),
            cache / "panel.png")
    extra = chrome_qss(skin.chrome, pro=skin.theme == THEME,
                       panel_bg=bool(panel))
    return load_qss(skin.theme, variables, icons, extra)


def apply_palette(changes, variables):
    """The application palette in the skin's colours, for what paints with
    it instead of the style sheet (layer names in Layers)."""
    old = QPalette(QApplication.palette())
    QApplication.setPalette(build_palette(variables, old))
    changes.add(lambda: QApplication.setPalette(old))


def moves_panes(skin):
    """Whether ``skin`` rearranges docks or toolbars (Pro, tiling or zen
    layout, toolbars on the left or hidden). Only then is the window state
    saved before it and restored after it; other skins leave the panes
    wherever the user put them."""
    toolbars = (skin.chrome or {}).get("toolbars", "top")
    return skin.layout != "none" or toolbars != "top"


def active_skin():
    found = skins.load_skin(QgsSettings().value(SKIN_KEY, skins.DEFAULT_SKIN))
    if found is None:
        found = skins.load_skin(skins.DEFAULT_SKIN)
    if found is None:  # no skin folders at all: plain rice theme
        found = skins.Skin("rice", skins.BUILTIN, "builtin",
                           {"name": "Rice"})
    return found


class QRicePlugin:
    """QGIS plugin entry point: a checkable action toggles the skin."""

    def __init__(self, iface, translator=None):
        self.iface = iface
        self.translator = translator
        self.changes = None  # undo log while the skin is on
        self.skin = None  # skin currently applied
        self.manager = None

    def initGui(self):  # noqa: N802 (QGIS API name)
        icon = QIcon(str(PLUGIN_DIR / "resources" / "icons" / "icon.svg"))
        win = self.iface.mainWindow()
        self.action = QAction(icon, tr("QRice skin"), win, checkable=True)
        self.action.toggled.connect(self.set_enabled)
        self.iface.addPluginToMenu(MENU_NAME, self.action)
        self.manager_action = QAction(icon, tr("Skin Manager…"), win)
        self.manager_action.triggered.connect(self.show_manager)
        self.iface.addPluginToMenu(MENU_NAME, self.manager_action)
        self.skins_menu = QMenu(tr("Skins"), win)
        self.skins_menu.aboutToShow.connect(self._fill_skins_menu)
        self.iface.addPluginToMenu(MENU_NAME, self.skins_menu.menuAction())
        self.iface.addToolBarIcon(self.action)
        # The skin is on whenever the plugin is loaded. At QGIS start-up
        # wait until all plugins are loaded so their toolbars reach the
        # ribbon's Add-ins tab.
        if win.isVisible():
            self.action.setChecked(True)
        else:
            self.iface.initializationCompleted.connect(
                lambda: self.action.setChecked(True)
            )

    def unload(self):
        # QGIS also unloads plugins when it quits; it freezes the map canvas
        # first. Then the skin is left recorded as on (icon theme, original
        # window state) for the next start instead of being reverted.
        try:
            if not self.iface.mapCanvas().isFrozen():
                self.set_enabled(False)
        finally:
            if self.manager is not None:
                self.manager.close()
                self.manager.deleteLater()
            self.iface.removeToolBarIcon(self.action)
            for action in (self.action, self.manager_action,
                           self.skins_menu.menuAction()):
                self.iface.removePluginMenu(MENU_NAME, action)
            if self.translator:
                QCoreApplication.removeTranslator(self.translator)

    # --- skins ---------------------------------------------------------

    def _fill_skins_menu(self):
        self.skins_menu.clear()
        group = QActionGroup(self.skins_menu)
        current = QgsSettings().value(SKIN_KEY, skins.DEFAULT_SKIN)
        category = None
        for skin in skins.list_skins():
            if skin.category != category:
                category = skin.category
                self.skins_menu.addSection(category.title())
            action = self.skins_menu.addAction(skin.name)
            action.setCheckable(True)
            action.setChecked(skin.id == current)
            action.setActionGroup(group)
            action.triggered.connect(
                lambda _=False, s=skin.id: self.switch_skin(s))

    def switch_skin(self, skin_id):
        """Make ``skin_id`` the active skin (and show it if the skin is on)."""
        QgsSettings().setValue(SKIN_KEY, skin_id)
        if self.action.isChecked():
            self.set_enabled(False)
            self.set_enabled(True)
        else:
            self.action.setChecked(True)

    def reapply(self):
        """Apply the active skin again (after it was edited)."""
        if self.action.isChecked():
            self.set_enabled(False)
            self.set_enabled(True)

    def show_manager(self):
        from .manager import SkinManager

        if self.manager is None:
            self.manager = SkinManager(self, self.iface.mainWindow())
        self.manager.refresh()
        self.manager.show()
        self.manager.raise_()
        self.manager.activateWindow()

    # --- on / off ------------------------------------------------------

    def _steps(self, skin, changes):
        """(relative duration, step) pairs; the bar moves with the time."""
        iface = self.iface
        steps = [(3, lambda: changes.set(QApplication.instance(),
                                         "styleSheet", skin_qss(skin))),
                 (1, lambda: apply_palette(changes, skin_variables(skin)))]
        if skin.layout == "pro" or skin.icons == "pro":
            steps.append((5, lambda: apply_icon_theme(iface, changes)))
        if skin.layout == "pro":
            steps += [
                (1, lambda: WindowDresser(iface, changes)),
                (1, lambda: build_ribbon(iface, changes, self.action)),
                (1, lambda: arrange_panes(iface, changes)),
                (1, lambda: frame_map(iface, changes)),
                (3, lambda: ProSymbology(changes, iface.mapCanvas())),
            ]
        steps += [
            (1, lambda: apply_chrome(iface, changes, skin.chrome,
                                     skin.layout, skin_variables(skin))),
            (1, lambda: apply_mascot(iface, changes,
                                     skin.section("mascot"))),
        ]
        return steps

    def set_enabled(self, enabled: bool) -> None:
        """Apply the active skin or restore the previous QGIS interface."""
        win = self.iface.mainWindow()
        settings = QgsSettings()
        if enabled and self.changes is None:
            skin = self.skin = active_skin()
            if moves_panes(skin):
                if settings.value(STATE_KEY) is None:
                    settings.setValue(STATE_KEY, win.saveState())
            else:
                # Panes stay where the user put them; a state left over
                # from an earlier skin would bring an old layout back.
                settings.remove(STATE_KEY)
            changes = self.changes = Changes()
            steps = self._steps(skin, changes)
            total = sum(weight for weight, _ in steps)
            progress = Progress(
                win, tr("Applying the {} skin…").format(skin.name))
            try:
                done = 0
                for weight, step in steps:
                    step()
                    done += weight
                    progress.set(done / total)
            except Exception:
                # Half a skin is worse than none: back to plain QGIS, and
                # the switch shows off. QGIS reports the error.
                changes.undo()
                self.changes = self.skin = None
                if moves_panes(skin):
                    self._restore_window()
                self.action.blockSignals(True)
                self.action.setChecked(False)
                self.action.blockSignals(False)
                raise
            finally:
                progress.done()
        elif not enabled and self.changes is not None:
            progress = Progress(win, tr("Restoring the QGIS look…"))
            try:
                self.changes.undo(progress.set)
            finally:
                # Also after a failed step (undo reverts all the others):
                # the window state and the switch must match plain QGIS.
                progress.done()
                moved = moves_panes(self.skin)
                self.changes = self.skin = None
                if moved:
                    self._restore_window()

    def _restore_window(self):
        """Toolbars and panes as they were before the skin went on."""
        win = self.iface.mainWindow()
        settings = QgsSettings()
        state = settings.value(STATE_KEY)
        if isinstance(state, QByteArray):
            win.restoreState(state)
        settings.remove(STATE_KEY)
        bars = [b for b in win.findChildren(QToolBar)
                if b.parent() is win and b.actions()]
        if not any(b.isVisible() for b in bars):
            # The saved state was taken from a skinned window (e.g. after
            # a crash): fall back to showing QGIS's toolbars.
            for bar in bars:
                bar.show()

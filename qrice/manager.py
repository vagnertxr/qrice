"""Skin Manager: browse, apply, create and edit skins.

Built-in skins are read-only (duplicate one to change it). Edits to a user
skin are written to its ``skin.json`` and, when it is the active skin,
shown live (the skin is applied again shortly after the last change).
"""

from qgis.PyQt.QtCore import QSize, Qt, QTimer, QUrl
from qgis.PyQt.QtGui import (
    QColor, QDesktopServices, QFont, QIcon, QPainter, QPixmap,
)
from qgis.PyQt.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QDoubleSpinBox,
    QFileDialog, QFontComboBox, QFormLayout, QGridLayout, QHBoxLayout,
    QInputDialog, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QSlider, QSpinBox, QTabWidget, QToolButton, QVBoxLayout,
    QWidget,
)

from . import skins
from .chrome import DEFAULTS as CHROME_DEFAULTS
from .flags import countries, flag_skin_data
from .mascot import CORNERS
from .util import tr

THUMB = QSize(176, 112)
# Variables offered as colour swatches in the editor.
SWATCHES = [("accent", tr("Accent")), ("accent2", tr("Second accent")),
            ("bg-window", tr("Window")), ("bg-panel", tr("Panes")),
            ("bg-header", tr("Headers")), ("text", tr("Text")),
            ("selected", tr("Selection")), ("border", tr("Borders"))]
CHOICES = {"dock_titles": ("full", "minimal", "hidden"),
           "menubar": ("shown", "hidden"),
           "toolbars": ("top", "left", "hidden"),
           "statusbar": ("plain", "polybar"),
           "map_background": ("keep", "theme"),
           "bars": ("plain", "accent")}
PICTURE_FILTER = tr("Pictures (*.png *.jpg *.jpeg *.gif *.svg *.webp)")


def thumbnail(skin):
    """Small preview: the skin's colours with its picture on the right."""
    from .plugin import skin_variables

    try:
        v = skin_variables(skin)
    except Exception:  # noqa: BLE001 (a broken skin still gets a tile)
        v = {}
    pixmap = QPixmap(THUMB)
    pixmap.fill(QColor(v.get("bg-window", "#202020")))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    w, h = THUMB.width(), THUMB.height()
    painter.setBrush(QColor(v.get("bg-panel", "#303030")))
    painter.drawRoundedRect(6, 18, w // 2 - 6, h - 24, 6, 6)
    painter.setBrush(QColor(v.get("bg-header", "#404040")))
    painter.drawRoundedRect(6, 6, w - 12, 9, 4, 4)
    painter.setBrush(QColor(v.get("accent", "#ff79c6")))
    painter.drawRoundedRect(12, 26, w // 2 - 18, 8, 4, 4)
    painter.setBrush(QColor(v.get("accent2", "#8be9fd")))
    painter.drawRoundedRect(12, 40, w // 3 - 12, 8, 4, 4)
    painter.setBrush(QColor(v.get("text", "#dddddd")))
    for i in range(3):
        painter.drawRoundedRect(12, 56 + 10 * i, w // 2 - 30 + 8 * i, 4, 2, 2)
    picture = skin.thumbnail()
    if picture:
        image = QPixmap(str(picture))
        if not image.isNull():
            image = image.scaled(QSize(w // 2 - 6, h - 24),
                                 Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(w - image.width() - 6, h - image.height() - 6,
                               image)
    painter.end()
    return pixmap


class SkinManager(QDialog):

    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.skin = None
        self.picture_name = None
        self.loading = False
        self.setWindowTitle(tr("QRice Skin Manager"))
        self.resize(980, 640)
        self.timer = QTimer(self, singleShot=True, interval=500)
        self.timer.timeout.connect(self._apply_edit)

        layout = QHBoxLayout(self)
        left = QVBoxLayout()
        self.category = QComboBox()
        self.category.addItem(tr("All skins"), None)
        for name in skins.CATEGORIES:
            self.category.addItem(name.title(), name)
        self.category.currentIndexChanged.connect(self.refresh)
        left.addWidget(self.category)
        self.list = QListWidget(viewMode=QListWidget.ViewMode.IconMode,
                                iconSize=THUMB, movement=QListWidget.Movement.Static,
                                resizeMode=QListWidget.ResizeMode.Adjust,
                                spacing=6, wordWrap=True)
        self.list.setMinimumWidth(420)
        self.list.currentItemChanged.connect(self._select)
        self.list.itemDoubleClicked.connect(lambda _: self.apply())
        left.addWidget(self.list)
        row = QHBoxLayout()
        for text, slot in ((tr("New from picture…"), self.new_from_picture),
                           (tr("New flag skin…"), self.new_flag),
                           (tr("Import…"), self.import_zip)):
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        left.addLayout(row)
        layout.addLayout(left, 3)

        right = QVBoxLayout()
        self.title = QLabel(objectName="QRiceSkinTitle")
        font = self.title.font()
        font.setPointSizeF(font.pointSizeF() * 1.5)
        font.setBold(True)
        self.title.setFont(font)
        right.addWidget(self.title)
        self.credit = QLabel(wordWrap=True, openExternalLinks=True)
        right.addWidget(self.credit)
        row = QHBoxLayout()
        self.apply_button = QPushButton(tr("Apply"), default=True)
        self.apply_button.clicked.connect(self.apply)
        row.addWidget(self.apply_button)
        self.buttons = {}
        for key, text, slot in (
                ("duplicate", tr("Duplicate…"), self.duplicate),
                ("rename", tr("Rename…"), self.rename),
                ("export", tr("Export…"), self.export_zip),
                ("folder", tr("Open folder"), self.open_folder),
                ("delete", tr("Delete"), self.delete)):
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
            self.buttons[key] = button
        right.addLayout(row)
        self.readonly = QLabel(tr("Built-in skin: duplicate it to edit."),
                               wordWrap=True)
        right.addWidget(self.readonly)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._colors_tab(), tr("Colours"))
        self.tabs.addTab(self._picture_tab(), tr("Picture"))
        self.tabs.addTab(self._window_tab(), tr("Window"))
        right.addWidget(self.tabs, 1)
        layout.addLayout(right, 2)

    # --- editor tabs ---------------------------------------------------

    def _colors_tab(self):
        page = QWidget()
        box = QVBoxLayout(page)
        form = QFormLayout()
        self.auto_palette = QCheckBox(tr("Colours from the picture"))
        self.auto_palette.toggled.connect(self._edited)
        form.addRow(self.auto_palette)
        self.darkness = QComboBox()
        for text, value in ((tr("As the picture"), None), (tr("Dark"), True),
                            (tr("Light"), False)):
            self.darkness.addItem(text, value)
        self.darkness.currentIndexChanged.connect(self._edited)
        form.addRow(tr("Theme"), self.darkness)
        box.addLayout(form)
        grid = QGridLayout()
        self.swatches = {}
        for i, (name, label) in enumerate(SWATCHES):
            button = QToolButton(toolTip=name)
            button.setFixedSize(46, 24)
            button.clicked.connect(lambda _=False, n=name: self._pick(n))
            reset = QToolButton(text="×", toolTip=tr("Back to the generated "
                                                     "colour"))
            reset.clicked.connect(lambda _=False, n=name: self._unpick(n))
            grid.addWidget(QLabel(label), i // 2, (i % 2) * 3)
            grid.addWidget(button, i // 2, (i % 2) * 3 + 1)
            grid.addWidget(reset, i // 2, (i % 2) * 3 + 2)
            self.swatches[name] = button
        box.addLayout(grid)
        box.addStretch()
        return page

    def _slider(self, low, high):
        slider = QSlider(Qt.Orientation.Horizontal, minimum=low, maximum=high)
        slider.valueChanged.connect(self._edited)
        return slider

    def _picture_tab(self):
        page = QWidget()
        form = QFormLayout(page)
        row = QHBoxLayout()
        self.picture_label = QLabel()
        row.addWidget(self.picture_label, 1)
        choose = QPushButton(tr("Choose…"))
        choose.clicked.connect(self._choose_picture)
        row.addWidget(choose)
        clear = QPushButton(tr("None"))
        clear.clicked.connect(self._clear_picture)
        row.addWidget(clear)
        form.addRow(tr("Picture"), row)
        self.panel_bg = QCheckBox(tr("Faded picture behind the panes"))
        self.panel_bg.toggled.connect(self._edited)
        form.addRow(self.panel_bg)
        self.panel_opacity = self._slider(2, 60)
        form.addRow(tr("Pane picture opacity"), self.panel_opacity)
        self.mascot = QCheckBox(tr("Also over the map (mascot; covers "
                                   "part of the data)"))
        self.mascot.toggled.connect(self._edited)
        form.addRow(self.mascot)
        self.corner = QComboBox()
        self.corner.addItems(CORNERS)
        self.corner.currentIndexChanged.connect(self._edited)
        form.addRow(tr("Corner"), self.corner)
        self.mascot_height = self._slider(5, 100)
        form.addRow(tr("Size (% of map)"), self.mascot_height)
        self.opacity = self._slider(5, 100)
        form.addRow(tr("Opacity"), self.opacity)
        self.rounded = QSpinBox(maximum=60, suffix=" px")
        self.rounded.valueChanged.connect(self._edited)
        form.addRow(tr("Rounded corners"), self.rounded)
        self.mirror = QCheckBox(tr("Mirror"))
        self.mirror.toggled.connect(self._edited)
        form.addRow(self.mirror)
        self.mascot_widgets = (self.corner, self.mascot_height, self.opacity,
                               self.rounded, self.mirror)
        for widget in self.mascot_widgets:
            self.mascot.toggled.connect(widget.setEnabled)
        return page

    def _window_tab(self):
        page = QWidget()
        form = QFormLayout(page)
        self.layout_combo = QComboBox()
        for value, text in (("none", tr("Keep my layout")),
                            ("tiling", tr("Tiling")),
                            ("zen", tr("Zen (map only, Ctrl+Alt+Z)")),
                            ("pro", tr("ArcGIS Pro-style (ArcSkin)"))):
            self.layout_combo.addItem(text, value)
        self.layout_combo.currentIndexChanged.connect(self._edited)
        form.addRow(tr("Layout"), self.layout_combo)
        self.spins = {}
        for key, label, high in (("gaps", tr("Gaps"), 40),
                                 ("radius", tr("Corner radius"), 30),
                                 ("focus_border", tr("Focus frame"), 8),
                                 ("glow", tr("Glow around the focused pane"),
                                  60),
                                 ("map_frame", tr("Frame around the map"),
                                  8)):
            spin = QSpinBox(maximum=high, suffix=" px")
            spin.valueChanged.connect(self._edited)
            form.addRow(label, spin)
            self.spins[key] = spin
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(self._edited)
        self.font_default = QCheckBox(tr("Interface font"))
        self.font_default.toggled.connect(self.font_combo.setDisabled)
        self.font_default.toggled.connect(self._edited)
        row = QHBoxLayout()
        row.addWidget(self.font_default)
        row.addWidget(self.font_combo, 1)
        form.addRow(tr("Font"), row)
        self.font_size = QDoubleSpinBox(minimum=0, maximum=24, decimals=1,
                                        suffix=" pt",
                                        specialValueText=tr("default"))
        self.font_size.valueChanged.connect(self._edited)
        form.addRow(tr("Font size"), self.font_size)
        self.choices = {}
        labels = {"dock_titles": tr("Pane titles"),
                  "menubar": tr("Menu bar (Ctrl+Alt+M)"),
                  "toolbars": tr("Toolbars"), "statusbar": tr("Status bar"),
                  "map_background": tr("Map background"),
                  "bars": tr("Bar colours")}
        for key, values in CHOICES.items():
            combo = QComboBox()
            combo.addItems(values)
            combo.currentIndexChanged.connect(self._edited)
            form.addRow(labels[key], combo)
            self.choices[key] = combo
        self.window_opacity = self._slider(30, 100)
        form.addRow(tr("Window opacity"), self.window_opacity)
        self.checks = {}
        for key, label in (("glow_pulse", tr("Pulsing glow")),
                           ("shine", tr("Glossy bars and buttons"))):
            check = QCheckBox(label)
            check.toggled.connect(self._edited)
            form.addRow(check)
            self.checks[key] = check
        return page

    # --- list ----------------------------------------------------------

    def refresh(self):
        current = self.skin.id if self.skin else self.plugin_skin_id()
        category = self.category.currentData()
        self.list.blockSignals(True)
        self.list.clear()
        select = None
        for skin in skins.list_skins():
            if category and skin.category != category:
                continue
            name = skin.name + ("  ·  dev" if skin.kind == "dev" else "")
            item = QListWidgetItem(QIcon(thumbnail(skin)), name)
            item.setData(Qt.ItemDataRole.UserRole, skin.id)
            item.setToolTip(f"{skin.name} — {skin.category}")
            self.list.addItem(item)
            if skin.id == current:
                select = item
        self.list.blockSignals(False)
        self.list.setCurrentItem(select or self.list.item(0))

    def plugin_skin_id(self):
        from .plugin import SKIN_KEY
        from qgis.core import QgsSettings

        return QgsSettings().value(SKIN_KEY, skins.DEFAULT_SKIN)

    def _select(self, item, _previous=None):
        if item is None:
            return
        self.skin = skins.load_skin(item.data(Qt.ItemDataRole.UserRole))
        self._load_editor()

    def _update_tile(self):
        item = self.list.currentItem()
        if item is not None and self.skin is not None:
            item.setIcon(QIcon(thumbnail(self.skin)))

    # --- editor <-> skin.json -----------------------------------------

    def _load_editor(self):
        skin = self.skin
        self.loading = True
        try:
            self.title.setText(skin.name)
            parts = []
            if skin.author:
                parts.append(tr("by {}").format(skin.author))
            if skin.license:
                parts.append(skin.license)
            if skin.credit_url:
                parts.append(f'<a href="{skin.credit_url}">{tr("source")}</a>')
            self.credit.setText(" · ".join(parts))
            editable = skin.editable
            self.readonly.setVisible(not editable)
            self.tabs.setEnabled(editable)
            self.buttons["delete"].setEnabled(editable)
            self.buttons["rename"].setEnabled(editable)
            data = skin.data
            self.auto_palette.setChecked(data.get("palette") == "auto")
            self.darkness.setCurrentIndex(
                {None: 0, True: 1, False: 2}[data.get("dark")])
            self._paint_swatches()
            mascot = data.get("mascot") or {}
            panel = data.get("panel_bg") or {}
            self.picture_name = panel.get("file") or mascot.get("file")
            self.picture_label.setText(self.picture_name or (
                tr("flag") if data.get("flag") else tr("none")))
            self.mascot.setChecked(bool(mascot))
            for widget in self.mascot_widgets:
                widget.setEnabled(bool(mascot))
            self.corner.setCurrentText(mascot.get("corner", CORNERS[0]))
            self.mascot_height.setValue(round(mascot.get("height", 0.3) * 100))
            self.opacity.setValue(round(mascot.get("opacity", 0.95) * 100))
            self.rounded.setValue(int(mascot.get("rounded", 0)))
            self.mirror.setChecked(bool(mascot.get("mirror")))
            self.panel_bg.setChecked(bool(panel))
            self.panel_opacity.setValue(round(panel.get("opacity", 0.1) * 100))
            self.layout_combo.setCurrentIndex(
                max(self.layout_combo.findData(skin.layout), 0))
            chrome = dict(CHROME_DEFAULTS)
            chrome.update(skin.chrome)
            for key, spin in self.spins.items():
                spin.setValue(int(chrome[key]))
            for key, check in self.checks.items():
                check.setChecked(bool(chrome[key]))
            self.font_default.setChecked(not chrome["font"])
            if chrome["font"]:
                self.font_combo.setCurrentFont(
                    QFont(chrome["font"]))
            self.font_size.setValue(float(chrome["font_size"] or 0))
            for key, combo in self.choices.items():
                combo.setCurrentText(chrome[key])
            self.window_opacity.setValue(round(float(chrome["opacity"]) * 100))
        finally:
            self.loading = False

    def _paint_swatches(self):
        from .plugin import skin_variables

        variables = skin_variables(self.skin)
        own = self.skin.data.get("variables") or {}
        for name, button in self.swatches.items():
            color = variables.get(name, "#000000")
            weight = "bold" if name in own else "normal"
            button.setStyleSheet(
                f"background: {color}; border: 1px solid #888;"
                f" border-radius: 4px; font-weight: {weight};")
            button.setText("●" if name in own else "")

    def _save_editor(self):
        data = self.skin.data
        if self.auto_palette.isChecked():
            if data.get("palette") != "auto":
                # Just switched on: the picture decides, so fixed colours
                # (e.g. a club's) give way to it.
                data.pop("colors", None)
            data["palette"] = "auto"
        else:
            data.pop("palette", None)
        dark = self.darkness.currentData()
        if dark is None:
            data.pop("dark", None)
        else:
            data["dark"] = dark
        picture = self.picture_name
        has_picture = bool(picture or data.get("flag"))
        if self.mascot.isChecked() and has_picture:
            mascot = data.setdefault("mascot", {})
            mascot.update(corner=self.corner.currentText(),
                          height=self.mascot_height.value() / 100,
                          opacity=self.opacity.value() / 100,
                          rounded=self.rounded.value(),
                          mirror=self.mirror.isChecked())
            if picture:
                mascot["file"] = picture
        else:
            data.pop("mascot", None)
        if self.panel_bg.isChecked() and has_picture:
            panel = data.setdefault("panel_bg", {})
            if picture:
                panel["file"] = picture
            panel["opacity"] = self.panel_opacity.value() / 100
        else:
            data.pop("panel_bg", None)
        data["layout"] = self.layout_combo.currentData()
        chrome = {key: spin.value() for key, spin in self.spins.items()}
        chrome["font"] = (None if self.font_default.isChecked()
                          else self.font_combo.currentFont().family())
        chrome["font_size"] = self.font_size.value() or None
        chrome.update({k: c.currentText() for k, c in self.choices.items()})
        chrome["opacity"] = self.window_opacity.value() / 100
        chrome.update({k: c.isChecked() for k, c in self.checks.items()})
        data["chrome"] = {k: v for k, v in chrome.items()
                          if v != CHROME_DEFAULTS.get(k)}
        skins.write_skin(self.skin)

    def _edited(self, *_):
        if self.loading or self.skin is None or not self.skin.editable:
            return
        self._save_editor()
        self._paint_swatches()
        self._update_tile()
        if self.skin.id == self.plugin_skin_id():
            self.timer.start()

    def _apply_edit(self):
        self.plugin.reapply()

    def _pick(self, name):
        from .plugin import skin_variables

        current = QColor(skin_variables(self.skin).get(name, "#000000"))
        color = QColorDialog.getColor(current, self, name)
        if color.isValid():
            self.skin.data.setdefault("variables", {})[name] = color.name()
            self._edited()

    def _unpick(self, name):
        (self.skin.data.get("variables") or {}).pop(name, None)
        self._edited()

    def _choose_picture(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("Skin picture"),
                                              "", PICTURE_FILTER)
        if not path:
            return
        import shutil
        from pathlib import Path

        shutil.copy2(path, self.skin.path / Path(path).name)
        self.picture_name = Path(path).name
        self.loading = True
        self.panel_bg.setChecked(True)
        self.loading = False
        self._edited()
        self._load_editor()

    def _clear_picture(self):
        self.picture_name = None
        self.skin.data.pop("mascot", None)
        self.skin.data.pop("panel_bg", None)
        self._load_editor()
        self._edited()

    # --- actions -------------------------------------------------------

    def apply(self):
        if self.skin is not None:
            self.plugin.switch_skin(self.skin.id)

    def _show_new(self, skin):
        self.category.setCurrentIndex(0)
        self.skin = skin
        self.refresh()

    def new_from_picture(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Picture for the new skin"), "", PICTURE_FILTER)
        if path:
            self._show_new(skins.skin_from_picture(path))
            self.apply()

    def new_flag(self):
        names = countries()
        labels = [f"{name} ({code.upper()})" for code, name in names.items()]
        label, ok = QInputDialog.getItem(self, tr("Flag skin"),
                                         tr("Country"), labels, 0, False)
        if ok:
            code = list(names)[labels.index(label)]
            data = flag_skin_data(code)
            self._show_new(skins.new_skin(data.pop("name"), data))
            self.apply()

    def _ask_name(self, title, current):
        """A non-empty skin name from the user, or None (cancelled)."""
        name, ok = QInputDialog.getText(self, title, tr("Name"),
                                        text=current)
        name = name.strip()
        return name if ok and name else None

    def duplicate(self):
        if self.skin is None:
            return
        name = self._ask_name(tr("Duplicate skin"),
                              tr("{} copy").format(self.skin.name))
        if name:
            self._show_new(skins.duplicate_skin(self.skin, name))

    def rename(self):
        """New display name for a user skin; its folder (and so whether
        it is the active skin) stays the same."""
        if self.skin is None or not self.skin.editable:
            return
        name = self._ask_name(tr("Rename skin"), self.skin.name)
        if name and name != self.skin.name:
            self.skin.data["name"] = name
            skins.write_skin(self.skin)
            self.refresh()

    def delete(self):
        if self.skin is None or not self.skin.editable:
            return
        answer = QMessageBox.question(
            self, tr("Delete skin"),
            tr("Delete the skin “{}” and its pictures?").format(
                self.skin.name))
        if answer == QMessageBox.StandardButton.Yes:
            skins.delete_skin(self.skin)
            self.skin = None
            self.refresh()

    def export_zip(self):
        if self.skin is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Export skin"), f"{self.skin.id}.zip",
            tr("QRice skin (*.zip)"))
        if path:
            skins.export_skin(self.skin, path)

    def import_zip(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Import skin"), "", tr("QRice skin (*.zip)"))
        if path:
            try:
                self._show_new(skins.import_skin(path))
            except (ValueError, OSError) as error:
                QMessageBox.warning(self, tr("Import skin"), str(error))

    def open_folder(self):
        if self.skin is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.skin.path)))

"""Mascot: a picture in a corner of the map, over the map but not part of it.

The picture is a child widget of the map canvas, not a map item: it never
reaches map exports or print layouts, lets clicks through to the map, and
follows the canvas size. Animated GIFs play.
"""

from qgis.PyQt import sip
from qgis.PyQt.QtCore import QEvent, QRectF, QSize, Qt
from qgis.PyQt.QtGui import (
    QMovie, QPainter, QPainterPath, QPixmap, QTransform,
)
from qgis.PyQt.QtWidgets import QGraphicsOpacityEffect, QLabel

from .panel_bg import load_picture

CORNERS = ("bottom-right", "bottom-left", "top-right", "top-left")


class MascotOverlay(QLabel):
    """Picture anchored to a corner of ``canvas``; ``height`` is a fraction
    of the canvas height."""

    def __init__(self, canvas, path, corner="bottom-right", height=0.3,
                 opacity=0.95, margin=16, mirror=False, rounded=0):
        super().__init__(canvas, objectName="QRiceMascot")
        self.canvas = canvas
        self.corner = corner if corner in CORNERS else CORNERS[0]
        self.fraction = min(max(float(height), 0.05), 1.0)
        self.margin = int(margin)
        self.rounded = int(rounded)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent; border: none;")
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(min(max(float(opacity), 0.05), 1.0))
        self.setGraphicsEffect(effect)
        self.movie = None
        path = str(path)
        if path.lower().endswith(".gif"):
            movie = QMovie(path)
            if movie.isValid() and movie.frameCount() != 1:
                self.movie = movie
                movie.jumpToFrame(0)
                self.source_size = movie.currentPixmap().size()
                self.setMovie(movie)
        if self.movie is None:
            # Large enough for any map height; SVGs drawn sharp at it.
            pixmap = QPixmap.fromImage(load_picture(path, 1200))
            if mirror:
                pixmap = pixmap.transformed(QTransform().scale(-1, 1))
            self.pixmap_full = pixmap
            self.source_size = pixmap.size()
        canvas.installEventFilter(self)
        self.place()
        self.show()
        if self.movie:
            self.movie.start()

    def eventFilter(self, obj, event):  # noqa: N802 (Qt API name)
        if obj is self.canvas and event.type() == QEvent.Type.Resize:
            self.place()
        return False

    def place(self):
        if self.source_size.isEmpty():
            return
        target_h = max(int(self.canvas.height() * self.fraction), 16)
        size = self.source_size.scaled(
            QSize(self.canvas.width() - 2 * self.margin, target_h),
            Qt.AspectRatioMode.KeepAspectRatio)
        if self.movie:
            self.movie.setScaledSize(size)
        else:
            self.setPixmap(self._rounded(self.pixmap_full.scaled(
                size, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)))
        self.resize(size)
        right = "right" in self.corner
        bottom = "bottom" in self.corner
        x = (self.canvas.width() - size.width() - self.margin) if right \
            else self.margin
        y = (self.canvas.height() - size.height() - self.margin) if bottom \
            else self.margin
        self.move(x, y)
        self.raise_()

    def _rounded(self, pixmap):
        """``pixmap`` with rounded corners (for pictures with a
        background, which would otherwise show as a hard rectangle)."""
        if not self.rounded:
            return pixmap
        out = QPixmap(pixmap.size())
        out.fill(Qt.GlobalColor.transparent)
        painter = QPainter(out)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(out.rect()), self.rounded, self.rounded)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        return out

    def remove(self):
        if sip.isdeleted(self):
            return
        if not sip.isdeleted(self.canvas):
            self.canvas.removeEventFilter(self)
        if self.movie:
            self.movie.stop()
        self.hide()
        self.deleteLater()


def apply_mascot(iface, changes, cfg):
    """Show the mascot described by ``cfg`` (a skin's resolved ``mascot``
    section) and register its removal."""
    if not cfg:
        return None
    keys = ("corner", "height", "opacity", "margin", "mirror", "rounded")
    options = {k: cfg[k] for k in keys if k in cfg}
    overlay = MascotOverlay(iface.mapCanvas(), cfg["file"], **options)
    changes.add(overlay.remove)
    return overlay

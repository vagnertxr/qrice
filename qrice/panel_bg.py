"""Faded picture behind the panes (Layers, Browser, ...).

Style sheets cannot make a background image translucent, so the picture is
drawn once at the wanted opacity, with an alpha channel, and saved to the
skin's cache folder; the style sheet then uses that file. Only the Layers
pane shows it (in Browser it was cut off at the bottom).
"""

from pathlib import Path

from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor, QImage, QImageReader, QPainter


def load_picture(path, height):
    """``path`` as a QImage ``height`` pixels high (a null image when it
    cannot be read).

    SVG files are drawn at that height, so they stay sharp (read at their
    nominal size, a 60 px crest would be blown up and blurry); other
    pictures are scaled (enlarged too, if asked: the user chose the size).
    """
    reader = QImageReader(str(path))
    size = reader.size()
    if size.isValid() and size.height() > 0:
        target = int(height)
        reader.setScaledSize(QSize(
            max(round(size.width() * target / size.height()), 1), target))
    image = reader.read()
    return image.convertToFormat(QImage.Format.Format_ARGB32) \
        if not image.isNull() else image


HORIZONTAL = ("left", "center", "right")
VERTICAL = ("top", "center", "bottom")


def position(cfg):
    """QSS ``background-position`` for a skin's ``panel_bg`` settings."""
    h = cfg.get("align_x", "right")
    v = cfg.get("align_y", "bottom")
    h = h if h in HORIZONTAL else "right"
    v = v if v in VERTICAL else "bottom"
    return "center" if h == v == "center" else f"{v} {h}"


def render_panel_bg(picture, panel_color, opacity=0.12, height=200,
                    out=None, align=("right", "bottom"), margin=(0, 0)):
    """Write ``picture`` faded (``opacity``) to ``out`` (PNG with alpha).

    Style sheets can anchor a background to an edge but not offset it, so
    ``margin`` (x, y pixels from the anchored edges of ``align``) is
    transparent padding around the picture: the picture moves inwards.
    ``panel_color`` is kept for callers; the fade no longer needs it.

    Returns the QSS value for ``@panel-bg`` (``url(...)``, or ``none``
    when the picture cannot be read).
    """
    image = load_picture(picture, height)
    if image.isNull() or out is None:
        return "none"
    mx, my = (max(int(m), 0) for m in margin)
    h, v = align
    left = mx if h == "left" else 0
    right = mx if h == "right" else 0
    top = my if v == "top" else 0
    bottom = my if v == "bottom" else 0
    # Transparent canvas: the pane's own background colour (which differs
    # between themes) shows through, so no rectangle shows around it.
    result = QImage(image.width() + left + right,
                    image.height() + top + bottom,
                    QImage.Format.Format_ARGB32)
    result.fill(QColor(0, 0, 0, 0))
    painter = QPainter(result)
    painter.setOpacity(min(max(float(opacity), 0.0), 1.0))
    painter.drawImage(left, top, image)
    painter.end()
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.save(str(out), "PNG")
    return f"url({out.as_posix()})"

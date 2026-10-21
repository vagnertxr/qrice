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
    pictures are scaled, never enlarged beyond their own size.
    """
    reader = QImageReader(str(path))
    size = reader.size()
    if size.isValid() and size.height() > 0:
        is_svg = str(path).lower().endswith((".svg", ".svgz"))
        target = int(height) if is_svg else min(int(height), size.height())
        reader.setScaledSize(QSize(
            max(round(size.width() * target / size.height()), 1), target))
    image = reader.read()
    return image.convertToFormat(QImage.Format.Format_ARGB32) \
        if not image.isNull() else image


def render_panel_bg(picture, panel_color, opacity=0.12, height=200,
                    out=None):
    """Write ``picture`` faded (``opacity``) to ``out`` (PNG with alpha).

    ``panel_color`` is kept for callers; the fade no longer needs it.

    Returns the QSS value for ``@panel-bg`` (``url(...)``, or ``none``
    when the picture cannot be read).
    """
    image = load_picture(picture, height)
    if image.isNull() or out is None:
        return "none"
    # Transparent canvas: the pane's own background colour (which differs
    # between themes) shows through, so no rectangle shows around it.
    result = QImage(image.size(), QImage.Format.Format_ARGB32)
    result.fill(QColor(0, 0, 0, 0))
    painter = QPainter(result)
    painter.setOpacity(min(max(float(opacity), 0.0), 1.0))
    painter.drawImage(0, 0, image)
    painter.end()
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.save(str(out), "PNG")
    return f"url({out.as_posix()})"

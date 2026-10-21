"""Theme colours from a picture, in the spirit of pywal.

:func:`colors_of` reduces an image to a few representative colours
(median cut); :func:`palette` turns them into the ``@name`` variables of a
theme (the names ``variables.qss`` uses), light or dark depending on the
picture, with readable text on every background.

The colour maths is plain Python on ``(r, g, b)`` tuples of 0-255 so it is
testable without images.
"""

import colorsys

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QImage

SAMPLE = 64  # the picture is scaled to at most SAMPLE x SAMPLE pixels
MIN_TEXT_CONTRAST = 4.5  # WCAG AA for normal text
MIN_ACCENT_CONTRAST = 3.0  # WCAG AA for large text and UI parts


# --- colour helpers ---------------------------------------------------------

def hex_color(rgb):
    return "#{:02x}{:02x}{:02x}".format(*(round(c) for c in rgb))


def parse_hex(text):
    text = text.lstrip("#")
    return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))


def to_hls(rgb):
    return colorsys.rgb_to_hls(*(c / 255 for c in rgb))


def from_hls(h, l, s):  # noqa: E741 (colour maths names)
    return tuple(round(c * 255) for c in colorsys.hls_to_rgb(h, l, s))


def luminance(rgb):
    """Relative luminance (WCAG 2)."""
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mix(a, b, t):
    """``a`` blended over ``b`` with weight ``t`` (0: b, 1: a)."""
    return tuple(round(x * t + y * (1 - t)) for x, y in zip(a, b))


def with_lightness(rgb, lightness, max_saturation=1.0):
    h, _, s = to_hls(rgb)
    return from_hls(h, lightness, min(s, max_saturation))


def readable_on(rgb, background, minimum=MIN_TEXT_CONTRAST):
    """``rgb`` made lighter or darker until it reads on ``background``."""
    h, l, s = to_hls(rgb)  # noqa: E741
    step = 0.02 if luminance(background) < 0.18 else -0.02
    while contrast(rgb, background) < minimum and 0 <= l <= 1:
        l += step  # noqa: E741
        rgb = from_hls(h, min(max(l, 0), 1), s)
    return rgb


def hue_distance(a, b):
    d = abs(to_hls(a)[0] - to_hls(b)[0])
    return min(d, 1 - d)


# --- picture -> colours -----------------------------------------------------

def pixels(image):
    """Opaque pixels of ``image`` (a QImage or a file path), sampled."""
    if not isinstance(image, QImage):
        image = QImage(str(image))
    if image.isNull():
        return []
    small = image.scaled(SAMPLE, SAMPLE,
                         Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    small = small.convertToFormat(QImage.Format.Format_ARGB32)
    found = []
    for y in range(small.height()):
        for x in range(small.width()):
            argb = small.pixel(x, y)
            if (argb >> 24) & 0xFF >= 128:
                found.append(((argb >> 16) & 0xFF, (argb >> 8) & 0xFF,
                              argb & 0xFF))
    return found


def median_cut(found, count=8):
    """``count`` boxes of similar pixels -> [(average colour, pixels)],
    the most common first."""
    boxes = [found] if found else []
    while len(boxes) < count:
        # Split the box with the widest channel range at its median.
        best = None
        for i, box in enumerate(boxes):
            if len(box) < 2:
                continue
            for channel in range(3):
                values = [p[channel] for p in box]
                spread = max(values) - min(values)
                if best is None or spread > best[0]:
                    best = (spread, i, channel)
        if best is None or best[0] == 0:
            break
        _, i, channel = best
        box = sorted(boxes.pop(i), key=lambda p: p[channel])
        half = len(box) // 2
        boxes += [box[:half], box[half:]]
    result = []
    for box in boxes:
        n = len(box)
        result.append((tuple(sum(p[c] for p in box) / n for c in range(3)), n))
    return sorted(result, key=lambda item: -item[1])


def colors_of(image, count=8):
    return median_cut(pixels(image), count)


# --- colours -> theme variables -------------------------------------------

def _accent_candidates(colors):
    """Colours worth an accent: saturated, not near black or white; the
    most striking (saturation weighted by how much of the picture) first."""
    total = sum(n for _, n in colors) or 1
    ranked = []
    for rgb, n in colors:
        _, l, s = to_hls(rgb)  # noqa: E741
        if s >= 0.25 and 0.15 <= l <= 0.85:
            ranked.append((s * (n / total) ** 0.5, rgb))
    return [rgb for _, rgb in sorted(ranked, key=lambda item: -item[0])]


def palette(colors, dark=None, base=None, accent=None, accent2=None):
    """Theme variables (name -> "#rrggbb") from ``[(rgb, weight)]``.

    ``dark`` forces a dark (True) or light (False) theme; by default the
    picture decides (mostly dark picture -> dark theme). ``base`` (the hue
    of the greys), ``accent`` and ``accent2`` force those colours, e.g. a
    club's or a brand's colours; forced accents are kept exactly.
    """
    forced = (accent, accent2)
    if not colors:
        colors = [(base or (128, 128, 128), 1)]
    total = sum(n for _, n in colors)
    if dark is None:
        mean = sum(luminance(rgb) * n for rgb, n in colors) / total
        dark = mean < 0.25
    base = base or colors[0][0]
    candidates = _accent_candidates(colors)
    if accent:
        pass
    elif candidates:
        accent = candidates[0]
    else:  # a grey picture: the base hue, made colourful
        h, _, _ = to_hls(base)
        accent = from_hls(h, 0.5, 0.6)
    second = accent2 or next((c for c in candidates
                              if hue_distance(c, accent) > 0.1), None)
    if second is None:
        h, l, s = to_hls(accent)  # noqa: E741
        second = from_hls((h + 0.42) % 1, l, s)

    tint = 0.18  # how much of the base hue the greys keep
    if dark:
        window = with_lightness(base, 0.09, tint)
        panel = with_lightness(base, 0.13, tint)
        header = with_lightness(base, 0.18, tint)
        border_light = with_lightness(base, 0.24, tint)
        border = with_lightness(base, 0.32, tint)
        text = with_lightness(base, 0.86, 0.12)
        emphasis = with_lightness(base, 0.95, 0.10)
        disabled = with_lightness(base, 0.50, tint)
    else:
        window = with_lightness(base, 0.94, tint)
        panel = with_lightness(base, 0.985, tint)
        header = with_lightness(base, 0.90, tint)
        border_light = with_lightness(base, 0.84, tint)
        border = with_lightness(base, 0.70, tint)
        text = with_lightness(base, 0.22, 0.15)
        emphasis = with_lightness(base, 0.12, 0.15)
        disabled = with_lightness(base, 0.58, tint)
    text = readable_on(text, header)
    emphasis = readable_on(emphasis, header)
    if not forced[0]:
        accent = readable_on(accent, panel, MIN_ACCENT_CONTRAST)
    if not forced[1]:
        second = readable_on(second, panel, MIN_ACCENT_CONTRAST)
    h, l, s = to_hls(accent)  # noqa: E741
    accent_dark = from_hls(h, max(l - 0.12, 0) if not dark else
                           min(l + 0.12, 1), s)
    on_accent = max(((255, 255, 255), (20, 20, 20)),
                    key=lambda c: contrast(c, accent))
    on_second = max(((255, 255, 255), (20, 20, 20)),
                    key=lambda c: contrast(c, second))
    selected = mix(accent, panel, 0.38)
    variables = {
        "bg-window": window,
        "bg-panel": panel,
        "bg-header": header,
        "border": border,
        "border-input": border,
        "border-light": border_light,
        "text": text,
        "text-emphasis": emphasis,
        "text-disabled": disabled,
        "accent": accent,
        "accent-dark": accent_dark,
        "accent-text": on_accent,
        "accent2": second,
        "accent2-text": on_second,
        "hover": mix(accent, panel, 0.18),
        "border-hover": mix(accent, panel, 0.6),
        "pressed": mix(accent, panel, 0.3),
        "selected": selected,
        "selected-hover": mix(accent, panel, 0.26),
        "scrollbar-bg": window,
        "scrollbar-handle": border,
        "scrollbar-handle-hover": mix(accent, border, 0.5),
    }
    variables["selected-text"] = readable_on(emphasis, selected)
    return {name: hex_color(rgb) for name, rgb in variables.items()}


def palette_from_image(image, dark=None, **forced):
    return palette(colors_of(image), dark, **forced)

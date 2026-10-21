"""Style sheets: a theme folder plus a skin's variables -> one QSS string.

A theme is a directory under ``resources/themes/<name>/`` with two files:

* ``style.qss``     - Qt style sheet that may reference ``@name`` variables,
* ``variables.qss`` - ``@name: value;`` lines (same convention as QGIS themes).

The small widget icons the style sheets use (arrows, check marks) are drawn
in dark grey; for a skin they are copied to its cache folder recoloured
with the skin's text colour, so that they also show on dark themes.
"""

import re
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent
THEMES = PLUGIN_DIR / "resources" / "themes"
ICONS = PLUGIN_DIR / "resources" / "icons"
VARIABLE_RE = re.compile(r"^\s*@([\w-]+)\s*:\s*(.+?)\s*;\s*$", re.MULTILINE)
# Greys of the bundled widget icons -> variable giving their new colour.
ICON_GREYS = {"#4a4a4a": "text", "#6a6a6a": "text-disabled",
              "#2b2b2b": "text-emphasis"}
WIDGET_ICONS = ("arrow-down", "arrow_down_small", "arrow_up_small",
                "branch_closed", "branch_open", "check", "check_partial",
                "radio_dot")


def theme_names():
    return sorted(p.name for p in THEMES.iterdir()
                  if (p / "style.qss").exists())


def theme_variables(theme):
    """``@name: value;`` lines of the theme as a dict."""
    text = (THEMES / theme / "variables.qss").read_text(encoding="utf-8")
    return dict(VARIABLE_RE.findall(text))


def recolor_icons(variables, folder):
    """Write the widget icons, recoloured with ``variables``, to ``folder``.

    Returns the folder for the ``@icons`` variable.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name in WIDGET_ICONS:
        svg = (ICONS / f"{name}.svg").read_text(encoding="utf-8")
        for grey, variable in ICON_GREYS.items():
            svg = svg.replace(grey, variables.get(variable, grey))
        (folder / f"{name}.svg").write_text(svg, encoding="utf-8")
    return folder


def load_qss(theme, overrides=None, icons=None, extra=""):
    """Return the theme's style sheet with ``@name`` variables substituted.

    ``overrides`` replace the theme's own variables; ``@icons`` expands to
    ``icons`` (default: the plugin's icon directory), for ``url()`` values.
    ``extra`` (more QSS, e.g. from the skin's chrome) is appended first, so
    its variables are substituted too.
    """
    variables = theme_variables(theme)
    variables.update(overrides or {})
    variables["icons"] = Path(icons or ICONS).as_posix()
    qss = (THEMES / theme / "style.qss").read_text(encoding="utf-8")
    qss += "\n" + extra
    return re.sub(
        r"@([\w-]+)", lambda m: str(variables.get(m.group(1), m.group(0))),
        qss)


def build_palette(variables, base=None):
    """A QPalette in the theme's colours, on top of ``base``.

    Some widgets do not follow the style sheet and paint with the
    application palette, e.g. layer and group names in the Layers pane
    (QgsLayerTreeModel uses its Text colour).
    """
    from qgis.PyQt.QtGui import QColor, QPalette

    palette = QPalette(base) if base is not None else QPalette()
    Role, Group = QPalette.ColorRole, QPalette.ColorGroup

    def color(name, fallback):
        value = variables.get(name, fallback)
        return QColor(value if str(value).startswith("#") else fallback)

    roles = {
        Role.Window: color("bg-window", "#efefef"),
        Role.WindowText: color("text", "#000000"),
        Role.Base: color("bg-panel", "#ffffff"),
        Role.AlternateBase: color("bg-header", "#f7f7f7"),
        Role.Text: color("text", "#000000"),
        Role.Button: color("bg-header", "#efefef"),
        Role.ButtonText: color("text", "#000000"),
        Role.BrightText: color("text-emphasis", "#000000"),
        Role.Highlight: color("selected", "#308cc6"),
        Role.HighlightedText: color("selected-text", "#ffffff"),
        Role.ToolTipBase: color("bg-header", "#ffffdc"),
        Role.ToolTipText: color("text-emphasis", "#000000"),
        Role.PlaceholderText: color("text-disabled", "#808080"),
        Role.Link: color("accent", "#0000ff"),
    }
    for group in (Group.Active, Group.Inactive):
        for role, value in roles.items():
            palette.setColor(group, role, value)
    disabled = color("text-disabled", "#808080")
    for role, value in roles.items():
        palette.setColor(Group.Disabled, role, value)
    for role in (Role.WindowText, Role.Text, Role.ButtonText):
        palette.setColor(Group.Disabled, role, disabled)
    return palette

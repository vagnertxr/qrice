"""Country flags (flag-icons by Panayiotis Lipiridis, MIT; the flags
themselves are public domain) as skin pictures and palette sources.

A skin with ``"flag": "<ISO code>"`` uses the flag as its pane picture
(and mascot, if it has one) when it names no files of its own; see skins.py.
"""

import json

from .theme import PLUGIN_DIR

FLAGS = PLUGIN_DIR / "resources" / "flags"


def countries():
    """ISO code -> country name, sorted by name."""
    names = json.loads((FLAGS / "countries.json").read_text(encoding="utf-8"))
    return dict(sorted(names.items(), key=lambda item: item[1]))


def flag_file(code):
    path = FLAGS / f"{str(code).lower()}.svg"
    return path if path.exists() else None


def flag_skin_data(code):
    """skin.json contents of a skin for the country ``code``."""
    return {"name": countries().get(code, code.upper()),
            "category": "flag", "flag": code, "theme": "rice",
            "palette": "auto",
            "panel_bg": {"opacity": 0.22, "height": 140},
            "chrome": {"bars": "accent", "shine": True, "glow": 18},
            "credit_url": "https://github.com/lipis/flag-icons",
            "license": "MIT (flag-icons); flags: public domain"}

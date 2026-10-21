"""Skins: a folder with ``skin.json`` and its pictures.

``skin.json`` (every key optional except ``name``)::

    {"name": "Tux", "author": "Larry Ewing", "license": "...",
     "credit_url": "https://...", "category": "mascot",
     "theme": "rice",                  # folder in resources/themes
     "variables": {"accent": "#f5c211"},   # over the theme's variables.qss
     "palette": "auto",                # variables from the picture (below)
     "palette_from": "tux.png",        # default: the skin's picture
     "colors": {"base": "#000000", "accent": "#c8102e",
                "accent2": "#ffffff"},  # forced palette colours
     "dark": true,                     # force a dark/light palette
     "panel_bg": {"file": "tux.png", "opacity": 0.2, "height": 220},
     "mascot": {"file": "tux.png", "corner": "bottom-right",  # optional:
                "height": 0.3, "opacity": 0.95, "margin": 16},  # over the map
     "layout": "none",                 # none | pro | tiling | zen
     "chrome": {...},                  # see chrome.py
     "icons": "qgis"}                  # qgis | pro (Pro icon theme)

The skin's picture shows faded behind the panes; showing it over the map as
well (``mascot``) is optional, since it covers part of the data.

A skin may name a country instead of pictures (``"flag": "br"``): the flag
then serves as panel picture and palette source (see flags.py).

Skins are looked up, in this order, in the plugin's ``resources/skins``,
the user's ``<QGIS profile>/qrice/skins`` and, for development, the folder
named by the ``QRICE_DEV_SKINS`` environment variable. A later folder wins
over an earlier one for the same skin id (folder name).
"""

import json
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from qgis.core import QgsApplication

from .theme import PLUGIN_DIR

BUILTIN = PLUGIN_DIR / "resources" / "skins"
DEV_ENV = "QRICE_DEV_SKINS"
DEFAULT_SKIN = "tux"
LAYOUTS = ("none", "pro", "tiling", "zen")
CATEGORIES = ("theme", "mascot", "anime", "flag", "football", "meme")
PICTURES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")


def user_dir():
    return Path(QgsApplication.qgisSettingsDirPath()) / "qrice"


def user_skins_dir():
    return user_dir() / "skins"


def cache_dir(skin_id):
    return user_dir() / "cache" / skin_id


def skin_dirs():
    """(folder, kind) pairs in lookup order."""
    dirs = [(BUILTIN, "builtin"), (user_skins_dir(), "user")]
    if os.environ.get(DEV_ENV):
        dirs.append((Path(os.environ[DEV_ENV]).expanduser(), "dev"))
    return dirs


@dataclass
class Skin:
    id: str
    path: Path
    kind: str = "user"  # builtin | user | dev
    data: dict = field(default_factory=dict)

    def __getattr__(self, name):
        # skin.name, skin.license, ... read from skin.json.
        if name in ("id", "path", "kind", "data"):
            raise AttributeError(name)
        return self.data.get(name)

    @property
    def theme(self):
        return self.data.get("theme") or (
            "pro_light" if self.layout == "pro" else "rice")

    @property
    def layout(self):
        return self.data.get("layout", "none")

    @property
    def category(self):
        return self.data.get("category", "theme")

    @property
    def chrome(self):
        return self.data.get("chrome") or {}

    def file(self, name):
        """Absolute path of a picture of the skin (or None)."""
        if not name:
            return None
        path = Path(name)
        if not path.is_absolute():
            path = self.path / name
        return path if path.exists() else None

    def section(self, key):
        """``mascot`` / ``panel_bg`` settings with their picture resolved,
        or None when the skin has none."""
        cfg = self.data.get(key)
        if not cfg:
            return None
        cfg = dict(cfg)
        cfg["file"] = self.file(cfg.get("file"))
        if cfg["file"] is None and self.data.get("flag"):
            from .flags import flag_file
            cfg["file"] = flag_file(self.data["flag"])
        return cfg if cfg["file"] else None

    def palette_source(self):
        name = self.data.get("palette_from")
        if name:
            return self.file(name)
        if self.data.get("flag"):
            from .flags import flag_file
            return flag_file(self.data["flag"])
        return self.picture()

    def picture(self):
        """The skin's picture: behind the panes, or else its mascot."""
        for key in ("panel_bg", "mascot"):
            cfg = self.section(key)
            if cfg:
                return cfg["file"]
        return None

    def thumbnail(self):
        """Picture standing for the skin in the manager."""
        return self.picture() or self.file(self.data.get("thumbnail"))

    @property
    def editable(self):
        return self.kind == "user"


def read_skin(folder, kind="user"):
    folder = Path(folder)
    data = json.loads((folder / "skin.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("name"):
        raise ValueError(f"{folder}: skin.json needs a name")
    if data.get("layout", "none") not in LAYOUTS:
        raise ValueError(f"{folder}: unknown layout {data['layout']!r}")
    return Skin(folder.name, folder, kind, data)


def list_skins():
    """All skins by id (later folders win), sorted by category and name."""
    found = {}
    for folder, kind in skin_dirs():
        if not folder.is_dir():
            continue
        for sub in sorted(folder.iterdir()):
            if (sub / "skin.json").exists():
                try:
                    found[sub.name] = read_skin(sub, kind)
                except (ValueError, OSError, json.JSONDecodeError):
                    continue  # a broken skin must not hide the others
    order = {c: i for i, c in enumerate(CATEGORIES)}
    return sorted(found.values(),
                  key=lambda s: (order.get(s.category, 99), s.name.lower()))


def load_skin(skin_id):
    for skin in list_skins():
        if skin.id == skin_id:
            return skin
    return None


def write_skin(skin):
    (skin.path / "skin.json").write_text(
        json.dumps(skin.data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")


def _free_id(base):
    base = "".join(c if c.isalnum() else "-" for c in base.lower()).strip("-")
    base = base or "skin"
    taken = {s.id for s in list_skins()}
    skin_id, n = base, 2
    while skin_id in taken:
        skin_id, n = f"{base}-{n}", n + 1
    return skin_id


def new_skin(name, data=None, pictures=()):
    """A user skin named ``name``; ``pictures`` are copied into it."""
    skin_id = _free_id(name)
    folder = user_skins_dir() / skin_id
    folder.mkdir(parents=True)
    for picture in pictures:
        shutil.copy2(picture, folder / Path(picture).name)
    skin = Skin(skin_id, folder, "user", {"name": name, **(data or {})})
    write_skin(skin)
    return skin


def skin_from_picture(picture, name=None):
    """A user skin around one picture: faded behind the panes, with a
    palette taken from it."""
    picture = Path(picture)
    return new_skin(
        name or picture.stem.replace("_", " ").replace("-", " ").title(),
        {"category": "mascot", "theme": "rice", "palette": "auto",
         "panel_bg": {"file": picture.name, "opacity": 0.2,
                      "height": 220},
         "layout": "none"},
        [picture])


CREDIT_KEYS = ("author", "license", "credit_url")


def duplicate_skin(skin, name=None):
    """A user copy of ``skin``. The copy is yours: it does not carry the
    original's author, licence and source link."""
    data = {k: v for k, v in skin.data.items() if k not in CREDIT_KEYS}
    copy = new_skin(name or f"{skin.name} copy", data)
    for item in skin.path.iterdir():
        if item.name != "skin.json" and item.is_file():
            shutil.copy2(item, copy.path / item.name)
    copy.data["name"] = name or f"{skin.name} copy"
    write_skin(copy)
    return copy


def delete_skin(skin):
    if not skin.editable:
        raise ValueError("only user skins can be deleted")
    shutil.rmtree(skin.path)
    shutil.rmtree(cache_dir(skin.id), ignore_errors=True)


def export_skin(skin, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(skin.path.rglob("*")):
            if item.is_file():
                zf.write(item, f"{skin.id}/{item.relative_to(skin.path)}")


def import_skin(zip_path):
    """Unpack a skin exported by :func:`export_skin` as a new user skin."""
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        roots = {n.split("/")[0] for n in names}
        if len(roots) != 1 or f"{next(iter(roots))}/skin.json" not in names:
            raise ValueError("not a QRice skin archive")
        root = roots.pop()
        data = json.loads(zf.read(f"{root}/skin.json"))
        skin = new_skin(data.get("name") or root, data)
        for name in names:
            rel = Path(name).relative_to(root)
            if rel.name == "skin.json" or ".." in rel.parts:
                continue
            target = skin.path / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(name))
    return skin

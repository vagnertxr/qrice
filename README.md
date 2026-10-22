# QRice

**QRice is a skin manager for QGIS**: rice it like your desktop. A skin gives QGIS
its colours (picked, or taken from a picture, pywal style), a faded picture behind
the panes, the window chrome (gaps, rounded corners, a glowing focus frame, glossy
bars, a polybar-style status bar) and a layout (tiling, zen or the
ArcGIS Pro-style ribbon). One click on, one click off: switching the skin off
restores QGIS exactly as it was.

QRice is a fork of [ArcSkin](https://github.com/envirosolutionspl/arcskin) by
EnviroSolutions; ArcSkin's ArcGIS Pro look lives on as the *Pro Light* skin.

![QGIS with the Tux skin: dark theme in Tux's black and yellow, Tux behind the Layers pane, polybar status bar and a glow around the focused pane](docs/images/qrice-tux.jpg)

## Skins

| Skin | What it is |
|---|---|
| Tux, Tux Redesign | Linux's penguin; dark theme with polybar / light theme with tiling layout |
| QGIS-tan | Wikipe-tan's green sister: map pins in her hair, the QGIS logo on her apron |
| Wikipe-tan | Wikipedia's mascot by Kasuga |
| Brasil, Estados Unidos, China, Cuba, Palestina (and any other country) | Flag behind the panes, palette and bars in the flag's colours |
| Rice Dark, Rice Light, Zen | Colours only; Zen hides everything but the map |
| Pro Light (ArcSkin) | The ArcGIS Pro-style ribbon, panes, icons and symbology |
| Pro Dark | The Pro layout riced: dark palette, gaps, rounded corners, glow and shine |
| Pro QGIS-tan | The Pro layout in soft QGIS greens, with QGIS-tan behind Contents |

Every bundled picture has a free licence; see
[CREDITS.md](qrice/resources/skins/CREDITS.md).

Switch skins with *Plugins → QRice → Skins*. The QRice toolbar button (a rice bowl
shaped like a Q) opens the Skin Manager; turn the skin off and on with its
**Skin on** box.

## Skin Manager

*Plugins → QRice → Skin Manager…* shows every skin as a tile with its colours and
picture. Double-click a tile, or select it and click **Apply**.

![Skin Manager with the Tux skin selected: its colours on the Colours tab](docs/images/qrice-manager.png)

Built-in skins are read-only. To change one, select it and click **Duplicate…**
and give the copy a name (here *My Tux*): the copy can be edited, and while it is
the active skin every change shows at once. **Rename…** changes a copy's name
later.

- **Colours:** *Colours from the picture* builds the palette from the skin's
  picture; *Theme* forces dark or light. Click a swatch (accent, second accent,
  window, panes, headers, text, selection, borders) to pick a colour yourself; the
  **×** next to it goes back to the generated one.
- **Picture:** **Choose…** another picture, e.g. another character for a copy of
  *Pro QGIS-tan*. It shows faded behind the Layers pane, with its own opacity,
  size (height in pixels), position (left / centre / right, top / middle /
  bottom) and distance from that edge, e.g. to lift a picture whose feet are cut
  off at the bottom of the pane; *Also over the map* turns
  it into a mascot in a corner of the map (it covers part of the data, so no
  bundled skin does that).

![Picture tab of My Tux: Tux faded behind the panes, mascot over the map switched off](docs/images/qrice-manager-picture.png)

- **Window:** layout, gaps, corner radius, glow around the focused pane (optionally
  pulsing), frame around the map, font, pane titles, menu bar, toolbars, polybar
  status bar, map background, bar colours, glossy bars and window opacity (see
  the table below).

![Window tab of My Tux: gaps, corners, glow, polybar status bar, themed map background and glossy bars](docs/images/qrice-manager-window.png)

**New from picture…** turns any picture into a skin, with a palette from its
colours; **New flag skin…** does the same for a country. **Export…** and
**Import…** share skins as ZIP files; **Open folder** shows a skin's files. Your
skins live in `<QGIS profile>/qrice/skins/`.

### Window chrome and layouts

| Setting | Values |
|---|---|
| Layout | keep my layout · tiling (map + Layers over Browser) · zen (map only) · ArcGIS Pro-style |
| Gaps, corner radius, focus frame | pixels |
| Pane titles | full · minimal · hidden |
| Menu bar | shown · hidden |
| Toolbars | top · left · hidden |
| Status bar | plain · polybar |
| Map background | keep · theme |
| Bar colours | plain · accent (menu bar, pane titles and status bar in the skin's colours) |
| Glow | px of neon halo around the focused pane; optionally pulsing |
| Shine | glossy gradients on bars, tabs and buttons |
| Map frame | px of accent frame around the map |
| Font, font size, window opacity | any installed font; opacity needs a compositor |

Shortcuts while a skin is on: **Ctrl+Alt+M** shows or hides a hidden menu bar,
**Ctrl+Alt+Z** brings the panes back in the zen layout. When zen is applied, a box
recalls these shortcuts and how to leave zen (it can be told not to show again).

### skin.json

A skin is a folder with `skin.json` and its pictures:

```json
{"name": "Tux", "category": "mascot", "author": "Larry Ewing", "license": "…",
 "palette": "auto", "dark": true,
 "variables": {"accent": "#f5c211"},
 "panel_bg": {"file": "tux.png", "opacity": 0.2, "height": 220},
 "layout": "none",
 "chrome": {"gaps": 6, "radius": 8, "statusbar": "polybar",
            "map_background": "theme", "glow": 18, "glow_pulse": true,
            "shine": true, "map_frame": 0}}
```

`variables` use the names of
[`themes/rice/variables.qss`](qrice/resources/themes/rice/variables.qss); `colors`
(`base`, `accent`, `accent2`) force exact colours, e.g. a club's. A skin may also show
its picture over the map (`"mascot": {"file": …, "corner": "bottom-right",
"height": 0.3}`); no bundled skin does, since it covers part of the data. The mascot is
a widget, not a map item: clicks go through it and it never appears in exports or
print layouts. Animated GIFs play.

### Test skins

For skins that must not be committed or shipped (football clubs, memes), put
skin folders in `dev-skins/` (git-ignored, not packaged) and start QGIS with
`QRICE_DEV_SKINS=/path/to/dev-skins qgis`.

## Requirements

- QGIS 4.x (Qt 6), the main platform
- QGIS 3.40 or newer (Qt 5)

## Installation

Download the latest .zip from the Releases tab

Or:
1. Build the ZIP with `python scripts/package.py` (`dist/qrice-<version>.zip`).
2. In QGIS open *Plugins → Manage and Install Plugins… → Install from ZIP*,
   choose the file and click *Install Plugin*.

The active skin (Tux by default) is applied as soon as the plugin is loaded; switch
it with *Plugins → QRice → Skins* or the toolbar button (Skin Manager), off and
on with the manager's **Skin on** box.

## Good to know

- QGIS keeps one layer tree per project, so the drawing order is shared by all view
  tabs; each tab has its own layer visibility (a QGIS map theme) and extent.
- 3D views and print layouts open in their own windows; their tabs bring them to the
  front.
- The icon theme is installed into QGIS's `resources/themes` folder when it is
  writable, because QGIS 4 only reads UI themes from there.

## Development

```
qrice/                        the plugin (packed into the ZIP)
  plugin.py                   on / off switch, skin steps, progress box
  skins.py                    skin folders and skin.json (built-in, user, dev)
  theme.py                    theme folder + variables -> style sheet
  palette.py                  colours from a picture (median cut, WCAG contrast)
  mascot.py                   mascot over the map canvas
  panel_bg.py                 faded picture behind the panes
  chrome.py                   gaps, corners, bars, tiling and zen layouts
  flags.py                    country flags as skins
  manager.py                  Skin Manager dialog
  util.py                     tr(), Pro icons, undo log of all changes (Changes)
  ribbon.py                   ribbon, title row, Project menu
  panes.py                    Contents, Catalog, Geoprocessing, Symbology panes
  contents_views.py           List By views, raster legend, context menu icons
  mapview.py                  view tabs, map status bar
  coords.py                   coordinate formats of the status bar
  dialogs.py                  attribute table, Pro icons in other windows
  symbology.py                default symbols, label font, colour ramps
  icon_theme.py               QGIS icon theme
  basemaps.py                 basemap gallery
  resources/                  icons, style sheets, generated icon theme, colour ramps
  i18n/                       translations (.ts sources)
scripts/
  package.py                  builds dist/qrice-<version>.zip
  i18n.py                     update .ts files from the code, compile .qm files
  build_icon_theme.py         generates the QGIS icon theme (run with python-qgis)
  build_demo.py               builds the demo project (QGIS Python console)
demo/                         demo project and data
docs/images/                  screenshots
```

Every change QRice makes to QGIS goes through `util.Changes`, which records how to
undo it; switching off replays that log backwards.

For development, link the plugin folder into your QGIS profile (PowerShell as
administrator, or with Windows developer mode on):

```powershell
New-Item -ItemType SymbolicLink `
  -Path "$env:APPDATA\QGIS\QGIS4\profiles\default\python\plugins\qrice" `
  -Target "$PWD\qrice"
```

On Linux:

```bash
ln -s "$PWD/qrice" ~/.local/share/QGIS/QGIS4/profiles/default/python/plugins/qrice
```

**Tests.** `tests/` holds unit tests that need no QGIS window: coordinate
formats, the undo log, the style sheet and icon references, default symbols
and colour ramps, translations and metadata. Run them with QGIS's Python from
the repository root (they also run in CI on QGIS 3.44 and the latest release):

```powershell
C:\OSGeo4W\bin\python-qgis.bat -m unittest discover -s tests -t . -v
```

`tests/smoke_in_qgis.py` is a smoke test for a running QGIS with ArcSkin on:
run it from the Python console and it switches the look off and on, checking
that QGIS comes back as it was and that the skin is complete. It also lists
any tool of QGIS's core toolbars that no ribbon button or drop-down reaches
(the label, raster, annotation, GPS and mesh toolbars are not on the ribbon
yet).

**Translations.** Texts in the code are English and go through `tr("...")`. After
changing them run `python scripts/i18n.py update`, translate the new entries in
`qrice/i18n/arcskin_pl.ts` (Qt Linguist or a text editor) and the `.qm` files are
compiled when packaging. For a new language, add an empty
`qrice/i18n/arcskin_<code>.ts` and run `update`.

**Packaging and releases.** `python scripts/package.py` writes
`dist/qrice-<version>.zip`. For a release, raise `version` in
`qrice/metadata.txt`, tag the commit `v<version>` and push the tag; GitHub
Actions builds the ZIP and attaches it to the release.

## Credits and licence

QRice is licensed under the GPL-2.0-or-later, see [LICENSE](LICENSE). It is based
on ArcSkin by EnviroSolutions (GPL-2.0-or-later). Mascot pictures: see
[CREDITS.md](qrice/resources/skins/CREDITS.md). Country flags:
[flag-icons](https://github.com/lipis/flag-icons) (MIT). The Pro icon
theme is derived from QGIS's own icons (GPL-2.0-or-later). Demo data: Natural
Earth (public domain). Basemaps: © OpenStreetMap contributors, OpenTopoMap
(CC-BY-SA), CARTO, Sentinel-2 cloudless by EOX IT Services GmbH (CC BY 4.0).

> QRice and ArcSkin are independent open source projects, not affiliated with,
> sponsored or endorsed by Esri. ArcGIS and ArcGIS Pro are trademarks of Esri.

# SAGE-Viewer Handoff

A snapshot of where the project sits so a fresh chat can pick it up cleanly.

---

## How to launch

```bash
# Activate the environment with sage-viewer installed
export PATH="/Users/mbradley/Library/Python/3.12/bin:$PATH"

# Run against miniMillennium
sage-viewer --par /Users/mbradley/Documents/PhD/SAGE26/input/millennium.par --snap 63
```

Then open <http://localhost:8080> in any browser.

Useful flags:
- `--snap N` initial snapshot (default: last = z = 0)
- `--port N` (default 8080)
- `--n-jobs N` halo loader threads (default: CPUs − 1)
- `--max-halos N`, `--max-galaxies N` downsample ceilings
- `--min-halo-mass M`, `--min-stellar-mass M` (Msun)

---

## Repo layout

```
SAGE-Viewer/
├── sage_viewer/
│   ├── _version.py
│   ├── app.py                  # Trame layout + view wiring
│   ├── cli.py
│   ├── config.py               # SimConfig dataclass
│   ├── io/
│   │   ├── par_reader.py       # parses .par into SimConfig
│   │   ├── snapshot_table.py   # scale-factor / redshift lookup
│   │   ├── halo_reader.py      # lhalo_binary reader, joblib threads
│   │   └── galaxy_reader.py    # SAGE HDF5 reader
│   ├── parallel/loader.py      # prefetch + LRU snapshot cache
│   ├── scene/
│   │   ├── scene.py            # owns plotter, layers, focus state
│   │   ├── halo_layer.py
│   │   ├── galaxy_layer.py
│   │   └── camera.py           # all fly-to / zoom / indicator drawing
│   ├── ui/
│   │   ├── toolbar.py          # transport buttons + snapshot slider
│   │   ├── navigation_panel.py # right panel with Layers + 4 nav tabs
│   │   └── info_panel.py       # footer + left-click galaxy select
│   └── utils/
│       ├── colormap.py         # normalize_log + KDE density
│       ├── sizing.py           # point size scalers
│       └── kdtree.py           # nearest-halo lookup wrapper
├── tests/                      # 22 unit tests, all passing
├── docs/                       # MkDocs Material site
└── pyproject.toml
```

---

## What works today

- **Rendering**: haloes + galaxies as point clouds, both with independent
  toggle / opacity / colour-by mode / colormap dropdowns
- **Playback**: play / pause / stop / reverse / repeat with 1× / 2× / 5×
  speed, snapshot slider tracks position, stop returns to z = 0
- **Navigation tabs** (right panel, Layers is primary on top):
  - **Halo** — fly to halo index with standoff
  - **Galaxy** — fly to galaxy index, 1/3/5 Mpc/h presets (Enter to go),
    auto-enables focus
  - **Coords** — fly to (x, y, z) at a chosen standoff
  - **Box** — frame an axis-aligned sub-box
- **Focus mode** (target icon button) — masks haloes and galaxies outside
  the active zoom region; persists across snapshot changes
- **Left-click any point** → selects nearest galaxy, updates index field
  in panel, draws a face-on red circle around the galaxy
- **Mouse wheel** does NOT change values in inputs / sliders (intentional)

---

## Likely next-up things

- Halo and galaxy point sizes are fixed (mass-binned) — could expose as a
  slider per layer
- No saved camera positions / bookmarks yet
- No screenshot / movie export from the live viewer (only the headless
  flythrough script in SAGE26)
- Density colour mode does KDE per snapshot which is slow; could be cached
- microUchuu is wired up (single huge tree file) but not stress-tested
- Search by halo mass or galaxy property could replace fly-to by index
- Hover tooltip with object info (currently only on click)
- The right panel's content scrolls when long; might want responsive
  re-layout for narrow screens

---

## Style / housekeeping

- No Claude/Anthropic mentions anywhere (commits, code, docs) — keep it that way
- Comments only when the *why* is non-obvious; no chapter-doc paragraphs
- Black + ruff configured; `pre-commit install` to enable on commit
- `pytest tests/ -v` → 22 passing
- Python ≥ 3.10; PyVista 0.46, Trame 3.13, Vuetify 3 (vue3 client)

---

## Known quirks worth knowing

- `state.focus_active` in Trame is a proxy — read with `bool(state.focus_active)`
  inside callbacks, never use truthy `state.focus_active` directly
- The async play loop reads from a plain Python dict `_ctl` not from
  `state.is_playing` (the proxy isn't reactive inside a running coroutine)
- VTK is single-threaded — all rendering / camera mutation must happen on
  the main Trame event loop thread, not in joblib workers
- After PyVista callbacks (the point picker), call `state.flush()` to push
  state changes to the client — they run outside the normal event dispatch
- Relative paths in `.par` files resolve against `parent.parent` of the
  par file (i.e. the SAGE root, not the par file's dir)

---

## Status at handoff

All UI requests implemented. Right panel re-arranged with Layers as the
primary horizontal tab, four small nav tabs below it, render window fills
the rest of the screen. `layer_panel.py` deleted; its contents live in
`navigation_panel.py` as the Layers tab.

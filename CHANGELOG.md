# Changelog

All notable changes to SAGE-Viewer are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.0.4] — 2026-06-22

### Fixed

- Launch Mode: clicking **×** to close now properly stops the server (`asyncio.ensure_future` instead of bare `await` in sync handler, which caused a `RuntimeWarning: coroutine was never awaited` and left the process running)

---

## [1.0.3] — 2026-06-22

### Fixed

- Launch Mode: **×** button now calls `server.stop()` to shut down the process when running standalone; previously it only hid the wizard UI without terminating the server

---

## [1.0.1] — 2026-06-22

### Fixed

- GIF frames resized to canonical resolution when a mixed native/supersampled frame arrives mid-recording — prevents dimension mismatch crash
- `scipy` added to declared package dependencies (was used but omitted from `pyproject.toml`, breaking `pip install` environments)
- CI: `libgl1-mesa-glx` → `libgl1` (package renamed in Ubuntu 22+)
- CI: removed invalid `W503` ruff selector; added intentional-style codes (`E402`, `E701`, `E702`, `E401`, `C408`) to ignore list; auto-fixed `UP037`/`UP035` quoted annotations and deprecated `Callable` import
- Docs URL updated from readthedocs.io to GitHub Pages (`mbradley1985.github.io/SAGE-Viewer`)
- README image paths changed to absolute `raw.githubusercontent.com` URLs so images render on PyPI

### Added

- GitHub Actions publish workflow (`.github/workflows/publish.yml`) — builds wheel + sdist and publishes to PyPI via Trusted Publishing on every `v*` tag push; no API token needed in CI
- Docs pages: Multi-Box Comparison, Launch Mode, Recording, Library (all new)
- `docs/mkdocs.yml` nav updated with new pages

### Changed

- `docs/getting_started/installation.md`: removed broken `pip install sage-viewer` section; HPC section updated to use `install_hpc.sh` instead of conda
- `docs/getting_started/quickstart.md`: fixed "left panel" → Structure tab (right panel); "click" → double-click
- `docs/user_guide/console.md`: rewrote Terminal mode to reflect PTY backend; removed stale "no pty" limitations section
- `docs/user_guide/interface.md`: seven tabs → nine tabs; added Console and Library rows; added Multi-Box Strip section

---

## [1.0.0] — 2026-06-22

First public release on PyPI.

### Added

#### HPC install script (`install_hpc.sh`)
- Creates a Python venv and pip-installs SAGE-Viewer in editable mode in one step
- Checks Python ≥ 3.10; accepts optional positional argument for venv path on scratch filesystems
- Checks for `ffmpeg` separately and prints a `module load ffmpeg` hint if absent

#### Side-by-side multi-box comparison
- Load two or more SAGE models side-by-side via `+SBS` in the hamburger Models section
- Each box is fully independent: snapshot, filters, colormaps, opacity, layer visibility
- Box strip at the bottom of the viewport; clicking a box makes it active (green label)
- Play, step, and snapshot slider advance only the active box's snapshot
- Halo Mvir colour mode locked to Viridis for visual consistency across boxes
- Background snapshot preloading and per-snapshot KDTree pre-building

#### Launch Mode wizard (`sage_viewer/wizard/`)
- Guided setup flow for configuring and launching SAGE26
- Step chips in the header track progress (cyan = current, green = done, white = pending)
- **Rescan** button restarts the environment scan at any point
- **Create config file** option writes a new `.par` from the built-in template
- Par file editor opens side-by-side with the terminal for simultaneous editing and output review
- SAGE26 `OutputDir` is created automatically before the binary runs
- Wizard always resets cleanly when re-opened from Explore Mode

#### PTY-backed xterm.js terminal (Console tab)
- Terminal mode replaced with a real PTY (`pty.openpty()`) — full ANSI colour, cursor control, interactive programs (`vim`, `top`, `htop`, `less`) all work
- PTY sessions cleaned up automatically on app exit via `atexit` handler
- Multiple sessions, each with their own PTY process, history, mode, cwd, env, and Python interpreter

#### Interactive draw widgets — Coords and Box tabs
- **Draw Sphere**: two draggable handle balls (centre + edge) with live field updates; **Lock Sphere** commits as the active focus region
- **Draw Box**: native `vtkBoxWidget2` with face and corner handles; **Lock Box** commits; **Clear** cancels without navigating
- Both widgets centre on the camera focal point when first placed; cleared automatically on Reset Camera and model switch

#### Library pop-out improvements
- Multiple items open simultaneously as independent floating cards with diagonal cascade positioning
- GIF always restarts from frame 0 on open (unique `#N` URL fragment busts browser animation cache)
- Close reliability fixed: authoritative Python list as source of truth instead of reading stale Trame proxy state

#### Movie recording fixes
- FPS now honoured: frame written every `1/fps` seconds, reusing cached image when playback frame hasn't changed
- Encoding offloaded to a daemon thread so UI stays responsive during GIF/MOV assembly
- Intermediate frames saved as JPEG quality 95 (~10 ms/frame) instead of PNG (~100 ms/frame)
- Minimum 1 ms sleep per tick prevents event-loop starvation when frame capture exceeds `1/fps`

### Fixed

#### Launch Mode wizard
- **Back navigation**: clicking Back from any downstream step (run SAGE26, par edit, compile failure) now correctly returns to the main menu instead of the Start Fresh submenu
- UI text: "Edit the file below" → "Edit the file to the right" (par editor is side-by-side); "Running SAGE26 — output streams below" → "Running SAGE26 — output follows"
- Layout: terminal card `max-width` dynamic (1100 px solo, 860 px with par editor); choice buttons scroll within `max-height:120px`; buttons shrink to `x-small` when more than 5 choices
- xterm.js CDN entries and `wiz_active` state initialisation fixed — terminal was blank on launch via `./sage-viewer` with no `--par` flag

#### Draw Box / Draw Sphere widget placement
- Both widgets now appear centred on the camera focal point at field-of-view-appropriate size
- Box widget handles restored to constant size after each drag via `EndInteractionEvent` observer

#### Double-click galaxy selection accuracy
- Two-stage selection: find 50 nearest galaxies in 3D (KDTree), then project to screen and pick the visually closest
- Respects environment checkbox state and `_combined_mask()` so only visible galaxies are selectable

#### Trame / rendering
- `view_update()` called after `plotter.render()` in box-switch and toggle handlers so new frames reach the browser immediately
- FoF satellite→central links respect active halo filter mask, focus region, and halos-visible toggle
- Playback frame cache keyed on a `_scene_hash()` covering all filter, visibility, colormap, and focus state — cached frames never replayed after scene changes

---

## [0.3.0]

### Added

#### Embedded shell console
- Real shell via `asyncio.create_subprocess_shell`; globs, pipes, redirects, backgrounding all work
- `cd`, `pwd`, `export` handled as in-process built-ins
- Python REPL mode; SAGE natural-language command mode
- Multiple sessions, Load Script, Pop-out floating card

#### Tab-aware Focus button
- Focuses on whatever is active in the current tab (target galaxy, environment halo, coords point, or box region)

#### Dynamic colour-by dropdowns
- Only modes whose underlying field is present in the loaded model appear; rebuild automatically on model switch

#### Library tab — per-row delete
- Red trash button permanently removes the file from disk and refreshes the list immediately

#### Filter active-only architecture
- Filters only take effect when moved from full-range defaults; all galaxies visible at startup

#### Double-click everywhere
- Picker globally on; double-click populates Target tab fields and draws the red marker

#### Switching-models overlay
- Cyan-bordered overlay covers the viewport while a model is loading; rotating quip shows server is alive

### Changed
- Toolbar re-arranged: hamburger left, transport + controls right
- Right panel locked at 300 px, never scrolls
- Indicators persist across tab switches
- Structure mode simplified to three layers (outer envelope, cold-gas envelope, property shell)
- All Unicode super/subscripts replaced with ASCII across user-visible strings
- Full still-quality rendering at all times (no interactive quality reduction)

### Fixed
- Galaxy filters silently excluding low-mass galaxies — active-only architecture resolves this
- Double-click could select invisible (filtered / out-of-focus) galaxies
- Snapshot-slider crash when focus mask and filter mask have different lengths after snapshot change
- Pop-out console now actually draggable (static asset replaces inline `<script>` stripped by Vue 3)
- FoF links hidden for halos that don't pass active filters or focus region

---

## [0.2.0]

### Added

#### Multi-model support
- Scan `<sage_root>/output/` for subfolders; switch primary model from hamburger menu
- Overlay a second compatible model (same box size + snap count)
- Loading overlay + compatibility-error snackbar

#### Filters tab
- Halo filters: Mvir, Rvir, Vvir
- Galaxy filters: stellar mass, sSFR, B/T, age, BH mass, ICS mass, Type, FFB regime, CGM/Hot regime
- Reset Filters button; filters auto-disable for fields not present in the loaded model

#### Environment tab
- Halo selector + Group Info card + Highlight Members (cyan splats on FOF members)
- Field / Isolated / Group / Cluster environment-class checkboxes

#### Target tab additions
- Galaxy Info card; Highlight Galaxy toggle; Clear Indicator button

#### Structure render mode
- Multi-layer galaxy splats: cold-gas envelope (blue), outer envelope (CGM green / Hot red), property shell
- Colormap expanded to 27 maps; inline colorbar beneath each selector

#### Record tab
- Screenshots (PNG / JPG / TIFF); movies (GIF / MOV / PNG sequence)
- FPS slider, resolution selector (Native / 2× / 4×), per-session output folder

#### Camera
- Centre button; Camera bookmarks (save, restore, delete)

### Self-contained HDF5 metadata
- Cosmology, box size, and snapshot redshifts read from `model_0.hdf5` — `.par` file only needed for tree paths

### Rendering overhaul
- World-space gaussian splats (`vtkPointGaussianMapper`) with per-point `radius` array
- In-place PolyData updates across snapshot transitions

---

## [0.1.0]

### Added — Initial release
- PyVista + Trame stack (Vue 3 frontend)
- `io/` layer: lhalo_binary halo reader, SAGE HDF5 galaxy reader, snapshot table, par file parser
- `scene/` layer: Scene, HaloLayer, GalaxyLayer, CameraController
- `parallel/` loader with prefetch pool and LRU snapshot cache
- `sage-viewer` CLI entry point
- miniMillennium and microUchuu support
- Play / Pause / Stop / Reverse / Repeat transport; speed selector; snapshot slider
- Fly to halo, galaxy, coordinates, or sub-box; Focus mode; Camera bookmarks
- MkDocs Material documentation; GitHub Actions CI and docs deployment

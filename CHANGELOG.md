# Changelog

All notable changes to SAGE-Viewer are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.1.2] — dev (unreleased)

### Fixed

#### Recording — playback smoothness (root-cause investigation, two-session fix)

This section documents a chain of bugs that were introduced and resolved over two sessions.
The full causal chain is recorded here so it is not repeated.

**Stage 1 — original symptom:** Recording during snapshot playback was choppy because
`_record_loop` captured the pre-rendered overlay JPEGs and duplicated each 3 fps frame to
fill the 30 fps output.  Fix: dedicated VTK capture path reads directly from the render
window via `_vtk_to_pil()`.

**Stage 2 — double-play regression:** After the Stage 1 fix, recordings played through the
snapshot sequence twice when `is_repeat` was enabled.  Root cause: `_record_loop` followed
`state.snap_num`, which `_image_playback` loops indefinitely on repeat.  Fix: introduced
`_pb_order` — a one-pass list built from the starting snapshot to the last snapshot — and
`_pb_done` flag that stops capture after the list is exhausted.

**Stage 3 — live-recording slowdown:** With a 30 fps recording active, moving the camera on
a single snapshot (no playback) became sluggish.  Root cause: `_vtk_to_pil()` calls
`rw.SetOffScreenRendering(1)` + `rw.Render()` every recording tick, blocking the asyncio
event loop at 30 Hz and competing with interactive rendering.  Fix: added
`_vtk_to_pil_passive()`, which reads the last completed framebuffer via
`vtkWindowToImageFilter` with `ShouldRerenderOff()` / `ReadFrontBufferOff()` — no extra
`Render()` call.  Live recording with no rotation now uses the passive path; rotation and
snap changes still use `_vtk_to_pil()`.

**Stage 4 — rotation double-step:** Both `_rotate_loop` (toolbar.py, 12 Hz) and
`_record_loop` applied a camera rotation per tick.  Result: rotation rate doubled during
recording.  Fix: `_rotate_loop` checks `state.recording_active` at each tick and skips both
the rotation step and the `_push()` call when True.  The recording loop owns all camera
movement while a recording is active; `_rotate_loop` resumes ownership when recording stops.

**Stage 5 — playback smoothness regression (this session):** After Stage 2–4, playback
recordings were choppy again at any FPS.  Root cause had two independent components:

- *Pre-render phase interference:* `playback_active=True` is set by `_render_frames()` as
  soon as the first frame is pre-rendered, which is well before `_image_playback()` starts.
  Because `_record_loop` started its `_pb_order` pass the moment it saw
  `playback_active=True`, `_pb_idx` advanced through 10–30 snaps during the pre-render
  phase (several seconds at 30 fps).  When `_image_playback` finally started, recording
  was already deep into the sequence and the camera angles were mismatched (pre-render
  restores the camera to its starting position at the end; recording had already baked in
  extra rotation from the pre-render window).

- *PIL caching eliminated VTK temporal variation:* The Stage 3 optimisation cached the raw
  PIL image for frames where neither snap nor rotation changed (up to 9 out of every 10
  frames at 1× speed without rotation).  VTK's MSAA jitter produces subtly different renders
  on successive `Render()` calls for the same scene; caching the PIL bypassed this and
  produced runs of byte-identical frames that the human eye perceives as harder / choppier
  than renders with natural inter-frame variation.

  **Final fix:** Replaced `_pb_order` with overlay-driven `state.snap_num` tracking plus a
  `prerender_busy` guard that holds capture until `_image_playback()` is actually running.
  Removed all PIL caching in the playback path; every recording frame now calls
  `_vtk_to_pil()` (force render).  One-pass detection uses end-snap rollover: when
  `state.snap_num` reaches `_pb_end_snap` the `_pb_at_end` flag is set; when `snap_num`
  subsequently changes away from the end snap (repeat wrap-around), `_pb_done` is set and
  capture stops.  `is_repeat=False` (default) still terminates naturally when
  `playback_active` goes False.

**Key invariant for future work:** `playback_active=True` does NOT mean `_image_playback()`
is running — it is also True during `_render_frames()` pre-render.  Always gate playback
recording on `prerender_busy=False`.

#### Recording — reset camera not showing all structure

`on_reset()` called `scene.camera.focus_on_boxes()` then `_sync_fof_layer()`, which
shows/hides FoF-link actors.  `scene.plotter.renderer.ResetCameraClippingRange()` was called
before the visibility change, so near/far clipping planes were computed against the wrong
actor set and some geometry was clipped out of view.  Fix: moved
`ResetCameraClippingRange()` to after `_sync_fof_layer()`.

#### Recording — galaxy/group info card absent from output frames

The Galaxy Information and Group Information overlay cards were being composited during
screenshots but not during recording.  Root cause: `_composite_overlays()` was accidentally
dropped from `_save_frame()` during a `_record_loop` refactor.  Fix: re-added
`_composite_overlays(raw).save(...)` as the final step of `_save_frame()` so every captured
frame, regardless of recording mode, has the same overlay compositing as a screenshot.

Note: highlight markers (Highlight Galaxy / Highlight Members) are baked into the
pre-rendered frames via `_render_frames()` and are therefore always present in recordings.
Info cards are composited separately from current `state` at capture time.

#### Launch Mode terminal — persistent 1-row sliver (root-cause investigation)

Three successive fixes were required before the sliver was eliminated.  The full history is
recorded here to avoid re-treading the same ground.

**Attempt 1 — height guard:** `_initWizTerm()` polled until `container.offsetWidth > 0` but
did not check height.  In the VCard's `display:flex;flex-direction:column` layout, height
resolves after width, so the poll could pass with `offsetHeight=0`.  `fitAddon.fit()` then
called `getComputedStyle(container).height` → "0px" → 0 rows → 1-row sliver.
Fix: added `container.offsetHeight < 50` to the poll condition.

**Attempt 2 — requestAnimationFrame:** Even with the height guard passing (container had a
real height), the sliver reappeared after server hot-restarts.  Root cause: `fitAddon.fit()`
was called synchronously after `term.open()`, before xterm.js had completed its first
browser paint cycle and measured character cell dimensions (`actualCellHeight` was 0).
`fitAddon.proposeDimensions()` returns `undefined` when cell height is 0; `fit()` silently
no-ops; the terminal keeps its default 1-row height.  Fix: moved the first `fit()` call into
a `requestAnimationFrame` callback (after the initial paint) with 150 ms and 500 ms deferred
re-fits as insurance.

**Attempt 3 — CSS grid (final fix):** The sliver persisted through Attempt 2 because the
root cause was not timing but layout: `display:flex;flex-direction:column` with `flex:1` on
the terminal div does not always produce a pixel height readable by `getComputedStyle()` at
the moment xterm.js needs it — the browser may report `height:auto` for flex children under
certain conditions.  `fitAddon.proposeDimensions()` calls `parseInt(height)` on that value,
which returns `NaN`, causing `fit()` to bail silently.

  **Final fix:** Changed the VCard from `display:flex;flex-direction:column` to
  `display:grid;grid-template-rows:1fr auto`.  The terminal div occupies the `1fr` row and
  the action bar occupies the `auto` row.  CSS grid always resolves grid track sizes to
  explicit pixel values before layout completes — `getComputedStyle(terminal).height` is
  always a number, never `"auto"`.  `fitAddon.fit()` reliably reads the correct height
  regardless of when it is called.  The `offsetHeight < 50` poll guard and
  `requestAnimationFrame` deferral are retained as belt-and-suspenders.

  **Rule for future layout changes in the Launch Mode card:** the terminal container
  (`sage-wiz-pty`) must always sit in a CSS context that resolves its height to an explicit
  pixel value — grid `1fr`, absolute with known `top`/`bottom`, or an explicit `height:`.
  Do not use `flex:1;min-height:0` as the sole height source for an xterm.js container.

---

## [1.0.9] — 2026-06-22

### Fixed

- GIF recordings no longer show visible contour lines around gaussian splat points — switched from `imageio` (no dithering) to PIL's native GIF writer with Floyd-Steinberg dithering, which distributes colour quantisation error across neighbouring pixels and produces smooth gradients instead of hard bands

---

## [1.0.8] — 2026-06-22

### Added

- **Galaxy Info and Group Info panels now appear in screenshots and recordings** — the info card is composited as a PIL overlay (matching its on-screen position at top-right) whenever it is visible at capture time, same technique already used for the console pop-out and library cards
- **Highlight actors (Highlight Galaxy / Highlight Members) now appear in playback recordings** — the pre-rendered frame cache is invalidated whenever the indicator state changes, so pressing Play after adding highlights always re-renders with them included

### Fixed

- Screenshots taken while **not** in playback no longer use a stale pre-rendered JPEG from a previous playback session; they always capture the live VTK render window

---

## [1.0.7] — 2026-06-22

### Fixed

- Library tab now scans `sage_library/` and `sage_outputs/` relative to the **working directory** instead of the package install location — items are found correctly when installed via `pip`
- `sage_library/` folder is created in the working directory on startup (alongside `sage_outputs/`)
- `./sage-viewer` launcher now finds whichever Python version has `trame` installed, instead of assuming the shell's default `python3` — fixes failures on macOS where multiple Python versions coexist

---

## [1.0.6] — 2026-06-22

### Fixed

- Screenshots, recordings, GIFs, and catalogue exports now save to a `sage_outputs/` folder in the **current working directory** rather than inside the Python package installation (a `site-packages` subfolder), which made them inaccessible when installed via `pip`
- `.par` template no longer contains hardcoded personal paths — `OutputDir`, `SimulationDir`, and `FileWithSnapList` are now filled in dynamically from the detected or cloned SAGE26 directory
- README: replaced 47 MB and 13 MB embedded GIFs (which overran PyPI's image proxy) with text links to the animated demos on GitHub

### Added

- Launch Mode wizard: **Clone SAGE26** step now prompts for the parent directory (defaults to home folder) before cloning, so pip-installed users can choose where SAGE26 lands rather than having it hardcoded relative to CWD

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

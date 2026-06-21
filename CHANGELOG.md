# Changelog

All notable changes to SAGE-Viewer are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased] — post-0.3.0 (wizard + library + HPC)

### Added

#### HPC install script (`install_hpc.sh`)
- New `install_hpc.sh` script at the repo root creates a Python venv and pip-installs SAGE-Viewer in editable mode (`-e`) in one step
- Checks Python ≥ 3.10; prints a clear error if the version is too old or `python3` is not in PATH
- Accepts an optional positional argument to place the venv on a fast scratch filesystem (`./install_hpc.sh /scratch/$USER/sage-env`)
- Checks for `ffmpeg` separately and prints a `module load ffmpeg` hint if absent
- Editable install means `git pull` updates the code immediately with no reinstall

### Fixed

#### Launch Mode wizard — navigation
- Clicking **Run SAGE26** from the main menu then **Back** from any downstream step (pick par, par edit, compile failure) now correctly returns to the main menu instead of the Start Fresh submenu
- Fix: `self._back` instance variable set to `"back_main"` at the top of `_step_run_sage26_existing` and `"back_fresh"` at the top of `_step_fresh_choice`; all Back buttons in `_step_compile`, `_step_pick_par`, `_step_create_par`, `_step_par_edit`, and `_step_run_sage26` use `self._back` instead of the hardcoded `"back_fresh"`

#### Launch Mode wizard — OutputDir creation
- SAGE26 does not create its `OutputDir` itself and will fail if it does not exist
- Wizard now parses `OutputDir` from the saved par file via `parse_par()` and calls `Path.mkdir(parents=True, exist_ok=True)` before launching the binary; emits `"Output dir ready: <path>"` in green or a yellow warning if mkdir fails (non-fatal)

#### Launch Mode wizard — UI text
- "Edit the file below" → "Edit the file to the right" (par editor is side-by-side, not below)
- "Edit the paths below" → "Edit the paths to the right"
- "Running SAGE26 — output streams below" → "Running SAGE26 — output follows"
- No-par-files hint reworded to "Use 'Create config file' below, or add a .par file to SAGE26/input/ and rescan"

#### Launch Mode wizard — layout
- Terminal card has `overflow:hidden` so it never busts out of its `640 px / 80 vh` container
- Choice button area capped at `max-height:120px; overflow-y:auto` so many buttons never push terminal content out of view
- Terminal card `max-width` is now dynamic: `1100 px` when the par editor is hidden (solo), `860 px` when side-by-side
- Choice buttons shrink to `x-small` when there are more than 5 choices (many models), `small` otherwise
- SAGE logo reduced from `140 px` to `90 px`

#### Library pop-out — close reliability
- `on_library_close_item` previously read `state.library_items` back from the Trame state proxy, which can be stale after multiple mutations
- Fix: authoritative `_lib_items: list[dict]` Python list as source of truth; close mutates `_lib_items[:]` directly and rebuilds `state.library_items` from it

#### Library pop-out — stacking
- All pop-out cards were hardcoded to `top:32px; right:24px` regardless of the `top_px` field calculated in Python — every card opened on top of the previous one
- Fix: each new card gets `top_px` and `right_px` computed from the current open count (`idx = len(_lib_items)`) with a diagonal cascade (50 px down + 44 px left per card, wrapping at 6); Vue template uses a JS template literal so both values are reactive

#### Library pop-out — GIF restart
- Browsers (especially Chrome) cache GIF animation state by URL; reopening the same GIF continued mid-animation rather than from frame 0
- Fix: GIF data URLs get a unique `#N` fragment (`data:image/gif;base64,...#3`) on each open — the fragment makes the URL string distinct so the browser discards the cached animation; PNG/JPG/TIFF/MOV unaffected

#### Console PTY session cleanup
- Shell processes spawned by console sessions were never killed on app shutdown (Ctrl+C) — left as orphans
- Fix: `atexit` handler `_kill_all_ptys()` registered in `navigation_panel.py` immediately after `_consoles_data` is created; iterates all sessions and calls `close()` on any live PTY
- `_PTYSession.close()` upgraded from `proc.terminate()` (SIGTERM, ignorable) to `proc.kill()` (SIGKILL)

---

## [Unreleased] — post-0.3.0 (draw widgets + recording fixes)

### Fixed

#### Draw Box / Draw Sphere widget placement
- Both widgets now appear centred on the camera focal point (what the user is currently looking at) when first placed, sized to the current field of view — previously they appeared at stored field-bound coordinates which could be off-screen
- Box half-extent = 50 % of the visible half-width at the focal plane (`d * tan(FOV/2) * 0.5`); sphere radius = 25 % of the same value
- Placement also updates the corresponding nav state fields (`nav_x/y/z/distance` for sphere, `nav_box_*` for box) so Locking without dragging still navigates to the correct position

#### Draw Box handle size
- Box widget handles (the seven spheres used to resize/translate the box) were being rescaled by VTK's internal `SizeHandles()` on every Scale/Translate interaction, causing them to jump to a different world-space size after each drag
- `SetHandleSize()` has no visual effect in VTK 9.5 and is not the fix; `GetRepresentation()` does not exist on `vtkBoxWidget` (only on `vtkBoxWidget2`)
- Fix: snapshot the `vtkSphereSource` objects backing the handle actors at placement time, then restore their radius directly via `EndInteractionEvent` and camera `ModifiedEvent` observers — handles stay constant-sized at any zoom or after any drag

#### Removed orphaned file
- `sage_viewer/scene/heatmap_layer.py` deleted — file had no imports and no UI wiring

#### Movie recording
- Fixed FPS not being honoured: the loop previously wrote one frame per snapshot change regardless of target FPS; slow playback (e.g. 0.25x) produced one frame per snapshot instead of `fps * seconds_per_snapshot` frames, making all recordings play back at the same speed. Fix: write a frame every `1/fps` seconds, reusing the cached decoded image when the playback frame has not changed
- Fixed UI freezing during recording: when frame capture took longer than `1/fps` the sleep collapsed to zero with no `asyncio.sleep` call, starving the event loop so Stop/Pause clicks were never processed. Fix: minimum 1 ms sleep per tick
- Fixed UI freezing on Stop: `_finalize_movie()` (imageio GIF encode / ffmpeg MOV encode) was called synchronously inside the Trame controller, blocking the UI for the full encode duration. Fix: finalize now runs in a daemon thread; UI shows "Encoding…" immediately and updates to the output path when done
- Fixed slow frame capture: intermediate frames were saved as PNG (lossless, ~100 ms per frame) making 30 FPS impossible on typical viewport sizes. Fix: intermediate frames saved as JPEG quality 95 (~10 ms per frame); output quality is unaffected since GIF and H.264 are both lossy encoders

---

## [Unreleased] — post-0.3.0 (side-by-side multi-box comparison)

### Added

#### Side-by-side multi-box comparison
- Load two or more SAGE models side-by-side via `+SBS` in the hamburger Models section
- Boxes are laid out along the X axis with a 30 % gap between them
- Each box is fully independent: its own snapshot, filters, colormaps, opacity, layer visibility, and rendering settings are saved and restored whenever the active box changes (`BOX_PROFILE_KEYS` — 56 keys in `scene/box_profile.py`)
- A **box strip** at the bottom of the viewport shows all loaded boxes; clicking a box makes it active (green label) and routes the entire right panel to it
- Active box label rendered with `vtkBillboardTextActor3D` (always faces camera, no anchor dot) — green for active, white for idle; format: `{model name}  z={redshift:.2f}`
- Play, step, and snapshot slider advance **only the active box's snapshot** — other boxes stay at their current snapshot
- Rotation selector greyed out in multi-box mode; any active rotation is cancelled when a second box is added (all boxes share one camera — independent rotation is not supported)
- Toolbar snap-count cache synced to the active model on every box switch so step/play use the correct range
- Adjacent boxes always initialise with defaults (Mvir / viridis for halos, Structure / plasma for galaxies) so they don't inherit the primary box's settings

#### Halo Mvir colormap lock
- Selecting Mvir as the halo colour mode forces the colormap to **Viridis** and greys out the colormap selector — Mvir always uses the same scale for visual consistency across boxes

#### Background snapshot preloading
- All snapshots are preloaded into memory in background threads immediately on startup and whenever a model is added as an adjacent box or overlay
- KDTree for nearest-halo search is pre-built per snapshot in the background loader thread; stored in `_tree_cache` and passed directly to `update_halo_index()` — eliminates per-click KDTree build delay

### Fixed

#### Double-click galaxy selection accuracy
- Two-stage selection: find 50 nearest galaxies in 3D (KDTree), then project to screen pixels and pick the visually closest — eliminates the off-by-one click that selected a galaxy behind the cursor
- Environment checkbox state is respected: when `_combined_mask()` returns `None` mid-transition, falls back to `_filter_mask` instead of querying all galaxies
- Halo search uses the selected galaxy's world position as the query point (not raw click coordinates), and respects `halo_layer._combined_mask()` — keeps halo + galaxy from the same environment

#### Launch Mode wizard terminal
- xterm.js CDN (xterm 5.3.0 + FitAddon 0.10.0) was missing from `launch.py` — terminal appeared blank when launched via `./sage-viewer` with no `--par` flag; fixed by adding `server.enable_module` CDN entries
- `wiz_active` state was never set in `launch.py`; xterm JS polls for this variable changing to `True` to mount — fixed by explicitly setting `server.state.wiz_active = True` after `WizardController` creation
- Wizard terminal text colour changed from dark grey to white

#### Trame / rendering
- CLR button in box strip used `$ctrl.clear_box()` (not accessible in Trame 3 Vue templates via `raw_attrs`); replaced with `click=(server.controller.clear_box, "[b.name]")` binding
- `shape="none"` (string) in `add_point_labels` raises `ValueError`; labels replaced with `vtkBillboardTextActor3D` which has no shape artifact
- After `plotter.render()` in box-switch and toggle-adjacent handlers, `server.controller.view_update()` is now called so the new frame reaches the browser immediately (was invisible until the next mouse event)
- `on_set_active_box` signature change (added `extend` bool) broke `info_panel.py`'s direct `ctrl.set_active_box(name)` call — fixed by keeping signature as `on_set_active_box(name)` after multi-select was removed

---

## [Unreleased] — post-0.3.0 (PTY terminal + Launch wizard + UI polish)

### Added

#### PTY-backed xterm.js terminal (Console tab)
- Terminal mode replaced with a real PTY (`pty.openpty()`) + daemon reader thread; output is pushed to the browser via `state.pty_out_seq` / `pty_out_data` (base64) and rendered by xterm.js
- Full ANSI colour, cursor movement, and interactive programs (`vim`, `top`, `htop`, `less`) all work
- JS → server relay uses a hidden `<input v-model>` + native DOM setter to trigger Vue reactivity — the only reliable keypress path in Trame 3
- Python REPL mode removed; terminal mode covers all scripting needs via the shell
- Console command mode renamed: **SAGE Commands** (was "sage" / "nl")

#### Launch Mode wizard (`sage_viewer/wizard/`)
- New wizard package: `controller.py` (async step machine + state), `launch.py` (entry point), `ui.py` (Trame/Vuetify layout)
- Step chips in the header track progress — cyan = current, green = done, white = pending
- **Rescan** button restarts the environment scan from the beginning
- **Create config file** option writes a new `.par` from the built-in millennium.par template; user chooses the output filename via an inline text field
- Par file editor appears in a side-by-side panel alongside the terminal when a `.par` needs editing; panels share the available width equally; terminal remains centered when the par panel is hidden
- Wizard always resets cleanly when opened from Explore Mode (dedicated `open_wizard` controller — avoids Trame's value-reactive `@state.change` limitation that would skip the reset if `wiz_active` was already `True`)
- SAGE26 logo pinned to the bottom-right corner of the wizard screen

#### Heatmap layer (`scene/heatmap_layer.py`)
- 2D projected density heatmap of haloes; number/mass mode; 256-bin grid; configurable projection axis

### Changed

#### UI — global
- Toolbar background forced black (`tb.color = "#000000"`, `tb.elevation = 0`)
- Right panel outer VSheet background black (`#000000`)
- Footer hidden entirely (`height=0`, `display:none`) — `build_info_panel` is still called for the double-click picker wiring
- Both VMenu dropdowns (Launch Mode, Explore Mode) auto-dismiss after a selection (`close_on_content_click=True`)
- Dropdown list backgrounds transparent (`bg_color="transparent"`)
- Theme CSS now served via `server.enable_module` (`sage_static/sage_theme.css`) for reliable page-head injection

#### UI — Filters tab
- All 42 range sliders scaled down (`transform:scale(0.65)`) to reduce vertical space, with `margin-left:-12.5%` to re-centre each slider within its panel column
- Filter section scroll container has `overflow-x:hidden` to prevent horizontal scrollbar from appearing
- Slider labels and section headings centred (`text-align:center`)

#### UI — Structure tab
- Halo and galaxy visibility toggles changed from `VSwitch` to `VCheckbox`

#### UI — Export catalogue dialog
- Card background transparent; CSV / HDF5 / FITS / TXT format buttons have black backgrounds

#### UI — input fields
- "Enter to…" hint suffix removed from all input labels (Galaxy idx, screenshot label, recording label, console command mode label)

#### Library tab
- Pop-out cards are browser-resizable (`resize:both; overflow:auto` on the card container)

---

## [Unreleased] — post-0.3.0 (continued)

### Added

#### Streaming shell output
- Shell commands in the Console tab now stream output line-by-line as they run — long-running commands update the history entry in real time instead of waiting until the process exits
- Implemented via `asyncio.create_subprocess_shell`; stdout+stderr are merged and the history entry is patched on every received line

#### Threaded Python REPL execution
- Python REPL `exec` is offloaded to a thread via `asyncio.to_thread` so the Trame event loop stays responsive during long-running scripts — previously the UI froze until the script returned
- Script loading (`Load Script` button) uses the same thread-offload approach

#### Dynamic colour-by dropdowns
- Halo and galaxy "Colour by" selectors now only show modes whose underlying field is actually present in the loaded model (checked against `model_fields`)
- Dropdown lists rebuild automatically when the primary model is switched

#### Library tab — per-row delete button
- Each row in the Library file list now has a red delete (trash) button that permanently removes the file from disk and refreshes the list immediately

### Changed

#### Colour scheme
- **Filters tab**: DARK MATTER HALOES section header and all seven halo range sliders use purple (`#c084fc`); GALAXIES and CATEGORICAL headers and all galaxy range sliders use gold (`#FFD700`)
- **Environment tab**: HALO section header and its Go button use purple (`#c084fc`); ENVIRONMENT FILTER header and all five environment-class checkboxes use cyan
- **Target tab**: Highlight Galaxy button uses gold (`#FFD700`); Group Info and Highlight Members buttons use purple (`#c084fc`)

#### Snapshot step buttons
- Previous / next snapshot buttons rendered without any border, background, outline, or box-shadow in any interaction state (hover, focus, active)
- Buttons flash cyan on press and return to white after 300 ms — implemented via inline `onmousedown` JS so the flash overrides Vuetify's `!important` CSS rules that CSS animations cannot

#### Halo default opacity
- Default halo layer opacity changed from 0.15 → 0.12

### Removed

- **Density colour mode** removed from both halo and galaxy "Colour by" dropdowns — `scipy.stats.gaussian_kde` computation was slow and not physically meaningful; all other colour modes are unaffected

### Fixed

- Filter section thumb label bubbles were clipped by `overflow-x:hidden` on the scrollable section container, and there was no top padding to give the topmost slider's label room — removed the overflow restriction and added `padding-top:18px` so labels appear fully at all scroll positions
- Thumb label bubble width was too narrow for values like `−14.0` or `10000` — `min-width` raised to `4em` and `white-space:nowrap` added so the full numeric value is never truncated
- Library tab caused a Vue template compile error (blank/black page) due to three issues: `html.Template` used instead of `v3.Template` for slot content; `v_else=True` generating `v-else="True"` (Vue's `v-else` directive takes no value); `v_model` bound to a compound expression (`entry.rename_val || ''`) which Vue 3 cannot assign to — replaced the entire slot structure with plain `html.Div` flex rows

---

## [Unreleased] — post-0.3.0 (draw widgets + step polish)

### Added

#### Interactive draw widgets — Coords and Box tabs

- **Draw Sphere** button in the Coords tab places two draggable handle balls in the 3D viewport:
  - *Centre ball* — drag to translate the sphere; fields (X, Y, Z) update live as you drag
  - *Edge ball* (+X from centre) — drag toward or away from centre to resize; Standoff updates live
  - The sphere is rendered as five great-circle rings (1 equatorial + 4 meridionals at 0°, 45°, 90°, 135°) — identical in style to the indicator that appears on a normal Coords Zoom
  - Both balls and rings track each other in real time (`interaction_event='always'`)
  - Button turns orange and reads **Lock Sphere**; clicking it removes the widget and runs Zoom so the locked sphere becomes the active focus region
- **Draw Box** button in the Box tab places a native `vtkBoxWidget2` with corner and face handle balls:
  - Drag any handle to translate or resize; all six min/max fields update live
  - Button turns orange and reads **Lock Box**; clicking it removes the widget and runs Zoom so the locked box becomes the active focus region
- **Clear** button appears at the bottom of both Coords and Box tabs while a draw widget is active; cancels the widget without committing or navigating
- Both draw widgets are cleared automatically on Reset Camera, Focus toggle (off), and model switch
- Initial sphere radius is `min(Standoff × 0.25, 3.0)` Mpc/h; initial box is 50 % of the current field extents from centre — both intentionally small so you can grow to taste

#### Model switch always lands at z=0

- `scene.switch_primary()` always sets `snap = snap_count − 1` (z=0 of the new model) instead of clamping to the previous model's snapshot position
- `on_switch_model` in `app.py` explicitly syncs `snap_num`, `snap_max`, and `snap_label` in its `finally` block so the slider and snap chip reflect z=0 of the new model immediately, even when `snap_num` didn't change numerically

### Changed

- Coords tab **"Go" button renamed to "Zoom"** — consistent with the Box tab

---

## [Unreleased] — 0.3.0

### Major additions

#### Embedded shell console (terminal in a tab)
- The Console tab is now a real terminal — every command runs through
  the user's `$SHELL` via `subprocess` with the per-session `cwd` and
  `env`, so globs, pipes, redirects, `&` backgrounding, and `$VAR`
  expansion all work
- `cd <path>`, `pwd`, and `export FOO=bar` handled as in-process
  built-ins so they survive between commands
- macOS-style prompt: `host:basename user$` (e.g. `G2YYHL4LCN:SAGE-Viewer mbradley$`)
- 300 s timeout per command (background long jobs with `&`)
- Type `python` / `python3` / `py` to drop into an embedded Python REPL
  whose locals expose `scene`, `state`, `ctrl`, `server`, `plotter`,
  `np`. Type `exit` / `quit` / `shell` to return.
- Type `sage` / `nl` / `natural` to enter natural-language mode for the
  existing SAGE command parser (`show only clusters`, `go to halo 42`,
  `snap 30`, `screenshot`, etc.)
- **Multiple sessions**: tab strip with one button per console + a `+`
  to spawn new ones; each session has its own history, mode, cwd, env,
  and Python interpreter
- **Load Script** button reads a `.py` path from the script field and
  `exec`s it in the session's Python locals — useful for plotting and
  test scripts on HPC
- **Pop-out** button floats the console over the viewport in a movable
  card (drag by the title bar) so you can keep typing while watching
  the render
- Console fills most of the right panel; type-command + script-path
  inputs and the four action buttons (Run, Clear, Load Script, Pop-out)
  are anchored at the bottom

#### Tab-aware Focus button
- Focus icon now does the right thing based on the active tab:
  - **Target** → focus on the current galaxy at `nav_gal_last_radius`
  - **Environment** → focus on the current halo at `nav_distance`
  - **Coords** → focus sphere at `(nav_x, nav_y, nav_z)` of `nav_distance`
  - **Box** → focus on the current axis-aligned sub-box
  - Other tabs → re-apply the last established focus region
- Turning Focus OFF always just clears, regardless of tab

#### Double-click everywhere
- Picker is now globally on, not just in Target / Environment
- A double-click anywhere populates `nav_halo_idx` + `nav_gal_idx`,
  switches to the Target tab, and draws the red marker on the picked
  galaxy
- If Focus is already active when you double-click, the camera carries
  to the new selection at the last-used radius

#### Switching-models overlay
- A cyan-bordered "SWITCHING MODELS, PLEASE HOLD..." card now covers
  the viewport whenever a model is being loaded or swapped
- A rotating italic quip refreshes every 2.5 s so the user knows the
  server is still alive

### UI polish

- **Toolbar re-arranged**: hamburger + SAGE-Viewer title clustered on
  the LEFT; transport + slider + snap chip + speed + rotation all
  clustered on the RIGHT, with a single big spacer between
- **Right panel locked at 300 px width**, never scrolls — the panel's
  internal flex layout fits all content per tab
- **Indicators persist across tab switches** — the box wireframe,
  sphere wireframe, member dots, and red galaxy marker no longer get
  cleared when you change tabs; they only clear on explicit user
  action (Reset Camera, Go/Zoom, Clear, Focus toggle)
- **Coords-mode wireframe sphere** (5 great-circle rings, pure lines
  with no vertex markers) drawn when you Go to coords, matching the
  Box mode's wireframe-box convention
- **"Use Current Position" button** in the Coords tab populates X/Y/Z
  + Standoff from the camera's focal point and standoff distance
- **"Use Current View" button** in the Box tab populates the six min/max
  bounds from the camera's current frustum at the focal plane
- **Box-mode Zoom always engages focus** (was conditional on already
  being focused), matching Target / Environment / Coords behaviour
- **Default halo opacity** raised from 0.10 → 0.15

### Enter to run (everywhere)
- Every text field that has a paired action button now also fires
  that button on Enter. Wired across Target (halo Go, galaxy Go),
  Environment (Go), Coords (Go), Box (Zoom), Console (Run, Load
  Script), pop-out console, Record (Take Screenshot, Start Recording).
- Implemented via a global JS handler (`data-enter-click="<btn-id>"`)
  served from `sage_viewer/static/sage_viewer.js` — bypasses Vuetify's
  internal keydown handling for reliability
- The wrapper `<div>` carries the marker via trame's `raw_attrs=`,
  not a plain `data-enter-click=` kwarg: trame only renders attribute
  keys in its allowed-keys set and silently drops unknown ones, so the
  kwarg form never reached the DOM and Enter did nothing

### Galaxy rendering simplified
- Per-galaxy **star scatter removed entirely** — the 15–25 M splat
  draws per frame were the main perf killer at high galaxy counts
  with no spatial-perception payoff
- **BH accretion-disk core layer removed** — visually invisible
  against the surrounding warm-toned splats at typical zoom levels
- Structure mode now renders just three lightweight layers per galaxy:
  outer envelope (CGM/Hot), cold-gas envelope, and the optional
  property-coloured outer shell
- **CGMgas + HotGas as a sized field**: the outer envelope is now
  sized and coloured by `CGMgas` (CGM-regime galaxies) and `HotGas`
  (Hot-regime galaxies). `h2_mass` is no longer consumed by the
  rendering layers (still loaded + shown in the Galaxy Info card).

### Data model
- `GalaxySnapshot` gains `cgm_gas` and `hot_gas` fields (both Msun,
  read as optional HDF5 columns `CGMgas` / `HotGas`)
- Par-file parser now strips `;`, `#`, and `%` as inline-comment
  markers — fixes a parse error on microUchuu's `.par`
  (`BoxSize 100.0 ; ...`)

### Static asset system
- Trame module registered to serve `sage_viewer/static/` at
  `/sage_static/` — needed because Vue 3 silently drops `<script>`
  tags from templates, so all client JS now comes in via real files
- Currently hosts `sage_viewer.js` (pop-out drag handler + Enter-to-
  click handler); new client helpers can drop into the same folder

### Text rendering consistency
- All Unicode super/subscripts replaced with ASCII across user-visible
  strings (`M☉ → Msun`, `yr⁻¹ → yr^-1`, `10¹²·⁵ → 10^12.5`,
  `log₁₀ → log10`, `H₂ → H2`, `Σ → Total`). Avoids font-substitution
  inconsistencies that mixed super- and normal-size glyphs.

### Performance
- All "lower quality during drag" hacks reverted; full still-quality
  rendering is now in effect at all times
  (`interactive_ratio=1.0, interactive_quality=100, still_quality=100`,
  no `SetDesiredUpdateRate(15.0)` toggling during play / rotate /
  mouse drag)

### Galaxy filter active-only architecture

- Every range-slider filter now only takes effect when it has been moved away from its full-range
  default — sliders sitting at both endpoints are completely inert, so every galaxy with a
  detectable mass is visible at startup without touching any slider
- Slider ranges widened to cover the full SAGE26 distribution: stellar mass 0–14,
  sSFR −14–0, cold gas / bulge / BH mass 0–14, SFR / mass-loading −6–5,
  cooling/heating −7–7, disk radius −4–1, metallicities −2–12
- B/T clamping: SAGE can produce BulgeMass > StellarMass for satellites that lost
  stellar mass after a major merger; the computed ratio is now clamped to [0, 1]
  before the filter comparison so these galaxies are never falsely excluded
- Same `_active(lo, hi, mn, mx)` guard used for all ~25 conditional fields (BH mass,
  ICS mass, cooling, heating, disk radius, metallicities, etc.) — off by default,
  engaged only when the user moves a slider

### Visibility-aware galaxy picking

- Double-click now queries only galaxies that are currently visible — the
  `_combined_mask()` from `GalaxyLayer` (intersection of filter + focus masks)
  is used to build a `visible` index array before the KDTree search, so
  environment-class checkboxes, focus regions, and all slider filters are all
  respected: you can only click what you can see
- The hit index from the KDTree is mapped back into the full galaxy array to give
  the correct `gidx`

### Regime-coloured member and selected-galaxy indicators

- **Highlight Members** splats are now coloured by CGM/Hot regime:
  CGM-regime members in dodgerblue, Hot-regime in tomato, unknown/absent in cyan —
  matching the outer envelope colouring used in Structure render mode
- The **selected galaxy** (from Target tab or from Highlight Members) now shows
  a white border ring (36 px, opacity 0.90) with a regime-coloured fill (26 px)
  layered on top — visually distinct from the surrounding group members
- `camera.py` redesigned: `_member_actors: list` and `_selected_actors: list`
  replace the old single `_indicator_actor`; `_clear_member_indicators()` removes
  all per-regime actors at once; `_add_member_indicators(positions, regimes)` groups
  members by regime and draws one mesh per colour

### Library: multi-item movable pop-outs

- Any number of library items can now be open simultaneously — each becomes its own
  independent draggable card floating over the 3D viewport
- **Double-click** a row in the Library file list to open an item (single-click no
  longer opens anything)
- Each pop-out card is draggable by its title bar (same JS drag handler used by the
  console pop-out — `.sage-popout` / `.sage-popout-handle` CSS classes)
- Per-item close (×) on every card; **Close all** button in the Library tab clears
  all open cards at once
- GIF/video always plays from frame 0: `v_if` (not `v_show`) ensures a fresh DOM
  media element is created each time an item is opened — no more mid-stream start
- Videos carry `muted` so browsers permit autoplay without requiring user interaction
- Backend: `state.library_items` list (each entry `{id, name, kind, data_url,
  top_px}`) replaces the old single-item scalar state vars
  (`library_show`, `library_data_url`, `library_kind`, `library_name`)

### Filter-aware FoF links
- FoF satellite→central line segments now respect the active halo filter
  mask, focus sphere/box, and the halos-visible toggle — links for hidden
  or filtered halos are no longer drawn
- `FofLinkLayer.sync_masks(visible_positions)` is the single update point:
  pass `None` when all halos are visible (skips the position lookup); pass
  `snap.positions[combined_mask]` when masking is active
- Central membership is tested by exact float32 byte comparison against
  the visible halo position set — reliable because FoF centrals come from
  the same struct array as `halos.positions`
- FoF links are gated on both `halos_visible` AND `fof_links_on`, so
  toggling either off hides them correctly
- `_sync_fof_layer()` helper in `navigation_panel.py` is called from
  `_apply_filters()` (covers all snapshot and filter changes) and from
  every focus-changing handler — so FoF links stay correct throughout
  playback, recording, and all manual navigation

### Playback frame-cache invalidation
- Pre-rendered frames are now keyed by a `_scene_hash()` fingerprint that
  covers all filter sliders, environment-class checkboxes, layer
  visibility / opacity / color-mode / colormap, FoF visibility, and the
  active focus region — cached frames are never replayed after any of
  these change
- `_SCENE_FILTER_VARS` module constant in `toolbar.py` lists every trame
  state variable name that affects the rendered output; add entries there
  when new filter state is introduced

### Bug fixes
- Galaxy filters were silently excluding all zero-mass and low-mass galaxies:
  stellar mass slider defaulted to [8.0, 12.5], sSFR slider max was −6 (excluding
  all starbursty small galaxies), B/T could reject satellites with BulgeMass > StellarMass.
  Fixed by the active-only architecture above.
- Double-click could select a galaxy that was invisible (filtered or outside focus
  region) — KDTree now restricted to `_combined_mask()` visible indices only.
- Snapshot-slider crash when focus is active and adjacent snapshots have
  different galaxy / halo counts: `_combined_mask()` now returns `None`
  on a length mismatch (focus mask vs filter mask sized for different
  snapshots) so `_redraw()` shows everything unmasked for that one
  intermediate frame instead of raising `ValueError`
- Switching to microUchuu used to crash on `BoxSize 100.0 ; Size of the
  simulation box` — par parser now handles `;` comments
- Tab switches no longer destroy in-progress indicators (box / sphere /
  member dots)
- Sphere indicator no longer renders vertex point-markers along its
  great-circle polylines (explicit `verts` cell clear on the PolyData)
- Pop-out console window is now actually draggable (was broken because
  Vue 3 stripped the inline `<script>` block; now served as a real
  static asset)

---

## [0.2.0]

### Major additions

#### Multi-model support
- Scan `<sage_root>/output/` for subfolders containing `model_0.hdf5`; each is one model
- Switch the primary model from the hamburger-menu dropdown (any box size / snap count)
- Overlay a second compatible model on top of the primary (same box size + snap count) — visualise two SAGE flavours of the same sim simultaneously
- Compatibility-error snackbar pops over the render view when an overlay attempt is rejected
- Loading overlay (`VOverlay` + spinner) covers the render view while a new model is being loaded
- Optional `--par-dir DIR` CLI flag to override the auto-detected `.par` scan location

#### Filters tab
- Halo filters: Mvir (log₁₀ M☉), Rvir (Mpc/h, raw), Vvir (km/s, raw)
- Galaxy filters: stellar mass, sSFR, B/T, stellar age, BH mass, ICS mass, Type, FFB regime, CGM / Hot regime
- All filter widgets shrink proportionally to fit a 300 px panel without scrolling
- Reset Filters button restores defaults; filters auto-disable (greyed out) for any model whose HDF5 doesn't carry the required field
- Galaxy filter masks combine with the spatial focus mask via logical AND

#### Environment tab (new)
- Halo selector (index + standoff) drives a "Go" that flies to the halo and snaps `nav_gal_idx` to the FOF central
- Four checkboxes — Field / Isolated / Group / Cluster — to include/exclude environment classes
- **Group Info** button: opens a semi-transparent right-side card showing FOF-aggregate properties
- **Highlight Members** button: cyan gaussian splats on every FOF group member; toggles on/off; positions cached so re-toggling never drifts even if the snapshot has advanced

#### Target tab additions
- **Galaxy Info** button: opens a right-side panel with per-galaxy properties (semi-transparent card)
- **Highlight Galaxy** button: cyan splat on the picked galaxy (toggle)
- **Clear Indicator** button clears all overlays + closes panels in one go
- Camera flies to 30 Mpc/h standoff and locks a 10 Mpc/h focus sphere when Galaxy Info opens

#### Structure tab additions
- Galaxy "Colour by" expanded: B/T, BH mass, ICS mass, Age in addition to existing options
- New **Structure** render mode — multi-layer galaxies built from gaussian splats:
  - Black core sized by BlackHoleMass
  - Blue cold-gas envelope sized by ColdGas
  - Coolwarm scattered "stellar particles" inside the envelope, count scaled by stellar mass
  - Outer envelope coloured green for CGM-regime / red for Hot-regime, sized by H₂ / cold gas
  - Sparser coolwarm scatter through the outer envelope
- Colormap dropdown expanded to 27 selectable maps (Viridis, Plasma, Inferno, Magma, Cividis, Turbo, Blues, Purples, Greens, Oranges, Reds, Greys, YlOrRd, YlGnBu, BuPu, Hot, Cool, Bone, Copper, Coolwarm, RdBu, Seismic, Spectral, BrBG, Twilight, Jet, Rainbow); halo + galaxy lists are identical
- Reset Opacities button restores per-layer opacity defaults
- Inline colorbar beneath each colormap selector, with min/max labels appropriate to the active colour mode

#### Record tab
- Screenshots in PNG / JPG / TIFF (default PNG button + per-format quick buttons)
- Movie recording: FPS slider (1–60), Resolution selector (Native / 2× / 4× supersampled), Output format selector (GIF / MOV (H.264) / PNG sequence), Loop-forever checkbox for GIF
- Optional user-typed Label; falls back to a timestamp
- One session folder per app launch: `<SAGE-Viewer>/sage_outputs/session_YYYYMMDD_HHMMSS/`; screenshots and movies live alongside each other
- Frame PNGs are deleted automatically after a successful GIF / MOV conversion (kept only for the PNG-sequence format)

#### Toolbar
- Playback speeds: 0.1× / 0.25× / 0.5× / 0.75× / 1× / 2× / 5×
- New rotation selector: Off / CW / CCW at 15° / 30° / 60° per second; rotation runs as an independent asyncio task so play/pause stays responsive
- Snap label chip shows snap number, redshift, and scale factor
- Pause and Stop now genuinely interrupt the play loop (uses `asyncio.Event` + cancellable Task)
- Mode chip removed; the hamburger icon in the top-left opens a dropdown listing every tab AND every discovered model

#### Hamburger menu (top-left)
- Tabs section: every tab navigable from a single dropdown
- Models section: each output-folder name as a clickable row, with a "+ overlay" sub-row for each non-primary model

#### Galaxy & Group Info panels
- Semi-transparent VCard pinned to the top-right of the render view; same position and dismissal button for both
- Mutually exclusive — opening one closes the other (so they never overlap)
- Galaxy panel: GalaxyID, Type, Halo Mvir, Stellar Mass, sSFR, Cold Gas, B/T, BH Mass, H₂ Mass, Gas Regime, FFB Regime, Environment, mass-weighted Approx Age (Gyr)
- Group panel: Classification, member count breakdown, host Mvir, Σ Stellar / Cold Gas / SFR, mean B/T, spatial extent, target role (central / satellite), BCG stellar mass

### Self-contained HDF5 metadata
- New `io/sage_header.py` reads `Header/Simulation` and `Header/Runtime` directly from the `model_0.hdf5` for cosmology (`hubble_h`, `omega_m`, `omega_l`), `box_size`, snapshot redshifts, tree paths, and feature flags
- `load_galaxy_snapshot` and `Model._detect_fields()` now prefer HDF5 metadata over the `.par` file — point at the HDF5 and (almost) everything works

### Data field additions
`GalaxySnapshot` now also carries:
- `bh_mass`, `ics_mass`, `central_mvir`, `h2_mass` (all converted to Msun)
- `ffb_regime`, `cgm_regime` (FFBRegime, Regime int flags)
- `galaxy_id`, `central_id`, `time_of_infall`
- `mean_age` — mass-weighted stellar age in Gyr, integrated from `SFHMassDisk` + `SFHMassBulge` × per-snapshot lookback times via flat-ΛCDM from the HDF5 cosmology

### Rendering pipeline overhaul
- Switched both halo and galaxy layers to **world-space** gaussian splats (`vtkPointGaussianMapper` with per-point `radius` array in Mpc/h) — splats now scale correctly with camera distance
- **In-place data updates**: persistent PolyData + actor across snapshot transitions; only rebuild on colormap / opacity / mode changes, with size-mismatch fallback to a safe full rebuild
- Spurious mid-update VTK renders eliminated (`render=False` on every `add_mesh` / `remove_actor`)
- Rotation/playback drive `vtkRenderWindow.SetDesiredUpdateRate` so VTK picks the fast-path each frame
- Image quality settings tuned for animation: `interactive_ratio=0.75`, `interactive_quality=65`, `still_quality=100`
- Point picker enabled only in Target / Environment tabs; eliminates the per-click ray-cast + render cycle on other tabs
- Near-clipping plane tolerance shrunk so the camera can zoom right inside structures without geometry vanishing

### Selection & indicators
- Galaxy selection now requires a **double-click** (single clicks are pure camera interactions)
- Red gaussian indicator marks the picked galaxy (or the FOF central, when Group Info is open)
- Cyan splats mark group members; member positions are cached on first toggle so re-pressing the button reproduces the same set
- Picker writes both `nav_gal_idx` AND `nav_halo_idx` so the Environment tab's halo field stays in sync with what was double-clicked

### Camera
- New `Center` button next to Focus places the camera at the box centre looking outward
- New `Camera bookmarks` system (Cam tab): save, restore, delete arbitrary camera viewpoints

### UI polish
- Hamburger icon in the top-left opens a dropdown with all tabs + all discovered models
- Tab toggle grid uses `flex-wrap` so all seven tabs render across multiple rows without clipping
- Slider thumb labels appear only while dragging (no longer obscure surrounding labels)
- Tab content scrollbar gutter is always reserved so switching tabs doesn't reflow the render view
- Filter sliders for fields not present in the loaded model are automatically greyed out

### Bug fixes
- Heap corruption when filter masks changed the point count in in-place updates — fixed by checking `cloud.n_points == len(positions)` before re-using
- VtkRemoteView blank-screen on trame-vuetify 3.x — moved Vuetify theme into `vuetify_config=` and removed obsolete `layout.head` block
- Black background when CSS variables for theme weren't applied — fixed by using `SinglePageLayout(vuetify_config=…)` instead of `server.state["$vuetify"]`
- Pause / Stop responsiveness — `asyncio.Event` signalling replaces polled flag
- `state.flush()` removed from per-frame play loop (was doubling round-trip traffic)

### Removed
- The screen-pixel-bucket gaussian rendering path (`_GALAXY_GAUSSIAN_BINS`, `_HALO_GAUSSIAN_BINS`) — superseded by world-space `scale_array`
- The Explore/Gaussian mode toggle (Gaussian is now the only render style)
- The mouse-wheel intercept JS shim (no longer needed in current Trame)

---

## [0.1.0]

### Added — Initial 0.1.0 release
- Package structure with PyVista + Trame stack (Vue 3 frontend, browser-served)
- `io/` layer: lhalo_binary halo reader, SAGE HDF5 galaxy reader, snapshot table, par file parser
- `scene/` layer: Scene, HaloLayer, GalaxyLayer, CameraController
- `parallel/` loader with prefetch pool (joblib threads) and LRU snapshot cache
- `ui/` Trame frontend: toolbar + navigation panel + info panel
- `sage-viewer` CLI entry point with progress messages
- miniMillennium and microUchuu support
- MkDocs Material documentation site
- GitHub Actions CI (lint + tests) and docs deployment

### Data fields
- `HaloSnapshot`: Mvir, plus Vmax read from tree and computed Rvir/Vvir
- `GalaxySnapshot`: StellarMass, Mvir, BulgeMass, ColdGas, SFR, sSFR, Type

### Colour modes
- Haloes: Mvir, Rvir, Vvir
- Galaxies: Stellar Mass, sSFR, SFR, Cold Gas, Bulge Mass, Density, Type
- 14 selectable colormaps per layer (Blues, Purples, Greens, Oranges, Reds, viridis, plasma, inferno, magma, cividis, coolwarm, RdBu, YlOrRd, Spectral)

### Playback
- Async play loop on the Trame asyncio event loop (VTK-safe; no background threads)
- Play / Pause / Stop / Reverse / Repeat transport controls
- Stop always returns to z = 0 (last snapshot)
- Speed selector (1× / 2× / 5×)
- Snapshot slider tracks position during playback

### Camera & navigation
- Fly to halo by index (with standoff distance)
- Fly to galaxy by index (1 / 3 / 5 Mpc/h preset zoom radii, Enter key triggers last used)
- Fly to arbitrary coordinates (x, y, z, standoff)
- Zoom to axis-aligned sub-box
- Reset camera centres on the simulation box midpoint
- Camera centre snaps to box midpoint with explicit `camera_position` triple
- Galaxy zoom places camera at the chosen radius looking inward at the galaxy
- Wireframe indicators: gray box for sub-box, gray sphere for radius/coords/halo,
  small face-on red circle for galaxy targets (always perpendicular to view ray)

### Focus mode
- Toggle button hides all haloes and galaxies outside the active zoom region
- Box and sphere focus regions stored on `Scene` and re-applied automatically
  whenever the snapshot changes (so a region you zoomed to at z=0 keeps masking
  as you scrub back in time)
- Galaxy zooms auto-enable focus

### Mouse interaction
- Left-click any point in the render window selects the nearest galaxy:
  - Galaxy index field in the right panel updates immediately
  - A small face-on red circle is drawn around the target galaxy
- Mouse wheel inside number inputs and slider thumbs is intercepted globally so
  the wheel can no longer accidentally change values (keyboard ↑/↓ still work)

### UI structure
- Trame `SinglePageLayout`: top toolbar, render window fills width, single
  300 px right panel, footer pick-info bar
- Right panel:
  - Reset Camera + Focus toggle (target icon, cyan when on)
  - Primary full-width **LAYERS** tab horizontally above the others
  - Secondary tab row: **Halo / Galaxy / Coords / Box**
  - Content shown via `v_show` (no remount cost; content sticks to the top-left of the panel)
- Dark theme forced via `server.state["$vuetify"]`
- Inactive tab labels and transport buttons render in neutral gray (`#6b7280`);
  active tab and active toggles render cyan
- View-update push wired to every state change so opacity / colormap / colour-by /
  snapshot changes update the render window immediately without needing mouse movement

### Fixed during development
- Initial `setuptools.backends.legacy` build backend → `setuptools.build_meta`
- Par file path resolution: relative paths are resolved against SAGE root, not par dir
- `VApp` → `SinglePageLayout` (Vuetify 3 requires it for `state.translator`)
- joblib loky process pool → threads (`prefer="threads"`) to eliminate semaphore /
  mmap leaks on every snapshot prefetch
- Play-loop VTK thread-safety crash by moving playback to an asyncio coroutine on
  the Trame event loop
- Pause / Stop now actually stop the loop (plain Python dict as the control flag;
  Trame state proxy is not reactive inside a running coroutine)
- Focus toggle now applies the stored zoom region immediately when turned on
- `state.flush()` after click-to-select so the galaxy index VTextField updates
- Camera framing centred on box midpoint (was offset because `reset_camera()`
  ran after `focal_point` was set)
- Layout offset and label clipping fixed by replacing Vuetify grid containers
  with plain flexbox `VSheet`s

### Removed
- `sage_viewer/ui/layer_panel.py` (inlined as the Layers tab inside navigation_panel.py)

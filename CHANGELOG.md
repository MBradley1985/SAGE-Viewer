# Changelog

All notable changes to SAGE-Viewer are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

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

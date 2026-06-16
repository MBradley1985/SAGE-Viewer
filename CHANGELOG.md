# Changelog

All notable changes to SAGE-Viewer are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased] — 0.2.0

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

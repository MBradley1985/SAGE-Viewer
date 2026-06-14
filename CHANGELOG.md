# Changelog

All notable changes to SAGE-Viewer are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

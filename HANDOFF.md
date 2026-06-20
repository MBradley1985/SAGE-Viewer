# SAGE-Viewer Handoff

Snapshot of the project so a new chat can pick up cleanly. Reflects state at the close of the 0.3.0 work cycle.

---

## How to launch

```bash
export PATH="/Users/mbradley/Library/Python/3.12/bin:$PATH"

sage-viewer --par /Users/mbradley/Documents/PhD/SAGE26/input/millennium.par --snap 63
```

Open <http://localhost:8080> in any browser. For HPC use, SSH-tunnel the port.

Useful flags:

- `--snap N` initial snapshot (default: z = 0)
- `--port N` Trame server port (default 8080)
- `--n-jobs N` halo loader threads (default: CPUs − 1)
- `--max-halos N` / `--max-galaxies N` uniform-random downsample ceilings (both default 100,000)
- `--min-halo-mass M` / `--min-stellar-mass M` (Msun)
- `--par-dir DIR` override the auto-detected par-scan dir for the multi-model dropdown

---

## Repo layout

```
SAGE-Viewer/
├── sage_viewer/
│   ├── _version.py
│   ├── app.py                       # Trame layout, toolbar, viewport, pop-out console
│   ├── cli.py
│   ├── config.py                    # SimConfig dataclass
│   ├── io/
│   │   ├── par_reader.py            # parses .par into SimConfig; strips %, ;, # comments
│   │   ├── sage_header.py           # reads Header/Simulation cosmology from HDF5
│   │   ├── snapshot_table.py        # scale-factor / redshift lookup
│   │   ├── halo_reader.py           # lhalo_binary reader
│   │   └── galaxy_reader.py         # SAGE HDF5 reader; cgm_gas + hot_gas added
│   ├── parallel/loader.py           # prefetch + LRU snapshot cache
│   ├── scene/
│   │   ├── scene.py                 # Plotter, layers, focus state, interactor
│   │   ├── model.py                 # one SAGE model (loader + layers + cfg)
│   │   ├── halo_layer.py            # 3-layer NFW gaussian splats; _combined_mask() guard
│   │   ├── galaxy_layer.py          # outer envelope + cold-gas envelope + outer property; _combined_mask() guard
│   │   ├── fof_layer.py             # filter-aware FoF satellite→central gold lines
│   │   └── camera.py                # fly-to / sphere & box wireframe indicators
│   ├── ui/
│   │   ├── toolbar.py               # transport + slider + speed/rotation
│   │   ├── navigation_panel.py      # right panel: tabs + console + filters + ...
│   │   └── info_panel.py            # footer + double-click galaxy selection
│   ├── utils/
│   │   ├── colormap.py
│   │   ├── sizing.py
│   │   ├── command_parser.py        # natural-language SAGE commands (Console "sage" mode)
│   │   ├── galaxy_info.py           # builds Galaxy Info card rows
│   │   └── group_info.py            # builds Group Info card rows
│   └── static/
│       └── sage_viewer.js           # pop-out drag handler + Enter-to-click handler
├── tests/                           # unit tests
├── docs/                            # MkDocs Material site
├── CHANGELOG.md
├── README.md
├── HANDOFF.md                       # this file
└── pyproject.toml
```

---

## Recent changes (post-0.3.0)

### Interactive draw widgets — Coords and Box tabs

#### Draw Sphere (Coords tab)
- New **Draw Sphere** button places two draggable handle balls in the 3D viewport via `add_sphere_widget(num=2, pass_widget=True, interaction_event='always')`:
  - **index 0 — centre ball**: translates the sphere; when released the edge ball slides to `(cx + r, cy, cz)`.
  - **index 1 — edge ball**: resizes the sphere; radius = `norm(edge_pos − centre)`.
- Visual is 5 great-circle rings (identical to `_add_sphere_indicator` in `camera.py`): 1 equatorial + 4 meridionals at 0°, 45°, 90°, 135°, redrawn via `_rebuild_sphere_rings()` on every drag tick.
- A separate `_draw_sphere_actor` slot (alongside `_draw_sphere_widget`) tracks the ring mesh; `_remove_sphere_actor()` is called in all 4 sphere-clear paths.
- Button turns orange / "Lock Sphere"; second click removes the widget and ring mesh, then runs `on_go_to_coords` (now labelled **Zoom**) to apply the sphere as the focus region.
- Initial sphere radius: `min(nav_distance × 0.25, 3.0)` Mpc/h.

#### Draw Box (Box tab)
- New **Draw Box** button places a native `vtkBoxWidget2` (no rotation) via `add_box_widget(pass_widget=False)`.
- Callback receives `vtkPlanes`; bounds extracted as `min/max` over the 6 face-origin points.
- Initial box: 50 % of current field extents from centre (each half-width = `max(1.0, extent × 0.25)`).
- Button turns orange / "Lock Box"; second click removes the widget and runs `on_zoom_to_box`.

#### Clear buttons
- A red **Clear** button appears at the bottom of both Coords and Box tabs while a draw widget is active; calls `on_clear_draw_sphere` / `on_clear_draw_box` — cancels without committing.

#### Shared housekeeping
- `_clear_draw_widgets()` is the single authoritative cleaner for both widgets; called from `on_reset`, `on_toggle_focus` (off branch), and a `register_model_change_callback`.
- `on_go_to_coords` and `on_zoom_to_box` also call their respective clear paths so clicking Zoom with a widget active just commits the widget's last-reported position.

### Model switch → always z=0
- `scene.switch_primary()` sets `snap = self.primary.snap_count - 1` (z=0 of the new model) instead of `min(current_snap, new_max)`.
- `on_switch_model` in `app.py` explicitly syncs `snap_max`, `snap_num`, and `snap_label` in its `finally` block so the slider and snap chip reflect z=0 of the new model immediately, even when `snap_num` hasn't changed numerically.

### Coords tab "Go" → "Zoom"
- The action button in the Coords tab is now labelled **Zoom** for consistency with the Box tab. Controller name (`go_to_coords`) and Enter-submit target (`btn-coords-go`) are unchanged.

---

## What works today

### Rendering
- Haloes: 3-layer NFW-style gaussian splats (envelope + mid + core), single colormap, sized by mass/Rvir/Vmax.
- Galaxies (Structure mode): two envelopes per galaxy — outer (Greens for CGM-regime sized by `CGMgas`, Reds for Hot-regime sized by `HotGas`), inner cold-gas (Blues, sized by `ColdGas`). Optional outer property layer when the color-by mode isn't "structure".
- Full still-quality at all times — no resolution drop during drag, playback, or rotation.
- 27 selectable matplotlib colormaps per layer.

### Playback
- 0.1× / 0.25× / 0.5× / 0.75× / 1× / 2× / 5× speeds.
- Rotate: Off / CW / CCW at 15° / 30° / 60° per second.
- Pause / Stop interrupt cleanly (asyncio.Event + cancellable Task).

### Console tab
- **Default mode = terminal** — every command runs through `$SHELL` with persistent `cwd` + `env`. `cd`, `pwd`, `export` are in-process built-ins.
- Type `python` → embedded REPL (locals: `scene`, `state`, `ctrl`, `server`, `plotter`, `np`).
- Type `command` (or `cmd`) → SAGE-Viewer natural-language command mode.
- `exit` / `quit` / `terminal` from any non-default mode returns to terminal.
- Multi-session: `+` button creates new sessions; each has its own history, mode, cwd, env, Python interpreter.
- **Load Script** button reads a `.py` path and `exec`s it in the active session.
- **Pop-out** button floats a movable + resizable card over the viewport mirroring the active session.
- Console fills most of the right panel; inputs + 4 buttons anchored at the bottom.

### Galaxy filters — active-only
- Range sliders are **inert at their full-range defaults** — no galaxies are filtered unless the user moves a slider. This guarantees every galaxy with detectable mass is shown at startup.
- Implemented via `_active(lo, hi, mn, mx)` in `_apply_filters()` (`navigation_panel.py`): returns True only when the slider is inside its range.
- All slider maxima widened to cover the full SAGE26 distribution (mass fields to 14.0, sSFR max to 0.0, rates to 5.0, etc.).
- B/T computed as `clip(BulgeMass / StellarMass, 0, 1)` to prevent false exclusion of satellites where BulgeMass > StellarMass numerically.

### Galaxy picking — visibility-aware
- `info_panel.py` restricts the KDTree search to `GalaxyLayer._combined_mask()` visible indices before picking, so only rendered galaxies are selectable. Environment checkboxes, focus regions, and filter sliders all apply.

### Indicators — regime-coloured
- `camera.py` redesigned with `_member_actors: list` and `_selected_actors: list` (replaces single `_indicator_actor`).
- `_add_member_indicators(positions, regimes)` groups by regime and adds one mesh per colour: `dodgerblue` (CGM-regime, 0), `tomato` (Hot-regime, 1), `cyan` (unknown / no regime field).
- `_add_selected_indicator(position, regime)` draws a white border ring (36 px) + regime-coloured fill (26 px) so the selected galaxy is visually distinct from members.
- `_REGIME_COLORS = {0: "dodgerblue", 1: "tomato", -1: "cyan"}` at class level.

### Navigation
- **Focus button** is tab-aware: Target → galaxy, Environment → halo, Coords → sphere, Box → box. Off always clears.
- **Double-click** any point on any tab → populates Target halo + galaxy IDs, draws red marker. Only queries visible (unfiltered, unfocused-in) galaxies.
- **Indicators persist** across tab changes (only Reset Camera / Go / Clear / Focus toggle clear them).
- "Use Current Position" (Coords) populates X/Y/Z + Standoff from the camera.
- "Use Current View" (Box) populates the 6 bounds from the camera frustum.
- Camera bookmarks save/restore/delete.

### Enter to run
Every typed field now Enter-submits the same as clicking its action button. Wiring is per-field via `data-enter-click="<button-id>"` on a wrapping `<div>`; a global JS handler (in `sage_viewer/static/sage_viewer.js`) walks up to find the attribute and `.click()`s the button. Works in: Target Halo idx, Target Standoff, Galaxy idx, Environment Halo idx + Standoff, Coords X/Y/Z + Standoff, Box 6 bounds, Console command, Console script path, Pop-out console command, Screenshot label, Movie label.

### Snapshot slider
- `<` / `>` step buttons on either side of the slider advance one snapshot at a time.
- The slider `max` is reactive (`state.snap_max`) so it updates when switching models.
- Switching models via the Launch Mode menu refreshes the slider bounds, current snap, snap label, and the pre-rendered frame cache automatically.

### Environment filter (Environment tab)
- Five categories: **Field**, **Isolated**, **Pairs**, **Groups**, **Clusters** (mass labels removed).
- **Pairs** = galaxies in a 2-member FOF group (determined by counting members sharing the same `CentralGalaxyIndex`, matching `member_indices()` in `group_info.py`).

### Multi-model
- Auto-scan `<sage_root>/output/` for `model_0.hdf5` subdirs.
- Hamburger menu (top-left) → Models section to switch primary or toggle overlays.
- "SWITCHING MODELS, PLEASE HOLD..." overlay with rotating quips during loads.

### Output
- Screenshots: PNG / JPG / TIFF.
- Movies: GIF / MOV (ffmpeg) / PNG sequence; 1–60 fps; Native / 2× / 4× supersample.
- High-res (2×/4×) uses PIL LANCZOS upscaling instead of VTK tiled rendering to eliminate the grid-seam artifact that appeared at the end of supersample movies.
- One session folder per app launch under `<repo>/sage_outputs/session_*`.

### Library tab
- Browse stored screenshots / movies from `<repo>/sage_library/` and `sage_outputs/`.
- **Double-click** a row to open it as a draggable floating card over the 3D viewport.
- Multiple items can be open simultaneously — each card is independently movable (drag the title bar).
- Per-item close (×) button on each card; "Close all" in the Library tab dismisses everything.
- GIF/video always plays from frame 0 (a fresh `<img>` / `<video>` element is created for each open).
- Backend: `state.library_items = [{id, name, kind, data_url, top_px}, ...]` — replaces the old
  single-item `library_show` / `library_data_url` / `library_kind` / `library_name` state vars.

---

## Architecture notes

### Static asset system
Vue 3 silently strips `<script>` tags from templates, so any client JS must come in as a real `.js` file. We register a trame module:

```python
server.enable_module({
    "serve":   {"sage_static": "<package>/static"},
    "scripts": ["sage_static/sage_viewer.js"],
})
```

`sage_viewer/static/sage_viewer.js` currently contains:
- Pop-out drag handler (delegated `mousedown` on `.sage-popout-handle`).
- Enter-to-click handler (capture-phase `keydown` on `<input>` / `<textarea>`).

Add new client-side helpers to the same file (or add new files + extend `scripts`).

### Per-session console state
`navigation_panel.py` keeps a Python-side dict:

```python
_consoles_data: dict[int, dict] = {
    1: {
        "history":   [...],
        "input":     "",
        "mode":      "shell",  # "shell" | "python" | "sage"
        "prompt":    "$",
        "cwd":       "/home/me",
        "env":       {...},
        "py_buffer": [],                    # multi-line REPL accumulator
        "py_interp": code.InteractiveInterpreter(...),
        "py_locals": {"scene": ..., ...},
        "counter":   0,
    },
    ...
}
```

The single set of Vue-bound `state.console_*` vars always reflects the *active* session. On `console_switch` we `_save_active()` then `_load_console(new_id)` to snap the bindings into the new session's data.

### Layered rendering
Both halo and galaxy layers use `vtkPointGaussianMapper` with a per-point `radius` array in Mpc/h (world space). In-place data updates on snap change when the point count matches; full rebuild when it doesn't (avoids heap corruption from VTK's array-reuse).

### Focus mode
`scene._focus_region` is a dict describing the active focus area (`{"kind": "sphere", "center": ..., "radius": ...}` or `{"kind": "box", "bounds": ...}`). `set_focus_sphere` / `set_focus_box` populate it and immediately `_apply_focus_masks(halos.positions, galaxies.positions)` to filter both layers.

### `_combined_mask()` shape guard (halo_layer.py + galaxy_layer.py)
`_focus_mask` and `_filter_mask` are updated at different points during a snapshot transition — `_focus_mask` is recomputed first (inside `set_snapshot()`), then `_filter_mask` later (via the `_apply_filters()` callback). If the slider moves between snapshots with different halo/galaxy counts, the two masks are temporarily sized for different populations. Both `HaloLayer._combined_mask()` and `GalaxyLayer._combined_mask()` return `None` when the lengths disagree, which causes `_redraw()` to render everything unmasked for that one intermediate frame rather than raising `ValueError`. Once both masks are refreshed for the new snapshot, the next `_redraw()` call applies them correctly.

### Playback frame-cache invalidation (`toolbar.py`)
`_frames = {"key": None, "data": {}}` caches the pre-rendered frame sequence for the Play button. The cache key is built by `_cam_key()`:
```
(camera_position, camera_focal_point, camera_up, rotate_mode, _scene_hash())
```
`_scene_hash()` hashes all values in `_SCENE_FILTER_VARS` (every filter slider + env checkboxes) plus layer visibility, opacity, color-mode, colormap, FoF visibility, and the focus region string. If any of these change between plays, the cache key changes and a fresh pre-render sweep runs. To add a new filter variable, append its trame state name to `_SCENE_FILTER_VARS` at the top of `toolbar.py`.

### Filter-aware FoF links (`fof_layer.py` + `navigation_panel.py`)
`FofLinkLayer` holds `_visible_halo_positions: np.ndarray | None`. Call:
- `fl.sync_masks(None)` — all halos visible; `_filter_segments()` passes all segments through
- `fl.sync_masks(snap.positions[combined_mask])` — only segments whose central halo is in the visible set are drawn

Central membership uses exact float32 byte comparison (`p.tobytes()`) against a set built from `visible_positions` — reliable because FoF central positions come from the same struct array as `halos.positions`.

`_sync_fof_layer()` in `navigation_panel.py` is the single helper that reads `halo_layer._combined_mask()`, extracts visible positions, and calls `fl.sync_masks()`. It must be called:
- At the end of `_apply_filters()` (covers all snapshot transitions and filter slider changes — this also fires during playback pre-rendering)
- Inside every focus-changing handler: `on_go_to_halo`, `_go_to_galaxy_at_radius`, `on_go_to_env_halo`, `on_go_to_coords`, `on_zoom_to_box`, `on_reset`, `on_toggle_focus`
- Inside `on_halo_toggle` and `on_toggle_fof_links` when turning the links on (not needed when turning off, since `fl.visible = False` skips the rebuild)

FoF links are gated on `halos_visible AND fof_links_on` — `fl.visible` is only set `True` when both flags are true.

---

## Known quirks worth knowing

- `state.focus_active` is a Trame proxy — always coerce with `bool(state.focus_active)` inside callbacks.
- The async play loop reads from a plain Python `_ctl` dict, not from `state.is_playing` (proxies aren't reactive inside a running coroutine).
- VTK is single-threaded — all rendering / camera mutation must run on the Trame event loop.
- After PyVista picker callbacks, call `state.flush()` to push state to the client (they run outside the normal event dispatch).
- Relative paths in `.par` files resolve against `parent.parent` of the par file (the SAGE root, not the par file's dir).
- Console shell mode has no pty — `vim`, `top`, `less` won't render. For HPC workflows (`sbatch`, `python plot.py`, `ls`, `tail file.log`) this is fine.
- `code.compile_command` returns `None` for incomplete Python input; in the REPL we buffer the line and show `...`. A blank line force-executes the buffer.

---

## Likely next-up things

- **PTY-backed shell mode** so `vim`, `top`, `less`, and other terminal apps work — would need a JS terminal emulator (xterm.js) and a websocket pty bridge.
- **Streaming command output** — current `subprocess.run` blocks until the command finishes; long-running scripts go silent until completion. Switch to `Popen` + async readline + state push.
- **Threading for long Python REPL execs** — currently blocks the event loop. Wrap in `asyncio.to_thread`?
- **Stress-test microUchuu** at higher `--max-halos` / `--max-galaxies` once perf is stable.
- **Density colour mode** still does KDE per snapshot — could be cached or precomputed.
- **Camera bookmarks UI** lives in a tab; could surface as a hover-out menu in the toolbar.
- **Library tab** multi-item pop-outs done; deletion, renaming, and inline thumbnails for movies still pending.
- **`HALO_CB` / `GAL_CB` colour-by descriptors** still hard-coded — could be derived from `model_fields` so unsupported fields don't even appear in the dropdown.

---

## Style / housekeeping

- Comments only when the *why* is non-obvious.
- No Unicode super/subscripts in user-visible strings (use ASCII: `Msun`, `10^12.5`, `log10`, `H2`, `yr^-1`).
- `pytest tests/ -v` before committing.
- Python ≥ 3.10; PyVista 0.46, Trame 3.13, Vuetify 3.

---

## Status at handoff

- All UI-polish requests from the 0.3.0 cycle implemented.
- Enter-to-run wired everywhere via the global JS handler.
- Pop-out console is draggable + resizable.
- Console modes renamed: **terminal** (was shell) and **command** (was sage). Type `command` or `python` from terminal mode to switch; type `terminal` to return.
- `sage-viewer` launcher script at repo root — run `./sage-viewer --par ...` without needing Python bin in PATH.
- Snapshot slider now has `<` / `>` step buttons; slider `max` is reactive and updates on model switch.
- Model switching now also refreshes the slider bounds, snap label, and pre-rendered frame cache.
- Environment filter has 5 categories: Field / Isolated / **Pairs** / Groups / Clusters (mass labels removed; Pairs detects 2-member FOF groups).
- WASD/arrow camera drift on key-release reduced: inner-loop re-check + push on final release.
- High-res screenshots/recordings use PIL LANCZOS upscaling instead of VTK tiling — no more 2×2 / 4×4 grid artifact at the end of videos.
- Star-scatter + BH-disk render layers removed — Structure mode is back to fast core layers only.
- Right panel is locked at 300 px and never scrolls.
- Playback frame cache invalidates correctly on any filter / focus / visibility / color-mode change.
- `_combined_mask()` shape-mismatch crash fixed in both `halo_layer.py` and `galaxy_layer.py`.
- FoF links are fully filter-aware: respect focus regions, halo filter masks, and the halos-visible toggle; sync during playback and recording.
- Galaxy filter sliders widened + **active-only** gate — all galaxies with mass now visible at startup; sliders only filter when moved away from endpoints.
- B/T clamped to [0, 1] before filter comparison — SAGE satellites with BulgeMass > StellarMass no longer falsely excluded.
- Double-click selection restricted to visible galaxies only (`_combined_mask()`).
- Highlight Members / Highlight Galaxy indicators now use **CGM/Hot regime colours** (dodgerblue / tomato / cyan); selected galaxy shows a white border ring + regime fill.
- Library tab redesigned: **multi-item draggable pop-outs** over the viewport, **double-click** to open, per-item × close, "Close all" button; GIF/video always starts from frame 0.

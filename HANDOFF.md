# SAGE-Viewer Handoff

Snapshot of the project so a new chat can pick up cleanly. Reflects state at the close of the post-0.3.0 draw-widget + recording cycle.

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
│   │   ├── scene.py                 # Plotter, layers, focus state, interactor; multi-box layout
│   │   ├── model.py                 # one SAGE model (loader + layers + cfg)
│   │   ├── box_profile.py           # BOX_PROFILE_KEYS (56); save_profile / load_profile per active box
│   │   ├── halo_layer.py            # 3-layer NFW gaussian splats; _combined_mask() guard
│   │   ├── galaxy_layer.py          # outer envelope + cold-gas envelope + outer property; _combined_mask() guard
│   │   ├── fof_layer.py             # filter-aware FoF satellite→central gold lines
│   │   └── camera.py                # fly-to / sphere & box wireframe indicators; focus_on_boxes()
│   ├── ui/
│   │   ├── toolbar.py               # transport + slider + speed/rotation
│   │   ├── navigation_panel.py      # right panel: tabs + PTY console + filters + ...
│   │   └── info_panel.py            # footer + double-click galaxy selection
│   ├── utils/
│   │   ├── colormap.py
│   │   ├── sizing.py
│   │   ├── command_parser.py        # natural-language SAGE commands (Console "SAGE Commands" mode)
│   │   ├── galaxy_info.py           # builds Galaxy Info card rows
│   │   └── group_info.py            # builds Group Info card rows
│   ├── wizard/
│   │   ├── controller.py            # async step machine; state vars; par template
│   │   ├── launch.py                # entry point called from app.py
│   │   └── ui.py                    # Trame/Vuetify wizard layout
│   └── static/
│       ├── sage_viewer.js           # pop-out drag handler + Enter-to-click handler
│       └── sage_theme.css           # global CSS overrides (served via enable_module → page <head>)
├── tests/                           # unit tests
├── docs/                            # MkDocs Material site
├── CHANGELOG.md
├── README.md
├── HANDOFF.md                       # this file
└── pyproject.toml
```

---

## Recent changes (post-0.3.0 wizard + library + HPC)

### HPC install script (`install_hpc.sh`)
`install_hpc.sh` at repo root. Usage:
```bash
module load python/3.12.0          # cluster-specific
./install_hpc.sh                   # creates .venv and pip installs
./install_hpc.sh /scratch/$USER/sage-env   # custom venv location
```
Checks Python ≥ 3.10, upgrades pip, `pip install -e .` (editable — `git pull` = instant update). Checks for `ffmpeg` separately with a `module load` hint.

### Wizard navigation — `self._back`
All wizard Back buttons used to hardcode `"back_fresh"`, so **Run SAGE26 → Back** sent the user to the Start Fresh submenu instead of the main menu.

Fix: `self._back: str = "back_fresh"` added to `__init__` and `reset_and_start`. Set to `"back_main"` at the top of `_step_run_sage26_existing`; set to `"back_fresh"` at the top of `_step_fresh_choice`. All Back button `value` fields in `_step_compile`, `_step_pick_par`, `_step_create_par`, `_step_par_edit`, `_step_run_sage26` use `self._back`.

### Wizard — OutputDir mkdir
`_step_run_sage26` now calls `parse_par(self._par_path)` after saving and does `cfg.output_dir.mkdir(parents=True, exist_ok=True)` before running the binary. SAGE26 won't create the directory itself.

### Wizard — text and layout
- "Edit the file below" → "Edit the file to the right" (par editor is to the right, not below)
- "Running SAGE26 — output streams below" → "Running SAGE26 — output follows"
- Terminal card: `overflow:hidden` added; solo `max-width` widened to `1100px` (was `860px`); side-by-side stays `860px`
- Choice button area: `max-height:120px; overflow-y:auto` so many buttons don't push terminal out of view
- Buttons shrink to `x-small` when `wiz_choices.length > 5`
- Logo shrunk from `140px` to `90px`

### Library pop-out fixes
Three bugs fixed in `navigation_panel.py` + `app.py`:

**Close reliability** — `on_library_close_item` read `state.library_items` back from the Trame proxy (stale after mutations). Fix: authoritative `_lib_items: list[dict]` Python list; close mutates `_lib_items[:]` directly and rebuilds state from it.

**Stacking** — all cards were hardcoded to `top:32px; right:24px`. Fix: `top_px` and `right_px` computed from `idx = len(_lib_items)` with diagonal cascade (50 px down + 44 px left, wrapping at 6); Vue template style is a JS template literal `` `...${item.top_px}px...${item.right_px}px...` ``.

**GIF restart** — Chrome caches GIF animation state by URL so reopening the same file continued mid-animation. Fix: GIF data URLs get a unique `#N` fragment (e.g. `data:image/gif;base64,...#3`) on each open; fragment makes the URL string distinct so browser discards cached animation.

### Console PTY cleanup
`atexit` handler `_kill_all_ptys()` registered after `_consoles_data` is created. Iterates all sessions and calls `close()` on any live PTY on app exit / Ctrl+C. `_PTYSession.close()` upgraded from `proc.terminate()` to `proc.kill()` (SIGKILL).

---

## Recent changes (post-0.3.0 draw widgets + recording)

### Draw widget placement — camera focal point

Both Draw Sphere and Draw Box now place the widget centred on the camera focal point (what the user is looking at) when first activated, sized to the current field of view. Previously they used stored `nav_box_*` / `nav_cx/cy/cz` coordinates which could be off-screen.

- **Draw Sphere** (`on_toggle_draw_sphere`): `cx, cy, cz = camera.focal_point`; `r = max(0.5, d * tan(FOV/2) * 0.25)` where `d = norm(camera.position − focal_point)`.
- **Draw Box** (`on_toggle_draw_box`): centre = `camera.focal_point`; half-extent `h = max(1.0, d * tan(FOV/2) * 0.5)`.
- Placement also writes the computed values back into `state.nav_x/y/z/distance` (sphere) and `state.nav_box_*` (box) so Locking without dragging still navigates to the correct position.

### Movie recording fixes (`navigation_panel.py`)

Four bugs fixed in `_record_loop` / `on_stop_recording`:

**1. FPS not honoured during playback**
The loop only wrote a frame when `state.playback_frame` changed (new snapshot). At slow playback speed each snapshot takes many seconds of real time but produced only one frame, making all recordings play back at the same speed regardless of settings. Fix: always write a frame every `1/fps` seconds; the last decoded PIL image is cached in `last_frame` and reused (written as a duplicate) when the playback frame hasn't changed yet.

**2. UI freezes (can't stop) when scene is heavy**
When frame capture took longer than `1/fps`, the compensated sleep collapsed to `0.0` — no `await` happened, the event loop starved, and Stop/Pause clicks were never processed. Fix: minimum `0.001 s` sleep per tick so the event loop always gets control.

**3. UI freezes on Stop**
`_finalize_movie()` (imageio GIF encode or `subprocess.run(ffmpeg ...)`) was called synchronously inside the Trame controller, blocking the UI for the full encode duration. Fix: finalize runs in a `daemon=True` thread; UI shows "Encoding…" immediately; `state.last_movie` is updated to the path (or error string) when encoding finishes.

**4. Slow frame capture → low FPS**
Intermediate frames were saved as PNG (lossless zlib, ~100 ms/frame). At typical viewport sizes 30 FPS was unachievable. Fix: intermediate frames saved as JPEG quality 95 (~10 ms/frame). Output quality is unaffected — both GIF (imageio) and MOV (ffmpeg H.264) are lossy encoders. `_finalize_movie` globs `frame_*.jpg` and passes them to imageio / ffmpeg accordingly.

---

## Recent changes (post-0.3.0 multi-box cycle)

### Side-by-side multi-box comparison

#### Architecture
- `scene.py` maintains a `_models: dict[str, Model]` and `_active_box_name: str`. All boxes share one plotter, one renderer, one camera.
- Boxes are placed along the X axis. The first box is at offset 0; each successive box is at `prev_offset + prev_box_size + gap`, where `gap = _BOX_GAP_FRACTION (0.30) × box_size`.
- `toggle_adjacent(path, remove=False)` adds or removes a side-by-side box. On add, it initialises the new Model with `halo_colormap="viridis"` and calls `view_update()` so the new box is immediately visible.
- `set_active_box(name)` updates `_active_box_name`, calls `_update_labels()`, and calls `plotter.render()`. The caller (`app.py`) must also call `view_update()` afterwards.
- `_add_label(name)` uses `vtkBillboardTextActor3D` (always faces camera, no anchor-point artifact). Active label = green `(0.2, 1.0, 0.4)`; idle = white `(1.0, 1.0, 1.0)`. Label text: `{model name}  z={redshift:.2f}`. Position: `(cx, -box_size * 0.22, cz)` — below the box floor.
- `box_name_at(world_x)` maps a world X coordinate to the owning box name; used by `info_panel.py` to switch the active box on single click.

#### Per-box state — `scene/box_profile.py`
- `BOX_PROFILE_KEYS`: 56 trame state keys (snapshot, all layer settings, all filter sliders) that belong to one box.
- `save_profile(state) → dict` — snapshot current state values into a plain dict.
- `load_profile(state, profile)` — write a saved profile back into state; call `state.dirty(*BOX_PROFILE_KEYS)` + `state.flush()` after.
- `_LAYER_DEFAULTS` includes `"halo_colormap": "viridis"` (intentionally viridis so adjacent boxes start consistent with Mvir mode).

#### App wiring (`app.py`)
- `_profiles: dict[str, dict]` stores one saved profile per box name.
- `on_set_active_box(name)`: saves the old box profile, calls `scene.set_active_box(name)`, loads the new box profile, dirtys all 56 keys, calls `sync_active_snap_count` + `view_update`.
- Box strip built by `_build_box_strip_items()`: `[{"name": n, "active": n == active_name} for n in models]`.
- When adjacent box is added, any active rotation is cancelled: `state.rotate_mode = "off"`.

#### Toolbar rotation disable (`toolbar.py`)
- Rotation VSelect has `disabled=("box_strip_items && box_strip_items.length > 1",)` and `title="Rotation disabled in multi-box mode"`.
- `sync_active_snap_count` controller: called after every active-box switch to update `_snap_count[0]` and invalidate the frame cache (`_frames["key"] = None; _frames["data"] = {}`).

#### Halo Mvir colormap lock (`navigation_panel.py`)
- `on_halo_mode` forces `state.halo_colormap = "viridis"` whenever `halo_color_mode == "mvir"`.
- The halo colormap VSelect has `disabled=("halo_color_mode === 'mvir'",)`.

#### Draw Box widget handle fix (`navigation_panel.py`)
VTK's internal `SizeHandles()` (C++, not Python-callable) recomputes handle sphere radii based on camera distance on every Scale/Translate interaction, making the handles jump size after each drag. `SetHandleSize()` has no visual effect in VTK 9.5 — not wired to sphere geometry. `GetRepresentation()` does not exist on `vtkBoxWidget` (only on `vtkBoxWidget2`, which PyVista does not use).

Fix:
1. Before `add_box_widget`: snapshot all existing `vtkSphereSource` IDs in the renderer.
2. After `add_box_widget`: collect the new sphere sources (= the 7 handle spheres) via `actor.GetMapper().GetInputAlgorithm()`.
3. Store `_handle_world_r[0]` = initial radius from `sources[0].GetRadius()`.
4. Two observers call `_rescale_box_handles()` which does `src.SetRadius(r); src.Modified()` on each source:
   - `widget.AddObserver("EndInteractionEvent", ...)` — fires after every Scale/Translate (after VTK's own `SizeHandles()` but before `Render()`)
   - `cam.AddObserver("ModifiedEvent", ...)` — fires on every zoom/pan/orbit
5. `_detach_box_cam_observer()` removes both observers; called in all 4 clear paths.

Key storage slots: `_draw_box_widget`, `_box_cam_obs_tag`, `_handle_world_r`, `_box_handle_sources` (all `list` wrappers for closure-mutability).

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

### Side-by-side multi-box comparison
- Load two or more SAGE models side-by-side via `+SBS` in the hamburger Models section.
- Each box is fully independent: its own snapshot, filters, colormaps, opacity, layer visibility (all 56 `BOX_PROFILE_KEYS` in `scene/box_profile.py`).
- Box strip at the bottom of the viewport; clicking a box makes it active (green label).
- Play, step, and snapshot slider advance only the active box. Rotation is disabled in multi-box mode.
- Halo Mvir mode locks colormap to Viridis; selector is greyed out.

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
- **Terminal mode** — real PTY (`pty.openpty()`) backed by `$SHELL -l`; output pushed to browser via `state.pty_out_seq` / `pty_out_data` (base64); rendered by xterm.js. Full ANSI colour, cursor movement, interactive programs (`vim`, `top`, `htop`, `less`) all work.
- **SAGE Commands mode** — natural-language SAGE commands; switch via the **SAGE Cmds** button, type `terminal` to return.
- Multi-session: `+` button creates new sessions; each has its own PTY process and history.
- **Pop-out** button floats a movable + resizable card over the viewport mirroring the active session.
- Python REPL mode removed — use the shell for scripting.

### Launch Mode wizard (`sage_viewer/wizard/`)
- Guided setup flow for configuring and launching SAGE26.
- Step chips track progress; **Rescan** button restarts the environment scan.
- **Create config file** writes a new `.par` from the built-in millennium.par template; user chooses filename.
- Par file editor opens side-by-side with the terminal when a `.par` needs editing.
- Opened from the Launch Mode dropdown or Explore Mode hamburger menu.
- `open_wizard` controller (in `app.py`) always calls `_wiz_ctrl.reset_and_start()` then sets `wiz_active = True` — this unconditional reset avoids Trame's `@state.change` which only fires when the value actually changes.

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
    "styles":  ["sage_static/sage_theme.css"],
})
```

`sage_viewer/static/sage_viewer.js` currently contains:
- Pop-out drag handler (delegated `mousedown` on `.sage-popout-handle`).
- Enter-to-click handler (capture-phase `keydown` on `<input>` / `<textarea>`).
- xterm.js PTY relay: polls `pty_out_seq` / `pty_out_data` at 50 ms, writes to the xterm Terminal instance; sends keystrokes back via a hidden `<input v-model>` + native DOM setter.

`sage_viewer/static/sage_theme.css` contains global CSS overrides (black backgrounds, shadow removal) loaded via `enable_module` so they land in the page `<head>` rather than inside the Vue template where root-level selectors don't reliably apply.

Add new client-side helpers to the same file (or add new files + extend `scripts`).

### Per-session console state
`navigation_panel.py` keeps a Python-side dict per console session. Each session now wraps a real PTY:

```python
_consoles_data: dict[int, dict] = {
    1: {
        "history":   [...],
        "input":     "",
        "mode":      "terminal",  # "terminal" | "sage"
        "pty":       {"master_fd": int, "pid": int, "seq": int},
        "counter":   0,
    },
    ...
}
```

The single set of Vue-bound `state.console_*` / `state.pty_*` vars always reflects the *active* session. On `console_switch` we `_save_active()` then `_load_console(new_id)` to snap the bindings into the new session's data.

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

### Multi-box architecture notes

**Single shared camera** — all boxes orbit together. Independent rotation per box would require one VTK renderer + camera per box. This is a large refactor; current workaround is to disable rotation in multi-box mode.

**`view_update()` after `plotter.render()`** — `plotter.render()` updates the VTK scene server-side but does not push a new frame to the browser. After any box-switch or box-add/remove, always call `server.controller.view_update()`. Missing this call causes the new box to be invisible until the next mouse event.

**Profile save/load order in `on_set_active_box`**:
1. Save old box profile (`save_profile(state)` → `_profiles[old_name]`).
2. Call `scene.set_active_box(name)` (updates VTK label colours, renders).
3. Resolve new profile: `_profiles.get(name, default_profile)`.
4. `load_profile(state, incoming)`.
5. `state.dirty(*BOX_PROFILE_KEYS); state.flush()`.
6. `sync_active_snap_count()` + `view_update()`.
Do not re-order steps 1–6 or the old box's state leaks into the new one.

**`box_name_at(world_x)` in `info_panel.py`** — every single click checks which box the user clicked by world-X coordinate. This runs before the double-click threshold check, so single-clicking a non-active box always switches it. This is intentional.

---

## Known quirks worth knowing

- `state.focus_active` is a Trame proxy — always coerce with `bool(state.focus_active)` inside callbacks.
- The async play loop reads from a plain Python `_ctl` dict, not from `state.is_playing` (proxies aren't reactive inside a running coroutine).
- VTK is single-threaded — all rendering / camera mutation must run on the Trame event loop.
- After PyVista picker callbacks, call `state.flush()` to push state to the client (they run outside the normal event dispatch).
- Relative paths in `.par` files resolve against `parent.parent` of the par file (the SAGE root, not the par file's dir).
- Console PTY: each session forks a real shell process — clean up with `os.kill(pid, SIGKILL)` on session close or app exit if not already handled.
- `@state.change("wiz_active")` only fires when the value changes; it won't re-run if `wiz_active` is already `True`. Use a dedicated controller (`open_wizard`) for any "always reset on open" behaviour.
- `plotter.render()` alone does **not** push a new frame to the browser in Trame 3. Always follow it with `server.controller.view_update()`. This applies everywhere, but especially in box-switch, toggle-adjacent, and any background-thread-triggered scene update.
- Controller signatures: grep all call sites before changing. `info_panel.py` calls `ctrl.set_active_box(name)` directly from a PyVista pick callback — it is outside the normal Trame event dispatch and easy to miss.
- `_snap_count[0]` in `toolbar.py` is a module-level cache for the primary model's snap count. Call `sync_active_snap_count` controller after every active-box switch or the step/play buttons use the wrong range.

---

## Likely next-up things

- **`HALO_CB` / `GAL_CB` colour-by descriptors** still hard-coded — could be derived from `model_fields` so unsupported fields don't even appear in the dropdown.

---

## Style / housekeeping

- Comments only when the *why* is non-obvious.
- No Unicode super/subscripts in user-visible strings (use ASCII: `Msun`, `10^12.5`, `log10`, `H2`, `yr^-1`).
- `pytest tests/ -v` before committing.
- Python ≥ 3.10; PyVista 0.46, Trame 3.13, Vuetify 3.

---

## Status at handoff

- **Multi-box side-by-side comparison** fully implemented: box strip, per-box profile, active-box label (green/white), rotation disabled in multi-box, snap-count sync on switch, `view_update()` after every box operation.
- **Halo Mvir colormap lock**: Viridis forced + colormap selector greyed out when Mvir is active.
- Console upgraded to real PTY + xterm.js — `vim`, `top`, `htop`, `less` all work. Python REPL mode removed.
- Launch Mode wizard implemented (`sage_viewer/wizard/`): step tracking, rescan, create config file, side-by-side par editor.
- UI polish: black toolbar + right panel, scaled-down filter sliders (0.65×) centred in panel, Structure tab checkboxes, transparent export dialog, dropdown menus auto-close, footer hidden, "Enter to…" hint labels removed.
- Library pop-out cards are browser-resizable.
- `sage_theme.css` served via `enable_module` for reliable global CSS injection.
- All UI-polish requests from the 0.3.0 cycle remain implemented (Enter-to-run, pop-out console, draw widgets, etc.).
- `sage-viewer` launcher script at repo root — run `./sage-viewer --par ...` without needing Python bin in PATH.
- **Draw Box widget handles**: constant world-space size via direct `vtkSphereSource.SetRadius()` in `EndInteractionEvent` + camera `ModifiedEvent` observers (see handle fix section above for full detail).
- **Draw widget placement**: both widgets now appear centred on the camera focal point, sized to the current FOV.
- **Movie recording**: FPS now honoured during slow playback; UI stays responsive during recording and on Stop; encoding runs in a background thread; intermediate frames saved as JPEG for ~10× faster capture.
- `heatmap_layer.py` deleted (was never wired to UI).
- **PTY session cleanup**: `atexit` handler (`_kill_all_ptys`) registered in `navigation_panel.py` after `_consoles_data` is created; kills all live PTY shell processes on app exit / Ctrl+C. `_PTYSession.close()` upgraded from `proc.terminate()` (SIGTERM) to `proc.kill()` (SIGKILL). Browser-disconnect cleanup is not handled (Trame has no reliable per-client hook) but shutdown covers the common case.
- **Library pop-out fixes**: close button now reliable (authoritative `_lib_items` Python list as source of truth — never reads back from Trame state proxy); cards no longer open stacked on top of each other (diagonal cascade: 50 px down + 44 px left per card, wrapping at 6; position driven by JS template literal in the Vue style binding).
- **GIF restart**: GIF data URLs get a unique `#N` fragment on each open so Chrome always starts from frame 0.
- **HPC install**: `install_hpc.sh` at repo root — creates a venv and editable-installs in one step; designed for module-system clusters.
- **Wizard navigation**: `self._back` instance variable routes Back buttons correctly from Run SAGE26 flow (`back_main`) vs Start Fresh flow (`back_fresh`).
- **Wizard OutputDir**: wizard creates `OutputDir` via `parse_par()` + `mkdir` before running SAGE26.
- **Wizard UI**: terminal card `overflow:hidden`, solo card widened to `1100px`, button area capped at `120px` with scroll, buttons shrink at >5 choices, logo `90px`.
- **Console PTY cleanup**: `atexit` handler kills all shell sessions on app exit; `close()` upgraded to SIGKILL.

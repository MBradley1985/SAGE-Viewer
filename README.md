# SAGE-Viewer

An interactive 3D visualization package for [SAGE26](https://github.com/MBradley1985/SAGE26) and [SAGE-PSO](https://github.com/MBradley1985/SAGE-PSO) semi-analytic galaxy formation outputs.

Renders dark matter haloes and SAGE galaxies together in a browser-based interactive viewer powered by [PyVista](https://pyvista.org) and [Trame](https://kitware.github.io/trame/).

## Features

### Rendering
- World-space gaussian splat rendering of haloes and galaxies — splats scale with camera distance and stay physically meaningful at any zoom
- **Structure** render mode: each galaxy drawn as a layered composition — cold-gas envelope (blue, sized by ColdGas) + outer envelope (green for CGM-regime sized by CGMgas, red for Hot-regime sized by HotGas)
- 27 selectable matplotlib colormaps, identical lists for halo and galaxy layers
- Live colormap, colour-by mode, opacity and visibility controls per layer
- Full still-quality rendering at all times — no resolution drop during camera drag or playback

### Playback & camera
- Play / Pause / Stop / Reverse / Repeat transport at 0.1× – 5× speeds
- Continuous camera rotation (CW / CCW at 15° / 30° / 60° per second)
- Reset / Centre / Focus buttons
- Fly to halo, galaxy, coordinates, or sub-box (with focus mode that masks everything outside)
- Camera bookmarks (save, restore, delete)

### Selection & inspection
- **Galaxy Info** panel (Target tab) — GalaxyID, type, halo Mvir, stellar mass, sSFR, cold gas, B/T, BH mass, H2 mass, gas regime, FFB regime, environment classification, mass-weighted stellar age
- **Group Info** panel (Environment tab) — FOF-aggregate stats: classification, member breakdown (centrals vs satellites), host Mvir, total stellar / cold gas / SFR, mean B/T, spatial extent, target role, BCG stellar mass
- **Highlight Galaxy** / **Highlight Members** buttons add cyan splat overlays
- **Double-click any point** in the viewport (any tab) to populate the Target tab's halo + galaxy IDs and draw a red marker on the selection. If Focus is active, the camera carries to the new selection at the last-used radius.
- **Enter to run** in every input field — Halo idx, Galaxy idx, Coords X/Y/Z, Box bounds, Console command, script path, screenshot/movie label all submit on Enter, equivalent to clicking the paired Go / Zoom / Run / Take Screenshot button

### Filtering
- Halo filters: Mvir (log10), Rvir (Mpc/h), Vvir (km/s)
- Galaxy filters: stellar mass, sSFR, B/T, age, BH mass, ICS mass, type (centrals / satellites), FFB regime, CGM / Hot regime, environment class (Field / Isolated / Group / Cluster, via checkboxes in the Environment tab)
- Filters auto-disable when the loaded model doesn't contain the underlying field
- Reset Filters button restores defaults

### Multi-model
- Auto-scans `<sage_root>/output/` for SAGE model subfolders
- Switch the primary model from the hamburger menu (any box size)
- Overlay a second compatible model on top (same box size + snap count)
- Loading spinner during model swaps; warning snackbar for incompatible overlays

### Output
- Screenshots in PNG / JPG / TIFF
- Movie recording in GIF / MOV (H.264, via ffmpeg) / PNG sequence
- Configurable FPS (1 – 60) and resolution (Native / 2× / 4× supersampled)
- Optional user-typed label per capture; everything goes into a single session folder per app launch

### Embedded console (Console tab)
- A real shell terminal — every command runs through `$SHELL` with a per-session `cwd` + `env`, so pipes, globs, `&` backgrounding, redirects, and `$VAR` expansion all work
- Built-in `cd`, `pwd`, `export` are sticky between commands
- Type `python` to drop into an embedded Python REPL (locals: `scene`, `state`, `ctrl`, `server`, `plotter`, `np`); `exit` returns to shell
- Type `sage` to enter natural-language SAGE command mode (`show only clusters`, `go to halo 42`, etc.)
- **Multiple sessions** with a `+` button — each console has its own history, cwd, env, and interpreter
- **Load Script** button reads a `.py` file from disk and executes it in the active session — perfect for plotting and analysis scripts on HPC
- **Pop-out** floats a movable / resizable console card over the viewport so you can keep typing while watching the render

### Self-contained metadata
- Cosmology (h, Ω_m, Ω_Λ), box size, and snapshot redshifts are read directly from `model_0.hdf5`'s `Header/Simulation`
- The `.par` file is now only needed for tree-file paths

## Supported simulations

| Simulation | Box size | Snapshots | Tree format |
|---|---|---|---|
| miniMillennium | 62.5 Mpc/h | 64 | lhalo_binary |
| microUchuu | 96 Mpc/h | 50 | lhalo_binary |

Both supported automatically — point at the `.par` file and SAGE-Viewer figures out the rest from the HDF5.

## Quick start

```bash
pip install sage-viewer
sage-viewer --par /path/to/millennium.par
```

Open the printed URL in any browser. To launch on a remote cluster and view locally, use SSH port-forwarding:

```bash
# On the cluster
sage-viewer --par millennium.par --port 8080

# In a local terminal
ssh -L 8080:localhost:8080 user@cluster
# Then open http://localhost:8080 in your browser
```

## Command-line options

```text
--par FILE              Path to a SAGE .par file (required)
--par-dir DIR           Directory to scan for additional .par files
                        (defaults to the parent of --par; used for the
                        multi-model dropdown)
--snap N                Initial snapshot number (default: last = z=0)
--port N                Trame server port (default: 8080)
--n-jobs N              Worker threads for parallel halo file reads
--max-halos N           Downsample ceiling per snapshot
--max-galaxies N        Downsample ceiling per snapshot
--min-halo-mass MSUN    Minimum halo mass to load
--min-stellar-mass MSUN Minimum stellar mass to load
```

## Multi-model workflow

If your SAGE root looks like:

```
SAGE26/
├── input/
│   ├── millennium.par
│   ├── millennium_vanilla.par
│   └── microuchuu.par
└── output/
    ├── millennium/model_0.hdf5
    ├── millennium_vanilla/model_0.hdf5
    └── microuchuu/model_0.hdf5
```

then `sage-viewer --par input/millennium.par` discovers all three models automatically. Click the hamburger icon (top-left) → Models section to switch, or click "+ overlay" next to a compatible model to render both at once.

## Installation

```bash
# From PyPI
pip install sage-viewer

# From source
git clone https://github.com/MBradley1985/SAGE-Viewer
cd SAGE-Viewer
pip install -e ".[dev]"
```

Requires Python ≥ 3.10. Movie recording in MOV format requires `ffmpeg` in your `PATH`.

## Documentation

Full documentation at [mbradley1985.github.io/SAGE-Viewer](https://mbradley1985.github.io/SAGE-Viewer).

## Tabs at a glance

| Tab | Purpose |
|---|---|
| Structure  | Layer visibility, opacity, colour-by mode, colormap (with inline colorbar) |
| Filters    | Range sliders for halo and galaxy properties |
| Record     | Screenshots and movie recording |
| Target     | Halo / galaxy navigation, focus zoom, Galaxy Info, Highlight Galaxy |
| Environment| Halo selector, environment-class checkboxes, Group Info, Highlight Members |
| Coords     | Fly to arbitrary (x, y, z) — "Use Current Position" populates from camera |
| Box        | Zoom to axis-aligned sub-box — "Use Current View" populates from camera |
| Console    | Shell terminal + Python REPL + SAGE natural-language commands. Multiple sessions, load scripts, pop-out window |
| Library    | Browse stored screenshots / movies, play back in the viewport |

The **Focus button** (top of the right panel) is tab-aware: it focuses on whatever's active in the current tab (target galaxy, environment halo, coords point, or box region).

## License

MIT — see [LICENSE](LICENSE).

## Citation

If you use SAGE-Viewer in published work, please cite:

```bibtex
@software{bradley_sage_viewer_2026,
  author = {Bradley, Michael},
  title  = {{SAGE-Viewer}: Interactive 3D Visualization for SAGE Galaxy Formation Outputs},
  year   = {2026},
  url    = {https://github.com/MBradley1985/SAGE-Viewer}
}
```

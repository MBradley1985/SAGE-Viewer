# API Reference

ViSAGE exposes a Python API for scripting, integration with notebooks, and extending the viewer.

## IO layer

### `visage.io.par_reader`

::: visage.io.par_reader.parse_par

### `visage.io.snapshot_table`

::: visage.io.snapshot_table.SnapshotTable

### `visage.io.halo_reader`

::: visage.io.halo_reader.load_halo_snapshot
::: visage.io.halo_reader.HaloSnapshot

### `visage.io.galaxy_reader`

::: visage.io.galaxy_reader.load_galaxy_snapshot
::: visage.io.galaxy_reader.GalaxySnapshot

## Scene layer

### `visage.scene.scene`

::: visage.scene.scene.Scene

### `visage.scene.camera`

::: visage.scene.camera.CameraController

### `visage.scene.halo_layer`

::: visage.scene.halo_layer.HaloLayer

### `visage.scene.galaxy_layer`

::: visage.scene.galaxy_layer.GalaxyLayer

## Parallel loader

::: visage.parallel.loader.SnapshotLoader

## Utilities

::: visage.utils.colormap
::: visage.utils.sizing
::: visage.utils.kdtree.NearestHaloIndex

## App

::: visage.app.create_app

## Example: headless snapshot render

```python
from visage.io import parse_par, SnapshotTable
from visage.io.halo_reader import load_halo_snapshot
from visage.io.galaxy_reader import load_galaxy_snapshot
import pyvista as pv

cfg = parse_par("input/millennium.par")
snap_table = SnapshotTable(cfg.snap_list_path)

halos = load_halo_snapshot(cfg.tree_dir, cfg.tree_name, snap_num=63)
galaxies = load_galaxy_snapshot(cfg.hdf5_path, snap_num=63)

pl = pv.Plotter(off_screen=True)
pl.add_points(halos.positions, color="cyan", opacity=0.02, point_size=3)
pl.add_points(galaxies.positions, color="white", point_size=2)
pl.screenshot("snapshot_63.png")
```

# API Reference

SAGE-Viewer exposes a Python API for scripting, integration with notebooks, and extending the viewer.

## IO layer

### `sage_viewer.io.par_reader`

::: sage_viewer.io.par_reader.parse_par

### `sage_viewer.io.snapshot_table`

::: sage_viewer.io.snapshot_table.SnapshotTable

### `sage_viewer.io.halo_reader`

::: sage_viewer.io.halo_reader.load_halo_snapshot
::: sage_viewer.io.halo_reader.HaloSnapshot

### `sage_viewer.io.galaxy_reader`

::: sage_viewer.io.galaxy_reader.load_galaxy_snapshot
::: sage_viewer.io.galaxy_reader.GalaxySnapshot

## Scene layer

### `sage_viewer.scene.scene`

::: sage_viewer.scene.scene.Scene

### `sage_viewer.scene.camera`

::: sage_viewer.scene.camera.CameraController

### `sage_viewer.scene.halo_layer`

::: sage_viewer.scene.halo_layer.HaloLayer

### `sage_viewer.scene.galaxy_layer`

::: sage_viewer.scene.galaxy_layer.GalaxyLayer

## Parallel loader

::: sage_viewer.parallel.loader.SnapshotLoader

## Utilities

::: sage_viewer.utils.colormap
::: sage_viewer.utils.sizing
::: sage_viewer.utils.kdtree.NearestHaloIndex

## App

::: sage_viewer.app.create_app

## Example: headless snapshot render

```python
from sage_viewer.io import parse_par, SnapshotTable
from sage_viewer.io.halo_reader import load_halo_snapshot
from sage_viewer.io.galaxy_reader import load_galaxy_snapshot
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

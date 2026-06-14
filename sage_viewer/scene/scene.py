from __future__ import annotations

from typing import Callable

import pyvista as pv

from sage_viewer.config import SimConfig
from sage_viewer.io.snapshot_table import SnapshotTable
from sage_viewer.parallel.loader import SnapshotLoader
from sage_viewer.scene.camera import CameraController
from sage_viewer.scene.galaxy_layer import GalaxyLayer
from sage_viewer.scene.halo_layer import HaloLayer


class Scene:
    """Owner of the PyVista plotter, data layers, and snapshot state.

    Playback animation is driven externally by the Trame async event loop
    (see toolbar.py) so that all VTK calls stay on the main thread.
    """

    def __init__(
        self,
        config: SimConfig,
        snap_table: SnapshotTable,
        loader: SnapshotLoader,
        off_screen: bool = False,
        initial_snap: int | None = None,
    ) -> None:
        self._cfg = config
        self._snap_table = snap_table
        self._loader = loader

        self._plotter = pv.Plotter(off_screen=off_screen, window_size=[1600, 900])
        self._plotter.set_background("black")

        self._halo_layer   = HaloLayer(self._plotter)
        self._galaxy_layer = GalaxyLayer(self._plotter)
        self._camera       = CameraController(self._plotter, config.box_size)

        self._current_snap: int = (
            initial_snap if initial_snap is not None else snap_table.count - 1
        )

        self._on_snap_change: list[Callable[[int], None]] = []
        self._focus_region: dict | None = None   # stores last zoom params for re-masking

        self.set_snapshot(self._current_snap)
        self._camera.reset()

    # ------------------------------------------------------------------
    # Layer / plotter access
    # ------------------------------------------------------------------

    @property
    def halo_layer(self) -> HaloLayer:
        return self._halo_layer

    @property
    def galaxy_layer(self) -> GalaxyLayer:
        return self._galaxy_layer

    @property
    def camera(self) -> CameraController:
        return self._camera

    @property
    def plotter(self) -> pv.Plotter:
        return self._plotter

    @property
    def current_snap(self) -> int:
        return self._current_snap

    @property
    def snap_label(self) -> str:
        return self._snap_table.label(self._current_snap)

    # ------------------------------------------------------------------
    # Snapshot control  (always called from main / Trame event-loop thread)
    # ------------------------------------------------------------------

    def set_snapshot(self, snap_num: int) -> None:
        snap_num = max(0, min(int(snap_num), self._snap_table.count - 1))
        self._current_snap = snap_num

        halos, galaxies = self._loader.get(snap_num)
        self._halo_layer.update(halos)
        self._galaxy_layer.update(galaxies)
        self._camera.update_halo_index(halos.positions)
        self._camera.update_galaxy_positions(galaxies.positions)

        # Re-apply any active focus mask to the new snapshot data
        if self._focus_region is not None:
            self._apply_focus_masks(halos.positions, galaxies.positions)

        for cb in self._on_snap_change:
            cb(snap_num)

    # ------------------------------------------------------------------
    # Focus / spatial masking
    # ------------------------------------------------------------------

    def set_focus_box(
        self,
        xmin: float, xmax: float,
        ymin: float, ymax: float,
        zmin: float, zmax: float,
    ) -> None:
        self._focus_region = dict(type="box", xmin=xmin, xmax=xmax,
                                  ymin=ymin, ymax=ymax, zmin=zmin, zmax=zmax)
        halos, galaxies = self._loader.get(self._current_snap)
        self._apply_focus_masks(halos.positions, galaxies.positions)

    def set_focus_sphere(
        self,
        center: tuple[float, float, float],
        radius: float,
    ) -> None:
        self._focus_region = dict(type="sphere", center=center, radius=radius)
        halos, galaxies = self._loader.get(self._current_snap)
        self._apply_focus_masks(halos.positions, galaxies.positions)

    def clear_focus(self) -> None:
        self._focus_region = None
        self._halo_layer.set_mask(None)
        self._galaxy_layer.set_mask(None)

    def _apply_focus_masks(
        self,
        halo_pos: "np.ndarray",
        gal_pos: "np.ndarray",
    ) -> None:
        import numpy as np
        r = self._focus_region
        if r is None:
            return
        if r["type"] == "box":
            def _box_mask(pos):
                if len(pos) == 0:
                    return np.array([], dtype=bool)
                return (
                    (pos[:, 0] >= r["xmin"]) & (pos[:, 0] <= r["xmax"]) &
                    (pos[:, 1] >= r["ymin"]) & (pos[:, 1] <= r["ymax"]) &
                    (pos[:, 2] >= r["zmin"]) & (pos[:, 2] <= r["zmax"])
                )
            self._halo_layer.set_mask(_box_mask(halo_pos))
            self._galaxy_layer.set_mask(_box_mask(gal_pos))
        elif r["type"] == "sphere":
            cx, cy, cz = r["center"]
            rad = r["radius"]
            def _sphere_mask(pos):
                if len(pos) == 0:
                    return np.array([], dtype=bool)
                return np.linalg.norm(pos - np.array([cx, cy, cz]), axis=1) <= rad
            self._halo_layer.set_mask(_sphere_mask(halo_pos))
            self._galaxy_layer.set_mask(_sphere_mask(gal_pos))

    def next_snap_num(self) -> int:
        return (self._current_snap + 1) % self._snap_table.count

    def prev_snap_num(self) -> int:
        return (self._current_snap - 1) % self._snap_table.count

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def register_snap_change_callback(self, cb: Callable[[int], None]) -> None:
        self._on_snap_change.append(cb)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._loader.shutdown()
        self._plotter.close()

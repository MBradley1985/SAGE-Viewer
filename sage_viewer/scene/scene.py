from __future__ import annotations

import threading
import time
from typing import Callable

import pyvista as pv

from sage_viewer.config import SimConfig
from sage_viewer.io.snapshot_table import SnapshotTable
from sage_viewer.parallel.loader import SnapshotLoader
from sage_viewer.scene.camera import CameraController
from sage_viewer.scene.galaxy_layer import GalaxyLayer
from sage_viewer.scene.halo_layer import HaloLayer


class Scene:
    """Top-level owner of the PyVista plotter, data layers, and playback state.

    Wired up by app.py and driven by Trame UI callbacks.
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

        self._halo_layer = HaloLayer(self._plotter)
        self._galaxy_layer = GalaxyLayer(self._plotter)
        self._camera = CameraController(self._plotter, config.box_size)

        self._current_snap: int = (
            initial_snap
            if initial_snap is not None
            else snap_table.count - 1
        )
        self._playing = False
        self._play_fps: float = 5.0
        self._play_thread: threading.Thread | None = None

        # Callbacks registered by the UI to receive state updates
        self._on_snap_change: list[Callable[[int], None]] = []

        # Load the initial snapshot
        self.set_snapshot(self._current_snap)
        self._camera.reset()

    # ------------------------------------------------------------------
    # Layer access
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
    # Snapshot control
    # ------------------------------------------------------------------

    def set_snapshot(self, snap_num: int) -> None:
        snap_num = int(snap_num)
        snap_num = max(0, min(snap_num, self._snap_table.count - 1))
        self._current_snap = snap_num

        halos, galaxies = self._loader.get(snap_num)
        self._halo_layer.update(halos)
        self._galaxy_layer.update(galaxies)
        self._camera.update_halo_index(halos.positions)
        self._camera.update_galaxy_positions(galaxies.positions)

        for cb in self._on_snap_change:
            cb(snap_num)

    def next_snapshot(self) -> None:
        next_s = (self._current_snap + 1) % self._snap_table.count
        self.set_snapshot(next_s)

    def prev_snapshot(self) -> None:
        prev_s = (self._current_snap - 1) % self._snap_table.count
        self.set_snapshot(prev_s)

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def play(self, fps: float = 5.0) -> None:
        if self._playing:
            return
        self._playing = True
        self._play_fps = fps
        self._play_thread = threading.Thread(
            target=self._play_loop, daemon=True
        )
        self._play_thread.start()

    def pause(self) -> None:
        self._playing = False

    def stop(self) -> None:
        self._playing = False
        self.set_snapshot(self._snap_table.count - 1)

    def _play_loop(self) -> None:
        interval = 1.0 / max(self._play_fps, 0.1)
        while self._playing:
            self.next_snapshot()
            time.sleep(interval)

    # ------------------------------------------------------------------
    # UI callbacks
    # ------------------------------------------------------------------

    def register_snap_change_callback(self, cb: Callable[[int], None]) -> None:
        self._on_snap_change.append(cb)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._playing = False
        self._loader.shutdown()
        self._plotter.close()

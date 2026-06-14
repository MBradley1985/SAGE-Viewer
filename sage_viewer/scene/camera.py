from __future__ import annotations

import numpy as np
import pyvista as pv

from sage_viewer.utils.kdtree import NearestHaloIndex


class CameraController:
    """High-level camera operations on top of a PyVista Plotter.

    All coordinate arguments are in Mpc/h, matching the simulation box units.
    """

    def __init__(self, plotter: pv.Plotter, box_size: float = 62.5) -> None:
        self._pl = plotter
        self._box_size = box_size
        self._halo_index: NearestHaloIndex = NearestHaloIndex()
        self._galaxy_positions: np.ndarray | None = None

    # ------------------------------------------------------------------
    # Index updates (called by Scene on snapshot change)
    # ------------------------------------------------------------------

    def update_halo_index(self, positions: np.ndarray) -> None:
        if len(positions) > 0:
            self._halo_index.update(positions)

    def update_galaxy_positions(self, positions: np.ndarray) -> None:
        self._galaxy_positions = positions

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Fit the full simulation box in view."""
        half = self._box_size / 2.0
        self._pl.camera.focal_point = (half, half, half)
        self._pl.camera.position = (half, half, self._box_size * 2.5)
        self._pl.camera.up = (0.0, 1.0, 0.0)
        self._pl.reset_camera()

    def go_to_coords(
        self,
        x: float,
        y: float,
        z: float,
        distance: float = 5.0,
    ) -> None:
        """Point camera at (x, y, z) from a given standoff distance."""
        self._pl.camera.focal_point = (x, y, z)
        self._pl.camera.position = (x, y, z + distance)
        self._pl.camera.up = (0.0, 1.0, 0.0)

    def go_to_halo(self, halo_idx: int, distance: float = 5.0) -> None:
        """Fly to the halo at index halo_idx in the current snapshot."""
        pos = self._halo_index.position_of(halo_idx)
        self.go_to_coords(float(pos[0]), float(pos[1]), float(pos[2]), distance)

    def go_to_nearest_halo(
        self,
        x: float,
        y: float,
        z: float,
        distance: float = 5.0,
    ) -> int:
        """Fly to the halo nearest to the given coordinates. Returns its index."""
        idx = self._halo_index.nearest((x, y, z))
        self.go_to_halo(idx, distance)
        return idx

    def go_to_galaxy(self, galaxy_idx: int, distance: float = 2.0) -> None:
        """Fly to the galaxy at index galaxy_idx in the current snapshot."""
        if self._galaxy_positions is None or len(self._galaxy_positions) == 0:
            return
        pos = self._galaxy_positions[galaxy_idx]
        self.go_to_coords(float(pos[0]), float(pos[1]), float(pos[2]), distance)

    def zoom_to_radius(
        self,
        center: tuple[float, float, float],
        radius: float,
    ) -> None:
        """Frame a sphere of the given radius centred at center."""
        cx, cy, cz = center
        self._pl.camera.focal_point = center
        # Stand back far enough that the sphere fills roughly 60 % of the FOV
        fov_rad = np.deg2rad(self._pl.camera.view_angle)
        distance = radius / np.tan(fov_rad / 2.0) * 1.2
        self._pl.camera.position = (cx, cy, cz + distance)
        self._pl.camera.up = (0.0, 1.0, 0.0)

    def zoom_to_box(
        self,
        xmin: float,
        xmax: float,
        ymin: float,
        ymax: float,
        zmin: float,
        zmax: float,
    ) -> None:
        """Frame an arbitrary axis-aligned sub-box."""
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0
        cz = (zmin + zmax) / 2.0
        radius = max(xmax - xmin, ymax - ymin, zmax - zmin) / 2.0
        self.zoom_to_radius((cx, cy, cz), radius)

from __future__ import annotations

import numpy as np
import pyvista as pv

from sage_viewer.utils.kdtree import NearestHaloIndex

_INDICATOR_COLOR   = "#888888"
_INDICATOR_OPACITY = 0.35
_INDICATOR_WIDTH   = 1.5


class CameraController:
    """High-level camera operations on top of a PyVista Plotter.

    All coordinate arguments are in Mpc/h, matching the simulation box units.
    """

    def __init__(self, plotter: pv.Plotter, box_size: float = 62.5) -> None:
        self._pl = plotter
        self._box_size = box_size
        self._halo_index: NearestHaloIndex = NearestHaloIndex()
        self._galaxy_positions: np.ndarray | None = None
        self._indicator_actor = None

    # ------------------------------------------------------------------
    # Index updates (called by Scene on snapshot change)
    # ------------------------------------------------------------------

    def update_halo_index(self, positions: np.ndarray) -> None:
        if len(positions) > 0:
            self._halo_index.update(positions)

    def update_galaxy_positions(self, positions: np.ndarray) -> None:
        self._galaxy_positions = positions

    # ------------------------------------------------------------------
    # Zoom indicators
    # ------------------------------------------------------------------

    def _clear_indicator(self) -> None:
        if self._indicator_actor is None:
            return
        actors = self._indicator_actor if isinstance(self._indicator_actor, list) \
            else [self._indicator_actor]
        for a in actors:
            if a is not None:
                self._pl.remove_actor(a)
        self._indicator_actor = None

    def _add_box_indicator(
        self,
        xmin: float, xmax: float,
        ymin: float, ymax: float,
        zmin: float, zmax: float,
    ) -> None:
        self._clear_indicator()
        box = pv.Box(bounds=(xmin, xmax, ymin, ymax, zmin, zmax))
        self._indicator_actor = self._pl.add_mesh(
            box.extract_all_edges(),
            color=_INDICATOR_COLOR,
            opacity=_INDICATOR_OPACITY,
            line_width=_INDICATOR_WIDTH,
            render_lines_as_tubes=False,
        )

    def _add_sphere_indicator(
        self,
        center: tuple[float, float, float],
        radius: float,
    ) -> None:
        self._clear_indicator()
        sphere = pv.Sphere(radius=radius, center=center, theta_resolution=16, phi_resolution=16)
        self._indicator_actor = self._pl.add_mesh(
            sphere,
            color=_INDICATOR_COLOR,
            opacity=_INDICATOR_OPACITY,
            style="wireframe",
            line_width=_INDICATOR_WIDTH,
        )

    def _add_point_indicator(
        self,
        center: tuple[float, float, float],
        radius: float = 1.0,
    ) -> None:
        """Small sphere marking a specific halo or galaxy position."""
        self._clear_indicator()
        sphere = pv.Sphere(radius=radius, center=center, theta_resolution=12, phi_resolution=12)
        self._indicator_actor = self._pl.add_mesh(
            sphere,
            color=_INDICATOR_COLOR,
            opacity=_INDICATOR_OPACITY,
            style="wireframe",
            line_width=_INDICATOR_WIDTH,
        )

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Fit the full simulation box in view, centred on the box midpoint."""
        self._clear_indicator()
        half = self._box_size / 2.0
        self._pl.camera_position = [
            (half, half, self._box_size * 2.2),
            (half, half, half),
            (0.0, 1.0, 0.0),
        ]

    def go_to_coords(
        self,
        x: float,
        y: float,
        z: float,
        distance: float = 5.0,
    ) -> None:
        """Point camera at (x, y, z) from a given standoff distance."""
        self._clear_indicator()
        self._pl.camera.focal_point = (x, y, z)
        self._pl.camera.position    = (x, y, z + distance)
        self._pl.camera.up          = (0.0, 1.0, 0.0)

    def go_to_halo(self, halo_idx: int, distance: float = 5.0) -> None:
        """Fly to the halo at halo_idx and show a small sphere indicator."""
        pos = self._halo_index.position_of(halo_idx)
        cx, cy, cz = float(pos[0]), float(pos[1]), float(pos[2])
        self._pl.camera.focal_point = (cx, cy, cz)
        self._pl.camera.position    = (cx, cy, cz + distance)
        self._pl.camera.up          = (0.0, 1.0, 0.0)
        self._add_point_indicator((cx, cy, cz), radius=distance * 0.08)

    def go_to_nearest_halo(
        self,
        x: float,
        y: float,
        z: float,
        distance: float = 5.0,
    ) -> int:
        idx = self._halo_index.nearest((x, y, z))
        self.go_to_halo(idx, distance)
        return idx

    def go_to_galaxy(self, galaxy_idx: int, radius: float = 3.0) -> tuple:
        """Fly to galaxy_idx; camera sits on the sphere surface looking inward.

        A red circle marks the galaxy position. No sphere shown.
        Returns (cx, cy, cz) so callers can apply a focus sphere.
        """
        if self._galaxy_positions is None or len(self._galaxy_positions) == 0:
            return (0.0, 0.0, 0.0)
        pos = self._galaxy_positions[galaxy_idx]
        cx, cy, cz = float(pos[0]), float(pos[1]), float(pos[2])

        self._pl.camera.focal_point = (cx, cy, cz)
        self._pl.camera.position    = (cx, cy, cz + radius)
        self._pl.camera.up          = (0.0, 1.0, 0.0)

        self._add_circle_indicator((cx, cy, cz), radius * 0.015)
        return (cx, cy, cz)

    def _add_circle_indicator(
        self,
        center: tuple[float, float, float],
        radius: float,
    ) -> None:
        """Red circle ring face-on to the camera, centred on the target galaxy."""
        self._clear_indicator()
        c = np.array(center, dtype=np.float64)

        # Build two orthogonal axes in the plane perpendicular to the view ray
        cam = np.array(self._pl.camera.position, dtype=np.float64)
        view = cam - c
        norm = np.linalg.norm(view)
        if norm < 1e-10:
            return
        view /= norm

        up = np.array([0.0, 1.0, 0.0])
        if abs(np.dot(view, up)) > 0.99:   # nearly parallel — use X instead
            up = np.array([1.0, 0.0, 0.0])
        right = np.cross(view, up)
        right /= np.linalg.norm(right)
        up_perp = np.cross(right, view)
        up_perp /= np.linalg.norm(up_perp)

        theta = np.linspace(0, 2 * np.pi, 128, endpoint=False)
        pts = c + radius * (
            np.outer(np.cos(theta), right) + np.outer(np.sin(theta), up_perp)
        )
        pts = np.vstack([pts, pts[0]])     # close the ring
        circle = pv.lines_from_points(pts)
        self._indicator_actor = self._pl.add_mesh(
            circle,
            color="red",
            line_width=2.0,
            opacity=0.95,
        )

    def zoom_to_radius(
        self,
        center: tuple[float, float, float],
        radius: float,
    ) -> None:
        """Frame a sphere of the given radius and draw a wireframe sphere indicator."""
        cx, cy, cz = center
        fov_rad  = np.deg2rad(self._pl.camera.view_angle)
        distance = radius / np.tan(fov_rad / 2.0) * 1.2
        self._pl.camera.focal_point = center
        self._pl.camera.position    = (cx, cy, cz + distance)
        self._pl.camera.up          = (0.0, 1.0, 0.0)
        self._add_sphere_indicator(center, radius)

    def zoom_to_box(
        self,
        xmin: float, xmax: float,
        ymin: float, ymax: float,
        zmin: float, zmax: float,
    ) -> None:
        """Frame an axis-aligned sub-box and draw a wireframe box indicator."""
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0
        cz = (zmin + zmax) / 2.0
        radius = max(xmax - xmin, ymax - ymin, zmax - zmin) / 2.0
        fov_rad  = np.deg2rad(self._pl.camera.view_angle)
        distance = radius / np.tan(fov_rad / 2.0) * 1.2
        self._pl.camera.focal_point = (cx, cy, cz)
        self._pl.camera.position    = (cx, cy, cz + distance)
        self._pl.camera.up          = (0.0, 1.0, 0.0)
        self._add_box_indicator(xmin, xmax, ymin, ymax, zmin, zmax)

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
        self._member_actor = None     # cyan splats for FOF group members
        self._selected_actor = None   # green splat for the selected galaxy itself
        self._central_actor = None    # thin white outline marking the FOF central
        self._group_ring_actor = None # red ring sized to enclose the group

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
                self._pl.remove_actor(a, render=False)
        self._indicator_actor = None

    def _clear_member_indicators(self) -> None:
        for attr in ("_member_actor", "_selected_actor"):
            a = getattr(self, attr, None)
            if a is not None:
                self._pl.remove_actor(a, render=False)
                setattr(self, attr, None)

    def _add_member_indicators(self, positions: "np.ndarray") -> None:
        """Cyan gaussian splats for FOF group members (excluding the selected galaxy)."""
        if self._member_actor is not None:
            self._pl.remove_actor(self._member_actor, render=False)
            self._member_actor = None
        if positions is None or len(positions) == 0:
            return
        cloud = pv.PolyData(np.asarray(positions, dtype=np.float64))
        self._member_actor = self._pl.add_mesh(
            cloud,
            color="cyan",
            point_size=24.0,
            render_points_as_spheres=True,
            opacity=0.55,
            show_scalar_bar=False,
            render=False,
            reset_camera=False,
        )

    def _add_selected_indicator(self, position: "np.ndarray") -> None:
        """Green gaussian splat marking the selected galaxy itself."""
        if self._selected_actor is not None:
            self._pl.remove_actor(self._selected_actor, render=False)
            self._selected_actor = None
        if position is None:
            return
        cloud = pv.PolyData(np.asarray([position], dtype=np.float64))
        self._selected_actor = self._pl.add_mesh(
            cloud,
            color="lime",
            point_size=28.0,
            render_points_as_spheres=True,
            opacity=0.75,
            show_scalar_bar=False,
            render=False,
            reset_camera=False,
        )

    @property
    def has_member_indicators(self) -> bool:
        return self._member_actor is not None or self._selected_actor is not None

    # ---- White central marker -----------------------------------------

    def _clear_central_indicator(self) -> None:
        if self._central_actor is None:
            return
        self._pl.remove_actor(self._central_actor, render=False)
        self._central_actor = None

    def _add_central_indicator(self, center: tuple[float, float, float]) -> None:
        """Thin white screen-space ring marking the FOF central."""
        self._clear_central_indicator()
        cloud = pv.PolyData(np.array([center], dtype=np.float64))
        self._central_actor = self._pl.add_mesh(
            cloud,
            color="white",
            point_size=22.0,
            render_points_as_spheres=False,
            opacity=0.95,
            show_scalar_bar=False,
            render=False,
            reset_camera=False,
        )

    # ---- Group-sized red circle ---------------------------------------

    def _clear_group_ring(self) -> None:
        if self._group_ring_actor is None:
            return
        self._pl.remove_actor(self._group_ring_actor, render=False)
        self._group_ring_actor = None

    def _add_group_ring(
        self,
        center: tuple[float, float, float],
        radius: float,
    ) -> None:
        """Red ring face-on to the camera, sized to enclose the whole group."""
        self._clear_group_ring()
        if radius <= 0:
            return
        c = np.array(center, dtype=np.float64)
        cam = np.array(self._pl.camera.position, dtype=np.float64)
        view = cam - c
        norm = np.linalg.norm(view)
        if norm < 1e-10:
            return
        view /= norm
        up = np.array([0.0, 1.0, 0.0])
        if abs(np.dot(view, up)) > 0.99:
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
        self._group_ring_actor = self._pl.add_mesh(
            circle,
            color="red",
            line_width=2.0,
            opacity=0.9,
            render=False,
            reset_camera=False,
        )

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
        """Three orthogonal great-circle rings — minimal wireframe look,
        much sparser than a full sphere mesh."""
        self._clear_indicator()
        cx, cy, cz = center
        t = np.linspace(0.0, 2.0 * np.pi, 64, dtype=np.float64)
        c, s = np.cos(t) * radius, np.sin(t) * radius
        # 1 equator (XY) + 4 meridians around the polar (Z) axis at
        # azimuths 0°, 45°, 90°, 135°.
        rings = [np.column_stack([cx + c, cy + s, np.full_like(c, cz)])]
        for deg in (0.0, 45.0, 90.0, 135.0):
            ca, sa = np.cos(np.deg2rad(deg)), np.sin(np.deg2rad(deg))
            rings.append(np.column_stack([cx + c * ca, cy + c * sa, cz + s]))
        # Build one PolyData with 5 closed polylines.
        all_pts = np.vstack(rings)
        n = len(t)
        n_rings = len(rings)
        lines = []
        for i in range(n_rings):
            lines.append(n + 1)
            lines.extend([i * n + j for j in range(n)])
            lines.append(i * n)   # close the loop
        poly = pv.PolyData(all_pts)
        # pv.PolyData(points) auto-creates a verts cell per point, which
        # VTK renders as visible point markers. Strip them so we get
        # pure lines.
        poly.verts = np.empty(0, dtype=np.int64)
        poly.lines = np.array(lines, dtype=np.int64)
        self._indicator_actor = self._pl.add_mesh(
            poly,
            color=_INDICATOR_COLOR,
            opacity=_INDICATOR_OPACITY,
            line_width=_INDICATOR_WIDTH,
            style="wireframe",
            render_points_as_spheres=False,
            point_size=0,
        )
        # Belt-and-braces: explicitly turn off vertex rendering on the
        # actor's property so VTK never draws point markers at the ring
        # vertices.
        try:
            self._indicator_actor.GetProperty().SetRenderPointsAsSpheres(False)
            self._indicator_actor.GetProperty().SetVertexVisibility(False)
            self._indicator_actor.GetProperty().SetPointSize(0)
        except Exception:
            pass

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

    def go_to_box_center(self) -> None:
        """Place the camera AT the box centre, looking along +z."""
        self._clear_indicator()
        half = self._box_size / 2.0
        self._pl.camera.focal_point = (half, half, half + 1.0)
        self._pl.camera.position    = (half, half, half)
        self._pl.camera.up          = (0.0, 1.0, 0.0)

    # ------------------------------------------------------------------
    # Keyboard fly movement
    # ------------------------------------------------------------------

    def fly(self, direction: str, step_frac: float = 0.012) -> None:
        """Translate the camera (and its focal point) one step in a view-
        relative direction. Because both move together this is a true fly —
        it carries the camera through the box centre and out the far side,
        unlike trackball dolly/orbit which stall at the focal point.

        direction: 'forward' | 'back' | 'left' | 'right' | 'up' | 'down'.
        """
        cam   = self._pl.camera
        pos   = np.array(cam.position,    dtype=np.float64)
        focal = np.array(cam.focal_point, dtype=np.float64)

        view = focal - pos
        nv = np.linalg.norm(view)
        if nv < 1e-9:
            return
        view /= nv
        up = np.array(cam.up, dtype=np.float64)
        nu = np.linalg.norm(up)
        up = up / nu if nu > 1e-9 else np.array([0.0, 1.0, 0.0])
        right = np.cross(view, up)
        nr = np.linalg.norm(right)
        right = right / nr if nr > 1e-9 else np.array([1.0, 0.0, 0.0])
        up = np.cross(right, view)   # re-orthonormalise

        basis = {
            "forward": view, "back": -view,
            "right": right,  "left": -right,
            "up": up,        "down": -up,
        }
        d = basis.get(direction)
        if d is None:
            return

        delta = d * (self._box_size * float(step_frac))
        cam.position    = tuple(pos + delta)
        cam.focal_point = tuple(focal + delta)
        # Keep near/far planes around the scene so nothing gets clipped as we
        # move through it — this is what stops geometry vanishing mid-box.
        self._pl.renderer.ResetCameraClippingRange()

    def go_to_coords(
        self,
        x: float,
        y: float,
        z: float,
        distance: float = 5.0,
    ) -> None:
        """Point camera at (x, y, z) from a given standoff distance, and
        draw a wireframe sphere of radius `distance` at the target so the
        focus region is visible (matches the Box-mode wireframe convention)."""
        self._pl.camera.focal_point = (x, y, z)
        self._pl.camera.position    = (x, y, z + distance)
        self._pl.camera.up          = (0.0, 1.0, 0.0)
        self._add_sphere_indicator((x, y, z), distance)

    def go_to_halo(self, halo_idx: int, distance: float = 5.0) -> None:
        """Fly to the halo at halo_idx and mark it with a red circle."""
        pos = self._halo_index.position_of(halo_idx)
        cx, cy, cz = float(pos[0]), float(pos[1]), float(pos[2])
        self._pl.camera.focal_point = (cx, cy, cz)
        self._pl.camera.position    = (cx, cy, cz + distance)
        self._pl.camera.up          = (0.0, 1.0, 0.0)
        self._add_circle_indicator((cx, cy, cz), distance * 0.015)

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
        """Soft red sphere centred on the target — always camera-facing."""
        self._clear_indicator()
        cloud = pv.PolyData(np.array([center], dtype=np.float64))
        self._indicator_actor = self._pl.add_mesh(
            cloud,
            color="firebrick",
            point_size=60.0,
            render_points_as_spheres=True,
            opacity=0.15,
            show_scalar_bar=False,
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

from __future__ import annotations

import numpy as np
from scipy.spatial import KDTree
from trame.widgets import vuetify3 as v3

from sage_viewer.scene.scene import Scene


def build_info_panel(server, scene: Scene) -> None:
    """Footer pick-info bar + left-click galaxy selection."""
    state = server.state
    state.pick_info = "Left-click any point to select the nearest galaxy"

    def _push():
        if hasattr(server.controller, "view_update"):
            server.controller.view_update()

    def _on_pick(point):
        """PyVista 0.44+ passes the 3D world-space point directly."""
        if point is None:
            return
        point = np.asarray(point, dtype=np.float64)
        if np.all(np.abs(point) < 1e-10):
            return

        halos, galaxies = scene._loader.get(scene.current_snap)
        lines = [f"({point[0]:.2f}, {point[1]:.2f}, {point[2]:.2f}) Mpc/h"]

        # Nearest halo info
        if halos.count > 0:
            hidx = scene.camera._halo_index.nearest(tuple(point))
            hm = halos.masses[hidx]
            lines.append(f"Halo Mvir = {hm:.2e} Msun (idx {hidx})")

        # Nearest galaxy — select it and update the nav panel
        if galaxies.count > 0:
            _, gidx = KDTree(galaxies.positions).query(point)
            gidx = int(gidx)
            sm = galaxies.stellar_mass[gidx]
            ss = galaxies.ssfr[gidx]
            gt = "central" if galaxies.gal_type[gidx] == 0 else "satellite"
            lines.append(
                f"Galaxy M* = {sm:.2e} Msun  sSFR = {ss:.2e} yr⁻¹  "
                f"({gt})  →  idx {gidx} selected"
            )

            # Update the galaxy index field in the nav panel
            state.nav_gal_idx = gidx
            # Flush so the VTextField updates immediately (PyVista callbacks
            # run outside Trame's event dispatch and need an explicit flush)
            state.flush()

            # Red circle scaled to camera distance
            gpos = galaxies.positions[gidx]
            cam_pos = np.array(scene.plotter.camera.position)
            dist = float(np.linalg.norm(cam_pos - gpos))
            circle_r = max(dist * 0.008, 0.02)
            scene.camera._add_circle_indicator(
                (float(gpos[0]), float(gpos[1]), float(gpos[2])),
                circle_r,
            )
            _push()

        state.pick_info = "   |   ".join(lines)

    scene.plotter.enable_point_picking(
        callback=_on_pick,
        show_message=False,
        show_point=False,
        left_clicking=True,
        tolerance=0.025,
    )

    v3.VLabel(
        ("pick_info",),
        style=(
            "font-size:0.75rem; font-family:monospace;"
            " color:#9ca3af; padding:0 12px; line-height:36px;"
        ),
    )

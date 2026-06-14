from __future__ import annotations

import numpy as np
from trame.widgets import vuetify3 as v3

from sage_viewer.scene.scene import Scene


def build_info_panel(server, scene: Scene) -> None:
    """Bottom status bar showing picked-point info.

    PyVista's point-pick callback fires when the user clicks a point in the
    render window. We look up the nearest halo and galaxy and display their
    properties.
    """
    state = server.state

    state.pick_info = "Click a point to inspect"

    def _on_pick(mesh, pid):
        if mesh is None:
            state.pick_info = "No point selected"
            return

        pos = mesh.points[pid] if pid < len(mesh.points) else None
        if pos is None:
            return

        lines = [f"Position: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f}) Mpc/h"]

        # Nearest halo info
        snap = scene.current_snap
        halos, galaxies = scene._loader.get(snap)

        if halos.count > 0:
            idx = scene.camera._halo_index.nearest(tuple(pos))
            hm = halos.masses[idx]
            lines.append(f"Nearest halo  Mvir = {hm:.2e} Msun  (idx {idx})")

        if galaxies.count > 0:
            from scipy.spatial import KDTree as _KDT
            _, gidx = _KDT(galaxies.positions).query(pos)
            sm = galaxies.stellar_mass[gidx]
            ss = galaxies.ssfr[gidx]
            gt = "central" if galaxies.gal_type[gidx] == 0 else "satellite"
            lines.append(
                f"Nearest galaxy  M* = {sm:.2e} Msun  "
                f"sSFR = {ss:.2e} yr⁻¹  ({gt}  idx {gidx})"
            )

        state.pick_info = "   |   ".join(lines)

    scene.plotter.enable_point_picking(
        callback=_on_pick,
        use_picker=True,
        show_message=False,
    )

    with v3.VFooter(color="#0d0d1a", height=36):
        v3.VLabel(
            ("pick_info",),
            style="font-size:0.75rem; font-family:monospace; color:#9ca3af;",
        )

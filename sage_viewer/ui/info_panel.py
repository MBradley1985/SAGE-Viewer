from __future__ import annotations

import time

import numpy as np
from scipy.spatial import KDTree
from trame.widgets import vuetify3 as v3

from sage_viewer.scene.scene import Scene

_DOUBLE_CLICK_THRESHOLD = 0.45   # seconds between two clicks to count as double-click


def build_info_panel(server, scene: Scene) -> None:
    """Footer pick-info bar + double-click galaxy selection."""
    state = server.state
    state.pick_info = "Double-click any point to select the nearest galaxy"

    _last_click: list[float] = [0.0]

    def _push():
        if hasattr(server.controller, "view_update"):
            server.controller.view_update()

    def _on_pick(point):
        """Fires on every left-click; only selects on a fast second click."""
        now = time.monotonic()
        dt, _last_click[0] = now - _last_click[0], now

        # Box activation: every click checks which box was clicked by world-X coord.
        if point is not None:
            pt = np.asarray(point, dtype=np.float64)
            if not np.all(np.abs(pt) < 1e-10):
                clicked_box = scene.box_name_at(float(pt[0]))
                if clicked_box != scene.active_box_name:
                    if hasattr(server.controller, "set_active_box"):
                        server.controller.set_active_box(clicked_box)

        if dt > _DOUBLE_CLICK_THRESHOLD:
            # First click — ignore; wait for the matching second click.
            return

        # Second click fired in time — reset the timer so the next click
        # starts a fresh double-click cycle (avoids triple-click cascades).
        _last_click[0] = 0.0

        if point is None:
            return
        point = np.asarray(point, dtype=np.float64)
        if np.all(np.abs(point) < 1e-10):
            return

        # Use the active model so double-click selection works in any box.
        active = scene.active_model
        halos, galaxies = active.loader.get(active.current_snap)
        off = active.offset.astype(np.float64)
        lines = [f"({point[0]:.2f}, {point[1]:.2f}, {point[2]:.2f}) Mpc/h"]

        # Nearest halo — record into nav_halo_idx so the Environment tab's
        # halo selector reflects what the user just double-clicked.
        # Camera halo index is built in world coords so point is used directly.
        if halos.count > 0:
            hidx = scene.camera._halo_index.nearest(tuple(point))
            hm = halos.masses[hidx]
            lines.append(f"Halo Mvir = {hm:.2e} Msun (idx {hidx})")
            state.nav_halo_idx = int(hidx)

        # Nearest galaxy — only among currently visible galaxies so that
        # environment filters, focus regions, and slider filters are all
        # respected: you can only click what you can see.
        if galaxies.count > 0:
            mask = scene.galaxy_layer._combined_mask()
            if mask is None:
                visible = np.arange(galaxies.count)
            else:
                visible = np.where(mask)[0]

            if len(visible) == 0:
                gidx = None
            else:
                # Galaxy positions are model-local; add offset for world coords.
                gal_world = galaxies.positions[visible] + off
                _, hit = KDTree(gal_world).query(point)
                gidx = int(visible[hit])

            if gidx is not None:
                sm = galaxies.stellar_mass[gidx]
                ss = galaxies.ssfr[gidx]
                gt = "central" if galaxies.gal_type[gidx] == 0 else "satellite"
                lines.append(
                    f"Galaxy M* = {sm:.2e} Msun  sSFR = {ss:.2e} yr^-1  "
                    f"({gt})  →  idx {gidx} selected"
                )
                state.nav_gal_idx = gidx
                gpos = galaxies.positions[gidx] + off
                scene.camera._add_circle_indicator(
                    (float(gpos[0]), float(gpos[1]), float(gpos[2])), 0.0
                )

        state.flush()
        _push()

        state.pick_info = "   |   ".join(lines)

    # Picker is on globally: a double-click anywhere selects the nearest
    # galaxy and halo, placing a circle indicator but NOT moving the
    # camera or switching tabs. The user flies/navigates independently
    # and can press Go in the Target tab when ready.
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

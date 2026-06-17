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

        halos, galaxies = scene._loader.get(scene.current_snap)
        lines = [f"({point[0]:.2f}, {point[1]:.2f}, {point[2]:.2f}) Mpc/h"]

        # Nearest halo — record into nav_halo_idx so the Environment tab's
        # halo selector reflects what the user just double-clicked.
        if halos.count > 0:
            hidx = scene.camera._halo_index.nearest(tuple(point))
            hm = halos.masses[hidx]
            lines.append(f"Halo Mvir = {hm:.2e} Msun (idx {hidx})")
            state.nav_halo_idx = int(hidx)

        # Nearest galaxy — select it and update the nav panel
        if galaxies.count > 0:
            _, gidx = KDTree(galaxies.positions).query(point)
            gidx = int(gidx)
            sm = galaxies.stellar_mass[gidx]
            ss = galaxies.ssfr[gidx]
            gt = "central" if galaxies.gal_type[gidx] == 0 else "satellite"
            lines.append(
                f"Galaxy M* = {sm:.2e} Msun  sSFR = {ss:.2e} yr^-1  "
                f"({gt})  →  idx {gidx} selected"
            )

            # Update the galaxy index field in the nav panel
            state.nav_gal_idx = gidx

            # Always show a red marker at the picked galaxy so the user
            # has visual feedback for what they just selected, regardless
            # of focus / tab state.
            gpos = galaxies.positions[gidx]
            scene.camera._add_circle_indicator(
                (float(gpos[0]), float(gpos[1]), float(gpos[2])), 0.0
            )

            # If the user is already zoomed/focused on a region, carry
            # the camera to the new selection within that region (using
            # the last-used target radius). Without an active focus,
            # picking is purely declarative — no camera move.
            if bool(state.focus_active):
                try:
                    radius = float(state.nav_gal_last_radius)
                except (TypeError, ValueError):
                    radius = 10.0
                scene.camera.go_to_galaxy(int(gidx), radius)
                scene.set_focus_sphere(
                    (float(gpos[0]), float(gpos[1]), float(gpos[2])), radius
                )

        # Double-click is an "I want to look at this" signal: jump to
        # the Target tab so the user sees the populated galaxy / halo
        # IDs ready to act on.
        state.nav_active_tab = "target"
        state.flush()
        _push()

        state.pick_info = "   |   ".join(lines)

    # Picker is on globally: a double-click anywhere is the "I want to
    # inspect this object" gesture — it populates the Target tab's
    # galaxy + halo IDs and switches to that tab. Switching tabs must
    # NOT clear indicators (box / sphere / member dots) — exploring
    # panels is non-destructive; clearing is explicit (Reset / Go /
    # Clear / focus toggle).
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

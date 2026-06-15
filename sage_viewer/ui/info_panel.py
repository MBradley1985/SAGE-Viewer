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
                f"Galaxy M* = {sm:.2e} Msun  sSFR = {ss:.2e} yr⁻¹  "
                f"({gt})  →  idx {gidx} selected"
            )

            # Update the galaxy index field in the nav panel
            state.nav_gal_idx = gidx
            # Flush so the VTextField updates immediately (PyVista callbacks
            # run outside Trame's event dispatch and need an explicit flush)
            state.flush()

            gpos = galaxies.positions[gidx]
            scene.camera._add_circle_indicator(
                (float(gpos[0]), float(gpos[1]), float(gpos[2])), 0.0
            )
            _push()

        state.pick_info = "   |   ".join(lines)

    # Picker is only useful when actively selecting a target. Enable it only
    # when the Target tab is active so that clicks on other tabs don't trigger
    # an expensive ray-cast + render cycle.
    _picker_enabled = [False]

    def _enable_picker() -> None:
        if _picker_enabled[0]:
            return
        scene.plotter.enable_point_picking(
            callback=_on_pick,
            show_message=False,
            show_point=False,
            left_clicking=True,
            tolerance=0.025,
        )
        _picker_enabled[0] = True

    def _disable_picker() -> None:
        if not _picker_enabled[0]:
            return
        try:
            scene.plotter.disable_picking()
        except Exception:
            pass
        _picker_enabled[0] = False

    @state.change("nav_active_tab")
    def on_tab_for_picker(nav_active_tab, **_):
        # Picker is useful in both Target (per-galaxy info) and Environment
        # (group inspection) tabs — they both rely on a clicked selection.
        if nav_active_tab in ("target", "environment"):
            _enable_picker()
        else:
            _disable_picker()
            scene.camera._clear_indicator()
            scene.camera._clear_member_indicators()
            _push()


    v3.VLabel(
        ("pick_info",),
        style=(
            "font-size:0.75rem; font-family:monospace;"
            " color:#9ca3af; padding:0 12px; line-height:36px;"
        ),
    )

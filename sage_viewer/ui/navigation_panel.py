from __future__ import annotations

from trame.widgets import vuetify3 as v3

from sage_viewer.scene.scene import Scene


_SECTION = "font-size:0.7rem;font-weight:700;letter-spacing:0.08em;color:#06b6d4;padding:16px 0 8px;"
_FIELD   = "padding:8px 0 4px;"
_BTN     = "padding:10px 0 4px;"


def build_navigation_panel(server, scene: Scene) -> None:
    state, ctrl = server.state, server.controller

    state.nav_halo_idx = 0
    state.nav_gal_idx = 0
    state.nav_x = round(scene._cfg.box_size / 2, 2)
    state.nav_y = round(scene._cfg.box_size / 2, 2)
    state.nav_z = round(scene._cfg.box_size / 2, 2)
    state.nav_distance = 5.0
    state.nav_box_xmin = 0.0
    state.nav_box_xmax = round(scene._cfg.box_size / 2, 2)
    state.nav_box_ymin = 0.0
    state.nav_box_ymax = round(scene._cfg.box_size / 2, 2)
    state.nav_box_zmin = 0.0
    state.nav_box_zmax = round(scene._cfg.box_size / 2, 2)
    state.nav_status  = ""
    state.focus_active = False

    def _push():
        if hasattr(server.controller, "view_update"):
            server.controller.view_update()

    @ctrl.set("go_to_halo")
    def on_go_to_halo():
        try:
            scene.camera.go_to_halo(int(state.nav_halo_idx), state.nav_distance)
            state.nav_status = f"Flew to halo {state.nav_halo_idx}"
        except Exception as e:
            state.nav_status = f"Error: {e}"
        _push()

    def _go_to_galaxy_at_radius(radius: float) -> None:
        try:
            center = scene.camera.go_to_galaxy(int(state.nav_gal_idx), radius)
            if state.focus_active:
                scene.set_focus_sphere(center, radius)
            state.nav_status = f"Galaxy {state.nav_gal_idx} | zoom {radius} Mpc/h"
        except Exception as e:
            state.nav_status = f"Error: {e}"
        _push()

    @ctrl.set("go_to_galaxy_1")
    def on_go_to_galaxy_1():
        _go_to_galaxy_at_radius(1.0)

    @ctrl.set("go_to_galaxy_3")
    def on_go_to_galaxy_3():
        _go_to_galaxy_at_radius(3.0)

    @ctrl.set("go_to_galaxy_5")
    def on_go_to_galaxy_5():
        _go_to_galaxy_at_radius(5.0)

    @ctrl.set("go_to_coords")
    def on_go_to_coords():
        x, y, z, d = (
            float(state.nav_x), float(state.nav_y),
            float(state.nav_z), float(state.nav_distance),
        )
        scene.camera.go_to_coords(x, y, z, d)
        if state.focus_active:
            scene.set_focus_sphere((x, y, z), d)
        state.nav_status = f"Camera → ({x:.1f}, {y:.1f}, {z:.1f})"
        _push()

    @ctrl.set("zoom_to_box")
    def on_zoom_to_box():
        xmin, xmax = float(state.nav_box_xmin), float(state.nav_box_xmax)
        ymin, ymax = float(state.nav_box_ymin), float(state.nav_box_ymax)
        zmin, zmax = float(state.nav_box_zmin), float(state.nav_box_zmax)
        scene.camera.zoom_to_box(xmin, xmax, ymin, ymax, zmin, zmax)
        if state.focus_active:
            scene.set_focus_box(xmin, xmax, ymin, ymax, zmin, zmax)
        state.nav_status = "Zoomed to sub-box"
        _push()

    @ctrl.set("reset_camera")
    def on_reset():
        scene.camera.reset()
        if state.focus_active:
            scene.clear_focus()
            state.focus_active = False
        state.nav_status = "Camera reset"
        _push()

    @ctrl.set("toggle_focus")
    def on_toggle_focus():
        state.focus_active = not state.focus_active
        if not state.focus_active:
            scene.clear_focus()
            state.nav_status = "Focus off — showing all objects"
        else:
            state.nav_status = "Focus on — zoom to filter objects"
        _push()

    with v3.VSheet(color="#0d0d1a", style="padding:0 16px 16px;height:100%;color:#e2e8f0;"):

        # Reset + Focus row
        with v3.VSheet(color="transparent", style=_BTN):
            with v3.VRow(no_gutters=True, style="gap:6px;"):
                with v3.VCol(style="padding:0;"):
                    v3.VBtn(
                        "Reset Camera",
                        block=True, variant="outlined", color="cyan",
                        density="compact", click=ctrl.reset_camera,
                    )
                with v3.VCol(cols="auto", style="padding:0;"):
                    v3.VBtn(
                        icon="mdi-target",
                        variant="outlined",
                        density="compact",
                        click=ctrl.toggle_focus,
                        color=("focus_active ? 'cyan' : ''",),
                        title="Focus — hide objects outside zoom region",
                    )

        # ── Fly to Halo ──────────────────────────────────
        v3.VLabel("FLY TO HALO", style=_SECTION)
        with v3.VSheet(color="transparent", style=_FIELD):
            v3.VTextField(
                v_model=("nav_halo_idx",), label="Halo index",
                type="number", hide_details=True, variant="outlined", bg_color="#1a1a2e",
            )
        with v3.VSheet(color="transparent", style=_FIELD):
            v3.VTextField(
                v_model=("nav_distance",), label="Standoff (Mpc/h)",
                type="number", hide_details=True, variant="outlined", bg_color="#1a1a2e",
            )
        with v3.VSheet(color="transparent", style=_BTN):
            v3.VBtn("Go", block=True, color="cyan", density="compact", click=ctrl.go_to_halo)

        v3.VDivider(style="margin:12px 0;")

        # ── Fly to Galaxy ────────────────────────────────
        v3.VLabel("FLY TO GALAXY", style=_SECTION)
        with v3.VSheet(color="transparent", style=_FIELD):
            v3.VTextField(
                v_model=("nav_gal_idx",), label="Galaxy index",
                type="number", hide_details=True, variant="outlined", bg_color="#1a1a2e",
            )
        with v3.VSheet(color="transparent", style=_BTN):
            v3.VLabel(
                "Zoom radius (Mpc/h)",
                style="font-size:0.68rem;color:#9ca3af;display:block;padding-bottom:4px;",
            )
            with v3.VBtnGroup(variant="outlined", density="compact", style="width:100%;"):
                v3.VBtn(
                    "1", style="flex:1;", color="deep-purple",
                    click=ctrl.go_to_galaxy_1,
                )
                v3.VBtn(
                    "3", style="flex:1;", color="deep-purple",
                    click=ctrl.go_to_galaxy_3,
                )
                v3.VBtn(
                    "5", style="flex:1;", color="deep-purple",
                    click=ctrl.go_to_galaxy_5,
                )

        v3.VDivider(style="margin:12px 0;")

        # ── Fly to Coordinates ───────────────────────────
        v3.VLabel("FLY TO COORDINATES", style=_SECTION)
        for label, key in [("X (Mpc/h)", "nav_x"), ("Y (Mpc/h)", "nav_y"), ("Z (Mpc/h)", "nav_z")]:
            with v3.VSheet(color="transparent", style=_FIELD):
                v3.VTextField(
                    v_model=(key,), label=label,
                    type="number", hide_details=True, variant="outlined", bg_color="#1a1a2e",
                )
        with v3.VSheet(color="transparent", style=_BTN):
            v3.VBtn("Go", block=True, color="cyan", density="compact", click=ctrl.go_to_coords)

        v3.VDivider(style="margin:12px 0;")

        # ── Zoom to Sub-box ──────────────────────────────
        v3.VLabel("ZOOM TO SUB-BOX", style=_SECTION)
        for label, key in [
            ("X min", "nav_box_xmin"), ("X max", "nav_box_xmax"),
            ("Y min", "nav_box_ymin"), ("Y max", "nav_box_ymax"),
            ("Z min", "nav_box_zmin"), ("Z max", "nav_box_zmax"),
        ]:
            with v3.VSheet(color="transparent", style=_FIELD):
                v3.VTextField(
                    v_model=(key,), label=label,
                    type="number", hide_details=True, variant="outlined", bg_color="#1a1a2e",
                )
        with v3.VSheet(color="transparent", style=_BTN):
            v3.VBtn("Zoom", block=True, color="cyan", density="compact", click=ctrl.zoom_to_box)

        v3.VDivider(style="margin:12px 0;")

        v3.VLabel(
            ("nav_status",),
            style="font-size:0.72rem;color:#9ca3af;word-break:break-all;",
        )

from __future__ import annotations

from trame.widgets import vuetify3 as v3

from sage_viewer.scene.scene import Scene


def build_navigation_panel(server, scene: Scene) -> None:
    """Right sidebar panel: fly-to controls and camera reset."""
    state, ctrl = server.state, server.controller

    state.nav_halo_idx = 0
    state.nav_gal_idx = 0
    state.nav_x = 31.25
    state.nav_y = 31.25
    state.nav_z = 31.25
    state.nav_distance = 5.0
    state.nav_box_xmin = 0.0
    state.nav_box_xmax = 31.25
    state.nav_box_ymin = 0.0
    state.nav_box_ymax = 31.25
    state.nav_box_zmin = 0.0
    state.nav_box_zmax = 31.25
    state.nav_status = ""

    @ctrl.set("go_to_halo")
    def on_go_to_halo():
        try:
            scene.camera.go_to_halo(int(state.nav_halo_idx), state.nav_distance)
            state.nav_status = f"Flew to halo {state.nav_halo_idx}"
        except Exception as e:
            state.nav_status = f"Error: {e}"

    @ctrl.set("go_to_galaxy")
    def on_go_to_galaxy():
        try:
            scene.camera.go_to_galaxy(int(state.nav_gal_idx), state.nav_distance)
            state.nav_status = f"Flew to galaxy {state.nav_gal_idx}"
        except Exception as e:
            state.nav_status = f"Error: {e}"

    @ctrl.set("go_to_coords")
    def on_go_to_coords():
        scene.camera.go_to_coords(
            float(state.nav_x),
            float(state.nav_y),
            float(state.nav_z),
            float(state.nav_distance),
        )
        state.nav_status = (
            f"Camera at ({state.nav_x:.1f}, {state.nav_y:.1f},"
            f" {state.nav_z:.1f})"
        )

    @ctrl.set("zoom_to_box")
    def on_zoom_to_box():
        scene.camera.zoom_to_box(
            float(state.nav_box_xmin), float(state.nav_box_xmax),
            float(state.nav_box_ymin), float(state.nav_box_ymax),
            float(state.nav_box_zmin), float(state.nav_box_zmax),
        )
        state.nav_status = "Zoomed to sub-box"

    @ctrl.set("reset_camera")
    def on_reset():
        scene.camera.reset()
        state.nav_status = "Camera reset"

    with v3.VNavigationDrawer(
        permanent=True, location="right", width=280, color="#0d0d1a"
    ):
        with v3.VList(density="compact"):
            v3.VListSubheader("NAVIGATION", style="color:#06b6d4;")

            # Reset
            with v3.VListItem():
                v3.VBtn(
                    "Reset Camera",
                    block=True,
                    variant="outlined",
                    color="cyan",
                    density="compact",
                    click=ctrl.reset_camera,
                )

            v3.VDivider()
            v3.VListSubheader("Fly to Halo")
            with v3.VListItem():
                v3.VTextField(
                    v_model=("nav_halo_idx",),
                    label="Halo index",
                    type="number",
                    density="compact",
                    hide_details=True,
                )
            with v3.VListItem():
                v3.VTextField(
                    v_model=("nav_distance",),
                    label="Standoff (Mpc/h)",
                    type="number",
                    density="compact",
                    hide_details=True,
                )
            with v3.VListItem():
                v3.VBtn(
                    "Go",
                    block=True,
                    color="cyan",
                    density="compact",
                    click=ctrl.go_to_halo,
                )

            v3.VDivider()
            v3.VListSubheader("Fly to Galaxy")
            with v3.VListItem():
                v3.VTextField(
                    v_model=("nav_gal_idx",),
                    label="Galaxy index",
                    type="number",
                    density="compact",
                    hide_details=True,
                )
            with v3.VListItem():
                v3.VBtn(
                    "Go",
                    block=True,
                    color="deep-purple",
                    density="compact",
                    click=ctrl.go_to_galaxy,
                )

            v3.VDivider()
            v3.VListSubheader("Fly to Coordinates")
            for label, key in [("X (Mpc/h)", "nav_x"), ("Y", "nav_y"), ("Z", "nav_z")]:
                with v3.VListItem():
                    v3.VTextField(
                        v_model=(key,),
                        label=label,
                        type="number",
                        density="compact",
                        hide_details=True,
                    )
            with v3.VListItem():
                v3.VBtn(
                    "Go",
                    block=True,
                    color="cyan",
                    density="compact",
                    click=ctrl.go_to_coords,
                )

            v3.VDivider()
            v3.VListSubheader("Zoom to Sub-box")
            for label, key in [
                ("X min", "nav_box_xmin"), ("X max", "nav_box_xmax"),
                ("Y min", "nav_box_ymin"), ("Y max", "nav_box_ymax"),
                ("Z min", "nav_box_zmin"), ("Z max", "nav_box_zmax"),
            ]:
                with v3.VListItem():
                    v3.VTextField(
                        v_model=(key,),
                        label=label,
                        type="number",
                        density="compact",
                        hide_details=True,
                    )
            with v3.VListItem():
                v3.VBtn(
                    "Zoom",
                    block=True,
                    color="cyan",
                    density="compact",
                    click=ctrl.zoom_to_box,
                )

            v3.VDivider()
            # Status line
            with v3.VListItem():
                v3.VLabel(
                    ("nav_status",),
                    style="font-size:0.75rem; color:#9ca3af;",
                )

from __future__ import annotations

from trame.widgets import vuetify3 as v3

from sage_viewer.scene.scene import Scene


_FIELD = "padding:8px 0 4px;"
_BTN   = "padding:8px 0 4px;"

_HALO_MODES = [
    {"title": "Mvir", "value": "mvir"},
    {"title": "Rvir", "value": "rvir"},
    {"title": "Vvir", "value": "vvir"},
]

_GALAXY_MODES = [
    {"title": "Stellar Mass", "value": "stellar_mass"},
    {"title": "sSFR",         "value": "ssfr"},
    {"title": "SFR",          "value": "sfr"},
    {"title": "Cold Gas",     "value": "cold_gas"},
    {"title": "Bulge Mass",   "value": "bulge_mass"},
    {"title": "Density",      "value": "density"},
    {"title": "Type",         "value": "type"},
]

_CMAPS = [
    {"title": "Blues",    "value": "Blues"},
    {"title": "Purples",  "value": "Purples"},
    {"title": "Greens",   "value": "Greens"},
    {"title": "Oranges",  "value": "Oranges"},
    {"title": "Reds",     "value": "Reds"},
    {"title": "Viridis",  "value": "viridis"},
    {"title": "Plasma",   "value": "plasma"},
    {"title": "Inferno",  "value": "inferno"},
    {"title": "Magma",    "value": "magma"},
    {"title": "Cividis",  "value": "cividis"},
    {"title": "Coolwarm", "value": "coolwarm"},
    {"title": "RdBu",     "value": "RdBu"},
    {"title": "YlOrRd",   "value": "YlOrRd"},
    {"title": "Spectral", "value": "Spectral"},
]


_HALO_CB = {
    "mvir": ("Mvir",  "10¹⁰",  "10¹⁵ M☉"),
    "rvir": ("Rvir",  "0.03",  "3 Mpc/h"),
    "vvir": ("Vvir",  "30",    "1000 km/s"),
}


def build_navigation_panel(server, scene: Scene) -> None:
    state, ctrl = server.state, server.controller

    # Navigation state
    state.nav_halo_idx         = 0
    state.nav_gal_idx          = 0
    state.nav_gal_last_radius  = 1.0
    state.nav_x                = round(scene._cfg.box_size / 2, 2)
    state.nav_y                = round(scene._cfg.box_size / 2, 2)
    state.nav_z                = round(scene._cfg.box_size / 2, 2)
    state.nav_distance         = 5.0
    state.nav_box_xmin         = 0.0
    state.nav_box_xmax         = round(scene._cfg.box_size / 2, 2)
    state.nav_box_ymin         = 0.0
    state.nav_box_ymax         = round(scene._cfg.box_size / 2, 2)
    state.nav_box_zmin         = 0.0
    state.nav_box_zmax         = round(scene._cfg.box_size / 2, 2)
    state.focus_active         = False
    state.nav_active_tab       = "layers"

    # Colorbar state (reflects halo layer; updated when halo mode/cmap changes)
    from sage_viewer.utils.colormap import cmap_css_gradient
    _cb_label, _cb_min, _cb_max = _HALO_CB[scene.halo_layer.color_mode]
    state.colorbar_gradient = cmap_css_gradient(scene.halo_layer.colormap)
    state.colorbar_label    = _cb_label
    state.colorbar_min      = _cb_min
    state.colorbar_max      = _cb_max

    # Layer state
    state.halos_visible     = True
    state.galaxies_visible  = True
    state.halo_opacity      = scene.halo_layer.opacity
    state.galaxy_opacity    = scene.galaxy_layer.opacity
    state.halo_color_mode   = scene.halo_layer.color_mode
    state.galaxy_color_mode = scene.galaxy_layer.color_mode
    state.halo_colormap     = scene.halo_layer.colormap
    state.galaxy_colormap   = scene.galaxy_layer.colormap


    def _push():
        if hasattr(server.controller, "view_update"):
            server.controller.view_update()

    def _focused() -> bool:
        return bool(state.focus_active)

    # ------------------------------------------------------------------
    # Layer change handlers
    # ------------------------------------------------------------------

    @state.change("halos_visible")
    def on_halo_toggle(halos_visible, **_):
        scene.halo_layer.visible = bool(halos_visible)
        _push()

    @state.change("galaxies_visible")
    def on_galaxy_toggle(galaxies_visible, **_):
        scene.galaxy_layer.visible = bool(galaxies_visible)
        _push()

    @state.change("halo_opacity")
    def on_halo_opacity(halo_opacity, **_):
        scene.halo_layer.opacity = float(halo_opacity)
        _push()

    @state.change("galaxy_opacity")
    def on_galaxy_opacity(galaxy_opacity, **_):
        scene.galaxy_layer.opacity = float(galaxy_opacity)
        _push()

    @state.change("halo_color_mode")
    def on_halo_mode(halo_color_mode, **_):
        scene.halo_layer.color_mode = halo_color_mode
        label, lo, hi = _HALO_CB[halo_color_mode]
        state.colorbar_label = label
        state.colorbar_min   = lo
        state.colorbar_max   = hi
        _push()

    @state.change("galaxy_color_mode")
    def on_galaxy_mode(galaxy_color_mode, **_):
        scene.galaxy_layer.color_mode = galaxy_color_mode
        _push()

    @state.change("halo_colormap")
    def on_halo_cmap(halo_colormap, **_):
        scene.halo_layer.colormap = halo_colormap
        from sage_viewer.utils.colormap import cmap_css_gradient
        state.colorbar_gradient = cmap_css_gradient(halo_colormap)
        _push()

    @state.change("galaxy_colormap")
    def on_galaxy_cmap(galaxy_colormap, **_):
        scene.galaxy_layer.colormap = galaxy_colormap
        _push()

    # ------------------------------------------------------------------
    # Navigation controllers
    # ------------------------------------------------------------------

    @ctrl.set("go_to_halo")
    def on_go_to_halo():
        try:
            idx = int(state.nav_halo_idx)
            d   = float(state.nav_distance)
            scene.camera.go_to_halo(idx, d)
            if _focused():
                pos = scene.camera._halo_index.position_of(idx)
                scene.set_focus_sphere(
                    (float(pos[0]), float(pos[1]), float(pos[2])), d
                )
        except Exception:
            pass
        _push()

    def _go_to_galaxy_at_radius(radius: float) -> None:
        try:
            state.nav_gal_last_radius = radius
            center = scene.camera.go_to_galaxy(int(state.nav_gal_idx), radius)
            if center != (0.0, 0.0, 0.0):
                scene.set_focus_sphere(center, radius)
                state.focus_active = True
        except Exception:
            pass
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

    @ctrl.set("go_to_galaxy_enter")
    def on_go_to_galaxy_enter():
        _go_to_galaxy_at_radius(float(state.nav_gal_last_radius))

    @ctrl.set("go_to_coords")
    def on_go_to_coords():
        x, y, z, d = (
            float(state.nav_x), float(state.nav_y),
            float(state.nav_z), float(state.nav_distance),
        )
        scene.camera.go_to_coords(x, y, z, d)
        if _focused():
            scene.set_focus_sphere((x, y, z), d)
        _push()

    @ctrl.set("zoom_to_box")
    def on_zoom_to_box():
        xmin, xmax = float(state.nav_box_xmin), float(state.nav_box_xmax)
        ymin, ymax = float(state.nav_box_ymin), float(state.nav_box_ymax)
        zmin, zmax = float(state.nav_box_zmin), float(state.nav_box_zmax)
        scene.camera.zoom_to_box(xmin, xmax, ymin, ymax, zmin, zmax)
        if _focused():
            scene.set_focus_box(xmin, xmax, ymin, ymax, zmin, zmax)
        _push()

    @ctrl.set("reset_camera")
    def on_reset():
        scene.camera.reset()
        scene.clear_focus()
        state.focus_active = False
        _push()

    @ctrl.set("toggle_focus")
    def on_toggle_focus():
        currently_on = bool(state.focus_active)
        state.focus_active = not currently_on
        if currently_on:
            scene.clear_focus()
        elif scene._focus_region is not None:
            halos, galaxies = scene._loader.get(scene._current_snap)
            scene._apply_focus_masks(halos.positions, galaxies.positions)
        _push()

    # ------------------------------------------------------------------
    # UI helper
    # ------------------------------------------------------------------

    def _tf(v_model, label):
        v3.VTextField(
            v_model=(v_model,), label=label,
            type="number", hide_details=True,
            variant="outlined", bg_color="#1a1a2e",
            density="compact",
        )

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    with v3.VSheet(
        color="#0d0d1a",
        style=(
            "height:100%;display:flex;flex-direction:column;"
            "color:#e2e8f0;overflow:hidden;"
        ),
    ):
        # ── Reset + Focus ──────────────────────────────────────────
        with v3.VSheet(color="transparent", style="padding:8px;flex-shrink:0;"):
            with v3.VRow(no_gutters=True, style="gap:6px;"):
                with v3.VCol(style="padding:0;"):
                    v3.VBtn(
                        "Reset Camera", block=True, variant="outlined",
                        color="cyan", density="compact",
                        click=ctrl.reset_camera,
                    )
                with v3.VCol(cols="auto", style="padding:0;"):
                    v3.VBtn(
                        icon="mdi-target", variant="outlined",
                        density="compact", click=ctrl.toggle_focus,
                        color=("focus_active ? 'cyan' : '#6b7280'",),
                        title="Focus",
                    )

        v3.VDivider(style="flex-shrink:0;")

        # ── Tab rows: Structure (full-width) + nav tabs below ──────
        with v3.VBtnToggle(
            v_model=("nav_active_tab",),
            mandatory=True,
            density="compact",
            style=(
                "width:100%;flex-shrink:0;background:#111827;"
                "border-radius:0;display:flex;flex-wrap:wrap;"
            ),
        ):
            v3.VBtn(
                "Structure",
                value="layers",
                style=(
                    "width:100%;font-size:0.72rem;font-weight:700;"
                    "letter-spacing:0.08em;min-width:0;text-transform:none;"
                ),
                color=("nav_active_tab === 'layers' ? 'cyan' : '#6b7280'",),
                variant="text",
                density="compact",
            )
            for label, value in [
                ("Halo",   "halo"),
                ("Galaxy", "galaxy"),
                ("Coords", "coords"),
                ("Box",    "box"),
            ]:
                v3.VBtn(
                    label, value=value,
                    style=(
                        "flex:1;font-size:0.72rem;letter-spacing:0;"
                        "min-width:0;text-transform:none;"
                    ),
                    color=(
                        "nav_active_tab === '{}' ? 'cyan' : '#6b7280'".format(value),
                    ),
                    variant="text",
                    density="compact",
                )

        v3.VDivider(style="flex-shrink:0;")

        # ── Tab content ────────────────────────────────────────────
        with v3.VSheet(
            color="transparent",
            style="flex:1;overflow-y:auto;padding:10px 12px;",
        ):
            # Layers
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'layers'",),
            ):
                v3.VLabel(
                    "DARK MATTER HALOES",
                    style=(
                        "font-size:0.7rem;font-weight:700;letter-spacing:0.08em;"
                        "color:#7c3aed;padding:6px 0 8px;display:block;"
                    ),
                )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSwitch(
                        v_model=("halos_visible",), label="Visible",
                        color="cyan", hide_details=True, density="compact",
                    )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSlider(
                        v_model=("halo_opacity",), label="Opacity",
                        min=0.0, max=0.3, step=0.005,
                        thumb_label="always", color="cyan", hide_details=True,
                    )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSelect(
                        v_model=("halo_color_mode",), items=(_HALO_MODES,),
                        label="Colour by", hide_details=True,
                        variant="outlined", color="cyan", density="compact",
                    )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSelect(
                        v_model=("halo_colormap",), items=(_CMAPS,),
                        label="Colormap", hide_details=True,
                        variant="outlined", color="cyan", density="compact",
                    )

                v3.VDivider(style="margin:14px 0;")

                v3.VLabel(
                    "GALAXIES",
                    style=(
                        "font-size:0.7rem;font-weight:700;letter-spacing:0.08em;"
                        "color:#7c3aed;padding:6px 0 8px;display:block;"
                    ),
                )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSwitch(
                        v_model=("galaxies_visible",), label="Visible",
                        color="deep-purple", hide_details=True, density="compact",
                    )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSlider(
                        v_model=("galaxy_opacity",), label="Opacity",
                        min=0.0, max=1.0, step=0.01,
                        thumb_label="always", color="deep-purple", hide_details=True,
                    )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSelect(
                        v_model=("galaxy_color_mode",), items=(_GALAXY_MODES,),
                        label="Colour by", hide_details=True,
                        variant="outlined", color="deep-purple", density="compact",
                    )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSelect(
                        v_model=("galaxy_colormap",), items=(_CMAPS,),
                        label="Colormap", hide_details=True,
                        variant="outlined", color="deep-purple", density="compact",
                    )

            # Halo
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'halo'",),
            ):
                with v3.VSheet(color="transparent", style=_FIELD):
                    _tf("nav_halo_idx", "Halo index")
                with v3.VSheet(color="transparent", style=_FIELD):
                    _tf("nav_distance", "Standoff (Mpc/h)")
                with v3.VSheet(color="transparent", style=_BTN):
                    v3.VBtn(
                        "Go", block=True, color="cyan",
                        density="compact", click=ctrl.go_to_halo,
                    )

            # Galaxy
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'galaxy'",),
            ):
                with v3.VSheet(color="transparent", style=_FIELD):
                    with v3.VForm(submit=ctrl.go_to_galaxy_enter):
                        _tf("nav_gal_idx", "Galaxy index  (Enter to go)")
                with v3.VSheet(color="transparent", style=_BTN):
                    v3.VBtn(
                        "Go", block=True, color="deep-purple",
                        density="compact", click=ctrl.go_to_galaxy_enter,
                    )
                v3.VLabel(
                    "Zoom radius (Mpc/h)",
                    style=(
                        "font-size:0.68rem;color:#9ca3af;"
                        "display:block;padding:10px 0 4px;"
                    ),
                )
                with v3.VBtnGroup(
                    variant="outlined", density="compact",
                    style="width:100%;",
                ):
                    v3.VBtn("1", style="flex:1;", color="deep-purple",
                            click=ctrl.go_to_galaxy_1)
                    v3.VBtn("3", style="flex:1;", color="deep-purple",
                            click=ctrl.go_to_galaxy_3)
                    v3.VBtn("5", style="flex:1;", color="deep-purple",
                            click=ctrl.go_to_galaxy_5)

            # Coords
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'coords'",),
            ):
                for label, key in [
                    ("X (Mpc/h)", "nav_x"),
                    ("Y (Mpc/h)", "nav_y"),
                    ("Z (Mpc/h)", "nav_z"),
                    ("Standoff",  "nav_distance"),
                ]:
                    with v3.VSheet(color="transparent", style=_FIELD):
                        _tf(key, label)
                with v3.VSheet(color="transparent", style=_BTN):
                    v3.VBtn(
                        "Go", block=True, color="cyan",
                        density="compact", click=ctrl.go_to_coords,
                    )

            # Box
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'box'",),
            ):
                for label, key in [
                    ("X min", "nav_box_xmin"), ("X max", "nav_box_xmax"),
                    ("Y min", "nav_box_ymin"), ("Y max", "nav_box_ymax"),
                    ("Z min", "nav_box_zmin"), ("Z max", "nav_box_zmax"),
                ]:
                    with v3.VSheet(color="transparent", style=_FIELD):
                        _tf(key, label)
                with v3.VSheet(color="transparent", style=_BTN):
                    v3.VBtn(
                        "Zoom", block=True, color="cyan",
                        density="compact", click=ctrl.zoom_to_box,
                    )

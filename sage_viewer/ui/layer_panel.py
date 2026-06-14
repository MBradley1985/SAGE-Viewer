from __future__ import annotations

from trame.widgets import vuetify3 as v3

from sage_viewer.scene.scene import Scene


_COLOR_MODES = [
    {"title": "Mass", "value": "mass"},
    {"title": "sSFR", "value": "ssfr"},
    {"title": "Density", "value": "density"},
    {"title": "Type", "value": "type"},
]


def build_layer_panel(server, scene: Scene) -> None:
    """Left sidebar panel: layer toggles, opacity, colormap, mass cuts."""
    state = server.state

    state.halos_visible = True
    state.galaxies_visible = True
    state.halo_opacity = scene.halo_layer.opacity
    state.galaxy_opacity = scene.galaxy_layer.opacity
    state.halo_color_mode = scene.halo_layer.color_mode
    state.galaxy_color_mode = scene.galaxy_layer.color_mode
    state.halo_min_mass_exp = 10.0   # log10(Msun)
    state.galaxy_min_mass_exp = 8.0  # log10(Msun)

    @state.change("halos_visible")
    def on_halo_toggle(halos_visible, **_):
        scene.halo_layer.visible = bool(halos_visible)

    @state.change("galaxies_visible")
    def on_galaxy_toggle(galaxies_visible, **_):
        scene.galaxy_layer.visible = bool(galaxies_visible)

    @state.change("halo_opacity")
    def on_halo_opacity(halo_opacity, **_):
        scene.halo_layer.opacity = float(halo_opacity)

    @state.change("galaxy_opacity")
    def on_galaxy_opacity(galaxy_opacity, **_):
        scene.galaxy_layer.opacity = float(galaxy_opacity)

    @state.change("halo_color_mode")
    def on_halo_cmap(halo_color_mode, **_):
        scene.halo_layer.color_mode = halo_color_mode

    @state.change("galaxy_color_mode")
    def on_galaxy_cmap(galaxy_color_mode, **_):
        scene.galaxy_layer.color_mode = galaxy_color_mode

    with v3.VNavigationDrawer(permanent=True, width=260, color="#0d0d1a"):
        with v3.VList(density="compact"):
            v3.VListSubheader("LAYERS", style="color:#7c3aed;")

            # Halo layer
            with v3.VListItem():
                v3.VSwitch(
                    v_model=("halos_visible",),
                    label="Dark Matter Haloes",
                    color="cyan",
                    hide_details=True,
                    density="compact",
                )
            with v3.VListItem():
                v3.VSlider(
                    v_model=("halo_opacity",),
                    label="Opacity",
                    min=0.0,
                    max=0.3,
                    step=0.005,
                    thumb_label="always",
                    color="cyan",
                    hide_details=True,
                    density="compact",
                )
            with v3.VListItem():
                v3.VSelect(
                    v_model=("halo_color_mode",),
                    items=(_COLOR_MODES,),
                    label="Colour by",
                    density="compact",
                    hide_details=True,
                    color="cyan",
                )

            v3.VDivider()

            # Galaxy layer
            with v3.VListItem():
                v3.VSwitch(
                    v_model=("galaxies_visible",),
                    label="Galaxies",
                    color="deep-purple",
                    hide_details=True,
                    density="compact",
                )
            with v3.VListItem():
                v3.VSlider(
                    v_model=("galaxy_opacity",),
                    label="Opacity",
                    min=0.0,
                    max=1.0,
                    step=0.01,
                    thumb_label="always",
                    color="deep-purple",
                    hide_details=True,
                    density="compact",
                )
            with v3.VListItem():
                v3.VSelect(
                    v_model=("galaxy_color_mode",),
                    items=(_COLOR_MODES,),
                    label="Colour by",
                    density="compact",
                    hide_details=True,
                    color="deep-purple",
                )

from __future__ import annotations

from trame.widgets import vuetify3 as v3

from sage_viewer.scene.scene import Scene


_HALO_MODES = [
    {"title": "Mvir",  "value": "mvir"},
    {"title": "Rvir",  "value": "rvir"},
    {"title": "Vvir",  "value": "vvir"},
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

_SECTION = (
    "font-size:0.7rem;font-weight:700;letter-spacing:0.08em;"
    "color:#7c3aed;padding:16px 0 8px;display:block;"
)
_FIELD = "padding:8px 0 4px;"


def build_layer_panel(server, scene: Scene) -> None:
    state = server.state

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
        _push()

    @state.change("galaxy_color_mode")
    def on_galaxy_mode(galaxy_color_mode, **_):
        scene.galaxy_layer.color_mode = galaxy_color_mode
        _push()

    @state.change("halo_colormap")
    def on_halo_cmap(halo_colormap, **_):
        scene.halo_layer.colormap = halo_colormap
        _push()

    @state.change("galaxy_colormap")
    def on_galaxy_cmap(galaxy_colormap, **_):
        scene.galaxy_layer.colormap = galaxy_colormap
        _push()

    with v3.VSheet(color="#0d0d1a", style="padding:0 16px 16px;height:100%;"):

        # ── Haloes ──────────────────────────────────────
        v3.VLabel("DARK MATTER HALOES", style=_SECTION)

        with v3.VSheet(color="transparent", style=_FIELD):
            v3.VSwitch(
                v_model=("halos_visible",),
                label="Visible",
                color="cyan",
                hide_details=True,
                density="compact",
            )
        with v3.VSheet(color="transparent", style=_FIELD):
            v3.VSlider(
                v_model=("halo_opacity",),
                label="Opacity",
                min=0.0, max=0.3, step=0.005,
                thumb_label="always",
                color="cyan",
                hide_details=True,
            )
        with v3.VSheet(color="transparent", style=_FIELD):
            v3.VSelect(
                v_model=("halo_color_mode",),
                items=(_HALO_MODES,),
                label="Colour by",
                hide_details=True,
                variant="outlined",
                color="cyan",
            )
        with v3.VSheet(color="transparent", style=_FIELD):
            v3.VSelect(
                v_model=("halo_colormap",),
                items=(_CMAPS,),
                label="Colormap",
                hide_details=True,
                variant="outlined",
                color="cyan",
            )

        v3.VDivider(style="margin:12px 0;")

        # ── Galaxies ─────────────────────────────────────
        v3.VLabel("GALAXIES", style=_SECTION)

        with v3.VSheet(color="transparent", style=_FIELD):
            v3.VSwitch(
                v_model=("galaxies_visible",),
                label="Visible",
                color="deep-purple",
                hide_details=True,
                density="compact",
            )
        with v3.VSheet(color="transparent", style=_FIELD):
            v3.VSlider(
                v_model=("galaxy_opacity",),
                label="Opacity",
                min=0.0, max=1.0, step=0.01,
                thumb_label="always",
                color="deep-purple",
                hide_details=True,
            )
        with v3.VSheet(color="transparent", style=_FIELD):
            v3.VSelect(
                v_model=("galaxy_color_mode",),
                items=(_GALAXY_MODES,),
                label="Colour by",
                hide_details=True,
                variant="outlined",
                color="deep-purple",
            )
        with v3.VSheet(color="transparent", style=_FIELD):
            v3.VSelect(
                v_model=("galaxy_colormap",),
                items=(_CMAPS,),
                label="Colormap",
                hide_details=True,
                variant="outlined",
                color="deep-purple",
            )

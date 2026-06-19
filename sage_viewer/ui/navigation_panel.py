from __future__ import annotations

import asyncio

from trame.widgets import html
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
    {"title": "Structure",    "value": "structure"},
    {"title": "Stellar Mass", "value": "stellar_mass"},
    {"title": "sSFR",         "value": "ssfr"},
    {"title": "SFR",          "value": "sfr"},
    {"title": "Cold Gas",     "value": "cold_gas"},
    {"title": "Bulge Mass",   "value": "bulge_mass"},
    {"title": "B / T",        "value": "bt"},
    {"title": "BH Mass",      "value": "bh_mass"},
    {"title": "ICS Mass",     "value": "ics_mass"},
    {"title": "Age",          "value": "age"},
    {"title": "Density",      "value": "density"},
    {"title": "Type",         "value": "type"},
]

_CMAPS = [
    # Sequential
    {"title": "Viridis",  "value": "viridis"},
    {"title": "Plasma",   "value": "plasma"},
    {"title": "Inferno",  "value": "inferno"},
    {"title": "Magma",    "value": "magma"},
    {"title": "Cividis",  "value": "cividis"},
    {"title": "Turbo",    "value": "turbo"},
    {"title": "Blues",    "value": "Blues"},
    {"title": "Purples",  "value": "Purples"},
    {"title": "Greens",   "value": "Greens"},
    {"title": "Oranges",  "value": "Oranges"},
    {"title": "Reds",     "value": "Reds"},
    {"title": "Greys",    "value": "Greys"},
    {"title": "YlOrRd",   "value": "YlOrRd"},
    {"title": "YlGnBu",   "value": "YlGnBu"},
    {"title": "BuPu",     "value": "BuPu"},
    {"title": "Hot",      "value": "hot"},
    {"title": "Cool",     "value": "cool"},
    {"title": "Bone",     "value": "bone"},
    {"title": "Copper",   "value": "copper"},
    # Diverging
    {"title": "Coolwarm", "value": "coolwarm"},
    {"title": "RdBu",     "value": "RdBu"},
    {"title": "Seismic",  "value": "seismic"},
    {"title": "Spectral", "value": "Spectral"},
    {"title": "BrBG",     "value": "BrBG"},
    # Cyclic / qualitative
    {"title": "Twilight", "value": "twilight"},
    {"title": "Jet",      "value": "jet"},
    {"title": "Rainbow",  "value": "rainbow"},
]


_HALO_CB = {
    "mvir": ("Mvir",    "10^10",  "10^15 Msun"),
    "rvir": ("Rvir",    "0.03",   "3 Mpc/h"),
    "vvir": ("Vvir",    "30",     "1000 km/s"),
}

_GAL_CB = {
    "stellar_mass": ("M*",      "10^8",    "10^12.5 Msun"),
    "ssfr":         ("sSFR",    "10^-14",  "10^-8 yr^-1"),
    "sfr":          ("SFR",     "10^-3",   "10^2 Msun/yr"),
    "cold_gas":     ("Mgas",    "10^7",    "10^11.5 Msun"),
    "bt":           ("B/T",     "0",       "1"),
    "bh_mass":      ("Mbh",     "10^4",    "10^10 Msun"),
    "ics_mass":     ("Mics",    "10^6",    "10^12 Msun"),
    "age":          ("Age",     "0",       "14 Gyr"),
    "bulge_mass":   ("Mbulge",  "10^7",    "10^12 Msun"),
    "density":      ("Density", "Low",     "High"),
    "type":         ("Type",    "Central", "Satellite"),
}

_CBAR_BASE = (
    "height:8px;flex:1;min-width:0;border-radius:2px;"
    "background:"
)

def _cbar_style(gradient: str) -> str:
    return _CBAR_BASE + gradient


def build_navigation_panel(server, scene: Scene) -> None:
    state, ctrl = server.state, server.controller

    # Navigation state
    state.nav_halo_idx         = 0
    state.nav_gal_idx          = 0
    state.nav_gal_last_radius  = 10.0  # 10 Mpc/h — Target Go default
    state.nav_x                = round(scene._cfg.box_size / 2, 2)
    state.nav_y                = round(scene._cfg.box_size / 2, 2)
    state.nav_z                = round(scene._cfg.box_size / 2, 2)
    state.nav_distance         = 10.0  # 10 Mpc/h — Target/Environment standoff
    state.nav_box_xmin         = 0.0
    state.nav_box_xmax         = round(scene._cfg.box_size / 2, 2)
    state.nav_box_ymin         = 0.0
    state.nav_box_ymax         = round(scene._cfg.box_size / 2, 2)
    state.nav_box_zmin         = 0.0
    state.nav_box_zmax         = round(scene._cfg.box_size / 2, 2)
    state.focus_active         = False
    state.nav_active_tab       = "layers"

    # Console — supports multiple parallel sessions. The state vars
    # below always reflect the *active* console; switching consoles
    # syncs them in/out of the per-session Python-side storage dict
    # (`_consoles_data`).
    state.console_input        = ""
    state.console_history      = []   # active console's history
    state.consoles_list        = [{"id": 1, "title": "Console 1"}]
    state.console_active_id    = 1
    state.console_script_path  = ""   # path used by Load Script
    state.console_popout_show  = False

    # Library
    state.library_show     = False
    state.library_files    = []        # list of {"name", "path", "kind", "size_kb"}
    state.library_data_url = ""
    state.library_kind     = ""        # "image" | "video"
    state.library_name     = ""

    # Group info panel state (mirrors galinfo_*)
    state.groupinfo_show  = False
    state.groupinfo_items = []

    # ── Filter state (log10 ranges where appropriate) ──────────
    state.filter_halo_mvir   = [10.0, 15.0]   # log10 Msun
    state.filter_halo_rvir   = [0.0, 3.0]     # Mpc/h (raw)
    state.filter_halo_vvir   = [0.0, 1000.0]  # km/s   (raw)
    state.filter_gal_smass   = [8.0, 12.5]    # log10 Msun
    state.filter_gal_ssfr    = [-14.0, -8.0]  # log10 yr^-1
    state.filter_gal_bt      = [0.0, 1.0]     # bulge/total
    state.filter_gal_type    = "both"         # both | central | satellite
    state.filter_gal_bhmass  = [0.0, 10.0]    # log10 Msun (0 includes zero-BH gals)
    state.filter_gal_ics     = [0.0, 12.0]    # log10 Msun (0 includes zero-ICS gals)
    state.filter_gal_ffb     = "any"          # any | yes | no   (FFBRegime)
    state.filter_gal_cgm     = "any"          # any | cold | hot (Regime 0/1)
    # Environment categories — each checkbox toggles inclusion of that class.
    # When all four are checked the filter is a no-op (= "show all").
    state.env_show_field    = True
    state.env_show_isolated = True
    state.env_show_group    = True
    state.env_show_cluster  = True
    state.fof_links_on      = False           # FoF-link gold lines toggle
    state.filter_gal_age    = [0.0, 14.0]    # Gyr  (mass-weighted stellar age)

    # ── Galaxy info panel ──────────────────────────────────────
    state.galinfo_show  = False
    state.galinfo_items = []   # list[{label, value}] for the panel

    # ── Record state ───────────────────────────────────────────
    state.recording_active   = False
    state.recording_frames   = 0
    state.recording_dir      = ""
    state.last_screenshot    = ""
    state.last_movie         = ""
    state.movie_fps          = 10
    state.movie_resolution   = "native"   # native | hd | uhd
    state.movie_format       = "gif"      # gif | mov | png
    state.screenshot_label   = ""
    state.movie_label        = ""
    state.movie_loop         = True   # only used for GIF output

    # Colorbar state — full style strings to avoid Vue concatenation issues
    from sage_viewer.utils.colormap import cmap_css_gradient
    _h_label, _h_min, _h_max = _HALO_CB[scene.halo_layer.color_mode]
    _g_label, _g_min, _g_max = _GAL_CB.get(
        scene.galaxy_layer.color_mode, ("—", "—", "—")
    )
    state.halo_cbar_style = _cbar_style(cmap_css_gradient(scene.halo_layer.colormap))
    state.halo_cbar_min   = _h_min
    state.halo_cbar_max   = _h_max
    state.gal_cbar_style  = _cbar_style(cmap_css_gradient(scene.galaxy_layer.colormap))
    state.gal_cbar_min    = _g_min
    state.gal_cbar_max    = _g_max

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
    # Filter recompute — runs whenever any filter changes OR snapshot changes
    # ------------------------------------------------------------------

    def _apply_filters() -> None:
        import numpy as np
        halos, galaxies = scene._loader.get(scene.current_snap)

        # Halo filters: Mvir (log10 M☉), Rvir (Mpc/h), Vvir (km/s)
        m_lo, m_hi   = state.filter_halo_mvir
        r_lo, r_hi   = state.filter_halo_rvir
        v_lo, v_hi   = state.filter_halo_vvir

        h_mvir_log = np.log10(np.maximum(halos.masses, 1.0))

        h_mask = (
            (h_mvir_log >= float(m_lo)) & (h_mvir_log <= float(m_hi)) &
            (halos.rvir >= float(r_lo)) & (halos.rvir <= float(r_hi)) &
            (halos.vvir >= float(v_lo)) & (halos.vvir <= float(v_hi))
        )
        # Skip masking work entirely if all three sliders are at full range
        full = (
            float(m_lo) <= 10.0 + 1e-6 and float(m_hi) >= 15.0 - 1e-6
            and float(r_lo) <=  0.0 + 1e-6 and float(r_hi) >=  3.0 - 1e-6
            and float(v_lo) <=  0.0 + 1e-6 and float(v_hi) >= 1000.0 - 1e-6
        )
        if full:
            h_mask = None
        scene.halo_layer.set_filter_mask(h_mask)

        # Galaxy: stellar mass, sSFR, B/T, type
        if galaxies.count == 0:
            scene.galaxy_layer.set_filter_mask(None)
        else:
            g_mask = np.ones(galaxies.count, dtype=bool)

            sm_lo, sm_hi = state.filter_gal_smass
            sm_log = np.log10(np.maximum(galaxies.stellar_mass, 1.0))
            g_mask &= (sm_log >= float(sm_lo)) & (sm_log <= float(sm_hi))

            ss_lo, ss_hi = state.filter_gal_ssfr
            ssfr_log = np.log10(np.maximum(galaxies.ssfr, 1e-30))
            g_mask &= (ssfr_log >= float(ss_lo)) & (ssfr_log <= float(ss_hi))

            bt_lo, bt_hi = state.filter_gal_bt
            sm_safe = np.maximum(galaxies.stellar_mass, 1.0)
            bt = galaxies.bulge_mass / sm_safe
            g_mask &= (bt >= float(bt_lo)) & (bt <= float(bt_hi))

            t = str(state.filter_gal_type)
            if t == "central":
                g_mask &= galaxies.gal_type == 0
            elif t == "satellite":
                g_mask &= galaxies.gal_type > 0

            fields = scene.primary.fields_available

            if fields.get("bh_mass", False):
                bh_lo, bh_hi = state.filter_gal_bhmass
                bh_log = np.log10(np.maximum(galaxies.bh_mass, 1.0))
                g_mask &= (bh_log >= float(bh_lo)) & (bh_log <= float(bh_hi))

            if fields.get("ics_mass", False):
                ics_lo, ics_hi = state.filter_gal_ics
                ics_log = np.log10(np.maximum(galaxies.ics_mass, 1.0))
                g_mask &= (ics_log >= float(ics_lo)) & (ics_log <= float(ics_hi))

            if fields.get("ffb_regime", False):
                ffb = str(state.filter_gal_ffb)
                if ffb == "yes":
                    g_mask &= galaxies.ffb_regime != 0
                elif ffb == "no":
                    g_mask &= galaxies.ffb_regime == 0

            if fields.get("cgm_regime", False):
                cgm = str(state.filter_gal_cgm)
                if cgm == "cold":
                    g_mask &= galaxies.cgm_regime == 0
                elif cgm == "hot":
                    g_mask &= galaxies.cgm_regime == 1

            if fields.get("mean_age", False):
                age_lo, age_hi = state.filter_gal_age
                ages = galaxies.mean_age
                # 0-age galaxies are those with no SFH data — keep them visible
                # only when the slider includes 0 to avoid hiding everything.
                age_mask = (ages >= float(age_lo)) & (ages <= float(age_hi))
                if float(age_lo) > 0.0:
                    g_mask &= age_mask
                else:
                    g_mask &= (ages == 0) | age_mask

            # Environment categories — checkbox-driven; subset → mask
            show_f = bool(state.env_show_field)
            show_i = bool(state.env_show_isolated)
            show_g = bool(state.env_show_group)
            show_c = bool(state.env_show_cluster)
            all_on = show_f and show_i and show_g and show_c
            if not all_on and fields.get("central_mvir", False):
                cm = galaxies.central_mvir
                log_cm = np.log10(np.maximum(cm, 1.0))
                cat_mask = np.zeros(galaxies.count, dtype=bool)
                if show_f:
                    cat_mask |= log_cm < 11.0
                if show_i:
                    cat_mask |= (log_cm >= 11.0) & (log_cm < 12.5)
                if show_g:
                    cat_mask |= (log_cm >= 12.5) & (log_cm < 14.0)
                if show_c:
                    cat_mask |= log_cm >= 14.0
                g_mask &= cat_mask

            scene.galaxy_layer.set_filter_mask(g_mask)

        _push()

    # Re-apply on every snapshot change (new data, masks must be rebuilt)
    scene.register_snap_change_callback(lambda _n: _apply_filters())

    @state.change(
        "filter_halo_mvir", "filter_halo_rvir", "filter_halo_vvir",
        "filter_gal_smass", "filter_gal_ssfr",
        "filter_gal_bt", "filter_gal_type",
        "filter_gal_bhmass", "filter_gal_ics",
        "filter_gal_ffb", "filter_gal_cgm",
        "env_show_field", "env_show_isolated",
        "env_show_group", "env_show_cluster",
        "filter_gal_age",
    )
    def on_filter_change(**_):
        _apply_filters()

    @ctrl.set("reset_opacities")
    def on_reset_opacities():
        state.halo_opacity   = 0.15
        state.galaxy_opacity = 1.0
        state.flush()

    @ctrl.set("reset_filters")
    def on_reset_filters():
        state.filter_halo_mvir  = [10.0, 15.0]
        state.filter_halo_rvir  = [0.0, 3.0]
        state.filter_halo_vvir  = [0.0, 1000.0]
        state.filter_gal_smass  = [8.0, 12.5]
        state.filter_gal_ssfr   = [-14.0, -8.0]
        state.filter_gal_bt     = [0.0, 1.0]
        state.filter_gal_type   = "both"
        state.filter_gal_bhmass = [0.0, 10.0]
        state.filter_gal_ics    = [0.0, 12.0]
        state.filter_gal_ffb    = "any"
        state.filter_gal_cgm    = "any"
        state.env_show_field    = True
        state.env_show_isolated = True
        state.env_show_group    = True
        state.env_show_cluster  = True
        state.filter_gal_age    = [0.0, 14.0]
        state.flush()

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
        _, lo, hi = _HALO_CB[halo_color_mode]
        state.halo_cbar_min = lo
        state.halo_cbar_max = hi
        _push()

    @state.change("galaxy_color_mode")
    def on_galaxy_mode(galaxy_color_mode, **_):
        scene.galaxy_layer.color_mode = galaxy_color_mode
        # Categorical / multi-layer modes (density, type, structure) don't have
        # a single colormap range — fall back to a generic label.
        if galaxy_color_mode in _GAL_CB:
            _, lo, hi = _GAL_CB[galaxy_color_mode]
        else:
            lo, hi = "—", "—"
        state.gal_cbar_min = lo
        state.gal_cbar_max = hi
        _push()

    @state.change("halo_colormap")
    def on_halo_cmap(halo_colormap, **_):
        scene.halo_layer.colormap = halo_colormap
        from sage_viewer.utils.colormap import cmap_css_gradient
        state.halo_cbar_style = _cbar_style(cmap_css_gradient(halo_colormap))
        _push()

    @state.change("galaxy_colormap")
    def on_galaxy_cmap(galaxy_colormap, **_):
        scene.galaxy_layer.colormap = galaxy_colormap
        from sage_viewer.utils.colormap import cmap_css_gradient
        state.gal_cbar_style = _cbar_style(cmap_css_gradient(galaxy_colormap))
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
            # Always engage focus on Go (user can toggle it off afterwards)
            pos = scene.camera._halo_index.position_of(idx)
            scene.set_focus_sphere(
                (float(pos[0]), float(pos[1]), float(pos[2])), d
            )
            state.focus_active = True
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
        _go_to_galaxy_at_radius(3.0)    # 3 Mpc/h

    @ctrl.set("go_to_galaxy_3")
    def on_go_to_galaxy_3():
        _go_to_galaxy_at_radius(5.0)    # 5 Mpc/h

    @ctrl.set("go_to_galaxy_5")
    def on_go_to_galaxy_5():
        _go_to_galaxy_at_radius(10.0)   # 10 Mpc/h

    @ctrl.set("go_to_galaxy_enter")
    def on_go_to_galaxy_enter():
        _go_to_galaxy_at_radius(float(state.nav_gal_last_radius))

    @ctrl.set("clear_indicator")
    def on_clear_indicator():
        scene.camera._clear_indicator()
        scene.camera._clear_member_indicators()
        state.galinfo_show   = False
        state.galinfo_items  = []
        state.groupinfo_show = False
        state.groupinfo_items = []
        state.flush()
        _push()

    @ctrl.set("toggle_fof_links")
    def on_toggle_fof_links():
        new_state = not bool(state.fof_links_on)
        scene.set_fof_links_visible(new_state)
        state.fof_links_on = new_state
        state.flush()
        _push()

    # Keyboard fly movement (WASD / arrow keys). A held key is pressed/
    # released via the hidden cam-press-*/cam-release-* buttons; a single
    # server loop flies every currently-held direction each tick. Driving it
    # off held-state (not per-key clicks) means movement stops the instant
    # the key is released — no queued-click drift.
    _held_dirs: set[str] = set()
    _fly_task: list = [None]

    async def _fly_loop():
        while _held_dirs:
            for d in list(_held_dirs):
                scene.camera.fly(d, step_frac=0.008)
            _push()
            await asyncio.sleep(0.033)
        _fly_task[0] = None

    @ctrl.set("cam_press")
    def on_cam_press(direction=None, **_):
        if not direction:
            return
        _held_dirs.add(str(direction))
        if _fly_task[0] is None or _fly_task[0].done():
            _fly_task[0] = asyncio.ensure_future(_fly_loop())

    @ctrl.set("cam_release")
    def on_cam_release(direction=None, **_):
        _held_dirs.discard(str(direction))

    @ctrl.set("go_to_env_halo")
    def on_go_to_env_halo():
        """Fly to the chosen halo and snap nav_gal_idx to the FOF central there."""
        try:
            hidx = int(state.nav_halo_idx)
            d    = float(state.nav_distance)
        except (TypeError, ValueError):
            return
        halos, galaxies = scene._loader.get(scene.current_snap)
        if hidx < 0 or hidx >= halos.count:
            return  # invalid halo index — silently bail
        try:
            halo_pos = scene.camera._halo_index.position_of(hidx)
        except Exception:
            return
        scene.camera.go_to_halo(hidx, d)
        # Resolve to nearest galaxy so Group Info / Highlight Members work
        import numpy as np
        if galaxies.count > 0:
            d2 = np.sum((galaxies.positions - np.array(halo_pos)) ** 2, axis=1)
            state.nav_gal_idx = int(np.argmin(d2))
        # Always engage focus on Go in the Environment tab
        scene.set_focus_sphere(
            (float(halo_pos[0]), float(halo_pos[1]), float(halo_pos[2])), d
        )
        state.focus_active = True
        state.flush()
        _push()

    @ctrl.set("show_galaxy_info")
    def on_show_galaxy_info():
        from sage_viewer.utils.galaxy_info import build_galaxy_info
        try:
            gidx = int(state.nav_gal_idx)
        except (TypeError, ValueError):
            return
        _, galaxies = scene._loader.get(scene.current_snap)
        if gidx < 0 or gidx >= galaxies.count:
            return

        # Show the info panel only — do NOT move the camera or change focus.
        info = build_galaxy_info(
            galaxies=galaxies,
            fields_available=scene.primary.fields_available,
            idx=gidx,
            snap_table=scene._snap_table,
            hubble_h=scene._cfg.hubble_h,
        )
        state.galinfo_items = [{"label": k, "value": v} for k, v in info.items()]
        state.galinfo_show  = True
        # Close any other right-side overlay
        state.groupinfo_show = False
        state.library_show   = False
        state.flush()
        _push()

    @ctrl.set("hide_galaxy_info")
    def on_hide_galaxy_info():
        state.galinfo_show = False
        state.flush()

    def _find_central_pos_and_extent(galaxies, gidx) -> tuple:
        """Return (central_position, group_extent_mpch, central_idx_in_galaxies)."""
        import numpy as np
        from sage_viewer.utils.group_info import member_indices
        members = member_indices(galaxies, gidx)
        if len(members) == 0:
            return None, 0.0, -1
        pos = galaxies.positions[members]
        gt  = galaxies.gal_type[members]
        # Prefer the type==0 central; fall back to the geometric centre
        central_mask = (gt == 0)
        if central_mask.any():
            central_idx_local = int(np.argmax(central_mask))
            central_pos = pos[central_idx_local]
            central_idx = int(members[central_idx_local])
        else:
            central_pos = pos.mean(axis=0)
            central_idx = -1
        extent = float(np.linalg.norm(pos - central_pos, axis=1).max()) if len(pos) else 0.0
        return central_pos, extent, central_idx

    @ctrl.set("show_group_info")
    def on_show_group_info():
        from sage_viewer.utils.group_info import build_group_info
        import numpy as np
        try:
            gidx = int(state.nav_gal_idx)
        except (TypeError, ValueError):
            return
        _, galaxies = scene._loader.get(scene.current_snap)
        if gidx < 0 or gidx >= galaxies.count:
            return
        info = build_group_info(
            galaxies=galaxies,
            fields_available=scene.primary.fields_available,
            idx=gidx,
            hubble_h=scene._cfg.hubble_h,
        )
        state.groupinfo_items = [{"label": k, "value": v} for k, v in info.items()]
        state.groupinfo_show  = True
        # Mutually exclusive with the other right-side overlays
        state.galinfo_show    = False
        state.library_show    = False

        # Place the standard small red circle on the FOF central — same
        # indicator style used by the Galaxy info action.
        central_pos, _extent, _central_idx = _find_central_pos_and_extent(galaxies, gidx)
        if central_pos is not None:
            scene.camera._add_circle_indicator(
                (float(central_pos[0]), float(central_pos[1]), float(central_pos[2])),
                0.0,
            )
        state.flush()
        _push()

    @ctrl.set("hide_group_info")
    def on_hide_group_info():
        state.groupinfo_show = False
        state.flush()
        _push()

    # ------------------------------------------------------------------
    # Export catalogue
    # ------------------------------------------------------------------

    state.export_dialog_show = False
    state.export_scope        = "filters"   # filters|target|group|coords|box
    state.export_format       = "csv"       # csv|hdf5|fits|txt
    state.export_filename     = ""          # optional custom stem
    state.export_status       = ""          # last result path or error
    state.export_busy         = False

    def _resolve_export_indices(scope: str) -> "np.ndarray":
        import numpy as np
        _, galaxies = scene._loader.get(scene.current_snap)
        if galaxies.count == 0:
            raise ValueError("No galaxies loaded.")

        if scope == "target":
            idx = int(state.nav_gal_idx)
            if idx < 0 or idx >= galaxies.count:
                raise ValueError(f"Target index {idx} out of range.")
            return np.array([idx], dtype=np.int64)

        if scope == "group":
            from sage_viewer.utils.group_info import member_indices
            idx = int(state.nav_gal_idx)
            members = member_indices(galaxies, idx)
            if len(members) == 0:
                raise ValueError("No group members found for target galaxy.")
            return members.astype(np.int64)

        if scope == "coords":
            cx, cy, cz = float(state.nav_x), float(state.nav_y), float(state.nav_z)
            r = float(state.nav_distance)
            d2 = np.sum((galaxies.positions - np.array([cx, cy, cz])) ** 2, axis=1)
            mask = d2 <= r * r
            if not mask.any():
                raise ValueError(f"No galaxies within {r} Mpc/h of ({cx:.1f},{cy:.1f},{cz:.1f}).")
            return np.where(mask)[0].astype(np.int64)

        if scope == "box":
            pos = galaxies.positions
            mask = (
                (pos[:, 0] >= float(state.nav_box_xmin)) & (pos[:, 0] <= float(state.nav_box_xmax)) &
                (pos[:, 1] >= float(state.nav_box_ymin)) & (pos[:, 1] <= float(state.nav_box_ymax)) &
                (pos[:, 2] >= float(state.nav_box_zmin)) & (pos[:, 2] <= float(state.nav_box_zmax))
            )
            if not mask.any():
                raise ValueError("No galaxies within the current box bounds.")
            return np.where(mask)[0].astype(np.int64)

        # default: "filters" — use the active filter mask on the galaxy layer
        import numpy as np
        fmask = scene.primary.galaxy_layer._filter_mask
        if fmask is None:
            gal_indices = np.arange(galaxies.count, dtype=np.int64)
        else:
            gal_indices = np.where(fmask)[0].astype(np.int64)
        if len(gal_indices) == 0:
            raise ValueError("Filter mask excludes all galaxies.")
        return gal_indices

    _SCOPE_LABELS = {
        "filters": "Current Filters",
        "target":  "Target Galaxy",
        "group":   "Group Members",
        "coords":  "Coords Sphere",
        "box":     "Box Region",
    }

    @ctrl.set("do_export")
    async def on_do_export():
        import asyncio, pathlib, datetime
        scope  = str(state.export_scope)
        fmt    = str(state.export_format)
        stem   = str(state.export_filename or "").strip()
        state.export_busy   = True
        state.export_status = "Exporting…"
        state.flush()

        try:
            gal_indices = _resolve_export_indices(scope)
            _, galaxies = scene._loader.get(scene.current_snap)
            sage_idx = galaxies.sage_indices[gal_indices]

            hdf5_path = scene.primary.cfg.hdf5_path
            snap_num  = scene.current_snap
            snap_lbl  = str(state.snap_label) if hasattr(state, "snap_label") else f"snap{snap_num}"

            repo_root = pathlib.Path(__file__).resolve().parents[2]
            out_dir   = repo_root / "sage_outputs" / "catalogues"
            if not stem:
                ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = f"catalogue_{scope}_{ts}"
            exts = {"csv": ".csv", "hdf5": ".h5", "fits": ".fits", "txt": ".txt"}
            out_path = out_dir / f"{stem}{exts.get(fmt, '.csv')}"

            from sage_viewer.utils.catalogue import write_catalogue
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: write_catalogue(
                    hdf5_path=hdf5_path,
                    snap_num=snap_num,
                    snap_label=snap_lbl,
                    sage_indices=sage_idx,
                    out_path=out_path,
                    fmt=fmt,
                    hubble_h=scene.primary.cfg.hubble_h,
                    scope_label=_SCOPE_LABELS.get(scope, scope),
                ),
            )
            n = len(sage_idx)
            state.export_status = f"✓ {n:,} galaxies → {result}"
        except Exception as exc:
            state.export_status = f"Error: {exc}"

        state.export_busy = False
        state.flush()

    # Auto-refresh whichever info card is open when the selection changes.
    @state.change("nav_gal_idx")
    def _refresh_info_on_selection(**_):
        if bool(state.galinfo_show):
            ctrl.show_galaxy_info()
        elif bool(state.groupinfo_show):
            ctrl.show_group_info()

    # Cache the last-highlighted set so re-toggling re-shows the SAME
    # positions even if the snapshot or nav_gal_idx have drifted in between.
    _highlight_cache: dict = {"positions": None, "gidx": -1, "snap": -1}

    @ctrl.set("highlight_group_members")
    def on_highlight_group_members():
        """Toggle: first click highlights members, second click clears them."""
        cam = scene.camera

        # Toggle off — but keep the cache so a third click reproduces the same
        # set of positions.
        if cam.has_member_indicators:
            cam._clear_member_indicators()
            _push()
            return

        from sage_viewer.utils.group_info import member_indices
        try:
            gidx = int(state.nav_gal_idx)
        except (TypeError, ValueError):
            return

        cur_snap = scene.current_snap
        cached = (
            _highlight_cache["positions"] is not None
            and _highlight_cache["gidx"] == gidx
            and _highlight_cache["snap"] == cur_snap
        )
        if cached:
            # Reuse the previous positions verbatim
            cam._add_member_indicators(_highlight_cache["positions"])
        else:
            _, galaxies = scene._loader.get(cur_snap)
            if gidx < 0 or gidx >= galaxies.count:
                return
            members = member_indices(galaxies, gidx)
            if len(members) == 0:
                return
            others = members[members != gidx]
            positions = galaxies.positions[others].copy()
            cam._add_member_indicators(positions)
            _highlight_cache["positions"] = positions
            _highlight_cache["gidx"]      = gidx
            _highlight_cache["snap"]      = cur_snap
        _push()

    # ------------------------------------------------------------------
    # Record / screenshot controllers
    # ------------------------------------------------------------------

    _record_state: dict = {
        "active": False, "dir": None, "frames": 0, "cb": None,
        "fps": 10, "format": "gif", "scale": 1, "movie_base": "movie",
    }
    _session_state: dict = {"dir": None}

    _RES_SCALE = {"native": 1, "hd": 2, "uhd": 4}

    def _get_session_dir() -> "pathlib.Path":
        """Lazily create one session folder per app launch."""
        import datetime
        if _session_state["dir"] is None:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            sess = _make_outdir("sage_outputs") / f"session_{ts}"
            sess.mkdir(parents=True, exist_ok=True)
            _session_state["dir"] = sess
        return _session_state["dir"]

    def _safe_label(label: str) -> str:
        """Sanitize a user-typed label into a safe filename fragment."""
        import re
        s = re.sub(r"[^\w\-]+", "_", str(label or "").strip())
        return s.strip("_")

    def _resolve_name(user_label: str, prefix: str) -> str:
        """Return '<prefix>_<label>' if labelled, else '<prefix>_<timestamp>'."""
        import datetime
        label = _safe_label(user_label)
        if label:
            return f"{prefix}_{label}"
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{ts}"

    def _capture_image(scale: int = 1):
        """Capture the current render window as a vtkImageData."""
        import vtk
        rw = scene.plotter.ren_win
        rw.Render()
        w2i = vtk.vtkWindowToImageFilter()
        w2i.SetInput(rw)
        w2i.SetScale(int(scale), int(scale))
        w2i.SetInputBufferTypeToRGB()
        w2i.ReadFrontBufferOff()
        w2i.Update()
        return w2i.GetOutput()

    def _save_image(image, path) -> None:
        """Write a vtkImageData to disk; format inferred from extension."""
        import vtk
        ext = str(path).lower().rsplit(".", 1)[-1]
        if ext in ("jpg", "jpeg"):
            writer = vtk.vtkJPEGWriter()
            writer.SetQuality(95)
        elif ext in ("tif", "tiff"):
            writer = vtk.vtkTIFFWriter()
        else:
            writer = vtk.vtkPNGWriter()
        writer.SetFileName(str(path))
        writer.SetInputData(image)
        writer.Write()

    def _make_outdir(sub: str) -> "pathlib.Path":
        import pathlib
        # Anchor outputs inside the SAGE-Viewer repo (gitignored)
        # __file__ = .../SAGE-Viewer/sage_viewer/ui/navigation_panel.py
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        outdir = repo_root / sub
        outdir.mkdir(parents=True, exist_ok=True)
        return outdir

    def _take_screenshot(ext: str) -> None:
        try:
            sess = _get_session_dir()
            name = _resolve_name(state.screenshot_label, "screenshot")
            path = sess / f"{name}.{ext}"
            # If a file with this name already exists (user re-used label),
            # append a short timestamp so we don't overwrite.
            if path.exists():
                import datetime
                ts = datetime.datetime.now().strftime("%H%M%S")
                path = sess / f"{name}_{ts}.{ext}"
            img = _capture_image(scale=1)
            _save_image(img, path)
            state.last_screenshot = str(path)
        except Exception as e:
            state.last_screenshot = f"ERROR: {e!s}"
        state.flush()

    @ctrl.set("take_screenshot")
    def on_take_screenshot():
        _take_screenshot("png")

    @ctrl.set("screenshot_png")
    def on_screenshot_png():
        _take_screenshot("png")

    @ctrl.set("screenshot_jpg")
    def on_screenshot_jpg():
        _take_screenshot("jpg")

    @ctrl.set("screenshot_tiff")
    def on_screenshot_tiff():
        _take_screenshot("tiff")

    # ------------------------------------------------------------------
    # Recording — PNG frames during playback, finalized to GIF/MOV at stop
    # ------------------------------------------------------------------

    _record_task: list = [None]   # asyncio.Task | None

    async def _record_loop():
        import asyncio
        interval = 1.0 / max(1, int(_record_state["fps"]))
        try:
            while _record_state["active"]:
                outpath = (
                    _record_state["dir"]
                    / f"frame_{_record_state['frames']:05d}.png"
                )
                try:
                    img = _capture_image(scale=_record_state["scale"])
                    _save_image(img, outpath)
                    _record_state["frames"] += 1
                    state.recording_frames = _record_state["frames"]
                    state.flush()
                except Exception as e:
                    state.last_movie = f"ERROR capturing frame: {e!s}"
                    state.flush()
                    break
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass

    @ctrl.set("start_recording")
    def on_start_recording():
        if _record_state["active"]:
            return
        import asyncio
        sess = _get_session_dir()
        movie_base = _resolve_name(state.movie_label, "movie")
        # Frames go to a temp subdir prefixed with "_" inside the session.
        # On finalize (gif/mov) the temp dir is deleted; for PNG seq we rename it.
        frames_dir = sess / f"_{movie_base}_frames"
        if frames_dir.exists():
            for f in frames_dir.glob("*"):
                try:
                    f.unlink()
                except OSError:
                    pass
        frames_dir.mkdir(parents=True, exist_ok=True)

        scale = _RES_SCALE.get(str(state.movie_resolution), 1)
        fps   = max(1, int(state.movie_fps))
        _record_state.update({
            "active": True, "dir": frames_dir, "frames": 0,
            "fps": fps,
            "format": str(state.movie_format),
            "scale": scale,
            "movie_base": movie_base,
            "session": sess,
        })
        state.recording_active = True
        state.recording_dir    = str(frames_dir)
        state.recording_frames = 0
        state.flush()
        # Schedule the capture loop as a separate task so this handler returns
        # immediately and Trame can process the Stop click while we record.
        _record_task[0] = asyncio.ensure_future(_record_loop())

    def _remove_dir(frames_dir) -> None:
        """Recursively remove a frames temp directory."""
        import pathlib
        import shutil
        try:
            shutil.rmtree(pathlib.Path(frames_dir))
        except OSError:
            pass

    def _finalize_movie(
        frames_dir, session_dir, movie_base: str, fps: int, fmt: str,
        gif_loop: bool = True,
    ) -> str:
        """Convert PNG sequence in frames_dir → <session>/<movie_base>.<fmt>.
        For PNG sequence, renames the temp frames dir to <session>/<movie_base>/.
        On successful gif/mov, the temp frames dir is removed."""
        import subprocess
        import pathlib
        frames_dir = pathlib.Path(frames_dir)
        session_dir = pathlib.Path(session_dir)

        if fmt == "png":
            target = session_dir / movie_base
            if target.exists():
                import datetime
                target = session_dir / f"{movie_base}_{datetime.datetime.now():%H%M%S}"
            frames_dir.rename(target)
            return str(target)

        out_path = session_dir / f"{movie_base}.{fmt}"
        if out_path.exists():
            import datetime
            out_path = session_dir / f"{movie_base}_{datetime.datetime.now():%H%M%S}.{fmt}"

        if fmt == "gif":
            try:
                import imageio.v2 as imageio
                pngs = sorted(frames_dir.glob("frame_*.png"))
                if not pngs:
                    _remove_dir(frames_dir)
                    return "ERROR: no frames captured"
                imgs = [imageio.imread(p) for p in pngs]
                # loop=0 = infinite, loop=1 = play once with no further repeats
                imageio.mimsave(out_path, imgs, fps=fps, loop=0 if gif_loop else 1)
                _remove_dir(frames_dir)
                return str(out_path)
            except Exception as e:
                return f"ERROR (gif): {e!s}"

        if fmt == "mov":
            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", str(frames_dir / "frame_%05d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                str(out_path),
            ]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if proc.returncode != 0:
                    return f"ERROR (mov): ffmpeg returned {proc.returncode}: {proc.stderr[-300:]}"
                _remove_dir(frames_dir)
                return str(out_path)
            except FileNotFoundError:
                return "ERROR: ffmpeg not found in PATH"
            except Exception as e:
                return f"ERROR (mov): {e!s}"

        return f"ERROR: unknown format {fmt!r}"

    @ctrl.set("stop_recording")
    def on_stop_recording():
        if not _record_state["active"]:
            return
        _record_state["active"] = False
        state.recording_active = False
        state.flush()
        # Cancel the capture task so no new frames get written before finalize
        if _record_task[0] is not None and not _record_task[0].done():
            _record_task[0].cancel()
        result = _finalize_movie(
            frames_dir=_record_state["dir"],
            session_dir=_record_state["session"],
            movie_base=_record_state["movie_base"],
            fps=_record_state["fps"],
            fmt=_record_state["format"],
            gif_loop=bool(state.movie_loop),
        )
        state.last_movie = result
        state.flush()

    @ctrl.set("go_to_coords")
    def on_go_to_coords():
        x, y, z, d = (
            float(state.nav_x), float(state.nav_y),
            float(state.nav_z), float(state.nav_distance),
        )
        scene.camera.go_to_coords(x, y, z, d)
        # Always engage focus on Go
        scene.set_focus_sphere((x, y, z), d)
        state.focus_active = True
        _push()

    @ctrl.set("populate_coords_from_camera")
    def on_populate_coords_from_camera():
        """Fill the Coords fields with the current camera focal point + standoff."""
        import numpy as _np
        cam = scene.plotter.camera
        fp  = _np.array(cam.focal_point, dtype=_np.float64)
        pos = _np.array(cam.position,    dtype=_np.float64)
        d   = float(_np.linalg.norm(pos - fp))
        state.nav_x = round(float(fp[0]), 3)
        state.nav_y = round(float(fp[1]), 3)
        state.nav_z = round(float(fp[2]), 3)
        # Standoff matches the current camera distance from the focal point.
        state.nav_distance = round(d, 3) if d > 0 else float(state.nav_distance)
        state.flush()

    @ctrl.set("populate_box_from_camera")
    def on_populate_box_from_camera():
        """Fill the Box fields with the axis-aligned bounding region currently in view."""
        import numpy as _np
        cam = scene.plotter.camera
        fp  = _np.array(cam.focal_point, dtype=_np.float64)
        pos = _np.array(cam.position,    dtype=_np.float64)
        d   = float(_np.linalg.norm(pos - fp))
        # Half-extent at the focal plane = d * tan(FOV/2). Use that as the
        # cube half-width so the box roughly matches what's on screen.
        fov_rad = _np.deg2rad(cam.view_angle)
        half = max(d * _np.tan(fov_rad / 2.0), 0.1)
        state.nav_box_xmin = round(float(fp[0] - half), 3)
        state.nav_box_xmax = round(float(fp[0] + half), 3)
        state.nav_box_ymin = round(float(fp[1] - half), 3)
        state.nav_box_ymax = round(float(fp[1] + half), 3)
        state.nav_box_zmin = round(float(fp[2] - half), 3)
        state.nav_box_zmax = round(float(fp[2] + half), 3)
        state.flush()

    @ctrl.set("zoom_to_box")
    def on_zoom_to_box():
        xmin, xmax = float(state.nav_box_xmin), float(state.nav_box_xmax)
        ymin, ymax = float(state.nav_box_ymin), float(state.nav_box_ymax)
        zmin, zmax = float(state.nav_box_zmin), float(state.nav_box_zmax)
        scene.camera.zoom_to_box(xmin, xmax, ymin, ymax, zmin, zmax)
        # Always engage focus on Zoom — matches Target / Environment /
        # Coords behaviour. User can toggle it off via the focus button.
        scene.set_focus_box(xmin, xmax, ymin, ymax, zmin, zmax)
        state.focus_active = True
        _push()

    @ctrl.set("reset_camera")
    def on_reset():
        scene.camera.reset()
        scene.clear_focus()
        state.focus_active = False
        _push()

    @ctrl.set("center_camera")
    def on_center_camera():
        scene.camera.go_to_box_center()
        _push()

    # ------------------------------------------------------------------
    # Console — natural-language command interpreter
    # ------------------------------------------------------------------

    from sage_viewer.utils.command_parser import (
        CommandContext, execute_command,
    )
    import sys as _sys
    import io as _io
    import code as _code
    import contextlib as _contextlib
    import traceback as _traceback
    import subprocess as _subprocess
    import shlex as _shlex
    import os as _os
    import socket as _socket
    import getpass as _getpass
    import numpy as _np

    _hostname_short = _socket.gethostname().split(".")[0]
    _username       = _getpass.getuser()
    _cmd_ctx = CommandContext(scene=scene, state=state, ctrl=ctrl)

    def _make_console_data() -> dict:
        """Per-session state for one console: a real shell terminal by
        default, with Python REPL and natural-language SAGE modes
        reachable via the `python` / `sage` commands.
        """
        locals_dict = {
            "__name__": "__console__",
            "__doc__":  None,
            "scene":    scene,
            "state":    state,
            "ctrl":     ctrl,
            "server":   server,
            "plotter":  scene.plotter,
            "np":       _np,
        }
        # cwd persists per-session so `cd somewhere` is sticky between
        # commands.  Env is the parent process env at startup; users can
        # mutate via `export FOO=bar` (handled below).
        return {
            "history":   [],
            "input":     "",
            "mode":      "shell",   # "shell" | "python" | "sage"
            "prompt":    "$",
            "cwd":       _os.getcwd(),
            "env":       dict(_os.environ),
            "py_buffer": [],
            "py_interp": _code.InteractiveInterpreter(locals_dict),
            "py_locals": locals_dict,
            "counter":   0,
        }

    _consoles_data: dict[int, dict] = {1: _make_console_data()}
    _active_console = [1]
    _console_id_counter = [1]

    def _truncate(text: str, n: int = 4000) -> str:
        if len(text) <= n:
            return text
        return text[:n] + f"\n… [{len(text) - n} chars truncated]"

    def _save_active() -> None:
        """Snapshot the state vars into the active console's storage."""
        cid = _active_console[0]
        d = _consoles_data.get(cid)
        if d is None:
            return
        d["history"] = list(state.console_history)
        d["input"]   = state.console_input

    def _load_console(cid: int) -> None:
        """Push storage[cid] into the state vars and mark active."""
        d = _consoles_data.get(cid)
        if d is None:
            return
        state.console_history   = list(d["history"])
        state.console_input     = d["input"]
        state.console_mode      = d["mode"]
        state.console_prompt    = d["prompt"]
        state.console_active_id = cid
        _active_console[0]      = cid
        state.flush()

    # Mode + prompt initialised from the default console.
    state.console_mode   = _consoles_data[1]["mode"]
    state.console_prompt = _consoles_data[1]["prompt"]

    def _py_eval(d: dict, source: str) -> str | None:
        """Compile + run source in this console's interpreter; return
        captured stdout+stderr, or None if the input is incomplete."""
        out_buf, err_buf = _io.StringIO(), _io.StringIO()
        try:
            compiled = _code.compile_command(source, "<console>", "single")
        except (SyntaxError, OverflowError, ValueError):
            with _contextlib.redirect_stderr(err_buf):
                d["py_interp"].showsyntaxerror("<console>")
            return err_buf.getvalue()
        if compiled is None:
            return None
        with _contextlib.redirect_stdout(out_buf), \
             _contextlib.redirect_stderr(err_buf):
            d["py_interp"].runcode(compiled)
        return out_buf.getvalue() + err_buf.getvalue()

    def _push_history(prompt: str, cmd: str, out: str) -> None:
        d = _consoles_data[_active_console[0]]
        d["counter"] += 1
        history = list(state.console_history)
        history.append({
            "id":  d["counter"],
            "cmd": f"{prompt} {cmd}" if cmd else prompt,
            "out": _truncate(out) if out else "",
        })
        if len(history) > 200:
            history = history[-200:]
        state.console_history = history
        d["history"] = list(history)

    def _shell_prompt(d: dict) -> str:
        """macOS / Bash style: `host:basename user$`. Matches a real
        Terminal.app prompt for visual consistency."""
        try:
            cwd  = d["cwd"]
            home = _os.path.expanduser("~")
            if cwd == home:
                base = "~"
            else:
                base = _os.path.basename(cwd) or "/"
            return f"{_hostname_short}:{base} {_username}$"
        except Exception:
            return "$"

    def _run_shell(d: dict, cmd: str) -> str:
        """Execute one shell command in `d`'s cwd. Handles `cd`, `pwd`,
        `export` as builtins; everything else hits the user's $SHELL."""
        stripped = cmd.strip()
        if not stripped:
            return ""

        # `cd` / `cd <path>` — must be handled in-process because
        # subprocess.run can't change our cwd.
        if stripped == "cd" or stripped.startswith("cd ") \
                or stripped.startswith("cd\t"):
            arg = stripped[2:].strip() or "~"
            target = _os.path.expanduser(_os.path.expandvars(arg))
            if not _os.path.isabs(target):
                target = _os.path.join(d["cwd"], target)
            target = _os.path.normpath(target)
            if not _os.path.isdir(target):
                return f"cd: {arg}: No such directory"
            d["cwd"] = target
            return ""

        if stripped == "pwd":
            return d["cwd"]

        # `export FOO=bar` — basic env mutation.
        if stripped.startswith("export "):
            try:
                assignments = _shlex.split(stripped[7:])
            except ValueError as e:
                return f"export: {e}"
            for a in assignments:
                if "=" in a:
                    k, v = a.split("=", 1)
                    d["env"][k] = v
                else:
                    d["env"].pop(a, None)
            return ""

        # Anything else: pass through the user's interactive shell so
        # globs, pipes, redirects, $vars, aliases (from .bashrc/.zshrc
        # — though non-interactive shells skip those by default) work.
        shell = d["env"].get("SHELL", "/bin/bash")
        try:
            res = _subprocess.run(
                cmd, shell=True, executable=shell,
                cwd=d["cwd"], env=d["env"],
                stdout=_subprocess.PIPE, stderr=_subprocess.STDOUT,
                text=True, timeout=300,
            )
            out = (res.stdout or "").rstrip()
            if res.returncode != 0 and not out:
                out = f"(exit {res.returncode})"
            elif res.returncode != 0:
                out += f"\n(exit {res.returncode})"
            return out
        except _subprocess.TimeoutExpired:
            return "(timed out after 300s — try backgrounding with &)"
        except Exception as e:
            return f"Error: {e}"

    @ctrl.set("console_submit")
    def on_console_submit():
        cid = _active_console[0]
        d   = _consoles_data[cid]
        cmd_raw = str(state.console_input or "")

        # In SHELL/SAGE modes an empty line is a no-op. In Python mode
        # empty lines terminate multi-line blocks, so we keep them.
        if d["mode"] in ("shell", "sage") and not cmd_raw.strip():
            return

        if d["mode"] == "shell":
            cmd = cmd_raw.rstrip()
            low = cmd.strip().lower()
            if low in ("python", "python3", "py"):
                d["mode"]   = "python"
                d["prompt"] = ">>>"
                state.console_mode   = "python"
                state.console_prompt = ">>>"
                _push_history(_shell_prompt(d), cmd,
                    f"Python {_sys.version.split()[0]} (embedded)\n"
                    "Locals: scene, state, ctrl, server, plotter, np.\n"
                    "Type 'exit' or 'quit' to leave the REPL.")
            elif low in ("sage", "nl", "natural"):
                d["mode"]   = "sage"
                d["prompt"] = "sage>"
                state.console_mode   = "sage"
                state.console_prompt = "sage>"
                _push_history(_shell_prompt(d), cmd,
                    "Natural-language SAGE command mode. "
                    "Examples: 'show only clusters', 'go to halo 42', "
                    "'snap 30', 'screenshot'. Type 'help' for the full "
                    "list, 'exit' to return to shell.")
            else:
                out = _run_shell(d, cmd)
                _push_history(_shell_prompt(d), cmd, out)

        elif d["mode"] == "sage":
            cmd = cmd_raw.rstrip()
            low = cmd.strip().lower()
            if low in ("exit", "quit", "shell"):
                d["mode"]   = "shell"
                d["prompt"] = "$"
                state.console_mode   = "shell"
                state.console_prompt = _shell_prompt(d)
                _push_history("sage>", cmd, "(back to shell)")
            else:
                try:
                    out_text = execute_command(cmd, _cmd_ctx) or "(ok)"
                except Exception as e:
                    out_text = f"Error: {e}"
                _push_history("sage>", cmd, out_text)

        else:  # python mode
            line = cmd_raw.rstrip()
            low  = line.strip().lower()
            if low in ("exit", "quit", "exit()", "quit()", "shell"):
                d["py_buffer"].clear()
                d["mode"]   = "shell"
                d["prompt"] = "$"
                state.console_mode   = "shell"
                state.console_prompt = _shell_prompt(d)
                _push_history(">>>", line, "(back to shell)")
            else:
                d["py_buffer"].append(line)
                source = "\n".join(d["py_buffer"])
                force = (line == "" and len(d["py_buffer"]) > 1)
                if force:
                    result = _py_eval(d, source)
                    if result is None:
                        result = "SyntaxError: unexpected EOF while parsing"
                    d["py_buffer"].clear()
                    _push_history("...", line, result.rstrip())
                    d["prompt"] = ">>>"
                    state.console_prompt = ">>>"
                else:
                    result = _py_eval(d, source)
                    if result is None:
                        prompt = ">>>" if len(d["py_buffer"]) == 1 else "..."
                        _push_history(prompt, line, "")
                        d["prompt"] = "..."
                        state.console_prompt = "..."
                        state.console_input = ""
                        d["input"] = ""
                        state.flush()
                        _push()
                        return
                    d["py_buffer"].clear()
                    _push_history(">>>", line, (result or "").rstrip())
                    d["prompt"] = ">>>"
                    state.console_prompt = ">>>"

        state.console_input = ""
        d["input"] = ""
        state.flush()
        _push()

    @ctrl.set("console_clear")
    def on_console_clear():
        state.console_history = []
        _consoles_data[_active_console[0]]["history"] = []
        state.flush()

    @ctrl.set("console_new")
    def on_console_new():
        _save_active()
        _console_id_counter[0] += 1
        new_id = _console_id_counter[0]
        _consoles_data[new_id] = _make_console_data()
        state.consoles_list = state.consoles_list + [
            {"id": new_id, "title": f"Console {new_id}"}
        ]
        _load_console(new_id)

    @ctrl.set("console_switch")
    def on_console_switch(cid):
        cid = int(cid)
        if cid == _active_console[0]:
            return
        _save_active()
        _load_console(cid)

    @ctrl.set("console_close")
    def on_console_close(cid):
        cid = int(cid)
        if len(_consoles_data) <= 1:
            return    # always keep at least one
        _save_active()
        _consoles_data.pop(cid, None)
        state.consoles_list = [c for c in state.consoles_list if c["id"] != cid]
        if _active_console[0] == cid:
            new_active = state.consoles_list[0]["id"]
            _load_console(new_active)
        else:
            state.flush()

    @ctrl.set("console_load_script")
    def on_console_load_script():
        path = str(state.console_script_path or "").strip()
        if not path:
            return
        cid = _active_console[0]
        d = _consoles_data[cid]
        try:
            with open(path) as f:
                source = f.read()
        except Exception as e:
            _push_history("$", f"load {path}", f"Error reading {path}: {e}")
            state.flush(); _push()
            return
        out_buf, err_buf = _io.StringIO(), _io.StringIO()
        try:
            with _contextlib.redirect_stdout(out_buf), \
                 _contextlib.redirect_stderr(err_buf):
                exec(compile(source, path, "exec"), d["py_locals"])
            out = (out_buf.getvalue() + err_buf.getvalue()).rstrip() \
                  or "(script ran)"
        except Exception:
            out = (out_buf.getvalue() + err_buf.getvalue()
                   + _traceback.format_exc()).rstrip()
        _push_history("$", f"load {path}", out)
        state.flush(); _push()

    @ctrl.set("console_toggle_popout")
    def on_console_toggle_popout():
        state.console_popout_show = not bool(state.console_popout_show)
        state.flush()

    # ------------------------------------------------------------------
    # Library — browse and replay stored screenshots / movies
    # ------------------------------------------------------------------

    import pathlib as _pathlib
    _repo_root = _pathlib.Path(__file__).resolve().parents[2]
    _LIBRARY_DIR = _repo_root / "sage_library"
    _LIBRARY_DIR.mkdir(parents=True, exist_ok=True)

    _MEDIA_EXTS = {
        ".png":  ("image", "image/png"),
        ".jpg":  ("image", "image/jpeg"),
        ".jpeg": ("image", "image/jpeg"),
        ".tif":  ("image", "image/tiff"),
        ".tiff": ("image", "image/tiff"),
        ".gif":  ("image", "image/gif"),
        ".mov":  ("video", "video/mp4"),    # MOV with H.264 ≈ MP4
        ".mp4":  ("video", "video/mp4"),
    }

    def _scan_library() -> list[dict]:
        out: list[dict] = []
        roots = [_LIBRARY_DIR, _repo_root / "sage_outputs"]
        for root in roots:
            if not root.exists():
                continue
            for p in sorted(root.rglob("*")):
                if not p.is_file():
                    continue
                ext = p.suffix.lower()
                if ext not in _MEDIA_EXTS:
                    continue
                kind, _mime = _MEDIA_EXTS[ext]
                try:
                    size_kb = max(1, p.stat().st_size // 1024)
                except OSError:
                    continue
                # Friendly display path (relative to repo root)
                try:
                    rel = p.relative_to(_repo_root)
                except ValueError:
                    rel = p
                out.append({
                    "name":     p.name,
                    "rel":      str(rel),
                    "path":     str(p),
                    "kind":     kind,
                    "ext":      ext.lstrip("."),
                    "size_kb":  int(size_kb),
                })
        return out

    @ctrl.set("library_refresh")
    def on_library_refresh():
        state.library_files = _scan_library()
        state.flush()

    @ctrl.set("library_open")
    def on_library_open(path: str):
        import base64
        p = _pathlib.Path(path)
        if not p.is_file():
            return
        ext = p.suffix.lower()
        if ext not in _MEDIA_EXTS:
            return
        kind, mime = _MEDIA_EXTS[ext]
        try:
            data = p.read_bytes()
        except OSError as e:
            state.library_data_url = ""
            state.library_name     = f"ERROR reading {p.name}: {e}"
            state.library_show     = True
            state.flush()
            return
        b64 = base64.b64encode(data).decode("ascii")
        state.library_data_url = f"data:{mime};base64,{b64}"
        state.library_kind     = kind
        state.library_name     = p.name
        state.library_show     = True
        # Mutually exclusive with other right-side overlays
        state.galinfo_show     = False
        state.groupinfo_show   = False
        state.flush()
        _push()

    @ctrl.set("library_close")
    def on_library_close():
        state.library_show     = False
        state.library_data_url = ""
        state.flush()

    # Populate the file list at startup
    state.library_files = _scan_library()

    # Triggers — Enter / per-row buttons fire these from Vue templates.
    server.trigger("console_submit_trigger")(on_console_submit)
    server.trigger("console_load_script_trigger")(on_console_load_script)
    server.trigger("console_switch_trigger")(on_console_switch)
    server.trigger("console_close_trigger")(on_console_close)

    @ctrl.set("highlight_galaxy")
    def on_highlight_galaxy():
        """Toggle a cyan splat on the currently-selected galaxy."""
        cam = scene.camera
        if cam.has_member_indicators:
            cam._clear_member_indicators()
            _push()
            return
        try:
            gidx = int(state.nav_gal_idx)
        except (TypeError, ValueError):
            return
        _, galaxies = scene._loader.get(scene.current_snap)
        if gidx < 0 or gidx >= galaxies.count:
            return
        import numpy as np
        pos = np.array([galaxies.positions[gidx]], dtype=np.float64)
        cam._add_member_indicators(pos)
        _push()

    @ctrl.set("toggle_focus")
    def on_toggle_focus():
        currently_on = bool(state.focus_active)
        if currently_on:
            # Turning OFF — always just clears focus, regardless of tab.
            state.focus_active = False
            scene.clear_focus()
            _push()
            return

        # Turning ON — engage focus appropriate to the active tab so the
        # button behaves naturally wherever the user is in the UI.
        tab = state.nav_active_tab
        halos, galaxies = scene._loader.get(scene.current_snap)

        if tab == "target":
            try:
                idx = int(state.nav_gal_idx)
                radius = float(state.nav_gal_last_radius)
                if 0 <= idx < galaxies.count:
                    g = galaxies.positions[idx]
                    scene.set_focus_sphere(
                        (float(g[0]), float(g[1]), float(g[2])), radius
                    )
                    state.focus_active = True
            except Exception:
                pass
        elif tab == "environment":
            try:
                hidx = int(state.nav_halo_idx)
                d    = float(state.nav_distance)
                if 0 <= hidx < halos.count:
                    pos = scene.camera._halo_index.position_of(hidx)
                    scene.set_focus_sphere(
                        (float(pos[0]), float(pos[1]), float(pos[2])), d
                    )
                    state.focus_active = True
            except Exception:
                pass
        elif tab == "box":
            try:
                xmin, xmax = float(state.nav_box_xmin), float(state.nav_box_xmax)
                ymin, ymax = float(state.nav_box_ymin), float(state.nav_box_ymax)
                zmin, zmax = float(state.nav_box_zmin), float(state.nav_box_zmax)
                scene.set_focus_box(xmin, xmax, ymin, ymax, zmin, zmax)
                state.focus_active = True
            except Exception:
                pass
        elif tab == "coords":
            try:
                x = float(state.nav_x)
                y = float(state.nav_y)
                z = float(state.nav_z)
                d = float(state.nav_distance)
                scene.set_focus_sphere((x, y, z), d)
                state.focus_active = True
            except Exception:
                pass
        else:
            # Other tabs (Structure, Filters, Record, Console, Library) —
            # re-apply whatever focus region was last set, if any.
            if scene._focus_region is not None:
                scene._apply_focus_masks(halos.positions, galaxies.positions)
                state.focus_active = True

        _push()

    # ------------------------------------------------------------------
    # UI helper
    # ------------------------------------------------------------------

    def _tf(v_model, label, on_enter=None, target_id=None):
        """Number-input helper. Enter binds via `target_id` (the id of
        an action button to simulate-click via the global JS handler);
        legacy callers can still pass `on_enter` and we'll keep that
        wired as a defensive backup."""
        kwargs = dict(
            v_model=(v_model,), label=label,
            type="number", hide_details=True,
            variant="outlined", bg_color="#1a1a2e",
            density="compact",
        )
        if on_enter is not None:
            kwargs["keydown_enter"] = on_enter
        if target_id is not None:
            with html.Div(
                raw_attrs=[f'data-enter-click="{target_id}"'],
                style="display:contents;",
            ):
                v3.VTextField(**kwargs)
        else:
            v3.VTextField(**kwargs)

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
        # Hidden fly-movement triggers — clicked by the keyboard handler in
        # sage_viewer.js (WASD / arrow keys). Kept in the DOM at all times so
        # getElementById always resolves regardless of the active tab.
        with html.Div(style="display:none;"):
            for _dir in ("forward", "back", "left", "right", "up", "down"):
                v3.VBtn(
                    "", id=f"cam-press-{_dir}",
                    click=(server.controller.cam_press, f"['{_dir}']"),
                )
                v3.VBtn(
                    "", id=f"cam-release-{_dir}",
                    click=(server.controller.cam_release, f"['{_dir}']"),
                )

        # ── Reset + Focus + Centre ─────────────────────────────────
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
                        color=("focus_active ? 'cyan' : 'white'",),
                        title="Focus",
                    )
                with v3.VCol(cols="auto", style="padding:0;"):
                    v3.VBtn(
                        icon="mdi-image-filter-center-focus",
                        variant="outlined",
                        density="compact", click=ctrl.center_camera,
                        color="white",
                        title="Place camera at box centre",
                    )

        v3.VDivider(style="flex-shrink:0;")

        # ── Tab rows: 3-up grid wrapping to multiple rows ───────────
        # NOTE: VBtnToggle's `density="compact"` clamps the wrapper to a
        # single row of buttons via a fixed --v-btn-height.  We force
        # height:auto so wrapped rows are actually visible.
        with v3.VBtnToggle(
            v_model=("nav_active_tab",),
            mandatory=True,
            style=(
                "width:100%;flex-shrink:0;background:#111827;"
                "border-radius:0;display:flex;flex-wrap:wrap;"
                "height:auto;min-height:118px;padding-bottom:6px;"
            ),
        ):
            for label, value in [
                ("Structure",   "layers"),
                ("Filters",     "filters"),
                ("Record",      "record"),
                ("Target",      "target"),
                ("Environment", "environment"),
                ("Coords",      "coords"),
                ("Box",         "box"),
                ("Console",     "console"),
                ("Library",     "library"),
            ]:
                v3.VBtn(
                    label, value=value,
                    style=(
                        "flex:0 0 33.333%;font-size:0.72rem;letter-spacing:0;"
                        "min-width:0;height:34px;text-transform:none;"
                        "font-weight:700;"
                    ),
                    color=(
                        "nav_active_tab === '{}' ? 'cyan' : '#6b7280'".format(value),
                    ),
                    variant="text",
                    density="compact",
                )

        v3.VDivider(style="flex-shrink:0;")

        # ── Tab content — fills the remaining panel height and clips
        # overflow rather than scrolling (panel size is fixed; each tab
        # is responsible for fitting its content).
        with v3.VSheet(
            color="transparent",
            style=(
                "flex:1;min-height:0;overflow:hidden;padding:10px 12px;"
                "display:flex;flex-direction:column;"
            ),
        ):
            # Layers
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'layers'",),
            ):
                v3.VLabel(
                    "DARK MATTER HALOES",
                    style=(
                        "font-size:0.95rem;font-weight:700;letter-spacing:0.08em;"
                        "color:#06b6d4;padding:6px 0 8px;display:block;"
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
                        min=0.0, max=1.0, step=0.01,
                        thumb_label=True, color="cyan", hide_details=True,
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
                with v3.VSheet(color="transparent", style="padding:4px 0 8px;"):
                    with v3.VSheet(
                        color="transparent",
                        style="display:flex;align-items:center;gap:4px;",
                    ):
                        v3.VLabel(
                            "{{ halo_cbar_min }}",
                            style="font-size:0.58rem;color:#6b7280;white-space:nowrap;flex-shrink:0;",
                        )
                        v3.VSheet(style=("halo_cbar_style",), color="transparent")
                        v3.VLabel(
                            "{{ halo_cbar_max }}",
                            style="font-size:0.58rem;color:#6b7280;white-space:nowrap;flex-shrink:0;",
                        )

                v3.VDivider(style="margin:14px 0;")

                v3.VLabel(
                    "GALAXIES",
                    style=(
                        "font-size:0.95rem;font-weight:700;letter-spacing:0.08em;"
                        "color:#06b6d4;padding:6px 0 8px;display:block;"
                    ),
                )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSwitch(
                        v_model=("galaxies_visible",), label="Visible",
                        color="#FFD700", hide_details=True, density="compact",
                    )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSlider(
                        v_model=("galaxy_opacity",), label="Opacity",
                        min=0.0, max=1.0, step=0.01,
                        thumb_label=True, color="#FFD700", hide_details=True,
                    )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSelect(
                        v_model=("galaxy_color_mode",), items=(_GALAXY_MODES,),
                        label="Colour by", hide_details=True,
                        variant="outlined", color="#FFD700", density="compact",
                    )
                with v3.VSheet(color="transparent", style=_FIELD):
                    v3.VSelect(
                        v_model=("galaxy_colormap",), items=(_CMAPS,),
                        label="Colormap", hide_details=True,
                        variant="outlined", color="#FFD700", density="compact",
                        # Structure mode is the bare composition (no outer
                        # property halo) — the colormap doesn't apply.
                        # For every other mode the colormap drives the
                        # outermost layer that sits around the envelope.
                        disabled=("galaxy_color_mode === 'structure'",),
                    )
                with v3.VSheet(color="transparent", style="padding:4px 0 8px;"):
                    with v3.VSheet(
                        color="transparent",
                        style="display:flex;align-items:center;gap:4px;",
                    ):
                        v3.VLabel(
                            "{{ gal_cbar_min }}",
                            style="font-size:0.58rem;color:#6b7280;white-space:nowrap;flex-shrink:0;",
                        )
                        v3.VSheet(style=("gal_cbar_style",), color="transparent")
                        v3.VLabel(
                            "{{ gal_cbar_max }}",
                            style="font-size:0.58rem;color:#6b7280;white-space:nowrap;flex-shrink:0;",
                        )

                v3.VDivider(style="margin:14px 0 10px;")

                v3.VBtn(
                    "Reset Opacities",
                    block=True, variant="outlined",
                    color="red", density="compact",
                    prepend_icon="mdi-restore",
                    click=ctrl.reset_opacities,
                )

            # Target (halo + galaxy combined)
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'target'",),
            ):
                v3.VLabel(
                    "HALO",
                    style=(
                        "font-size:0.85rem;font-weight:700;letter-spacing:0.06em;"
                        "color:#06b6d4;display:block;padding:4px 0 6px;"
                    ),
                )
                with v3.VSheet(color="transparent", style=_FIELD):
                    _tf("nav_halo_idx",  "Halo index",
                        on_enter=ctrl.go_to_halo,
                        target_id="btn-target-halo-go")
                with v3.VSheet(color="transparent", style=_FIELD):
                    _tf("nav_distance",  "Standoff (Mpc/h)",
                        on_enter=ctrl.go_to_halo,
                        target_id="btn-target-halo-go")
                with v3.VSheet(color="transparent", style=_BTN):
                    v3.VBtn(
                        "Go", block=True, color="cyan",
                        density="compact", click=ctrl.go_to_halo,
                        id="btn-target-halo-go",
                    )

                v3.VDivider(style="margin:12px 0;")

                v3.VLabel(
                    "GALAXY",
                    style=(
                        "font-size:0.85rem;font-weight:700;letter-spacing:0.06em;"
                        "color:#06b6d4;display:block;padding:4px 0 6px;"
                    ),
                )
                with v3.VSheet(color="transparent", style=_FIELD):
                    _tf("nav_gal_idx", "Galaxy index  (Enter to go)",
                        on_enter=ctrl.go_to_galaxy_enter,
                        target_id="btn-target-galaxy-go")
                with v3.VSheet(color="transparent", style=_BTN):
                    v3.VBtn(
                        "Go", block=True, color="#FFD700",
                        density="compact", click=ctrl.go_to_galaxy_enter,
                        id="btn-target-galaxy-go",
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
                    v3.VBtn("3",  style="flex:1;", color="#FFD700",
                            click=ctrl.go_to_galaxy_1)
                    v3.VBtn("5",  style="flex:1;", color="#FFD700",
                            click=ctrl.go_to_galaxy_3)
                    v3.VBtn("10", style="flex:1;", color="#FFD700",
                            click=ctrl.go_to_galaxy_5)

                v3.VDivider(style="margin:14px 0 10px;")

                v3.VBtn(
                    "Galaxy Info",
                    block=True, color="#FFD700",
                    density="compact",
                    prepend_icon="mdi-information-outline",
                    click=ctrl.show_galaxy_info,
                    style="margin-bottom:6px;",
                )

                v3.VBtn(
                    "Highlight Galaxy",
                    block=True, color="cyan", variant="outlined",
                    density="compact",
                    prepend_icon="mdi-bullseye-arrow",
                    click=ctrl.highlight_galaxy,
                    style="margin-bottom:6px;",
                )

                v3.VBtn(
                    "Clear Indicator",
                    block=True, variant="outlined",
                    color="red", density="compact",
                    prepend_icon="mdi-close-circle-outline",
                    click=ctrl.clear_indicator,
                )

            # Environment tab — group/cluster-level selection & inspection
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'environment'",),
            ):
                v3.VLabel(
                    "HALO  (pick a FOF group)",
                    style=(
                        "font-size:0.85rem;font-weight:700;letter-spacing:0.06em;"
                        "color:#06b6d4;display:block;padding:4px 0 6px;"
                    ),
                )
                with v3.VSheet(color="transparent", style=_FIELD):
                    _tf("nav_halo_idx", "Halo index",
                        on_enter=ctrl.go_to_env_halo,
                        target_id="btn-env-go")
                with v3.VSheet(color="transparent", style=_FIELD):
                    _tf("nav_distance", "Standoff (Mpc/h)",
                        on_enter=ctrl.go_to_env_halo,
                        target_id="btn-env-go")
                with v3.VSheet(color="transparent", style=_BTN):
                    v3.VBtn(
                        "Go", block=True, color="cyan",
                        density="compact", click=ctrl.go_to_env_halo,
                        id="btn-env-go",
                    )

                v3.VDivider(style="margin:12px 0;")

                v3.VLabel(
                    "ENVIRONMENT FILTER",
                    style=(
                        "font-size:0.85rem;font-weight:700;letter-spacing:0.06em;"
                        "color:#06b6d4;display:block;padding:4px 0 6px;"
                    ),
                )
                v3.VLabel(
                    "Show galaxies in these classes (host M_FOF)",
                    style="font-size:0.6rem;color:#9ca3af;padding:0 0 4px;display:block;",
                )
                _ENV_CB_STYLE = (
                    "margin-top:-6px;margin-bottom:-8px;"
                    "--v-input-control-height:24px;"
                )
                v3.VCheckbox(
                    v_model=("env_show_field",),
                    label="Field        (< 10^11 Msun)",
                    hide_details=True, density="compact",
                    color="#FFD700",
                    disabled=("!model_fields.central_mvir",),
                    style=_ENV_CB_STYLE,
                )
                v3.VCheckbox(
                    v_model=("env_show_isolated",),
                    label="Isolated   (10^11 - 10^12.5 Msun)",
                    hide_details=True, density="compact",
                    color="#FFD700",
                    disabled=("!model_fields.central_mvir",),
                    style=_ENV_CB_STYLE,
                )
                v3.VCheckbox(
                    v_model=("env_show_group",),
                    label="Group      (10^12.5 - 10^14 Msun)",
                    hide_details=True, density="compact",
                    color="#FFD700",
                    disabled=("!model_fields.central_mvir",),
                    style=_ENV_CB_STYLE,
                )
                v3.VCheckbox(
                    v_model=("env_show_cluster",),
                    label="Cluster    (> 10^14 Msun)",
                    hide_details=True, density="compact",
                    color="#FFD700",
                    disabled=("!model_fields.central_mvir",),
                    style=_ENV_CB_STYLE,
                )

                v3.VDivider(style="margin:14px 0 10px;")

                v3.VBtn(
                    "Group Info",
                    block=True, color="#FFD700",
                    density="compact",
                    prepend_icon="mdi-account-group-outline",
                    click=ctrl.show_group_info,
                    style="margin-bottom:6px;",
                )
                v3.VBtn(
                    "Highlight Members",
                    block=True, color="cyan", variant="outlined",
                    density="compact",
                    prepend_icon="mdi-bullseye-arrow",
                    click=ctrl.highlight_group_members,
                    style="margin-bottom:6px;",
                )
                v3.VBtn(
                    "{{ fof_links_on ? 'FoF Links: On' : 'FoF Links: Off' }}",
                    block=True, density="compact",
                    variant=("fof_links_on ? 'flat' : 'outlined'",),
                    color="#FFD700",
                    prepend_icon="mdi-vector-polyline",
                    click=ctrl.toggle_fof_links,
                    style="margin-bottom:6px;",
                )
                v3.VBtn(
                    "Clear",
                    block=True, variant="outlined",
                    color="red", density="compact",
                    prepend_icon="mdi-close-circle-outline",
                    click=ctrl.clear_indicator,
                )

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
                        _tf(key, label, on_enter=ctrl.go_to_coords,
                            target_id="btn-coords-go")
                with v3.VSheet(color="transparent", style=_BTN):
                    v3.VBtn(
                        "Use Current Position", block=True, variant="outlined",
                        color="cyan", density="compact",
                        prepend_icon="mdi-crosshairs-gps",
                        click=ctrl.populate_coords_from_camera,
                        style="margin-bottom:6px;",
                    )
                    v3.VBtn(
                        "Go", block=True, color="cyan",
                        density="compact", click=ctrl.go_to_coords,
                        id="btn-coords-go",
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
                        _tf(key, label, on_enter=ctrl.zoom_to_box,
                            target_id="btn-box-zoom")
                with v3.VSheet(color="transparent", style=_BTN):
                    v3.VBtn(
                        "Use Current View", block=True, variant="outlined",
                        color="cyan", density="compact",
                        prepend_icon="mdi-crosshairs-gps",
                        click=ctrl.populate_box_from_camera,
                        style="margin-bottom:6px;",
                    )
                    v3.VBtn(
                        "Zoom", block=True, color="cyan",
                        density="compact", click=ctrl.zoom_to_box,
                        id="btn-box-zoom",
                    )

            # ── CONSOLE tab — multi-session REPL ────────────────────
            # Layout: heading + tab strip pinned to the top, history
            # absorbs all remaining vertical space, and a bottom-anchored
            # block carries the two text fields plus the 4 action
            # buttons. `margin-top:auto` on the bottom block guarantees
            # it sits flush against the panel's bottom edge.
            with html.Div(
                v_show=("nav_active_tab === 'console'",),
                style=(
                    "display:flex;flex-direction:column;"
                    "height:100%;min-height:0;width:100%;"
                ),
            ):
                # Heading + session tab strip on one line — saves a row
                # of vertical space and keeps the buttons clearly visible.
                # `min-height` and `padding` are generous so the small
                # buttons don't visually clip inside the flex column.
                with html.Div(
                    style=(
                        "display:flex;align-items:center;gap:6px;"
                        "padding:2px 0 6px;flex-shrink:0;flex-wrap:wrap;"
                    ),
                ):
                    html.Span(
                        "CONSOLE",
                        style=(
                            "font-size:0.85rem;font-weight:700;"
                            "letter-spacing:0.08em;color:#06b6d4;"
                            "margin-right:4px;"
                        ),
                    )
                    # Per-session buttons — render the title + close X
                    # as a single contiguous span so flex-wrap keeps
                    # them together instead of breaking mid-session.
                    with html.Span(
                        v_for=("c in consoles_list",),
                        key=("c.id",),
                        style=(
                            "display:inline-flex;align-items:center;"
                            "gap:2px;"
                        ),
                    ):
                        v3.VBtn(
                            "{{ c.title }}",
                            size="x-small",
                            density="compact",
                            variant=("console_active_id === c.id ? 'flat' "
                                     ": 'outlined'",),
                            color=("console_active_id === c.id ? 'cyan' "
                                   ": '#6b7280'",),
                            click=("trigger('console_switch_trigger', "
                                   "[c.id])"),
                            style=(
                                "text-transform:none;font-size:0.62rem;"
                                "min-width:0;padding:0 8px;height:22px;"
                            ),
                        )
                        v3.VBtn(
                            icon="mdi-close",
                            size="x-small",
                            density="compact",
                            variant="text",
                            color="#6b7280",
                            v_show=("consoles_list.length > 1",),
                            click=("trigger('console_close_trigger', "
                                   "[c.id])"),
                            style="min-width:18px;padding:0;height:22px;",
                        )
                    v3.VBtn(
                        icon="mdi-plus",
                        size="x-small",
                        density="compact",
                        variant="outlined",
                        color="cyan",
                        click=ctrl.console_new,
                        title="New console",
                        style="min-width:24px;padding:0;height:22px;",
                    )

                # History — flex-fills the available vertical space.
                # min-height:0 lets it shrink when needed so the
                # bottom block is always visible.
                with v3.VSheet(
                    color="#0a0a0f",
                    classes="sage-console-scroll",
                    style=(
                        "flex:1 1 0;min-height:0;overflow-y:auto;"
                        "padding:6px 8px;border:1px solid #1f2937;"
                        "border-radius:4px;font-family:monospace;"
                        "font-size:0.7rem;line-height:1.4;"
                    ),
                ):
                    with html.Div(
                        v_for=("entry in console_history",),
                        key=("entry.id",),
                        style=(
                            "padding:2px 0 4px;"
                            "border-bottom:1px solid #1f2937;"
                        ),
                    ):
                        html.Div(
                            "{{ entry.cmd }}",
                            style=("color:cyan;white-space:pre-wrap;"
                                   "font-family:monospace;"),
                        )
                        html.Div(
                            "{{ entry.out }}",
                            style="color:#9ca3af;white-space:pre-wrap;",
                        )

                # Bottom block — anchored to the panel's bottom edge via
                # `margin-top:auto`. Holds the input field, script path,
                # and the four action buttons.
                with html.Div(
                    style=(
                        "margin-top:6px;flex-shrink:0;"
                        "display:flex;flex-direction:column;gap:6px;"
                    ),
                ):
                    with html.Div(
                        raw_attrs=['data-enter-click="btn-console-run"'],
                    ):
                        v3.VTextField(
                            v_model=("console_input",),
                            label=(
                                "console_mode === 'python' "
                                "? 'Python REPL  (Enter to run)' "
                                ": (console_mode === 'sage' "
                                "    ? 'SAGE command  (Enter to run)' "
                                "    : 'Shell  (Enter to run, type python "
                                "or sage to switch modes)')",
                            ),
                            hide_details=True, variant="outlined",
                            bg_color="#1a1a2e", density="compact",
                            keydown_enter=ctrl.console_submit,
                        )
                    with html.Div(
                        raw_attrs=['data-enter-click="btn-console-load"'],
                    ):
                        v3.VTextField(
                            v_model=("console_script_path",),
                            label="Script path  (Enter to load + execute)",
                            hide_details=True, variant="outlined",
                            bg_color="#1a1a2e", density="compact",
                            keydown_enter=ctrl.console_load_script,
                        )
                    with v3.VRow(no_gutters=True, style="gap:6px;"):
                        with v3.VCol(style="padding:0;"):
                            v3.VBtn(
                                "Run", block=True, color="cyan",
                                density="compact",
                                prepend_icon="mdi-play",
                                click=ctrl.console_submit,
                                id="btn-console-run",
                            )
                        with v3.VCol(style="padding:0;"):
                            v3.VBtn(
                                "Clear", block=True, variant="outlined",
                                color="red", density="compact",
                                prepend_icon="mdi-delete-sweep-outline",
                                click=ctrl.console_clear,
                            )
                    with v3.VRow(no_gutters=True, style="gap:6px;"):
                        with v3.VCol(style="padding:0;"):
                            v3.VBtn(
                                "Load Script", block=True,
                                variant="outlined",
                                color="cyan", density="compact",
                                prepend_icon="mdi-file-code-outline",
                                click=ctrl.console_load_script,
                                id="btn-console-load",
                            )
                        with v3.VCol(style="padding:0;"):
                            v3.VBtn(
                                "Pop-out", block=True, variant="outlined",
                                color=("console_popout_show ? 'cyan' "
                                       ": '#6b7280'",),
                                density="compact",
                                prepend_icon="mdi-dock-window",
                                click=ctrl.console_toggle_popout,
                            )

            # ── LIBRARY tab — browse stored media ──────────────
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'library'",),
                style=(
                    "display:flex;flex-direction:column;"
                    "height:100%;min-height:0;width:100%;"
                ),
            ):
                v3.VLabel(
                    "MEDIA LIBRARY",
                    style=(
                        "font-size:0.95rem;font-weight:700;letter-spacing:0.08em;"
                        "color:#06b6d4;padding:4px 0 4px;display:block;"
                        "flex-shrink:0;"
                    ),
                )
                v3.VLabel(
                    "Screenshots and movies from <SAGE-Viewer>/sage_library/ and "
                    "<SAGE-Viewer>/sage_outputs/.  Click a row to display.",
                    style=(
                        "font-size:0.6rem;color:#9ca3af;line-height:1.35;"
                        "display:block;padding:0 0 4px;flex-shrink:0;"
                    ),
                )
                # File list — flex-fills the available vertical space so the
                # black box runs the full height of the panel.
                with v3.VSheet(
                    color="#0a0a0f",
                    style=(
                        "flex:1 1 0;min-height:0;overflow-y:auto;"
                        "border:1px solid #1f2937;border-radius:4px;"
                        "margin-top:6px;"
                    ),
                ):
                    with v3.VList(density="compact", bg_color="transparent"):
                        v3.VListItem(
                            v_for=("entry in library_files",),
                            key=("entry.path",),
                            click=(
                                server.controller.library_open,
                                "[entry.path]",
                            ),
                            title=("entry.name",),
                            subtitle=(
                                "entry.ext.toUpperCase() + ' · ' + "
                                "entry.size_kb + ' KB · ' + entry.rel",
                            ),
                            prepend_icon=(
                                "entry.kind === 'video' "
                                "? 'mdi-movie-open-outline' : 'mdi-image-outline'",
                            ),
                            color="cyan",
                        )
                # Bottom block — count + action buttons anchored to the
                # panel's bottom edge, mirroring the Console tab layout.
                with html.Div(
                    style=(
                        "margin-top:6px;flex-shrink:0;"
                        "display:flex;flex-direction:column;gap:6px;"
                    ),
                ):
                    v3.VLabel(
                        "{{ library_files.length }} file"
                        "{{ library_files.length === 1 ? '' : 's' }}",
                        style=(
                            "font-size:0.6rem;color:#6b7280;display:block;"
                        ),
                    )
                    with v3.VRow(no_gutters=True, style="gap:6px;"):
                        with v3.VCol(style="padding:0;"):
                            v3.VBtn(
                                "Refresh", block=True, color="cyan",
                                density="compact", size="small",
                                prepend_icon="mdi-refresh",
                                click=ctrl.library_refresh,
                            )
                        with v3.VCol(style="padding:0;"):
                            v3.VBtn(
                                "Close viewer", block=True, variant="outlined",
                                color="red", density="compact", size="small",
                                prepend_icon="mdi-close-circle-outline",
                                click=ctrl.library_close,
                            )

            # ── FILTERS tab ────────────────────────────────────
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'filters'",),
            ):
                _FSEC = (
                    "font-size:0.78rem;font-weight:700;letter-spacing:0.08em;"
                    "color:#06b6d4;padding:2px 0 2px;display:block;"
                )
                _FLBL = (
                    "font-size:0.6rem;color:#9ca3af;display:block;"
                    "padding:2px 0 0;"
                )
                # Compact filter sliders — narrower AND shorter than the
                # default Vuetify range slider so they don't dominate.
                _FSLD = (
                    "padding:0;margin-top:-12px;margin-bottom:-12px;"
                    "transform:scale(0.7);transform-origin:left center;"
                    "width:125%;"
                )
                _FSEL = (
                    "--v-input-control-height:30px;"
                    "font-size:0.7rem;margin-top:1px;"
                )

                v3.VLabel("DARK MATTER HALOES", style=_FSEC)
                v3.VLabel("Mvir  (log10 Msun)", style=_FLBL)
                v3.VRangeSlider(
                    v_model=("filter_halo_mvir",),
                    min=10.0, max=15.0, step=0.1,
                    thumb_label=True, color="cyan",
                    density="compact", hide_details=True,
                    classes="sage-fslider",
                    style=_FSLD,
                )
                v3.VLabel("Rvir  (Mpc/h)", style=_FLBL)
                v3.VRangeSlider(
                    v_model=("filter_halo_rvir",),
                    min=0.0, max=3.0, step=0.05,
                    thumb_label=True, color="cyan",
                    density="compact", hide_details=True,
                    classes="sage-fslider",
                    style=_FSLD,
                )
                v3.VLabel("Vvir  (km/s)", style=_FLBL)
                v3.VRangeSlider(
                    v_model=("filter_halo_vvir",),
                    min=0.0, max=1000.0, step=10.0,
                    thumb_label=True, color="cyan",
                    density="compact", hide_details=True,
                    classes="sage-fslider",
                    style=_FSLD,
                )

                v3.VDivider(style="margin:4px 0 2px;")

                v3.VLabel("GALAXIES", style=_FSEC)
                v3.VLabel("Stellar mass  (log10 Msun)", style=_FLBL)
                v3.VRangeSlider(
                    v_model=("filter_gal_smass",),
                    min=8.0, max=12.5, step=0.1,
                    thumb_label=True, color="#FFD700",
                    density="compact", hide_details=True,
                    classes="sage-fslider",
                    style=_FSLD,
                )
                v3.VLabel("sSFR  (log10 yr^-1)", style=_FLBL)
                v3.VRangeSlider(
                    v_model=("filter_gal_ssfr",),
                    min=-14.0, max=-8.0, step=0.1,
                    thumb_label=True, color="#FFD700",
                    density="compact", hide_details=True,
                    classes="sage-fslider",
                    style=_FSLD,
                )
                v3.VLabel("B / T  (bulge / stellar)", style=_FLBL)
                v3.VRangeSlider(
                    v_model=("filter_gal_bt",),
                    min=0.0, max=1.0, step=0.02,
                    thumb_label=True, color="#FFD700",
                    density="compact", hide_details=True,
                    classes="sage-fslider",
                    style=_FSLD,
                )
                v3.VLabel("Stellar age  (Gyr, mass-weighted)", style=_FLBL)
                v3.VRangeSlider(
                    v_model=("filter_gal_age",),
                    min=0.0, max=14.0, step=0.1,
                    thumb_label=True, color="#FFD700",
                    density="compact", hide_details=True,
                    disabled=("!model_fields.mean_age",),
                    classes="sage-fslider",
                    style=_FSLD,
                )
                v3.VLabel("BH mass  (log10 Msun)", style=_FLBL)
                v3.VRangeSlider(
                    v_model=("filter_gal_bhmass",),
                    min=0.0, max=10.0, step=0.1,
                    thumb_label=True, color="#FFD700",
                    density="compact", hide_details=True,
                    disabled=("!model_fields.bh_mass",),
                    classes="sage-fslider",
                    style=_FSLD,
                )
                v3.VLabel("ICS mass  (log10 Msun)", style=_FLBL)
                v3.VRangeSlider(
                    v_model=("filter_gal_ics",),
                    min=0.0, max=12.0, step=0.1,
                    thumb_label=True, color="#FFD700",
                    density="compact", hide_details=True,
                    disabled=("!model_fields.ics_mass",),
                    classes="sage-fslider",
                    style=_FSLD,
                )

                v3.VLabel("Type", style=_FLBL)
                v3.VSelect(
                    v_model=("filter_gal_type",),
                    items=([
                        {"title": "All",         "value": "both"},
                        {"title": "Centrals",    "value": "central"},
                        {"title": "Satellites",  "value": "satellite"},
                    ],),
                    hide_details=True, variant="outlined",
                    color="#FFD700", density="compact",
                    style=_FSEL,
                )

                v3.VLabel("FFB regime", style=_FLBL)
                v3.VSelect(
                    v_model=("filter_gal_ffb",),
                    items=([
                        {"title": "Any",          "value": "any"},
                        {"title": "FFB only",     "value": "yes"},
                        {"title": "Non-FFB only", "value": "no"},
                    ],),
                    hide_details=True, variant="outlined",
                    color="#FFD700", density="compact",
                    disabled=("!model_fields.ffb_regime",),
                    style=_FSEL,
                )

                v3.VLabel("CGM / Hot regime", style=_FLBL)
                v3.VSelect(
                    v_model=("filter_gal_cgm",),
                    items=([
                        {"title": "Any",                     "value": "any"},
                        {"title": "CGM galaxies",            "value": "cold"},
                        {"title": "Hot atmosphere galaxies", "value": "hot"},
                    ],),
                    hide_details=True, variant="outlined",
                    color="#FFD700", density="compact",
                    disabled=("!model_fields.cgm_regime",),
                    style=_FSEL,
                )

                v3.VDivider(style="margin:6px 0 4px;")

                v3.VBtn(
                    "Reset Filters",
                    block=True, variant="outlined",
                    color="red", density="compact",
                    size="small",
                    prepend_icon="mdi-restore",
                    click=ctrl.reset_filters,
                )

            # ── RECORD tab ─────────────────────────────────────
            with v3.VSheet(
                color="transparent",
                v_show=("nav_active_tab === 'record'",),
            ):
                v3.VLabel(
                    "SCREENSHOT",
                    style=(
                        "font-size:0.95rem;font-weight:700;letter-spacing:0.08em;"
                        "color:#06b6d4;padding:6px 0 8px;display:block;"
                    ),
                )
                with html.Div(
                    raw_attrs=['data-enter-click="btn-take-screenshot"'],
                ):
                    v3.VTextField(
                        v_model=("screenshot_label",),
                        label="Label (optional)  (Enter to take screenshot)",
                        hide_details=True, variant="outlined",
                        bg_color="#1a1a2e", density="compact",
                        style="padding-bottom:8px;",
                        keydown_enter=ctrl.take_screenshot,
                    )
                v3.VBtn(
                    "Take Screenshot",
                    block=True, color="cyan",
                    density="compact",
                    prepend_icon="mdi-camera",
                    click=ctrl.take_screenshot,
                    id="btn-take-screenshot",
                )
                with v3.VRow(no_gutters=True, style="gap:6px;padding-top:6px;"):
                    with v3.VCol(style="padding:0;"):
                        v3.VBtn(
                            "PNG", block=True, variant="outlined",
                            color="cyan", density="compact",
                            click=ctrl.screenshot_png,
                        )
                    with v3.VCol(style="padding:0;"):
                        v3.VBtn(
                            "JPG", block=True, variant="outlined",
                            color="cyan", density="compact",
                            click=ctrl.screenshot_jpg,
                        )
                    with v3.VCol(style="padding:0;"):
                        v3.VBtn(
                            "TIFF", block=True, variant="outlined",
                            color="cyan", density="compact",
                            click=ctrl.screenshot_tiff,
                        )
                v3.VLabel(
                    "Saved to <SAGE-Viewer>/sage_outputs/session_*/",
                    style="font-size:0.62rem;color:#6b7280;display:block;padding:6px 0 2px;",
                )
                v3.VLabel(
                    "{{ last_screenshot ? 'Last: ' + last_screenshot : '' }}",
                    style="font-size:0.58rem;color:#6b7280;display:block;word-break:break-all;",
                )

                v3.VDivider(style="margin:14px 0;")

                v3.VLabel(
                    "RECORD MOVIE",
                    style=(
                        "font-size:0.95rem;font-weight:700;letter-spacing:0.08em;"
                        "color:#06b6d4;padding:6px 0 8px;display:block;"
                    ),
                )
                with html.Div(
                    raw_attrs=['data-enter-click="btn-start-recording"'],
                ):
                    v3.VTextField(
                        v_model=("movie_label",),
                        label="Label (optional)  (Enter to start recording)",
                        hide_details=True, variant="outlined",
                        bg_color="#1a1a2e", density="compact",
                        style="padding-bottom:8px;",
                        keydown_enter=ctrl.start_recording,
                    )
                v3.VLabel(
                    "FPS (output)  {{ '— ' + movie_fps }}",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:4px 0 2px;",
                )
                v3.VSlider(
                    v_model=("movie_fps",),
                    min=1, max=60, step=1,
                    thumb_label=True, color="cyan",
                    density="compact", hide_details=True,
                )

                v3.VLabel(
                    "Resolution",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:10px 0 2px;",
                )
                v3.VSelect(
                    v_model=("movie_resolution",),
                    items=([
                        {"title": "Native  (1×)",       "value": "native"},
                        {"title": "High   (2× window)", "value": "hd"},
                        {"title": "Ultra  (4× window)", "value": "uhd"},
                    ],),
                    hide_details=True, variant="outlined",
                    color="cyan", density="compact",
                )

                v3.VLabel(
                    "Output format",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:10px 0 2px;",
                )
                v3.VSelect(
                    v_model=("movie_format",),
                    items=([
                        {"title": "GIF",          "value": "gif"},
                        {"title": "MOV  (H.264)", "value": "mov"},
                        {"title": "PNG sequence", "value": "png"},
                    ],),
                    hide_details=True, variant="outlined",
                    color="cyan", density="compact",
                )

                # GIF-only: repeat (loop) checkbox
                v3.VCheckbox(
                    v_model=("movie_loop",),
                    label="Loop GIF forever",
                    v_show=("movie_format === 'gif'",),
                    color="cyan",
                    density="compact",
                    hide_details=True,
                    style="padding-top:4px;",
                )

                with v3.VRow(no_gutters=True, style="gap:6px;padding-top:10px;"):
                    with v3.VCol(style="padding:0;"):
                        v3.VBtn(
                            "Start", block=True, color="red",
                            density="compact",
                            prepend_icon="mdi-record-circle-outline",
                            click=ctrl.start_recording,
                            disabled=("recording_active",),
                            id="btn-start-recording",
                        )
                    with v3.VCol(style="padding:0;"):
                        v3.VBtn(
                            "Stop", block=True, color="#6b7280",
                            density="compact",
                            prepend_icon="mdi-stop",
                            click=ctrl.stop_recording,
                            disabled=("!recording_active",),
                        )

                v3.VLabel(
                    "{{ recording_active ? '● Recording — ' + recording_frames + ' frames' : 'Idle' }}",
                    style="font-size:0.68rem;color:#9ca3af;display:block;padding:10px 0 2px;",
                )
                v3.VLabel(
                    "{{ last_movie ? 'Last: ' + last_movie : '' }}",
                    style="font-size:0.58rem;color:#6b7280;display:block;word-break:break-all;padding:4px 0;",
                )

from __future__ import annotations

from pathlib import Path

from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import html, vuetify3 as v3
from trame_vtk.modules.vtk import has_capabilities
from trame_vtk.widgets.vtk import VtkRemoteView

from sage_viewer.scene.scene import Scene
from sage_viewer.utils.discover import find_models
from sage_viewer.ui.info_panel import build_info_panel
from sage_viewer.ui.navigation_panel import build_navigation_panel
from sage_viewer.ui.toolbar import build_toolbar


def create_app(
    par_path: str | Path,
    par_dir: str | Path | None = None,
    initial_snap: int | None = None,
    n_jobs: int = -1,
    min_halo_mass: float = 1.0e10,
    min_stellar_mass: float = 1.0e8,
    max_halos: int = 100_000,
    max_galaxies: int = 100_000,
):
    scene = Scene(
        primary_par_path=par_path,
        off_screen=False,
        initial_snap=initial_snap,
        n_jobs=n_jobs,
        min_halo_mass=min_halo_mass,
        min_stellar_mass=min_stellar_mass,
        max_halos=max_halos,
        max_galaxies=max_galaxies,
    )

    server = get_server(client_type="vue3")
    server.enable_module(has_capabilities)

    _vuetify_config = {
        "theme": {
            "defaultTheme": "dark",
            "themes": {
                "dark": {
                    "colors": {
                        "primary": "#7c3aed",
                        "secondary": "#06b6d4",
                        "background": "#0a0a0f",
                        "surface": "#111827",
                    }
                }
            },
        }
    }

    _NAV_TABS = [
        ("Structure", "layers"),
        ("Filters",   "filters"),
        ("Record",    "record"),
        ("Target",    "target"),
        ("Coords",    "coords"),
        ("Box",       "box"),
    ]

    # ---- Model discovery ------------------------------------------------
    # We list models by scanning the SAGE OUTPUT directory (each subfolder
    # with a model_0.hdf5 is one model, named after the folder).  The .par
    # files are still used internally for tree paths but they are no longer
    # surfaced in the UI.
    primary_hdf5 = Path(scene.primary.cfg.hdf5_path)
    output_dir = primary_hdf5.parent.parent
    par_d = Path(par_dir) if par_dir else Path(par_path).parent
    discovered = find_models(output_dir, par_dir=par_d)
    # Index by model name for fast lookup
    discovered_by_name: dict[str, dict] = {m["name"]: m for m in discovered}

    def _build_models_list() -> list[dict]:
        """Build the reactive list of model entries for the menu."""
        loaded = {m.name: m for m in scene.list_models()}
        out = []
        for entry in discovered:
            name = entry["name"]
            is_loaded   = name in loaded
            is_primary  = (name == scene.primary_name)
            compatible  = is_loaded and scene.is_compatible_for_overlay(name)
            overlay_on  = is_loaded and not is_primary and loaded[name].visible
            out.append({
                "name":       name,
                "path":       str(entry["par"]),
                "loaded":     is_loaded,
                "primary":    is_primary,
                "compatible": compatible,
                "overlay":    overlay_on,
            })
        # Loaded-but-not-on-disk (e.g. primary model whose output dir wasn't scanned)
        for name, m in loaded.items():
            if not any(e["name"] == name for e in out):
                out.append({
                    "name": name, "path": str(m.path), "loaded": True,
                    "primary": name == scene.primary_name,
                    "compatible": scene.is_compatible_for_overlay(name),
                    "overlay": m.visible and name != scene.primary_name,
                })
        return out

    server.state.models_list      = _build_models_list()
    server.state.model_loading    = False
    server.state.model_fields     = scene.primary.fields_available
    server.state.primary_model    = scene.primary.name
    # Snackbar for overlay-compatibility errors etc.
    server.state.notice_show      = False
    server.state.notice_text      = ""
    server.state.notice_color     = "warning"
    # Per-model flags used by static menu items (dict keyed by name)
    def _model_flags() -> dict:
        loaded = {m.name: m for m in scene.list_models()}
        out = {}
        for entry in discovered:
            n = entry["name"]
            out[n] = {
                "primary":     n == scene.primary.name,
                "loaded":      n in loaded,
                "overlay":     n in loaded and loaded[n].visible and n != scene.primary.name,
                "compatible":  scene.is_compatible_for_overlay(n) if n in loaded else True,
            }
        return out
    server.state.model_flags = _model_flags()

    def _refresh_models_state() -> None:
        server.state.models_list   = _build_models_list()
        server.state.model_fields  = scene.primary.fields_available
        server.state.primary_model = scene.primary.name
        server.state.model_flags   = _model_flags()
        server.state.flush()

    scene.register_model_change_callback(_refresh_models_state)

    @server.controller.set("switch_model")
    def on_switch_model(name: str):
        try:
            server.state.model_loading = True
            server.state.flush()
            if not scene.has_model(name):
                entry = discovered_by_name.get(name)
                if entry is None:
                    return
                scene.add_model(entry["par"])
            scene.switch_primary(name)
        finally:
            server.state.model_loading = False
            _refresh_models_state()

    @server.controller.set("toggle_overlay")
    def on_toggle_overlay(name: str):
        try:
            server.state.model_loading = True
            server.state.flush()
            if not scene.has_model(name):
                entry = discovered_by_name.get(name)
                if entry is None:
                    return
                scene.add_model(entry["par"])
            model = scene._models[name]
            # Try the toggle; capture any compatibility error
            err = scene.set_overlay_visible(name, not model.visible)
            if err is not None:
                server.state.notice_text  = err
                server.state.notice_color = "warning"
                server.state.notice_show  = True
        finally:
            server.state.model_loading = False
            _refresh_models_state()

    with SinglePageLayout(server, full_height=True, vuetify_config=_vuetify_config) as layout:
        layout.title.set_text("SAGE-Viewer")
        # Hide the default VAppBarNavIcon — replaced by our custom menu button below
        layout.icon.style = "display:none;"

        with layout.toolbar as tb:
            tb.density = "compact"
            tb.color = "#1a1a2e"

            # Tab dropdown menu — sits in the natural nav-icon position
            with v3.VMenu(close_on_content_click=False):
                with v3.Template(v_slot_activator="{ props }"):
                    v3.VBtn(
                        icon="mdi-menu",
                        variant="text",
                        density="compact",
                        v_bind="props",
                        title="Tab menu",
                    )
                with v3.VList(density="compact", bg_color="#1a1a2e"):
                    # ── Tabs ───────────────────────────────────────
                    for label, value in _NAV_TABS:
                        v3.VListItem(
                            title=label,
                            value=value,
                            click=f"nav_active_tab = '{value}'",
                            active=(f"nav_active_tab === '{value}'",),
                            color="cyan",
                        )

                    # ── Models (one row per discovered output folder) ──
                    if discovered:
                        v3.VDivider()
                        for entry in discovered:
                            mname = entry["name"]
                            # Switch row
                            v3.VListItem(
                                title=mname,
                                subtitle=(
                                    f"model_flags['{mname}'] && "
                                    f"model_flags['{mname}'].primary "
                                    f"? 'primary' : "
                                    f"(model_flags['{mname}'] && "
                                    f"model_flags['{mname}'].overlay "
                                    f"? 'overlay on' : 'click to switch')",
                                ),
                                click=(
                                    server.controller.switch_model,
                                    f"['{mname}']",
                                ),
                                active=(f"primary_model === '{mname}'",),
                                color="cyan",
                            )
                            # Overlay sub-row (shown only when model is loaded
                            # and compatible with the current primary)
                            v3.VListItem(
                                title=(
                                    f"model_flags['{mname}'] && "
                                    f"model_flags['{mname}'].overlay "
                                    f"? '✓ overlay: {mname}' "
                                    f": '+ overlay: {mname}'",
                                ),
                                click=(
                                    server.controller.toggle_overlay,
                                    f"['{mname}']",
                                ),
                                v_show=(
                                    f"primary_model !== '{mname}'",
                                ),
                                density="compact",
                                style="padding-left:24px;font-size:0.7rem;",
                            )

            build_toolbar(server, scene)


        with layout.content:
            with v3.VSheet(
                style=(
                    "display:flex;flex-direction:row;"
                    "height:100%;width:100%;overflow:hidden;"
                ),
                rounded=False,
                elevation=0,
                color="#0a0a0f",
            ):
                # Render window + loading overlay
                with v3.VSheet(
                    style="position:relative;flex:1;height:100%;display:flex;min-width:0;",
                    color="transparent", rounded=False, elevation=0,
                ):
                    view = VtkRemoteView(
                        scene.plotter.ren_win,
                        style="flex:1;height:100%;display:block;min-width:0;",
                        # Closer to original quality settings — less dramatic
                        # interactive→still cycling on each click reduces
                        # visible "flash" re-renders.
                        interactive_ratio=0.75,
                        interactive_quality=65,
                        still_quality=100,
                    )
                    server.controller.view_update = view.update

                    # Snackbar for compatibility / status messages
                    v3.VSnackbar(
                        "{{ notice_text }}",
                        v_model=("notice_show",),
                        timeout=4500,
                        color=("notice_color",),
                        location="top",
                        contained=True,
                        style="margin-top:16px;",
                    )

                    # Galaxy info panel — semi-transparent card pinned to
                    # the right of the render area; only relevant in target
                    # mode but the v_model controls visibility.
                    with v3.VCard(
                        v_show=("galinfo_show && nav_active_tab === 'target'",),
                        style=(
                            "position:absolute;top:32px;right:24px;"
                            "min-width:260px;max-width:320px;"
                            "background:rgba(17,24,39,0.85);"
                            "backdrop-filter:blur(6px);"
                            "border:1px solid #374151;"
                            "color:#e2e8f0;"
                            "z-index:5;"
                        ),
                        elevation=8,
                    ):
                        with v3.VCardTitle(
                            style=(
                                "display:flex;align-items:center;"
                                "font-size:0.85rem;letter-spacing:0.06em;"
                                "padding:10px 12px 6px;"
                            ),
                        ):
                            v3.VIcon("mdi-information-outline",
                                     size="small", color="cyan",
                                     style="margin-right:6px;")
                            html.Span("Galaxy info")
                            v3.VSpacer()
                            v3.VBtn(
                                icon="mdi-close",
                                size="x-small",
                                variant="text",
                                click=server.controller.hide_galaxy_info,
                            )
                        v3.VDivider()
                        with v3.VCardText(
                            style="padding:8px 12px;font-size:0.72rem;",
                        ):
                            with html.Div(
                                v_for=("row in galinfo_items",),
                                key=("row.label",),
                                style=(
                                    "display:flex;justify-content:space-between;"
                                    "padding:3px 0;border-bottom:1px solid #1f2937;"
                                ),
                            ):
                                html.Span(
                                    "{{ row.label }}",
                                    style="color:#9ca3af;",
                                )
                                html.Span(
                                    "{{ row.value }}",
                                    style="font-family:monospace;text-align:right;color:#e2e8f0;",
                                )

                    # Loading overlay shown while a model loads
                    with v3.VOverlay(
                        v_model=("model_loading",),
                        contained=True,
                        persistent=True,
                        classes="d-flex align-center justify-center",
                        scrim="rgba(0,0,0,0.65)",
                    ):
                        with v3.VSheet(
                            color="#1a1a2e",
                            style=(
                                "padding:24px 32px;border-radius:8px;"
                                "display:flex;flex-direction:column;align-items:center;"
                                "gap:14px;"
                            ),
                        ):
                            v3.VProgressCircular(
                                indeterminate=True, color="cyan", size=48, width=4,
                            )
                            v3.VLabel(
                                "Loading model…",
                                style="font-size:0.9rem;color:#e2e8f0;",
                            )
                            v3.VLabel(
                                "Reading snapshots and building scene",
                                style="font-size:0.7rem;color:#9ca3af;",
                            )

                # Right panel — layers + navigation tabs
                with v3.VSheet(
                    style="width:300px;flex-shrink:0;height:100%;overflow:hidden;",
                    color="#0d0d1a",
                    rounded=False,
                    elevation=0,
                ):
                    build_navigation_panel(server, scene)

        with layout.footer as footer:
            footer.color = "#0d0d1a"
            footer.height = 36
            build_info_panel(server, scene)

    return server, scene

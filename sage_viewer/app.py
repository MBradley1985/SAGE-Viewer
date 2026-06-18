from __future__ import annotations

from pathlib import Path

from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from textwrap import dedent

from trame.widgets import html, vuetify3 as v3
from trame_vtk.modules.vtk import has_capabilities
from trame_vtk.widgets.vtk import VtkRemoteView

from sage_viewer.scene.scene import Scene
from sage_viewer.utils.discover import find_models


# ──────────────────────────────────────────────────────────────────────────
# UI palettes
# ──────────────────────────────────────────────────────────────────────────
_THEME_CSS = dedent("""
/* ============================================================
   MODERN (default) — colours come from the Vuetify theme.  No
   structural overrides; Vuetify defaults apply.
   ============================================================ */

/* ============================================================
   DOS BLUE — Norton-Commander-style high-contrast IBM blue.
   Vuetify adds `.v-theme--dos_blue` to the application root when
   the theme is active; everything below is scoped to that class.
   ============================================================ */
/* Border-radius zero on everything (including icons — no harm) */
.v-theme--dos_blue,
.v-theme--dos_blue *,
.v-theme--dos_blue *::before,
.v-theme--dos_blue *::after { border-radius: 0 !important; }

/* VT323 font on text-bearing elements, but explicitly NOT on any icon
   wrapper / glyph so MDI keeps its own font and continues to render. */
.v-theme--dos_blue,
.v-theme--dos_blue *:not(.v-icon):not(.v-icon *):not(i.mdi):not(.mdi):not([class*="mdi-"]):not(.material-icons):not(.material-icons *) {
    font-family: 'VT323','Perfect DOS VGA 437','Courier New',monospace !important;
    letter-spacing: 0.03em;
}
/* VT323 renders smaller than equivalent-pt sans-serif fonts; bump every
   text-bearing element in DOS Blue mode so it reads at a comfortable size. */
.v-theme--dos_blue .v-label,
.v-theme--dos_blue .v-list-item-title,
.v-theme--dos_blue .v-list-subheader { font-size: 1.1rem !important; }
.v-theme--dos_blue .v-list-item-subtitle { font-size: 0.92rem !important; }
.v-theme--dos_blue .v-btn { font-size: 1.0rem !important; }
.v-theme--dos_blue .v-card-title { font-size: 1.2rem !important; }
.v-theme--dos_blue .v-card-text { font-size: 0.95rem !important; }
.v-theme--dos_blue .v-field__input,
.v-theme--dos_blue .v-field input,
.v-theme--dos_blue input { font-size: 1.05rem !important; }
.v-theme--dos_blue .v-chip { font-size: 1.0rem !important; }
/* Slider value bubbles (thumb labels) — default is tiny and unreadable;
   enlarge the bubble and its text on every slider / range slider. */
.v-theme--dos_blue .v-slider-thumb__label {
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    min-width: 2.4em !important;
    height: 1.9em !important;
    padding: 0 6px !important;
}
/* Filter range sliders are rendered at transform:scale(0.7) to save space,
   which shrinks their value bubble. Bump the font so the on-screen size
   matches the (unscaled) opacity sliders: 1.5rem * 0.7 ~= 1.05rem. */
.v-theme--dos_blue .sage-fslider .v-slider-thumb__label {
    font-size: 1.5rem !important;
}
.v-theme--dos_blue .v-select__selection-text { font-size: 1.0rem !important; }
.v-theme--dos_blue .v-select__selection { font-size: 1.0rem !important; }
.v-theme--dos_blue span { font-size: 1em; }       /* keep inheritance */
.v-theme--dos_blue .v-toolbar-title { font-size: 1.25rem !important; }
.v-theme--dos_blue .v-card {
    border: 2px solid #ffffff !important;
    box-shadow: 4px 4px 0 #000 !important;
    backdrop-filter: none !important;
}
.v-theme--dos_blue .v-card-title {
    background: #aaaaaa !important;
    color: #000 !important;
    letter-spacing: 0.12em;
}
.v-theme--dos_blue .v-btn {
    border: 1px solid #ffffff !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    box-shadow: 2px 2px 0 #000 !important;
    font-weight: 700;
}
.v-theme--dos_blue .v-text-field .v-field,
.v-theme--dos_blue .v-select .v-field { border-radius: 0 !important; }
.v-theme--dos_blue .v-chip { border-radius: 0 !important; }
""")
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

    # Serve SAGE-Viewer's client-side helpers (pop-out drag, Enter-to-
    # click). Vue 3 silently drops <script> tags from templates so we
    # have to inject these via the module/static-asset system.
    import os as _os_static
    _sage_static_dir = _os_static.path.join(
        _os_static.path.dirname(__file__), "static"
    )
    server.enable_module({
        "serve":   {"sage_static": _sage_static_dir},
        "scripts": ["sage_static/sage_viewer.js"],
    })

    # Single-theme config — DOS Blue is now the only palette.
    _vuetify_config = {
        "theme": {
            "defaultTheme": "dos_blue",
            "themes": {
                "dos_blue": {
                    "dark": True,
                    "colors": {
                        "primary":    "#ffff55",   # DOS yellow
                        "secondary":  "#ffffff",
                        "background": "#0000aa",   # IBM blue
                        "surface":    "#0000aa",
                        "on-surface": "#ffffff",
                        "on-background": "#ffffff",
                    },
                },
            },
        }
    }
    _NAV_TABS = [
        ("Structure",   "layers"),
        ("Filters",     "filters"),
        ("Record",      "record"),
        ("Target",      "target"),
        ("Environment", "environment"),
        ("Coords",      "coords"),
        ("Box",         "box"),
        ("Console",     "console"),
        ("Library",     "library"),
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
    # Rotating quip shown on the "switching models" overlay. Updated by
    # an asyncio task that runs while model_loading is True.
    server.state.model_quip       = "Switching models, please hold..."
    _MODEL_QUIPS: list[str] = [
        "Reticulating splines...",
        "Herding electrons into formation...",
        "Asking the universe nicely for the haloes...",
        "Spinning up galaxies — please don't shake the box.",
        "Negotiating with dark matter (it drives a hard bargain).",
        "Counting black holes... lost count.",
        "Convincing photons to travel faster. No luck.",
        "Reading SAGE bedtime stories to the trees...",
        "Stirring the cold gas. Gently.",
        "Polishing the CGM. Won't be long.",
        "Aligning angular momenta — close your eyes.",
        "Subhalo abundance matching the vibes...",
        "Hubble tension intensifies...",
        "Letting the H2 form on dust grains. Patience.",
        "Renormalizing the friend-of-friend friendships.",
        "Tracing merger trees — they're surprisingly deep.",
        "Reminding satellites who's central.",
        "Quenching star formation (sorry).",
        "Calibrating feedback — too much, less, more, less...",
        "Recomputing 1/H(z). Again.",
        "Reading the par file out loud, slowly.",
    ]

    async def _quip_loop():
        import asyncio as _asyncio
        import random as _random
        try:
            while bool(server.state.model_loading):
                server.state.model_quip = _random.choice(_MODEL_QUIPS)
                server.state.flush()
                await _asyncio.sleep(2.5)
        finally:
            server.state.model_quip = "Switching models, please hold..."
            server.state.flush()

    _quip_task: list = [None]

    @server.state.change("model_loading")
    def on_model_loading_change(model_loading, **_):
        import asyncio as _asyncio
        if model_loading:
            if _quip_task[0] is None or _quip_task[0].done():
                _quip_task[0] = _asyncio.ensure_future(_quip_loop())
        else:
            if _quip_task[0] is not None and not _quip_task[0].done():
                _quip_task[0].cancel()
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

    # `theme=("ui_theme",)` reactively binds the active Vuetify theme to
    # our state variable — Vuetify swaps the entire palette plus the root
    # `v-theme--<name>` class instantly when ui_theme changes.
    server.state.ui_theme = "dos_blue"
    with SinglePageLayout(
        server, full_height=True,
        vuetify_config=_vuetify_config,
        theme=("ui_theme",),
    ) as layout:
        # Hide the SinglePageLayout's auto-built title — we render our own
        # later inside the toolbar so we can control its position relative
        # to the hamburger menu.
        layout.title.style = "display:none;"
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

            # Title sits directly to the right of the hamburger menu —
            # both kept close together on the LEFT side of the toolbar.
            v3.VToolbarTitle(
                "SAGE-Viewer",
                style="padding-left:4px;",
            )

            build_toolbar(server, scene)


        with layout.content:
            # Pixel-style monospace for the retro palettes — loaded via a
            # real <link> tag so the browser treats it as a normal external
            # stylesheet (works even when injected inside a Vue template).
            html.Link(
                rel="stylesheet",
                href=(
                    "https://fonts.googleapis.com/css2?"
                    "family=VT323&display=swap"
                ),
            )
            # Theme overrides — encoded as a data: URL so it loads via a real
            # stylesheet link rather than an inline <style> element (Vue's
            # template compiler doesn't reliably emit inline <style>).
            import base64 as _b64
            _css_data_url = (
                "data:text/css;charset=utf-8;base64,"
                + _b64.b64encode(_THEME_CSS.encode("utf-8")).decode("ascii")
            )
            html.Link(rel="stylesheet", href=_css_data_url)

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
                        # Full quality at all times — no resolution drop
                        # during camera drag.
                        interactive_ratio=1.0,
                        interactive_quality=100,
                        still_quality=100,
                    )
                    server.controller.view_update = view.update

                    # Pre-rendered playback overlay — covers the live view
                    # while frames are rendered (hiding flicker) and during
                    # playback, where it flips through the cached frames.
                    with html.Div(
                        v_show=("playback_active || prerender_busy",),
                        style=(
                            "position:absolute;inset:0;z-index:6;"
                            "background:#000;display:flex;"
                            "align-items:center;justify-content:center;"
                        ),
                    ):
                        html.Img(
                            v_show=("playback_active",),
                            src=("playback_frame",),
                            style=(
                                "width:100%;height:100%;object-fit:contain;"
                                "display:block;"
                            ),
                        )
                        html.Div(
                            "{{ preload_status || 'Loading galaxies.....' }}",
                            v_show=("prerender_busy",),
                            style=(
                                "color:#FFD700;font-size:1.4rem;"
                                "font-family:monospace;letter-spacing:0.05em;"
                            ),
                        )

                    # Pop-out console — floats over the viewport, mirrors
                    # the active session's history. Toggle from the
                    # Console tab's "Pop-out" button. Drag-free for now;
                    # pinned to the bottom-left corner of the viewport.
                    with v3.VCard(
                        v_show=("console_popout_show",),
                        classes="sage-popout",
                        style=(
                            "position:absolute;left:24px;bottom:24px;"
                            "width:560px;max-width:60%;"
                            "height:360px;max-height:55%;"
                            "background:rgba(13,13,26,0.92);"
                            "border:1px solid #06b6d4;"
                            "box-shadow:0 0 18px rgba(6,182,212,0.30);"
                            "display:flex;flex-direction:column;"
                            "z-index:10;color:#e2e8f0;"
                            "resize:both;overflow:hidden;"
                        ),
                        elevation=0, rounded=False,
                    ):
                        # Title bar — also the drag handle (cursor:move +
                        # ".sage-popout-handle" picked up by the global
                        # drag script).
                        with html.Div(
                            classes="sage-popout-handle",
                            style=(
                                "display:flex;align-items:center;"
                                "padding:4px 8px;gap:8px;"
                                "border-bottom:1px solid #1f2937;"
                                "flex-shrink:0;cursor:move;"
                                "user-select:none;"
                            ),
                        ):
                            html.Span(
                                "CONSOLE  (Console {{ console_active_id }})",
                                style=(
                                    "font-size:0.75rem;font-weight:700;"
                                    "letter-spacing:0.08em;color:#06b6d4;"
                                ),
                            )
                            v3.VSpacer()
                            v3.VBtn(
                                icon="mdi-close", size="x-small",
                                variant="text", color="#9ca3af",
                                click=server.controller.console_toggle_popout,
                            )
                        # Mirrored history
                        with v3.VSheet(
                            color="#0a0a0f",
                            classes="sage-console-scroll",
                            style=(
                                "flex:1 1 0;min-height:0;overflow-y:auto;"
                                "padding:6px 10px;font-family:monospace;"
                                "font-size:0.72rem;line-height:1.4;"
                            ),
                        ):
                            with html.Div(
                                v_for=("entry in console_history",),
                                key=("'po-' + entry.id",),
                                style=(
                                    "padding:2px 0 4px;"
                                    "border-bottom:1px solid #1f2937;"
                                ),
                            ):
                                html.Div(
                                    "{{ entry.cmd }}",
                                    style=(
                                        "color:cyan;white-space:pre-wrap;"
                                        "font-family:monospace;"
                                    ),
                                )
                                html.Div(
                                    "{{ entry.out }}",
                                    style=(
                                        "color:#9ca3af;"
                                        "white-space:pre-wrap;"
                                    ),
                                )
                        # Input — submits via the same trigger as the
                        # in-panel input, so the pop-out is just a second
                        # surface onto the active console.
                        with html.Div(
                            style="padding:6px 8px;flex-shrink:0;",
                        ):
                            with html.Div(
                                raw_attrs=[
                                    'data-enter-click="btn-console-run"'
                                ],
                            ):
                                v3.VTextField(
                                    v_model=("console_input",),
                                    label=(
                                        "console_mode === 'python' "
                                        "? 'Python REPL  (Enter to run)' "
                                        ": (console_mode === 'sage' "
                                        "    ? 'SAGE command  (Enter to run)' "
                                        "    : 'Shell  (Enter to run)')",
                                    ),
                                    hide_details=True, variant="outlined",
                                    bg_color="#1a1a2e", density="compact",
                                    style="font-family:monospace;",
                                    keydown_enter=server.controller.console_submit,
                                )

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

                    # Group / cluster info panel — same right-hand position
                    # as the Galaxy info card; the two are mutually exclusive
                    # (opening one closes the other) so they never overlap.
                    with v3.VCard(
                        v_show=("groupinfo_show && nav_active_tab === 'environment'",),
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
                            v3.VIcon("mdi-account-group-outline",
                                     size="small", color="cyan",
                                     style="margin-right:6px;")
                            html.Span("Group info")
                            v3.VSpacer()
                            v3.VBtn(
                                icon="mdi-close",
                                size="x-small",
                                variant="text",
                                click=server.controller.hide_group_info,
                            )
                        v3.VDivider()
                        with v3.VCardText(
                            style="padding:8px 12px;font-size:0.72rem;",
                        ):
                            with html.Div(
                                v_for=("row in groupinfo_items",),
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

                    # Library media viewer — same right-side slot as the
                    # Galaxy / Group info cards; mutually exclusive.
                    with v3.VCard(
                        v_show=("library_show",),
                        style=(
                            "position:absolute;top:32px;right:24px;"
                            "min-width:280px;max-width:520px;"
                            "background:rgba(17,24,39,0.92);"
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
                            v3.VIcon("mdi-folder-multimedia-outline",
                                     size="small", color="cyan",
                                     style="margin-right:6px;")
                            html.Span("{{ library_name }}")
                            v3.VSpacer()
                            v3.VBtn(
                                icon="mdi-close",
                                size="x-small",
                                variant="text",
                                click=server.controller.library_close,
                            )
                        v3.VDivider()
                        with v3.VCardText(
                            style="padding:8px 12px;",
                        ):
                            html.Img(
                                src=("library_data_url",),
                                v_show=("library_kind === 'image'",),
                                style="max-width:100%;max-height:60vh;display:block;",
                            )
                            html.Video(
                                src=("library_data_url",),
                                v_show=("library_kind === 'video'",),
                                controls=True,
                                autoplay=True,
                                loop=True,
                                style="max-width:100%;max-height:60vh;display:block;",
                            )

                    # Loading overlay shown while a model loads
                    with v3.VOverlay(
                        v_model=("model_loading",),
                        contained=True,
                        persistent=True,
                        classes="d-flex align-center justify-center",
                        scrim="rgba(0,0,0,0.78)",
                    ):
                        with v3.VSheet(
                            color="#1a1a2e",
                            style=(
                                "padding:40px 56px;border-radius:6px;"
                                "border:1px solid #06b6d4;"
                                "display:flex;flex-direction:column;align-items:center;"
                                "gap:18px;min-width:480px;max-width:640px;"
                                "box-shadow:0 0 24px rgba(6,182,212,0.35);"
                            ),
                        ):
                            v3.VLabel(
                                "SWITCHING MODELS, PLEASE HOLD…",
                                style=(
                                    "font-size:1.35rem;font-weight:700;"
                                    "letter-spacing:0.12em;color:#06b6d4;"
                                    "text-align:center;"
                                ),
                            )
                            v3.VProgressLinear(
                                indeterminate=True, color="cyan", height=4,
                                style="width:100%;",
                            )
                            v3.VLabel(
                                "{{ model_quip }}",
                                style=(
                                    "font-size:0.95rem;color:#e2e8f0;"
                                    "text-align:center;font-style:italic;"
                                    "min-height:1.4em;"
                                ),
                            )

                # Right panel — layers + navigation tabs.
                # Locked to a fixed 300px width so layouts stay consistent
                # across screen sizes; flex-shrink/grow disabled so the
                # main viewport area absorbs all the slack. Internal scroll
                # handles overflow on short windows.
                with v3.VSheet(
                    style=(
                        "width:300px;min-width:300px;max-width:300px;"
                        "flex:0 0 300px;"
                        "height:100%;box-sizing:border-box;"
                        "overflow:hidden;"
                    ),
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

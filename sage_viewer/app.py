from __future__ import annotations

from pathlib import Path

from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import vuetify3 as v3
from trame_vtk.modules.vtk import has_capabilities
from trame_vtk.widgets.vtk import VtkRemoteView

from sage_viewer.config import SimConfig
from sage_viewer.io.par_reader import parse_par
from sage_viewer.io.snapshot_table import SnapshotTable
from sage_viewer.parallel.loader import SnapshotLoader
from sage_viewer.scene.scene import Scene
from sage_viewer.ui.info_panel import build_info_panel
from sage_viewer.ui.navigation_panel import build_navigation_panel
from sage_viewer.ui.toolbar import build_toolbar


def create_app(
    par_path: str | Path,
    initial_snap: int | None = None,
    n_jobs: int = -1,
    min_halo_mass: float = 1.0e10,
    min_stellar_mass: float = 1.0e8,
    max_halos: int = 100_000,
    max_galaxies: int = 100_000,
):
    config: SimConfig = parse_par(par_path)
    snap_table = SnapshotTable(config.snap_list_path)
    loader = SnapshotLoader(
        config=config,
        snap_table=snap_table,
        n_jobs=n_jobs,
        min_halo_mass=min_halo_mass,
        min_stellar_mass=min_stellar_mass,
        max_halos=max_halos,
        max_galaxies=max_galaxies,
    )

    if initial_snap is None:
        initial_snap = snap_table.count - 1

    scene = Scene(
        config=config,
        snap_table=snap_table,
        loader=loader,
        off_screen=False,
        initial_snap=initial_snap,
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

    with SinglePageLayout(server, full_height=True, vuetify_config=_vuetify_config) as layout:
        layout.title.set_text("SAGE-Viewer")
        # Hide the default VAppBarNavIcon — replaced by our custom menu button below
        layout.icon.style = "display:none;"

        with layout.toolbar as tb:
            tb.density = "compact"
            tb.color = "#1a1a2e"

            # Tab dropdown menu — sits in the natural nav-icon position
            with v3.VMenu():
                with v3.Template(v_slot_activator="{ props }"):
                    v3.VBtn(
                        icon="mdi-menu",
                        variant="text",
                        density="compact",
                        v_bind="props",
                        title="Tab menu",
                    )
                with v3.VList(density="compact", bg_color="#1a1a2e"):
                    for label, value in _NAV_TABS:
                        v3.VListItem(
                            title=label,
                            value=value,
                            click=f"nav_active_tab = '{value}'",
                            active=(f"nav_active_tab === '{value}'",),
                            color="cyan",
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
                # Render window — fills all available space
                view = VtkRemoteView(
                    scene.plotter.ren_win,
                    style="flex:1;height:100%;display:block;min-width:0;",
                    # Lower quality / ratio during motion drastically reduces
                    # the per-frame JPEG size — the limiting factor on smoothness.
                    interactive_ratio=0.75,
                    interactive_quality=60,
                    still_quality=85,
                )
                server.controller.view_update = view.update

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

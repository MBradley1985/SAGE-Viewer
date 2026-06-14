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
from sage_viewer.ui.layer_panel import build_layer_panel
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

    # Force Vuetify 3 into dark mode globally
    server.state["$vuetify"] = {
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

    with SinglePageLayout(server, full_height=True) as layout:
        layout.title.set_text("SAGE-Viewer")

        with layout.toolbar as tb:
            tb.density = "compact"
            tb.color = "#1a1a2e"
            build_toolbar(server, scene)

        with layout.content:
            # Plain flexbox row — avoids Vuetify grid padding/margin quirks
            with v3.VSheet(
                style=(
                    "display:flex;flex-direction:row;"
                    "height:100%;width:100%;"
                    "overflow:hidden;"
                ),
                rounded=False,
                elevation=0,
                color="#0a0a0f",
            ):
                # Left panel — layer controls
                with v3.VSheet(
                    style="width:270px;flex-shrink:0;overflow-y:auto;height:100%;",
                    color="#0d0d1a",
                    rounded=False,
                    elevation=0,
                ):
                    build_layer_panel(server, scene)

                # Centre — PyVista render window, fills remaining space
                view = VtkRemoteView(
                    scene.plotter.ren_win,
                    style="flex:1;height:100%;display:block;min-width:0;",
                    interactive_ratio=1,      # full resolution during mouse interaction
                    interactive_quality=85,   # JPEG quality during interaction
                    still_quality=100,        # full quality when still
                )
                server.controller.view_update = view.update

                # Right panel — navigation controls
                with v3.VSheet(
                    style="width:290px;flex-shrink:0;overflow-y:auto;height:100%;",
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

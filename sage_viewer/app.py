from __future__ import annotations

from pathlib import Path

from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import html as thtml
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

        # Prevent mouse wheel from changing number inputs or slider thumbs.
        # Blurring the active element on wheel skips the value change while
        # still letting the panel scroll normally.
        with layout.head:
            thtml.Script("""
document.addEventListener('wheel', function(e) {
    var el = document.activeElement;
    if (!el) return;
    if (el.tagName === 'INPUT' && el.type === 'number') { el.blur(); return; }
    if (el.classList && el.classList.contains('v-slider-thumb')) { el.blur(); }
}, { passive: true });
""")

        with layout.toolbar as tb:
            tb.density = "compact"
            tb.color = "#1a1a2e"
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
                    interactive_ratio=1,
                    interactive_quality=85,
                    still_quality=100,
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

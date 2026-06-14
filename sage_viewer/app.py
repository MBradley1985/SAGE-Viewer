from __future__ import annotations

from pathlib import Path

from trame.app import get_server
from trame.widgets import vuetify3 as v3
from trame_vtk.modules.vtk import has_capabilities

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
    """Instantiate and return a configured Trame server ready to serve.

    Returns (server, scene) so the caller can start the server or inspect
    the scene programmatically.
    """
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

    with v3.VApp(theme="dark"):
        build_toolbar(server, scene)

        with v3.VMain():
            with v3.VLayout(style="height:100vh;"):
                build_layer_panel(server, scene)

                # PyVista render window embedded via trame-vtk
                from trame_vtk.widgets.vtk import VtkRemoteView
                VtkRemoteView(
                    scene.plotter.ren_win,
                    style="flex:1;",
                )

                build_navigation_panel(server, scene)

        build_info_panel(server, scene)

    return server, scene

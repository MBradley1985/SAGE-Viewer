from __future__ import annotations

import os
from pathlib import Path

from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import html, vuetify3 as v3
from trame_vtk.modules.vtk import has_capabilities

from sage_viewer.wizard.controller import WizardController
from sage_viewer.wizard.ui import build_wizard_ui


def create_launch_app(port: int):
    server = get_server(client_type="vue3")
    server.enable_module(has_capabilities)

    _sage_static_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "static"
    )
    server.enable_module(
        {
            "serve": {"sage_static": _sage_static_dir},
            "scripts": ["sage_static/sage_viewer.js"],
        }
    )

    # xterm.js — required for the wizard terminal in Launch Mode.
    server.enable_module(
        {
            "styles": [
                "https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css",
            ],
            "scripts": [
                "https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js",
                "https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.10.0/lib/addon-fit.js",
            ],
        }
    )

    _vuetify_config = {
        "theme": {
            "defaultTheme": "dos_blue",
            "themes": {
                "dos_blue": {
                    "dark": True,
                    "colors": {
                        "primary": "#ffff55",
                        "secondary": "#ffffff",
                        "background": "#0000aa",
                        "surface": "#0000aa",
                        "on-surface": "#ffffff",
                        "on-background": "#ffffff",
                    },
                },
            },
        }
    }

    ctrl = WizardController(server, port)
    # JS polls for wiz_active changing from null/undefined → True to mount
    # the xterm.js wizard terminal.  launch.py has no Explore-mode wrapper
    # that would trigger this transition, so we set it explicitly here.
    server.state.wiz_active = True

    with SinglePageLayout(
        server,
        full_height=True,
        vuetify_config=_vuetify_config,
    ) as layout:
        layout.title.style = "display:none;"
        layout.icon.style = "display:none;"

        with layout.toolbar as tb:
            tb.style = "display:none;"

        with layout.content:
            build_wizard_ui(server, ctrl)

        with layout.footer as footer:
            footer.style = "display:none;"

    return server

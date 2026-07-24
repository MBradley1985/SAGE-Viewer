"""Live PSO plot gallery — a dedicated, right-docked panel that shows the
diagnostic plots SAGEswarm writes into its main folder while a run is in
progress.

The panel is driven entirely by two state vars maintained by
``WizardController``: ``pso_gallery_show`` (visibility) and ``pso_plots``
(a list of ``{name, data_url, mtime}`` dicts, re-scanned on a timer during the
run). Vue re-renders the grid whenever ``pso_plots`` changes, so no client-side
polling is needed.
"""

from __future__ import annotations

from trame.widgets import html
from trame.widgets import vuetify3 as v3


def build_pso_gallery(server) -> None:
    # position:fixed so it docks to the viewport regardless of ancestor
    # positioning; z-index above the wizard overlay (z-50).
    with html.Div(
        v_show=("pso_gallery_show",),
        style=(
            "position:fixed;top:0;right:0;bottom:0;z-index:60;"
            "width:min(46vw,720px);background:#05050a;"
            "border-left:2px solid #06b6d4;"
            "display:flex;flex-direction:column;"
        ),
    ):
        # Header
        with html.Div(
            style=(
                "display:flex;align-items:center;gap:10px;"
                "padding:10px 14px;border-bottom:1px solid #06b6d4;"
                "flex-shrink:0;"
            ),
        ):
            v3.VIcon("mdi-chart-scatter-plot", color="#06b6d4")
            html.Span(
                "PSO Live Plots",
                style="color:#06b6d4;font-weight:700;letter-spacing:0.06em;",
            )
            html.Span(
                "({{ (pso_plots || []).length }})",
                style="color:#9ca3af;font-size:0.8rem;",
            )
            v3.VSpacer()
            v3.VBtn(
                icon="mdi-close",
                variant="text",
                size="small",
                color="#9ca3af",
                title="Hide gallery",
                click="pso_gallery_show = false",
            )

        # Grid of plots
        with html.Div(
            style=(
                "flex:1;overflow-y:auto;padding:12px;"
                "display:grid;gap:12px;align-content:start;"
                "grid-template-columns:repeat(auto-fill,minmax(300px,1fr));"
            ),
        ):
            html.Div(
                "Waiting for plots…",
                v_show=("!pso_plots || pso_plots.length === 0",),
                style=(
                    "grid-column:1/-1;color:#6b7280;"
                    "padding:24px;text-align:center;font-family:monospace;"
                ),
            )
            with html.Div(
                v_for="p in pso_plots",
                key="p.name",
                style=(
                    "border:1px solid #374151;background:#000000;"
                    "display:flex;flex-direction:column;"
                ),
            ):
                html.Img(
                    src=("p.data_url",),
                    style="width:100%;height:auto;display:block;",
                )
                html.Span(
                    "{{ p.name }}",
                    style=(
                        "color:#9ca3af;font-size:0.7rem;"
                        "padding:4px 6px;text-align:center;"
                        "font-family:monospace;word-break:break-all;"
                    ),
                )

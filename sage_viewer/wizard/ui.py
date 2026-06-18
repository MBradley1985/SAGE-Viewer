from __future__ import annotations

from trame.widgets import html
from trame.widgets import vuetify3 as v3

from sage_viewer.wizard.controller import WizardController, _STEPS


_WIZ_CSS = """
.wiz-title { color: #FFD700; font-weight: 700; letter-spacing: 0.08em; }
.wiz-ok    { color: #22c55e; }
.wiz-warn  { color: #f59e0b; }
.wiz-err   { color: #ef4444; font-weight: 600; }
.wiz-cmd   { color: #06b6d4; }
.wiz-out   { color: #9ca3af; }
.wiz-sep   { color: #374151; }
.wiz-info  { color: #e2e8f0; }
"""


def build_wizard_ui(server, ctrl: WizardController) -> None:
    import base64 as _b64

    css_url = (
        "data:text/css;charset=utf-8;base64,"
        + _b64.b64encode(_WIZ_CSS.encode()).decode()
    )

    with html.Div(
        style=(
            "display:flex;flex-direction:column;height:100vh;"
            "background:#0a0a1a;font-family:monospace;"
        ),
    ):
        html.Link(rel="stylesheet", href=css_url)

        # ── Header ──────────────────────────────────────────────────────────
        with html.Div(
            style=(
                "background:#1a1a2e;border-bottom:2px solid #FFD700;"
                "padding:10px 20px;display:flex;align-items:center;gap:12px;"
                "flex-shrink:0;"
            ),
        ):
            v3.VIcon("mdi-rocket-launch", color="#FFD700", size="large")
            html.Span(
                "SAGE-Viewer",
                style="font-size:1.3rem;font-weight:700;color:#FFD700;",
            )
            html.Span(
                "Launch Mode",
                style=(
                    "font-size:1.0rem;color:#06b6d4;"
                    "border:1px solid #06b6d4;padding:2px 8px;"
                ),
            )
            v3.VSpacer()
            # Step indicator chips
            with html.Div(style="display:flex;gap:6px;align-items:center;"):
                for i, label in enumerate(_STEPS):
                    v3.VChip(
                        label,
                        size="small",
                        color=(
                            f"wiz_step === {i} ? '#FFD700' : "
                            f"(wiz_step > {i} ? '#22c55e' : '#374151')",
                        ),
                        variant=(
                            f"wiz_step === {i} ? 'elevated' : 'outlined'",
                        ),
                        style="font-family:monospace;font-size:0.7rem;",
                    )

        # ── Main area ────────────────────────────────────────────────────────
        with html.Div(
            style=(
                "flex:1;display:flex;align-items:center;"
                "justify-content:center;overflow:hidden;padding:24px;"
            ),
        ):
            with v3.VCard(
                style=(
                    "width:860px;max-width:96vw;height:640px;max-height:80vh;"
                    "background:#1a1a2e;border:2px solid #FFD700;"
                    "display:flex;flex-direction:column;"
                ),
                elevation=0,
                rounded=False,
            ):
                # Terminal output
                with v3.VSheet(
                    classes="sage-console-scroll",
                    color="#0a0a0f",
                    style=(
                        "flex:1;min-height:0;overflow-y:auto;"
                        "padding:14px 18px;"
                        "font-size:0.82rem;line-height:1.55;"
                    ),
                ):
                    with html.Div(
                        v_for="(line, idx) in wiz_lines",
                        key="idx",
                    ):
                        html.Div(
                            "{{ line.text || ' ' }}",
                            classes=("'wiz-' + line.kind",),
                            style="white-space:pre-wrap;",
                        )

                # Par file editor (shown only when wiz_par_show)
                with v3.VSheet(
                    v_show=("wiz_par_show",),
                    color="#0d0d1a",
                    style=(
                        "border-top:1px solid #374151;"
                        "padding:8px 12px;flex-shrink:0;"
                        "max-height:220px;overflow-y:auto;"
                    ),
                ):
                    v3.VTextarea(
                        v_model=("wiz_par_text",),
                        rows=9,
                        variant="outlined",
                        bg_color="#0a0a0f",
                        hide_details=True,
                        style=(
                            "font-family:monospace;font-size:0.75rem;"
                            "color:#e2e8f0;"
                        ),
                        label="Parameter file (edit freely, format is preserved)",
                    )

                # Action bar
                with html.Div(
                    style=(
                        "border-top:1px solid #374151;"
                        "background:#111122;"
                        "padding:10px 14px;"
                        "flex-shrink:0;"
                        "display:flex;flex-direction:column;gap:8px;"
                    ),
                ):
                    v3.VProgressLinear(
                        v_show=("wiz_busy",),
                        indeterminate=True,
                        color="#FFD700",
                        height=3,
                        style="width:100%;",
                    )
                    with html.Div(
                        v_show=("!wiz_busy && wiz_choices.length > 0",),
                        style="display:flex;flex-wrap:wrap;gap:8px;",
                    ):
                        with html.Div(
                            v_for="(ch, ci) in wiz_choices",
                            key="ci",
                        ):
                            v3.VBtn(
                                "{{ ch.label }}",
                                prepend_icon=("ch.icon",),
                                color=("#FFD700" if True else ""),
                                variant="outlined",
                                size="small",
                                disabled=("ch.disabled",),
                                click=(server.controller.wiz_choose, "[ch.value]"),
                                style="font-family:monospace;text-transform:none;",
                            )

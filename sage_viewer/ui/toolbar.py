from __future__ import annotations

import asyncio

from trame.widgets import vuetify3 as v3

from sage_viewer.scene.scene import Scene

_FPS = {1: 3, 2: 6, 5: 15}


def build_toolbar(server, scene: Scene) -> None:
    """Toolbar: play/pause/stop/reverse/repeat, snapshot slider, label, speed."""
    state, ctrl = server.state, server.controller
    snap_count = scene._snap_table.count

    state.snap_num   = scene.current_snap
    state.snap_label = scene.snap_label
    state.play_speed = 1
    state.is_playing = False
    state.is_reverse = False
    state.is_repeat  = False

    # Plain dict so the async coroutine sees mutations immediately
    # (Trame state proxy is not reactive inside a running coroutine)
    _ctl = {"playing": False, "reverse": False, "repeat": False}

    scene.register_snap_change_callback(
        lambda n: state.update({"snap_num": n, "snap_label": scene.snap_label})
    )

    def _push():
        if hasattr(ctrl, "view_update"):
            ctrl.view_update()

    def _go_to(snap: int) -> None:
        scene.set_snapshot(snap)
        state.snap_num   = snap
        state.snap_label = scene.snap_label
        _push()

    # ------------------------------------------------------------------
    # Slider — fires only when not playing; play loop drives snap directly
    # ------------------------------------------------------------------

    @state.change("snap_num")
    def on_snap_slider(snap_num, **_):
        if not _ctl["playing"]:
            scene.set_snapshot(int(snap_num))
            _push()

    # ------------------------------------------------------------------
    # Async play loop (runs on Trame event loop = main thread, VTK-safe)
    # ------------------------------------------------------------------

    @ctrl.set("play")
    async def on_play():
        if _ctl["playing"]:
            return
        _ctl["playing"] = True
        state.is_playing = True

        while _ctl["playing"]:
            interval = 1.0 / _FPS.get(state.play_speed, 3)

            if _ctl["reverse"]:
                next_snap = (scene.current_snap - 1) % snap_count
                at_end = next_snap == 0
            else:
                next_snap = (scene.current_snap + 1) % snap_count
                at_end = next_snap == snap_count - 1

            _go_to(next_snap)

            if at_end and not _ctl["repeat"]:
                _ctl["playing"] = False
                state.is_playing = False
                break

            await asyncio.sleep(interval)

    # ------------------------------------------------------------------
    # Pause — sets flag; coroutine exits at next iteration
    # ------------------------------------------------------------------

    @ctrl.set("pause")
    def on_pause():
        _ctl["playing"] = False
        state.is_playing = False

    # ------------------------------------------------------------------
    # Stop — pauses and returns to z = 0 (snap 63)
    # ------------------------------------------------------------------

    @ctrl.set("stop")
    def on_stop():
        _ctl["playing"] = False
        state.is_playing = False
        _go_to(snap_count - 1)   # always z = 0

    # ------------------------------------------------------------------
    # Reverse / Repeat toggles
    # ------------------------------------------------------------------

    @ctrl.set("toggle_reverse")
    def on_toggle_reverse():
        _ctl["reverse"]  = not _ctl["reverse"]
        state.is_reverse = _ctl["reverse"]

    @ctrl.set("toggle_repeat")
    def on_toggle_repeat():
        _ctl["repeat"]  = not _ctl["repeat"]
        state.is_repeat = _ctl["repeat"]

    # ------------------------------------------------------------------
    # Widgets
    # ------------------------------------------------------------------

    v3.VToolbarTitle("SAGE-Viewer", style="font-size:1rem;min-width:120px;")
    v3.VSpacer()

    # Transport controls
    with v3.VBtnGroup(variant="outlined", density="compact"):
        v3.VBtn(
            icon="mdi-swap-horizontal",
            click=ctrl.toggle_reverse,
            color=("is_reverse ? 'cyan' : '#6b7280'",),
            title="Reverse direction",
        )
        v3.VBtn(
            icon="mdi-play",
            click=ctrl.play,
            disabled=("is_playing",),
            color=("#6b7280",),
        )
        v3.VBtn(
            icon="mdi-pause",
            click=ctrl.pause,
            disabled=("!is_playing",),
            color=("#6b7280",),
        )
        v3.VBtn(
            icon="mdi-stop",
            click=ctrl.stop,
            color=("#6b7280",),
            title="Stop and return to z=0",
        )
        v3.VBtn(
            icon="mdi-repeat",
            click=ctrl.toggle_repeat,
            color=("is_repeat ? 'cyan' : '#6b7280'",),
            title="Loop",
        )

    v3.VSpacer()

    # Snapshot slider
    with v3.VCol(style="max-width:340px;padding:0 12px;"):
        v3.VSlider(
            v_model=("snap_num",),
            min=0,
            max=snap_count - 1,
            step=1,
            thumb_label=False,
            hide_details=True,
            color="cyan",
            density="compact",
        )

    # Snapshot label
    v3.VChip(
        ("snap_label",),
        size="small",
        color="deep-purple",
        style="font-family:monospace;min-width:240px;",
    )

    v3.VSpacer()

    # Speed selector
    v3.VSelect(
        v_model=("play_speed",),
        items=([
            {"title": "1×", "value": 1},
            {"title": "2×", "value": 2},
            {"title": "5×", "value": 5},
        ],),
        density="compact",
        hide_details=True,
        style="max-width:80px;",
    )

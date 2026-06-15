from __future__ import annotations

import asyncio

import numpy as np
from trame.widgets import vuetify3 as v3

from sage_viewer.scene.scene import Scene

# Frames per second for each speed multiplier
_FPS: dict[float, float] = {
    0.1:  0.3,
    0.25: 0.75,
    0.5:  1.5,
    0.75: 2.25,
    1:    3,
    2:    6,
    5:    15,
}

_SPEED_ITEMS = [
    {"title": "0.1×", "value": 0.1},
    {"title": "0.25×", "value": 0.25},
    {"title": "0.5×", "value": 0.5},
    {"title": "0.75×", "value": 0.75},
    {"title": "1×",   "value": 1},
    {"title": "2×",   "value": 2},
    {"title": "5×",   "value": 5},
]

_ROTATE_ITEMS = [
    {"title": "Off",         "value": "off"},
    {"title": "CW  15°/s",  "value": "cw_15"},
    {"title": "CW  30°/s",  "value": "cw_30"},
    {"title": "CW  60°/s",  "value": "cw_60"},
    {"title": "CCW 15°/s",  "value": "ccw_15"},
    {"title": "CCW 30°/s",  "value": "ccw_30"},
    {"title": "CCW 60°/s",  "value": "ccw_60"},
]

_ROT_RATE_FPS = 12   # rotation render rate — lower = less load, larger steps

def _parse_rotate(mode: str) -> tuple[float, float]:
    """Return (sign, deg_per_second) for a rotate_mode string, or (0, 0) for off."""
    if mode == "off":
        return 0.0, 0.0
    parts = mode.split("_")
    sign  = 1.0 if parts[0] == "cw" else -1.0
    return sign, float(parts[1])


def build_toolbar(server, scene: Scene) -> None:
    state, ctrl = server.state, server.controller
    snap_count = scene._snap_table.count

    state.snap_num    = scene.current_snap
    state.snap_label  = scene.snap_label
    state.play_speed  = 1
    state.is_playing  = False
    state.is_reverse  = False
    state.is_repeat   = False
    state.rotate_mode = "off"

    # Plain dict — direction/repeat flags read from the play coroutine
    _ctl = {"reverse": False, "repeat": False, "rotate_mode": "off"}

    # asyncio.Event drives pause/stop without relying on state-proxy reactivity.
    # Created lazily on first use so we bind to the running loop.
    _stop_evt: list[asyncio.Event | None] = [None]
    _play_task: list[asyncio.Task | None] = [None]
    _rotate_task: list[asyncio.Task | None] = [None]

    def _get_stop_evt() -> asyncio.Event:
        if _stop_evt[0] is None:
            _stop_evt[0] = asyncio.Event()
        return _stop_evt[0]

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
        # No state.flush() here — let Trame batch state with the next render
        _push()

    # ------------------------------------------------------------------
    # Slider
    # ------------------------------------------------------------------

    @state.change("snap_num")
    def on_snap_slider(snap_num, **_):
        if _play_task[0] is None or _play_task[0].done():
            scene.set_snapshot(int(snap_num))
            state.snap_label = scene.snap_label
            state.flush()
            _push()

    # ------------------------------------------------------------------
    # Playback — driven by a single task + asyncio.Event for instant stop
    # ------------------------------------------------------------------

    async def _play_loop():
        stop_evt = _get_stop_evt()
        stop_evt.clear()
        state.is_playing = True
        state.flush()
        # Tell VTK "we want fast frames" so it picks low-cost rendering paths
        rw = scene.plotter.ren_win
        rw.SetDesiredUpdateRate(15.0)
        try:
            while not stop_evt.is_set():
                fps      = _FPS.get(float(state.play_speed), 3)
                interval = 1.0 / fps

                if _ctl["reverse"]:
                    next_snap = (scene.current_snap - 1) % snap_count
                    at_end    = next_snap == 0
                else:
                    next_snap = (scene.current_snap + 1) % snap_count
                    at_end    = next_snap == snap_count - 1

                _go_to(next_snap)

                if at_end and not _ctl["repeat"]:
                    break

                # Sleep but break early if stop fires
                try:
                    await asyncio.wait_for(stop_evt.wait(), timeout=interval)
                    break
                except asyncio.TimeoutError:
                    pass
        finally:
            rw.SetDesiredUpdateRate(0.0001)   # back to high-quality rendering
            state.is_playing = False
            state.flush()

    @ctrl.set("play")
    async def on_play():
        if _play_task[0] is not None and not _play_task[0].done():
            return
        _play_task[0] = asyncio.ensure_future(_play_loop())

    @ctrl.set("pause")
    def on_pause():
        if _stop_evt[0] is not None:
            _stop_evt[0].set()
        if _play_task[0] is not None and not _play_task[0].done():
            _play_task[0].cancel()
        state.is_playing = False
        state.flush()

    @ctrl.set("stop")
    def on_stop():
        if _stop_evt[0] is not None:
            _stop_evt[0].set()
        if _play_task[0] is not None and not _play_task[0].done():
            _play_task[0].cancel()
        state.is_playing = False
        _go_to(snap_count - 1)

    @ctrl.set("toggle_reverse")
    def on_toggle_reverse():
        _ctl["reverse"]  = not _ctl["reverse"]
        state.is_reverse = _ctl["reverse"]

    @ctrl.set("toggle_repeat")
    def on_toggle_repeat():
        _ctl["repeat"]  = not _ctl["repeat"]
        state.is_repeat = _ctl["repeat"]

    # ------------------------------------------------------------------
    # Rotation — smaller per-frame angle for smoothness
    # ------------------------------------------------------------------

    async def _rotate_loop():
        interval = 1.0 / _ROT_RATE_FPS
        rw = scene.plotter.ren_win
        rw.SetDesiredUpdateRate(_ROT_RATE_FPS)
        try:
            while _ctl["rotate_mode"] != "off":
                mode = _ctl["rotate_mode"]
                sign, deg_per_sec = _parse_rotate(mode)
                if sign == 0:
                    break
                delta  = sign * deg_per_sec * interval
                cam    = scene.plotter.camera
                focal  = np.array(cam.focal_point, dtype=np.float64)
                pos    = np.array(cam.position,    dtype=np.float64)
                r      = pos - focal
                angle  = np.deg2rad(delta)
                c, s   = np.cos(angle), np.sin(angle)
                rm     = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
                cam.position = tuple(focal + rm @ r)
                cam.up       = (0.0, 1.0, 0.0)
                _push()
                await asyncio.sleep(interval)
        finally:
            rw.SetDesiredUpdateRate(0.0001)   # back to high-quality rendering

    @state.change("rotate_mode")
    def on_rotate_mode(rotate_mode, **_):
        _ctl["rotate_mode"] = rotate_mode
        if rotate_mode == "off":
            if _rotate_task[0] is not None and not _rotate_task[0].done():
                _rotate_task[0].cancel()
            return
        if _rotate_task[0] is None or _rotate_task[0].done():
            _rotate_task[0] = asyncio.ensure_future(_rotate_loop())

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
        v3.VBtn(icon="mdi-play",  click=ctrl.play,  color="#6b7280")
        v3.VBtn(icon="mdi-pause", click=ctrl.pause, color="#6b7280")
        v3.VBtn(icon="mdi-stop",  click=ctrl.stop,  color="#6b7280",
                title="Stop and return to z=0")
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
            min=0, max=snap_count - 1, step=1,
            thumb_label=False, hide_details=True,
            color="cyan", density="compact",
        )

    # Snapshot label chip — Mustache interpolation for reactive content
    v3.VChip(
        "{{ snap_label }}",
        size="small",
        color="deep-purple",
        style="font-family:monospace;min-width:240px;",
    )

    v3.VSpacer()

    # Speed selector
    v3.VSelect(
        v_model=("play_speed",),
        items=(_SPEED_ITEMS,),
        density="compact",
        hide_details=True,
        style="max-width:90px;",
    )

    # Rotation selector
    v3.VSelect(
        v_model=("rotate_mode",),
        items=(_ROTATE_ITEMS,),
        density="compact",
        hide_details=True,
        style="max-width:120px;",
    )

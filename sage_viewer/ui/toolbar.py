from __future__ import annotations

import asyncio
import base64
import io

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
    state.preload_status = ""   # non-empty while the snapshot cache warms
    # Pre-rendered playback: frames are rendered once on play, then flipped
    # through as images for stutter-free playback.
    state.playback_active = False   # showing pre-rendered frames
    state.playback_frame  = ""      # current frame data URL
    state.prerender_busy  = False   # rendering frames (full-viewport overlay)

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

    # Per-snapshot frame cache + the camera/rotation signature it's valid for.
    _frames: dict = {"key": None, "data": {}}

    def _cam_key():
        cam = scene.plotter.camera
        return (
            tuple(np.round(cam.position, 2)),
            tuple(np.round(cam.focal_point, 2)),
            tuple(np.round(cam.up, 3)),
            _ctl["rotate_mode"],
        )

    def _cancel_rotate():
        if _rotate_task[0] is not None and not _rotate_task[0].done():
            _rotate_task[0].cancel()

    def _ensure_rotate_loop():
        if _ctl["rotate_mode"] != "off" and (
            _rotate_task[0] is None or _rotate_task[0].done()
        ):
            _rotate_task[0] = asyncio.ensure_future(_rotate_loop())

    def _capture_frame() -> "np.ndarray":
        """Grab the current render-window image as an (H, W, 3) uint8 array.
        Uses vtkWindowToImageFilter directly because the remote-view plotter
        is never .show()n, so pyvista's screenshot() refuses to run."""
        from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter
        from vtkmodules.util.numpy_support import vtk_to_numpy
        rw = scene.plotter.ren_win
        rw.Render()
        w2if = vtkWindowToImageFilter()
        w2if.SetInput(rw)
        w2if.SetInputBufferTypeToRGB()
        w2if.ReadFrontBufferOff()
        w2if.Update()
        vimg = w2if.GetOutput()
        w, h, _ = vimg.GetDimensions()
        arr = vtk_to_numpy(vimg.GetPointData().GetScalars()).reshape(h, w, -1)
        return arr[::-1]   # VTK image origin is bottom-left

    async def _render_frames(order: list[int]) -> None:
        """Render the snapshots in `order` (skipping any already cached) into
        _frames['data']. Rotation, when active, is baked by play-order
        position so the spin starts from the current view. Camera + snapshot
        are restored afterwards."""
        from PIL import Image
        pl     = scene.plotter
        cam    = pl.camera
        pos0   = np.array(cam.position,    dtype=np.float64)
        focal0 = np.array(cam.focal_point, dtype=np.float64)
        save_snap = scene.current_snap
        sign, dps = _parse_rotate(_ctl["rotate_mode"])
        per_snap  = np.deg2rad(sign * dps / 3.0)
        stop_evt  = _get_stop_evt()

        todo = [(pos, s) for pos, s in enumerate(order)
                if s not in _frames["data"]]
        total = len(todo)
        if total == 0:
            return

        state.prerender_busy = True
        state.flush()
        # Off-screen rendering writes to an FBO we can actually read back —
        # the on-screen/back buffer comes out black on this setup.
        rw = pl.ren_win
        prev_offscreen = rw.GetOffScreenRendering()
        rw.SetOffScreenRendering(1)
        try:
            done = 0
            for pos, s in todo:
                if stop_evt.is_set():
                    break
                scene.set_snapshot(s)
                if per_snap:
                    ang = per_snap * pos
                    c, sn = np.cos(ang), np.sin(ang)
                    rm = np.array([[c, 0, sn], [0, 1, 0], [-sn, 0, c]])
                    cam.position    = tuple(focal0 + rm @ (pos0 - focal0))
                    cam.focal_point = tuple(focal0)
                    cam.up          = (0.0, 1.0, 0.0)
                img = _capture_frame()
                buf = io.BytesIO()
                Image.fromarray(img[..., :3]).save(buf, format="JPEG", quality=85)
                _frames["data"][s] = (
                    "data:image/jpeg;base64,"
                    + base64.b64encode(buf.getvalue()).decode("ascii")
                )
                done += 1
                state.preload_status = f"Loading galaxies.....  {done}/{total}"
                state.flush()
                await asyncio.sleep(0)
        finally:
            rw.SetOffScreenRendering(prev_offscreen)
            scene.set_snapshot(save_snap)
            cam.position    = tuple(pos0)
            cam.focal_point = tuple(focal0)
            cam.up          = (0.0, 1.0, 0.0)
            state.prerender_busy = False
            state.preload_status = ""
            state.flush()
            _push()

    async def _image_playback(order: list[int]) -> None:
        stop_evt = _get_stop_evt()
        n = len(order)
        if n == 0:
            return
        state.playback_active = True
        state.is_playing = True
        state.flush()
        idx = 0
        try:
            while not stop_evt.is_set():
                interval = 1.0 / _FPS.get(float(state.play_speed), 3)
                s = order[idx]
                frame = _frames["data"].get(s)
                if frame is not None:
                    state.playback_frame = frame
                state.snap_num   = s
                state.snap_label = scene._snap_table.label(s)
                state.flush()

                # Hold every frame — including the last — for the full
                # interval, otherwise the final snapshot just flashes past.
                try:
                    await asyncio.wait_for(stop_evt.wait(), timeout=interval)
                    break
                except asyncio.TimeoutError:
                    pass

                if idx == n - 1:
                    if not _ctl["repeat"]:
                        break
                    idx = 0
                else:
                    idx += 1
        finally:
            state.is_playing = False
            state.flush()

    async def _play_sequence():
        stop_evt = _get_stop_evt()
        _cancel_rotate()
        await _await_preload()
        if stop_evt.is_set():
            return
        # Invalidate the frame cache if the camera / rotation changed.
        key = _cam_key()
        if _frames["key"] != key:
            _frames["key"]  = key
            _frames["data"] = {}
        # Play from the current slider position toward z=0 (forward) or toward
        # high-z (reverse). Only that range is rendered.
        start = int(state.snap_num)
        if _ctl["reverse"]:
            order = list(range(start, -1, -1))
        else:
            order = list(range(start, snap_count))
        await _render_frames(order)
        if stop_evt.is_set():
            state.playback_active = False
            state.flush()
            return
        await _image_playback(order)
        # Ended naturally — sync the live view to the last frame and let it
        # reach the client BEFORE hiding the overlay, so there's no flash of a
        # stale frame as the overlay drops away.
        last = int(state.snap_num)
        scene.set_snapshot(last)
        state.snap_label = scene.snap_label
        state.flush()
        _push()
        await asyncio.sleep(0.15)
        state.playback_active = False
        state.flush()
        _ensure_rotate_loop()

    @ctrl.set("play")
    async def on_play():
        if _play_task[0] is not None and not _play_task[0].done():
            return
        _get_stop_evt().clear()
        _start_preload()
        _play_task[0] = asyncio.ensure_future(_play_sequence())

    def _end_playback_to(snap: int) -> None:
        """Stop any playback / prerender, hide the overlay, and show `snap`
        in the live view."""
        if _stop_evt[0] is not None:
            _stop_evt[0].set()
        if _play_task[0] is not None and not _play_task[0].done():
            _play_task[0].cancel()
        state.is_playing = False
        state.playback_active = False
        state.prerender_busy  = False
        state.preload_status  = ""
        scene.set_snapshot(snap)
        state.snap_num   = snap
        state.snap_label = scene.snap_label
        state.flush()
        _push()
        _ensure_rotate_loop()

    @ctrl.set("pause")
    def on_pause():
        _end_playback_to(int(state.snap_num))

    @ctrl.set("stop")
    def on_stop():
        _end_playback_to(snap_count - 1)

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
    # Snapshot preloading — warm the whole cache in the background so
    # playback steps frame-to-frame without disk stalls. A status chip in
    # the toolbar reports progress while it runs.
    # ------------------------------------------------------------------

    _preload_started = [False]
    _preload_done    = [False]

    async def _preload_loop():
        loader  = scene._loader
        futures = loader.preload_all()
        total   = len(futures)
        if total == 0:
            _preload_done[0] = True
            return
        while True:
            done = sum(1 for f in futures if f.done())
            if done >= total:
                break
            state.preload_status = f"Loading galaxies.....  {done}/{total}"
            state.flush()
            await asyncio.sleep(0.25)
        _preload_done[0] = True
        state.preload_status = ""
        state.flush()

    def _start_preload(**_):
        if _preload_started[0]:
            return
        _preload_started[0] = True
        try:
            asyncio.ensure_future(_preload_loop())
        except RuntimeError:
            # No running loop yet — fall back to first play press.
            _preload_started[0] = False

    async def _await_preload():
        """Block until every snapshot is cached so playback runs at an even
        cadence — without this, playback overtakes the background preload and
        stalls on uncached snapshots mid-run, then bursts through the rest."""
        _start_preload()
        if not _preload_started[0]:        # no loop earlier — start inline now
            _preload_started[0] = True
            asyncio.ensure_future(_preload_loop())
        while not _preload_done[0]:
            await asyncio.sleep(0.1)

    if hasattr(ctrl, "on_server_ready"):
        ctrl.on_server_ready.add(_start_preload)

    # ------------------------------------------------------------------
    # Widgets
    # ------------------------------------------------------------------

    # Single big spacer pushes the entire playback cluster to the right
    # of the toolbar, immediately adjacent to the title / hamburger on
    # the left.
    v3.VSpacer()

    # Cache warm-up indicator — sits just left of the transport controls and
    # only shows while snapshots are still loading in the background.
    v3.VChip(
        "{{ preload_status }}",
        v_show=("preload_status",),
        size="small",
        color="#FFD700",
        prepend_icon="mdi-database-clock-outline",
        style="font-family:monospace;margin-right:10px;",
    )

    # Transport controls — leftmost of the right-hand cluster.
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

    # Snapshot slider
    with v3.VCol(style="max-width:280px;padding:0 12px;"):
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
        color="cyan",
        style="font-family:monospace;min-width:220px;margin-right:8px;",
    )

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

    # (theme selector removed — DOS Blue is the only palette)

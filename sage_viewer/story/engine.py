"""Story playback engine.

``StoryPlayer`` owns the active story, the current scene index, and the async
playback task.  It applies scenes (camera + state + focus + target + theme),
runs per-scene motion, and steps with Next / Previous / Play / Pause.  It is a
non-destructive overlay: entering stashes the user's state, exiting restores it,
and pausing simply stops auto-advance without locking anything.
"""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy

import numpy as np

from sage_viewer.scene.camera_motion import (
    orbit_around,
    orbit_start_position,
    smooth_move,
)
from sage_viewer.story.keys import STORY_STATE_KEYS
from sage_viewer.story.model import Story

_FPS = 15.0  # render rate for transitions / motion (matches fly-through)
_UP = (0.0, 1.0, 0.0)

# Per-kind text-overlay defaults (size in rem, weight, italic, default colour).
_OVERLAY_DEFAULTS = {
    "title": {"size": 2.2, "weight": 800, "italic": False, "color": "#ffffff"},
    "heading": {"size": 1.6, "weight": 700, "italic": False, "color": "#ffffff"},
    "text": {"size": 1.15, "weight": 400, "italic": False, "color": "#e2e8f0"},
    "citation": {"size": 0.85, "weight": 400, "italic": True, "color": "#94a3b8"},
    "equation": {"size": 1.6, "weight": 400, "italic": False, "color": "#ffffff"},
}


async def _maybe_await(result):
    """Await *result* if it is awaitable; otherwise return it."""
    if asyncio.iscoroutine(result) or isinstance(result, asyncio.Future):
        return await result
    return result


def _overlay_position_style(anchor: str, x, y) -> str:
    """CSS positioning for a 9-grid anchor plus an offset.

    ``x``/``y`` are percentages when numeric, or pass-through CSS lengths when
    given as strings (e.g. ``"150px"``) — handy for pinning logos to a fixed
    pixel offset regardless of window width.
    """
    def _len(v):
        return v if isinstance(v, str) else f"{float(v)}%"

    parts: list[str] = ["position:absolute;"]
    transforms: list[str] = []
    # Vertical.
    if anchor.startswith("top"):
        parts.append(f"top:{_len(y)};")
    elif anchor.startswith("bottom"):
        parts.append(f"bottom:{_len(y)};")
    else:  # vertical centre
        parts.append("top:50%;")
        transforms.append("translateY(-50%)")
    # Horizontal.
    if anchor.endswith("left"):
        parts.append(f"left:{_len(x)};")
    elif anchor.endswith("right"):
        parts.append(f"right:{_len(x)};")
    else:  # horizontal centre
        parts.append("left:50%;")
        transforms.append("translateX(-50%)")
    if transforms:
        parts.append(f"transform:{' '.join(transforms)};")
    return "".join(parts)


def _normalize_overlay(item: dict) -> dict:
    """Turn an authored overlay into a render-ready dict for the JS renderer.

    Equation items carry ``latex`` + ``display`` so the client calls
    ``katex.render`` directly (more reliable than delimiter auto-render).
    Other items carry plain ``text``.
    """
    kind = item.get("kind", "text")
    anchor = item.get("anchor", "top-left")
    # Numeric → percentage; string → pass-through CSS length (e.g. "150px").
    x = item.get("x", 6.0)
    y = item.get("y", 6.0)

    # Image overlays (e.g. logos) carry a src + sizing, not text/font props.
    if kind == "image":
        w = item.get("width", 140)
        width_css = w if isinstance(w, str) else f"{float(w):g}px"
        style = (
            _overlay_position_style(anchor, x, y)
            + f"width:{width_css};height:auto;"
            + f"opacity:{float(item.get('opacity', 1.0))};"
            + "pointer-events:none;"
            + "filter:drop-shadow(0 2px 8px rgba(0,0,0,0.8));"
        )
        return {"id": str(item.get("id", "")), "style": style,
                "src": item.get("src", "")}

    base = _OVERLAY_DEFAULTS.get(kind, _OVERLAY_DEFAULTS["text"])

    size = float(item.get("size", base["size"]))
    color = item.get("color", base["color"])
    weight = int(item.get("weight", base["weight"]))
    italic = bool(item.get("italic", base["italic"]))
    align = item.get("align", "left")

    style = (
        _overlay_position_style(anchor, x, y)
        + f"font-size:{size}rem;color:{color};font-weight:{weight};"
        + f"text-align:{align};"
        + ("font-style:italic;" if italic else "")
        + "white-space:pre-wrap;pointer-events:none;"
        + "text-shadow:0 2px 8px rgba(0,0,0,0.8);line-height:1.25;"
        + f"max-width:{float(item.get('max_width', 60))}vw;"
    )
    out: dict = {"id": str(item.get("id", "")), "style": style}
    if kind == "equation":
        out["latex"] = item.get("latex", "")
        out["display"] = not bool(item.get("inline"))
    else:
        out["text"] = item.get("text", "")
    return out


def resolve_snap(value, count: int) -> int:
    """Resolve a (possibly symbolic) snapshot reference for a model.

    Accepts an int (absolute), ``"first"`` / ``"last"``, or a percentage
    string like ``"40%"`` — so a story is portable across models with
    different snapshot counts.  Always clamped to ``[0, count-1]``.
    """
    last = max(0, int(count) - 1)
    if isinstance(value, str):
        v = value.strip().lower()
        if v == "last":
            return last
        if v == "first":
            return 0
        if v.endswith("%"):
            try:
                frac = float(v[:-1]) / 100.0
            except ValueError:
                return last
            return max(0, min(last, round(frac * last)))
        try:
            value = int(float(v))
        except ValueError:
            return last
    return max(0, min(last, int(value)))


class StoryPlayer:
    def __init__(self, server, scene) -> None:
        self._server = server
        self._scene = scene
        self._story: Story | None = None
        self._index = 0
        self._playing = False
        self._paused = False  # True after pause() → next play() resumes in place
        self._task: asyncio.Task | None = None
        self._saved: dict | None = None  # user state stashed on enter
        # Scene indices whose fly-through intro (reset → approach → clusters)
        # has already played, so a pause/resume doesn't restart the tour.
        self._ft_done: set[int] = set()

    # ---- small helpers --------------------------------------------------

    @property
    def state(self):
        return self._server.state

    @property
    def ctrl(self):
        return self._server.controller

    def _push(self) -> None:
        if hasattr(self.ctrl, "view_update"):
            self.ctrl.view_update()

    def _start(self, coro) -> None:
        """Cancel any running task and start *coro*."""
        if self._task is not None and not self._task.done():
            self._task.cancel()
        self._task = asyncio.ensure_future(coro)

    # ---- HUD state ------------------------------------------------------

    def _push_hud(self) -> None:
        st = self.state
        if self._story is None:
            st.story_active = False
            st.flush()
            return
        sc = self._story.scenes[self._index]
        st.story_active = True
        st.story_playing = self._playing
        st.story_title = self._story.title
        st.story_scene_title = sc.title
        st.story_scene_caption = sc.caption
        st.story_scene_index = self._index + 1
        st.story_scene_count = len(self._story.scenes)
        st.flush()

    # ---- lifecycle ------------------------------------------------------

    def enter(self, story: Story) -> None:
        """Enter Story Mode: stash user state, preload sandbox, play scene 0."""
        if not story.scenes:
            return
        self._story = story
        self._index = 0
        self._playing = False
        self._save_user_state()
        self._start(self._enter_async(story))

    async def _enter_async(self, story: Story) -> None:
        try:
            await self._preload_sandbox(story)
            await self.apply_scene(0, transition=False)
            # Story-level autoplay: begin playback immediately so a title
            # scene's motion (e.g. a fly-through) runs without a Play click.
            if getattr(story, "autoplay", False):
                self._playing = True
                self._push_hud()
                await self._autoplay_from(0)
        except asyncio.CancelledError:
            pass

    def exit(self) -> None:
        """Leave Story Mode and restore the user's prior state."""
        self._playing = False
        self._story = None
        self.state.story_active = False
        self.state.story_playing = False
        self.state.story_overlays_json = "[]"
        self.state.flush()
        # Restore (incl. async model switch-back) on a fresh task.
        self._start(self._exit_async())

    async def _exit_async(self) -> None:
        try:
            await self._restore_models()
            self._restore_user_state()
        except asyncio.CancelledError:
            pass

    # ---- transport ------------------------------------------------------

    def next(self) -> None:
        if self._story is None:
            return
        i = min(self._index + 1, len(self._story.scenes) - 1)
        self._start(self._go(i, play=self._playing))

    def prev(self) -> None:
        if self._story is None:
            return
        i = max(self._index - 1, 0)
        self._start(self._go(i, play=self._playing))

    def play(self) -> None:
        if self._story is None:
            return
        if self._paused:
            # Resume in place: continue the current scene's motion WITHOUT
            # re-staging it (so a fly-through doesn't restart from the top),
            # and re-hide the panel per the scene's chrome.
            self._paused = False
            self._playing = True
            self._apply_chrome(self._story.scenes[self._index])
            self.state.flush()
            self._push_hud()
            self._start(self._resume())
        else:
            self._playing = True
            self._push_hud()
            self._start(self._go(self._index, play=True))

    async def _resume(self) -> None:
        try:
            await self._autoplay_from(self._index)
        except asyncio.CancelledError:
            pass

    def pause(self) -> None:
        # Stop auto-advance, freeze motion, and hand full control back: show
        # the right panel again (even if the scene hid it for presentation).
        self._playing = False
        self._paused = True
        if self._task is not None and not self._task.done():
            self._task.cancel()
        self.state.panels_hidden = False
        self.state.flush()
        self._push_hud()

    def goto(self, i: int) -> None:
        if self._story is None:
            return
        i = max(0, min(int(i), len(self._story.scenes) - 1))
        self._start(self._go(i, play=self._playing))

    # ---- async drivers --------------------------------------------------

    async def _go(self, i: int, *, play: bool) -> None:
        try:
            await self.apply_scene(i, transition=True)
            if play:
                await self._autoplay_from(i)
        except asyncio.CancelledError:
            pass

    async def _autoplay_from(self, i: int) -> None:
        n = len(self._story.scenes)
        while self._playing:
            await self._run_motion(self._story.scenes[i])
            if not self._playing:
                break
            if i + 1 >= n:
                self._playing = False
                self._push_hud()
                break
            i += 1
            await self.apply_scene(i, transition=True)

    # ---- scene application ----------------------------------------------

    async def apply_scene(self, i: int, *, transition: bool = True) -> None:
        scene = self._scene
        sc = self._story.scenes[i]
        self._index = i
        # Freshly staging a scene clears any paused/resume state and replays
        # this scene's fly-through intro on the next motion run.
        self._paused = False
        self._ft_done.discard(i)
        self._push_hud()

        # Model / multi-box layout first — it changes the active data.
        await self._apply_models(sc)
        # Data: snapshot (triggers filter re-apply via callbacks).
        self._apply_snapshot(sc)
        # Apply all reactive state, then flush ONCE so the client re-renders a
        # single time per scene (multiple flushes caused playback stutter).
        self._apply_flat_state(sc)
        self._apply_theme(sc)
        self._apply_chrome(sc)
        self._apply_overlays(sc)
        self.state.flush()

        # Camera (resolved — supports "box"/"reset" framing for portability).
        cam = scene.plotter.camera
        pos1, foc1, up1 = self._resolve_camera(sc)
        secs = float(sc.transition.get("duration_secs", 0.0)) if transition else 0.0
        if secs > 0.05:
            await smooth_move(
                cam,
                np.asarray(cam.position, dtype=float),
                np.asarray(cam.focal_point, dtype=float),
                pos1,
                foc1,
                secs,
                _FPS,
                is_active=lambda: True,
                push=self._push,
            )
        else:
            cam.position = tuple(pos1)
            cam.focal_point = tuple(foc1)
            cam.up = tuple(up1)
            self._push()

        # Focus + target after camera is settled (single flush).
        self._apply_focus(sc)
        self._apply_target(sc)
        self.state.flush()
        self._push()

    # ---- symbolic resolution (portability across models) ----------------

    def _box(self) -> tuple[float, np.ndarray]:
        """Return (box_size, box_centre) of the active model."""
        bs = float(self._scene.active_model.box_size)
        c = bs / 2.0
        return bs, np.array([c, c, c], dtype=float)

    def _resolve_point(self, value) -> np.ndarray | None:
        """Resolve a point: ``"box"`` → box centre, list → array."""
        if value is None:
            return None
        if isinstance(value, str):
            if value.strip().lower() == "box":
                return self._box()[1]
            return None
        return np.asarray(value, dtype=float)

    def _frame_boxes(self):
        """Frame all currently-loaded boxes (primary + adjacent).

        Box-size aware and multi-box aware, so the same ``"box"`` camera works
        whether one or several simulations are side-by-side.
        """
        scene = self._scene
        boxes = [(np.asarray(scene.primary.offset, dtype=float),
                  float(scene.primary.box_size))]
        for name in (getattr(scene, "_adjacent_order", []) or []):
            m = scene._models.get(name)
            if m is not None:
                boxes.append((np.asarray(m.offset, dtype=float),
                              float(m.box_size)))
        mins = np.array([min(o[i] for o, _ in boxes) for i in range(3)], float)
        maxs = np.array(
            [max(o[i] + bs for o, bs in boxes) for i in range(3)], float
        )
        center = (mins + maxs) / 2.0
        extent = float(np.max(maxs - mins))
        pos = np.array(
            [center[0], center[1], maxs[2] + extent * 1.2], dtype=float
        )
        return pos, center, np.array(_UP, dtype=float)

    def _resolve_camera(self, sc):
        """Resolve a scene camera to (position, focal_point, up) arrays.

        ``sc.camera`` may be an explicit dict, or the string ``"box"`` /
        ``"reset"`` to frame all loaded boxes (size- and multi-box-aware).
        """
        cam = self._scene.plotter.camera
        spec = sc.camera
        if isinstance(spec, str):
            return self._frame_boxes()
        pos = np.asarray(spec.get("position", cam.position), dtype=float)
        foc = np.asarray(spec.get("focal_point", cam.focal_point), dtype=float)
        up = np.asarray(spec.get("up", _UP), dtype=float)
        return pos, foc, up

    def _apply_snapshot(self, sc) -> None:
        scene = self._scene
        snap = resolve_snap(sc.snap_num, scene.active_model.snap_count)
        if snap != scene.current_snap:
            scene.set_snapshot(snap)

    def _apply_flat_state(self, sc) -> None:
        st = self.state
        if not sc.state:
            return
        for k, v in sc.state.items():
            setattr(st, k, deepcopy(v))
        st.dirty(*sc.state.keys())

    def _apply_theme(self, sc) -> None:
        theme = sc.theme or (self._story.theme if self._story else None)
        if theme and getattr(self.state, "ui_theme", None) != theme:
            self.state.ui_theme = theme

    def _available_models(self) -> list[str]:
        """Names of all models the app can load (discovered + loaded)."""
        ml = getattr(self.state, "models_list", None) or []
        names = [m.get("name") for m in ml if isinstance(m, dict) and m.get("name")]
        if names:
            return names
        return [m.name for m in self._scene.list_models()]

    def _resolve_model_ref(self, value, avail, initial, exclude):
        """Resolve a (possibly symbolic) model reference to a real name.

        ``"current"``/``"same"`` → the model loaded when the story started;
        ``"other"``/``"auto"``/``"any"`` → the first available model that isn't
        the current primary (or already chosen); anything else is a literal
        name.  Keeps stories portable — no hardcoded model names needed.
        """
        if value is None:
            return None
        v = str(value).strip().lower()
        if v in ("current", "same", "launched"):
            return initial
        if v in ("other", "auto", "any", "next"):
            for nm in avail:
                if nm != self._scene.primary_name and nm not in exclude:
                    return nm
            return None
        return value  # explicit name (as discovered, case-sensitive)

    async def _apply_models(self, sc) -> None:
        """Switch the primary model and adjacent boxes to match the scene.

        Supports adaptive refs (``current``/``other``/``auto``) so a portable
        story works without knowing the output's model names.  Reuses the
        existing async ``switch_model`` / ``toggle_adjacent`` controllers.
        """
        spec = sc.models
        if not spec:
            return
        scene = self._scene
        ctrl = self.ctrl
        avail = self._available_models()
        initial = (self._saved or {}).get("primary", scene.primary_name)

        if "primary" in spec and hasattr(ctrl, "switch_model"):
            primary = self._resolve_model_ref(
                spec.get("primary"), avail, initial, exclude=set()
            )
            if primary and primary != scene.primary_name:
                try:
                    await _maybe_await(ctrl.switch_model(primary))
                except Exception:
                    pass

        # Only touch adjacents when the scene explicitly mentions them.
        if "adjacent" in spec and hasattr(ctrl, "toggle_adjacent"):
            used = {scene.primary_name}
            wanted: list[str] = []
            for a in (spec.get("adjacent") or []):
                r = self._resolve_model_ref(a, avail, initial, exclude=used)
                if r and r not in used:
                    wanted.append(r)
                    used.add(r)
            wanted_set = set(wanted)
            current = set(getattr(scene, "_adjacent_order", []) or [])
            for name in wanted_set - current:
                try:
                    await _maybe_await(ctrl.toggle_adjacent(name))
                except Exception:
                    pass
            for name in current - wanted_set:
                try:
                    await _maybe_await(ctrl.toggle_adjacent(name))
                except Exception:
                    pass

    def _apply_chrome(self, sc) -> None:
        self.state.panels_hidden = bool((sc.chrome or {}).get("hide_panel", False))

    def _apply_overlays(self, sc) -> None:
        # Ship overlays as JSON for the client to render OUTSIDE Vue's control
        # (sage_viewer.js builds the DOM + runs KaTeX). Rendering them via Vue
        # would let KaTeX's DOM mutations corrupt Vue's virtual DOM.
        items = [_normalize_overlay(o) for o in (sc.overlays or [])]
        self.state.story_overlays_json = json.dumps(items)

    def _apply_focus(self, sc) -> None:
        scene = self._scene
        st = self.state
        f = sc.focus or {"kind": "none"}
        kind = f.get("kind", "none")
        if kind == "sphere":
            center = self._resolve_point(f.get("center"))
            if center is None:
                center = self._box()[1]  # default to box centre
            if f.get("radius") is not None:
                radius = float(f["radius"])
            else:  # radius_frac → fraction of the box size (portable)
                radius = float(f.get("radius_frac", 0.4)) * self._box()[0]
            scene.set_focus_sphere(tuple(center), radius)
            st.focus_active = True
        elif kind == "box":
            scene.set_focus_box(*[float(x) for x in f["bounds"]])
            st.focus_active = True
        else:
            scene.clear_focus()
            st.focus_active = False

    def _apply_target(self, sc) -> None:
        if not sc.target:
            return
        idx = self._resolve_target(sc.target)
        if idx is None:
            return
        self.state.nav_gal_idx = int(idx)
        if sc.target.get("highlight_group") and hasattr(
            self.ctrl, "highlight_group_members"
        ):
            self.ctrl.highlight_group_members()

    def _resolve_target(self, target: dict) -> int | None:
        """Resolve a target to a galaxy index in the current snapshot.

        Order: exact GalaxyIndex match → nearest position within radius →
        None (caller falls back to focus geometry only).
        """
        scene = self._scene
        model = scene.active_model
        _, galaxies = model.loader.get(scene.current_snap)
        if galaxies.count == 0:
            return None

        gi = target.get("galaxy_index")
        if gi is not None:
            hits = np.where(galaxies.galaxy_id == int(gi))[0]
            if len(hits):
                return int(hits[0])

        pos = target.get("position")
        if pos is None:
            return None
        off = np.asarray(model.offset, dtype=float)
        world = np.asarray(galaxies.positions, dtype=float) + off
        d = np.linalg.norm(world - np.asarray(pos, dtype=float), axis=1)
        j = int(np.argmin(d))
        radius = float(target.get("radius", np.inf))
        return j if d[j] <= radius else None

    # ---- motion ---------------------------------------------------------

    async def _run_motion(self, sc) -> None:
        m = sc.motion or {"kind": "still"}
        kind = m.get("kind", "still")
        if kind == "orbit":
            await self._motion_orbit(sc, m)
        elif kind == "snapshot_sweep":
            await self._motion_snapshot_sweep(sc, m)
        elif kind == "flythrough":
            await self._motion_flythrough(sc, m)
        else:
            await self._dwell(sc.dwell_secs)

    async def _dwell(self, secs: float) -> None:
        end = asyncio.get_event_loop().time() + max(0.0, float(secs))
        while self._playing and asyncio.get_event_loop().time() < end:
            await asyncio.sleep(0.1)

    async def _motion_orbit(self, sc, m) -> None:
        center = self._motion_center(sc)
        if center is None:
            await self._dwell(sc.dwell_secs)
            return
        cam = self._scene.plotter.camera
        radius = float(
            m.get(
                "radius",
                np.linalg.norm(np.asarray(cam.position, dtype=float) - center),
            )
        )
        await orbit_around(
            cam,
            center,
            radius,
            float(m.get("degrees", 360.0)),
            float(m.get("dps", 10.0)),
            _FPS,
            is_active=lambda: self._playing,
            push=self._push,
        )

    def _motion_center(self, sc) -> np.ndarray | None:
        if sc.target and sc.target.get("position"):
            return self._resolve_point(sc.target["position"])
        f = sc.focus or {}
        if f.get("kind") == "sphere":
            center = self._resolve_point(f.get("center"))
            return center if center is not None else self._box()[1]
        return None

    def _flythrough_targets(self):
        """(groups, clusters) world positions for the current snapshot.

        Groups (10^12.5 ≤ Mvir < 10^14) and clusters (Mvir ≥ 10^14), each
        sorted most-massive first — the same thresholds the toolbar
        fly-through uses.
        """
        scene = self._scene
        halos, _gal = scene.active_model.loader.get(scene.current_snap)
        if getattr(halos, "count", 0) <= 0:
            return [], []
        masses = np.asarray(halos.masses, dtype=float)
        log_m = np.log10(np.maximum(masses, 1.0))
        h_pos = np.asarray(halos.positions, dtype=float) + np.asarray(
            scene.active_model.offset, dtype=float
        )
        g_idx = np.where((log_m >= 12.5) & (log_m < 14.0))[0]
        g_idx = g_idx[np.argsort(masses[g_idx])[::-1]]
        c_idx = np.where(log_m >= 14.0)[0]
        c_idx = c_idx[np.argsort(masses[c_idx])[::-1]]
        return [h_pos[i] for i in g_idx], [h_pos[i] for i in c_idx]

    async def _motion_flythrough(self, sc, m) -> None:
        """Cinematic fly-through that keeps touring groups until Next.

        Reset → approach the box centre → visit the most-massive group →
        visit every cluster (most→least, with focus) → then keep hopping
        between groups (cycling the sorted list) until the presenter clicks
        Next.  Drives the camera with the shared ``camera_motion`` helpers
        (the same ones the toolbar uses) so the loop can keep visiting groups
        instead of settling into a box orbit.  Honours ``self._playing``.
        """
        scene = self._scene
        st = self.state
        cam = scene.plotter.camera
        bs, centre = self._box()
        cx, cy, cz = (float(centre[0]), float(centre[1]), float(centre[2]))
        active = lambda: self._playing  # noqa: E731

        fps = _FPS
        approach_secs = float(m.get("approach_secs", 8.0))
        fly_secs = float(m.get("fly_secs", 7.0))
        g_radius = float(m.get("group_radius", 15.0))
        c_radius = float(m.get("cluster_radius", 30.0))
        g_dps = float(m.get("group_dps", 10.0))
        c_dps = float(m.get("cluster_dps", 8.0))

        async def fly_to(target, radius, secs):
            t3 = np.asarray(target, dtype=float)
            dest = orbit_start_position(cam, t3, radius)
            return await smooth_move(
                cam, np.asarray(cam.position, dtype=float),
                np.asarray(cam.focal_point, dtype=float), dest, t3,
                secs, fps, is_active=active, push=self._push,
            )

        async def spin(target, radius, dps):
            return await orbit_around(
                cam, np.asarray(target, dtype=float), radius, 360.0, dps,
                fps, is_active=active, push=self._push,
            )

        groups, clusters = self._flythrough_targets()
        # The intro (reset → approach → biggest group → clusters) plays only
        # the first time this scene runs; a pause/resume skips straight to the
        # group-touring loop so the tour isn't restarted from the top.
        first_run = self._index not in self._ft_done
        self._ft_done.add(self._index)
        try:
            if first_run:
                # Reset camera, then approach the box centre.
                cam.position = (cx, cy, bs * 2.2)
                cam.focal_point = (cx, cy, cz)
                cam.up = _UP
                self._push()
                await asyncio.sleep(1.0 / fps)
                if not await smooth_move(
                    cam, np.array([cx, cy, bs * 2.2]), np.array([cx, cy, cz]),
                    np.array([cx, cy, cz]), np.array([cx, cy, cz - 0.5]),
                    approach_secs, fps, is_active=active, push=self._push,
                ):
                    return

                # Biggest group.
                if groups:
                    if not await fly_to(groups[0], g_radius, fly_secs):
                        return
                    if not await spin(groups[0], g_radius, g_dps):
                        return

                # Every cluster, most → least massive, with focus on each.
                for cpos in clusters:
                    if not await fly_to(cpos, c_radius, fly_secs):
                        return
                    scene.set_focus_sphere(
                        tuple(float(v) for v in cpos), c_radius
                    )
                    st.focus_active = True
                    st.flush()
                    self._push()
                    await asyncio.sleep(1.0 / fps)
                    ok = active() and await spin(cpos, c_radius, c_dps)
                    scene.clear_focus()
                    st.focus_active = False
                    st.flush()
                    if not ok:
                        return

            # Then keep touring groups (cycling) until Next.
            if not groups:
                while active():  # no groups → gentle box orbit fallback
                    if not await spin(centre, bs * 1.7, 8.0):
                        return
                return
            i = 0
            while active():
                g = groups[i % len(groups)]
                if not await fly_to(g, g_radius, fly_secs):
                    return
                if not await spin(g, g_radius, g_dps):
                    return
                i += 1
        finally:
            # Never leave a focus mask behind when the scene changes/pauses.
            if getattr(st, "focus_active", False):
                scene.clear_focus()
                st.focus_active = False
                st.flush()

    async def _motion_snapshot_sweep(self, sc, m) -> None:
        scene = self._scene
        count = scene.active_model.snap_count
        lo = resolve_snap(m.get("from", sc.snap_num), count)
        hi = resolve_snap(m.get("to", sc.snap_num), count)
        fps = float(m.get("fps", 4.0))
        step = 1 if hi >= lo else -1
        # In multi-box mode advance every loaded box (each clamped to its own
        # snapshot count) — scene.set_snapshot only moves the active box.
        multibox = len(getattr(scene, "_adjacent_order", []) or []) > 0
        for s in range(lo, hi + step, step):
            if not self._playing:
                return
            scene.set_snapshot(int(s))  # active box + state/label
            if multibox:
                active = scene.active_model
                for mdl in scene.list_models():
                    if mdl is active:
                        continue
                    mdl.set_snapshot(min(int(s), mdl.snap_count - 1))
            self._push()
            await asyncio.sleep(1.0 / max(0.5, fps))

    # ---- sandbox preload ------------------------------------------------

    def _required_snaps(self, story: Story) -> list[int]:
        """Snapshots to warm, resolved against the active model's count.

        Handles symbolic refs (first/last/%) so a portable story preloads the
        right frames for whatever model is connected.
        """
        count = self._scene.active_model.snap_count
        snaps: set[int] = set()
        req = story.requirements.get("snapshots")
        if isinstance(req, dict):
            lo = resolve_snap(req.get("from", 0), count)
            hi = resolve_snap(req.get("to", lo), count)
            snaps.update(range(min(lo, hi), max(lo, hi) + 1))
        elif isinstance(req, (list, tuple)):
            snaps.update(resolve_snap(s, count) for s in req)
        for sc in story.scenes:
            snaps.add(resolve_snap(sc.snap_num, count))
            mm = sc.motion or {}
            if mm.get("kind") == "snapshot_sweep":
                lo = resolve_snap(mm.get("from", sc.snap_num), count)
                hi = resolve_snap(mm.get("to", sc.snap_num), count)
                snaps.update(range(min(lo, hi), max(lo, hi) + 1))
        return sorted(snaps)

    async def _preload_sandbox(self, story: Story) -> None:
        scene = self._scene
        st = self.state
        loader = scene.active_model.loader
        snaps = self._required_snaps(story)
        n = len(snaps)
        for i, s in enumerate(snaps, start=1):
            if self._story is None:  # exited while loading
                return
            st.preload_status = f"Loading story... {i}/{n}"
            st.flush()
            try:
                await asyncio.to_thread(loader.get, int(s))
            except Exception:
                pass
        st.preload_status = ""
        st.flush()

    # ---- user-state stash / restore -------------------------------------

    def _save_user_state(self) -> None:
        st = self.state
        cam = self._scene.plotter.camera
        self._saved = {
            "state": {
                k: deepcopy(getattr(st, k, None)) for k in STORY_STATE_KEYS
            },
            "snap_num": int(getattr(st, "snap_num", self._scene.current_snap)),
            "ui_theme": getattr(st, "ui_theme", "dos_blue"),
            "focus_active": bool(getattr(st, "focus_active", False)),
            "panels_hidden": bool(getattr(st, "panels_hidden", False)),
            "primary": self._scene.primary_name,
            "adjacent": list(getattr(self._scene, "_adjacent_order", []) or []),
            "camera": {
                "position": tuple(cam.position),
                "focal_point": tuple(cam.focal_point),
                "up": tuple(cam.up),
            },
        }

    async def _restore_models(self) -> None:
        """Switch the primary model + adjacent boxes back to the saved layout."""
        if not self._saved:
            return
        scene = self._scene
        ctrl = self.ctrl
        saved = self._saved

        primary = saved.get("primary")
        if (
            primary
            and primary != scene.primary_name
            and hasattr(ctrl, "switch_model")
        ):
            try:
                await _maybe_await(ctrl.switch_model(primary))
            except Exception:
                pass

        if hasattr(ctrl, "toggle_adjacent"):
            wanted = set(saved.get("adjacent", []) or [])
            current = set(getattr(scene, "_adjacent_order", []) or [])
            for name in (wanted - current) | (current - wanted):
                try:
                    await _maybe_await(ctrl.toggle_adjacent(name))
                except Exception:
                    pass

    def _restore_user_state(self) -> None:
        if not self._saved:
            return
        scene = self._scene
        st = self.state
        saved = self._saved

        if int(saved["snap_num"]) != scene.current_snap:
            scene.set_snapshot(int(saved["snap_num"]))

        for k, v in saved["state"].items():
            setattr(st, k, deepcopy(v))
        st.dirty(*saved["state"].keys())

        scene.clear_focus()
        st.focus_active = False

        st.ui_theme = saved["ui_theme"]
        st.panels_hidden = saved.get("panels_hidden", False)
        st.story_overlays_json = "[]"

        cam = scene.plotter.camera
        cam.position = saved["camera"]["position"]
        cam.focal_point = saved["camera"]["focal_point"]
        cam.up = saved["camera"]["up"]

        st.flush()
        self._push()
        self._saved = None

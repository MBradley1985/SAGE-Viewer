"""Shared async camera-motion helpers.

Smooth ease-in/out moves and orbits used by both the toolbar fly-through and
Story Mode.  Each helper drives a PyVista camera frame-by-frame and yields to
the event loop between frames via ``asyncio.sleep``.

The caller supplies two callbacks:

``is_active()``
    Return ``True`` while the motion should keep running.  Returning ``False``
    aborts the move; the helper returns ``False`` so the caller can bail out of
    its sequence.

``push()``
    Push the freshly-posed frame to the client (typically a wrapper around
    ``server.controller.view_update``).
"""

from __future__ import annotations

import asyncio
from typing import Callable

import numpy as np

_UP = (0.0, 1.0, 0.0)


async def smooth_move(
    camera,
    p0: np.ndarray,
    f0: np.ndarray,
    p1: np.ndarray,
    f1: np.ndarray,
    secs: float,
    fps: float,
    *,
    is_active: Callable[[], bool],
    push: Callable[[], None],
) -> bool:
    """Ease the camera from (p0, f0) to (p1, f1) over *secs* seconds.

    ``p*`` are camera positions and ``f*`` are focal points, both length-3
    arrays.  Uses smoothstep easing.  Returns ``True`` if the move completed,
    ``False`` if ``is_active`` went false partway through.
    """
    interval = 1.0 / fps
    n = max(1, int(secs * fps))
    p0 = np.asarray(p0, dtype=float)
    f0 = np.asarray(f0, dtype=float)
    p1 = np.asarray(p1, dtype=float)
    f1 = np.asarray(f1, dtype=float)
    for i in range(n):
        if not is_active():
            return False
        t = (i + 1) / n
        ts = t * t * (3.0 - 2.0 * t)
        camera.position = tuple(p0 + ts * (p1 - p0))
        camera.focal_point = tuple(f0 + ts * (f1 - f0))
        camera.up = _UP
        push()
        await asyncio.sleep(interval)
    return True


async def orbit_around(
    camera,
    target,
    radius: float,
    spin_degs: float,
    dps: float,
    fps: float,
    *,
    is_active: Callable[[], bool],
    push: Callable[[], None],
) -> bool:
    """Orbit the camera around *target* in the XZ plane.

    Continues from the camera's current bearing — no jump.  Spins *spin_degs*
    total at *dps* degrees/second.  Returns ``True`` if it completed, ``False``
    if aborted.
    """
    interval = 1.0 / fps
    t3 = np.asarray(target, dtype=float)
    diff = np.asarray(camera.position, dtype=float) - t3
    diff[1] = 0.0
    nrm = np.linalg.norm(diff)
    theta = np.arctan2(diff[0], diff[2]) if nrm > 1e-6 else 0.0
    deg_step = dps * interval
    n = max(1, int(spin_degs / dps * fps))
    for _ in range(n):
        if not is_active():
            return False
        theta += np.deg2rad(deg_step)
        camera.position = (
            t3[0] + radius * np.sin(theta),
            t3[1],
            t3[2] + radius * np.cos(theta),
        )
        camera.focal_point = tuple(t3)
        camera.up = _UP
        push()
        await asyncio.sleep(interval)
    return True


def orbit_start_position(
    camera, target, radius: float
) -> np.ndarray:
    """Return the orbit-start position at *radius* around *target*.

    Keeps the camera on its current bearing so there is no direction flip when
    a move into the orbit begins.
    """
    t3 = np.asarray(target, dtype=float)
    diff = np.asarray(camera.position, dtype=float) - t3
    diff[1] = 0.0
    nrm = np.linalg.norm(diff)
    if nrm > 1e-6:
        diff = diff / nrm * radius
    else:
        diff = np.array([0.0, 0.0, radius])
    return np.array([t3[0] + diff[0], t3[1], t3[2] + diff[2]])

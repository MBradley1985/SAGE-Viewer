from __future__ import annotations

import numpy as np
import pyvista as pv

from sage_viewer.io.halo_reader import HaloSnapshot


class FofLinkLayer:
    """Thin line segments joining each satellite halo to its FOF-group
    central, drawn as fine gold lines. Hidden by default and toggled from
    the Environment tab.

    Work is skipped entirely while hidden — the line set is only (re)built
    when the layer is visible, so it adds nothing to playback cost unless
    the user has turned it on.
    """

    def __init__(
        self,
        plotter: pv.Plotter,
        color: str = "#FFD700",
        line_width: float = 1.0,
        opacity: float = 0.55,
    ) -> None:
        self._pl = plotter
        self._color = color
        self._line_width = line_width
        self._opacity = opacity
        self._visible = False
        self._actor = None
        self._snapshot: HaloSnapshot | None = None

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self._visible = bool(value)
        if self._visible:
            self._rebuild()
        else:
            self._clear()
        self._pl.render()

    def update(self, snapshot: HaloSnapshot) -> None:
        self._snapshot = snapshot
        if self._visible:
            self._rebuild()

    # ------------------------------------------------------------------

    def _clear(self) -> None:
        if self._actor is not None:
            self._pl.remove_actor(self._actor, render=False)
            self._actor = None

    def _rebuild(self) -> None:
        self._clear()
        snap = self._snapshot
        seg = None if snap is None else snap.fof_segments
        if seg is None or len(seg) == 0:
            return

        n = len(seg)
        # seg is (n, 2, 3): [satellite, central] per row. Flattened, point
        # 2*i is the satellite and 2*i+1 its central.
        points = seg.reshape(2 * n, 3).astype(np.float32)
        conn = np.empty((n, 3), dtype=np.int64)
        conn[:, 0] = 2
        conn[:, 1] = np.arange(0, 2 * n, 2)
        conn[:, 2] = np.arange(1, 2 * n, 2)

        mesh = pv.PolyData(points, lines=conn.ravel())
        self._actor = self._pl.add_mesh(
            mesh,
            color=self._color,
            line_width=self._line_width,
            opacity=self._opacity,
            render=False,
            reset_camera=False,
        )

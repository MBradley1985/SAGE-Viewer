from __future__ import annotations

import numpy as np
import pyvista as pv

from sage_viewer.io.halo_reader import HaloSnapshot


class FofLinkLayer:
    """Thin line segments joining each satellite halo to its FOF-group
    central, drawn as fine gold lines.  Hidden by default and toggled
    from the Environment tab.

    Respects the active halo filter and focus region: only segments
    whose central halo is in the current *visible* halo set are drawn.
    Call ``sync_masks(visible_positions)`` whenever the halo mask changes
    (filter, focus, or snapshot update).
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
        self._offset: np.ndarray = np.zeros(3, dtype=np.float32)
        # Positions of halos currently visible after focus + filter masking.
        # None means "all halos visible" — no position filtering is applied.
        self._visible_halo_positions: np.ndarray | None = None

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
        """Called on every snapshot change with fresh halo data.

        Stores the new snapshot and rebuilds if visible.  The visible-halo
        positions will be updated by sync_masks() immediately after (via
        the snap-change callbacks in navigation_panel), so any brief
        intermediate state from the previous mask is never rendered.
        """
        self._snapshot = snapshot
        if self._visible:
            self._rebuild()

    def set_offset(self, offset: np.ndarray) -> None:
        self._offset = np.asarray(offset, dtype=np.float32)
        if self._visible and self._snapshot is not None:
            self._rebuild()

    def sync_masks(self, visible_positions: np.ndarray | None) -> None:
        """Update the visible-halo-position filter and rebuild once.

        ``visible_positions`` — float32 (N, 3) array of halo positions that
        currently pass all active filters and focus masking combined, or None
        if every halo is visible (no masking needed — skip position lookup).
        """
        self._visible_halo_positions = visible_positions
        if self._visible and self._snapshot is not None:
            self._rebuild()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _clear(self) -> None:
        if self._actor is not None:
            self._pl.remove_actor(self._actor, render=False)
            self._actor = None

    def _filter_segments(self, seg: np.ndarray) -> np.ndarray:
        """Return the subset of *seg* whose central endpoint is in the
        visible halo set.  When _visible_halo_positions is None all
        segments pass."""
        vis = self._visible_halo_positions
        if vis is None:
            return seg
        if len(vis) == 0 or len(seg) == 0:
            return np.empty((0, 2, 3), dtype=np.float32)
        # Build a byte-key set for O(1) lookup.  FoF centrals come from the
        # same float32 struct array as halos.positions, so exact byte
        # comparison is reliable without rounding.
        vis_set = {p.tobytes() for p in vis.astype(np.float32)}
        central = seg[:, 1, :].astype(np.float32)
        keep = np.fromiter(
            (c.tobytes() in vis_set for c in central),
            dtype=bool,
            count=len(central),
        )
        return seg[keep]

    def _rebuild(self) -> None:
        self._clear()
        snap = self._snapshot
        seg = None if snap is None else snap.fof_segments
        if seg is None or len(seg) == 0:
            return

        seg = self._filter_segments(seg)
        if len(seg) == 0:
            return

        n = len(seg)
        points = (seg.reshape(2 * n, 3) + self._offset).astype(np.float32)
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

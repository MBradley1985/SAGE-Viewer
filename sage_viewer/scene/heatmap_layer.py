from __future__ import annotations

import numpy as np
import pyvista as pv

from sage_viewer.io.halo_reader import HaloSnapshot

_N_BINS = 256


class HaloHeatmapLayer:
    """2D projected density heatmap of the halo distribution.

    Bins halo positions onto a regular grid projected along one axis and
    renders the result as a flat slab in the scene.  Two modes:
      - number: log10(count + 1) per cell
      - mass:   log10(sum-of-Mvir + 1) per cell
    """

    def __init__(self, plotter: pv.Plotter, box_size: float) -> None:
        self._pl       = plotter
        self._box_size = box_size
        self._visible  = False
        self._mode     = "number"   # "number" | "mass"
        self._axis     = "z"        # project along this axis
        self._opacity  = 0.85
        self._colormap = "inferno"
        self._actor    = None
        self._snapshot: HaloSnapshot | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, v: bool) -> None:
        self._visible = bool(v)
        if self._actor is not None:
            self._actor.SetVisibility(self._visible)
            self._pl.render()
        elif self._visible and self._snapshot is not None:
            self._redraw()

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, v: str) -> None:
        self._mode = v
        if self._visible and self._snapshot is not None:
            self._redraw()

    @property
    def projection_axis(self) -> str:
        return self._axis

    @projection_axis.setter
    def projection_axis(self, v: str) -> None:
        self._axis = v
        if self._visible and self._snapshot is not None:
            self._redraw()

    @property
    def opacity(self) -> float:
        return self._opacity

    @opacity.setter
    def opacity(self, v: float) -> None:
        self._opacity = float(v)
        if self._visible and self._snapshot is not None:
            self._redraw()

    @property
    def colormap(self) -> str:
        return self._colormap

    @colormap.setter
    def colormap(self, v: str) -> None:
        self._colormap = v
        if self._visible and self._snapshot is not None:
            self._redraw()

    # ------------------------------------------------------------------
    # Data update
    # ------------------------------------------------------------------

    def update(self, snapshot: HaloSnapshot) -> None:
        self._snapshot = snapshot
        if self._visible:
            self._redraw()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _clear(self) -> None:
        if self._actor is not None:
            self._pl.remove_actor(self._actor)
            self._actor = None

    def _compute_histogram(self) -> np.ndarray:
        snap = self._snapshot
        pos  = snap.positions
        b    = self._box_size
        n    = _N_BINS
        rng  = [[0.0, b], [0.0, b]]

        if self._axis == "z":
            a1, a2 = pos[:, 0], pos[:, 1]
        elif self._axis == "y":
            a1, a2 = pos[:, 0], pos[:, 2]
        else:
            a1, a2 = pos[:, 1], pos[:, 2]

        weights = snap.masses if self._mode == "mass" else None
        H, _, _ = np.histogram2d(a1, a2, bins=n, range=rng, weights=weights)

        H = np.log10(H + 1.0)
        h_max = H.max()
        if h_max > 0.0:
            H /= h_max
        return H.astype(np.float32)

    def _redraw(self) -> None:
        self._clear()
        if self._snapshot is None or self._snapshot.count == 0:
            return

        H = self._compute_histogram()
        b = self._box_size
        n = _N_BINS

        # Build a thin ImageData slab: n×n cells projected onto the chosen plane.
        # VTK cell ordering: i_x varies fastest, then i_y, then i_z.
        # H[i_a1, i_a2] → H.flatten('F') matches VTK ordering for all three axes.
        grid = pv.ImageData()
        if self._axis == "z":
            grid.dimensions = (n + 1, n + 1, 2)
            grid.spacing    = (b / n, b / n, b * 0.001)
            grid.origin     = (0.0,   0.0,   -b * 0.015)
        elif self._axis == "y":
            grid.dimensions = (n + 1, 2, n + 1)
            grid.spacing    = (b / n, b * 0.001, b / n)
            grid.origin     = (0.0,   -b * 0.015, 0.0)
        else:
            grid.dimensions = (2, n + 1, n + 1)
            grid.spacing    = (b * 0.001, b / n, b / n)
            grid.origin     = (-b * 0.015, 0.0, 0.0)

        grid.cell_data["density"] = H.flatten("F")

        self._actor = self._pl.add_mesh(
            grid,
            scalars="density",
            cmap=self._colormap,
            clim=[0.0, 1.0],
            opacity=self._opacity,
            show_scalar_bar=False,
        )

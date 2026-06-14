from __future__ import annotations

from typing import Literal

import numpy as np
import pyvista as pv

from sage_viewer.io.halo_reader import HaloSnapshot
from sage_viewer.utils.colormap import (
    compute_density_colors,
    normalize_log_halo_mass,
)
from sage_viewer.utils.sizing import HALO_SIZE_BINS, halo_point_sizes, size_bin_mask

ColorMode = Literal["mass", "ssfr", "density", "type"]

_CMAPS: dict[ColorMode, str] = {
    "mass": "Blues",
    "ssfr": "coolwarm_r",
    "density": "magma",
    "type": "Blues",
}


class HaloLayer:
    """Manages the halo point-cloud actor inside a PyVista Plotter.

    Separates rendering concerns from data loading. Call `update()` with a
    new HaloSnapshot whenever the snapshot changes; the plotter actors are
    replaced in-place.
    """

    def __init__(
        self,
        plotter: pv.Plotter,
        color_mode: ColorMode = "mass",
        opacity: float = 0.025,
        visible: bool = True,
    ) -> None:
        self._pl = plotter
        self._color_mode: ColorMode = color_mode
        self._opacity = opacity
        self._visible = visible
        self._actors: list = []
        self._snapshot: HaloSnapshot | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self._visible = value
        for actor in self._actors:
            actor.SetVisibility(value)
        self._pl.render()

    @property
    def opacity(self) -> float:
        return self._opacity

    @opacity.setter
    def opacity(self, value: float) -> None:
        self._opacity = float(value)
        if self._snapshot is not None:
            self._redraw()

    @property
    def color_mode(self) -> ColorMode:
        return self._color_mode

    @color_mode.setter
    def color_mode(self, value: ColorMode) -> None:
        self._color_mode = value
        if self._snapshot is not None:
            self._redraw()

    def update(self, snapshot: HaloSnapshot) -> None:
        self._snapshot = snapshot
        self._redraw()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _clear_actors(self) -> None:
        for actor in self._actors:
            self._pl.remove_actor(actor)
        self._actors.clear()

    def _redraw(self) -> None:
        self._clear_actors()
        snap = self._snapshot
        if snap is None or snap.count == 0:
            return

        colors = self._compute_colors(snap)
        sizes = halo_point_sizes(snap.masses)
        masks = size_bin_mask(sizes, HALO_SIZE_BINS)
        cmap = _CMAPS.get(self._color_mode, "Blues")

        for i, mask in enumerate(masks):
            if not np.any(mask):
                continue
            cloud = pv.PolyData(snap.positions[mask])
            cloud["scalar"] = colors[mask]
            actor = self._pl.add_mesh(
                cloud,
                scalars="scalar",
                cmap=cmap,
                clim=[0.0, 1.0],
                point_size=HALO_SIZE_BINS[i],
                render_points_as_spheres=True,
                opacity=self._opacity,
                show_scalar_bar=False,
            )
            if not self._visible:
                actor.SetVisibility(False)
            self._actors.append(actor)

    def _compute_colors(self, snap: HaloSnapshot) -> np.ndarray:
        if self._color_mode == "density":
            return compute_density_colors(snap.positions)
        # mass, ssfr, and type all use halo mass for colouring
        return normalize_log_halo_mass(snap.masses)

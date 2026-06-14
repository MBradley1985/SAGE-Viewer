from __future__ import annotations

from typing import Literal

import numpy as np
import pyvista as pv

from sage_viewer.io.galaxy_reader import GalaxySnapshot
from sage_viewer.utils.colormap import (
    compute_density_colors,
    normalize_log_mass,
    normalize_log_ssfr,
)
from sage_viewer.utils.sizing import (
    GALAXY_SIZE_SCALE,
    HALO_SIZE_BINS,
    galaxy_point_sizes,
    size_bin_mask,
)

ColorMode = Literal["mass", "ssfr", "density", "type"]

_GALAXY_SIZE_BINS = [s * GALAXY_SIZE_SCALE for s in HALO_SIZE_BINS]

_CMAPS: dict[ColorMode, str] = {
    "mass": "plasma",
    "ssfr": "coolwarm_r",
    "density": "magma",
    "type": "plasma",  # per-type override applied below
}

_CENTRAL_CMAP = "Blues"
_SATELLITE_CMAP = "Reds"


class GalaxyLayer:
    """Manages the galaxy point-cloud actor(s) inside a PyVista Plotter."""

    def __init__(
        self,
        plotter: pv.Plotter,
        color_mode: ColorMode = "mass",
        opacity: float = 0.17,
        visible: bool = True,
    ) -> None:
        self._pl = plotter
        self._color_mode: ColorMode = color_mode
        self._opacity = opacity
        self._visible = visible
        self._actors: list = []
        self._snapshot: GalaxySnapshot | None = None

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

    def update(self, snapshot: GalaxySnapshot) -> None:
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

        sizes = galaxy_point_sizes(snap.stellar_mass)

        if self._color_mode == "type":
            self._render_by_type(snap, sizes)
        else:
            colors = self._compute_colors(snap)
            cmap = _CMAPS[self._color_mode]
            self._render_subset(snap.positions, colors, sizes, cmap)

    def _render_by_type(
        self, snap: GalaxySnapshot, sizes: np.ndarray
    ) -> None:
        mass_colors = normalize_log_mass(snap.stellar_mass)
        for mask, cmap in [
            (snap.gal_type == 0, _CENTRAL_CMAP),
            (snap.gal_type > 0, _SATELLITE_CMAP),
        ]:
            if not np.any(mask):
                continue
            self._render_subset(
                snap.positions[mask], mass_colors[mask], sizes[mask], cmap
            )

    def _render_subset(
        self,
        positions: np.ndarray,
        colors: np.ndarray,
        sizes: np.ndarray,
        cmap: str,
    ) -> None:
        masks = size_bin_mask(sizes, _GALAXY_SIZE_BINS)
        for i, mask in enumerate(masks):
            if not np.any(mask):
                continue
            cloud = pv.PolyData(positions[mask])
            cloud["scalar"] = colors[mask]
            actor = self._pl.add_mesh(
                cloud,
                scalars="scalar",
                cmap=cmap,
                clim=[0.0, 1.0],
                point_size=_GALAXY_SIZE_BINS[i],
                render_points_as_spheres=True,
                opacity=self._opacity,
                show_scalar_bar=False,
            )
            if not self._visible:
                actor.SetVisibility(False)
            self._actors.append(actor)

    def _compute_colors(self, snap: GalaxySnapshot) -> np.ndarray:
        if self._color_mode == "ssfr":
            return normalize_log_ssfr(snap.ssfr)
        if self._color_mode == "density":
            return compute_density_colors(snap.positions)
        return normalize_log_mass(snap.stellar_mass)

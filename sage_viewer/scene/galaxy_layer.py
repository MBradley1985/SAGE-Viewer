from __future__ import annotations

from typing import Literal

import numpy as np
import pyvista as pv

from sage_viewer.io.galaxy_reader import GalaxySnapshot
from sage_viewer.utils.colormap import compute_density_colors, normalize_log
from sage_viewer.utils.sizing import (
    GALAXY_SIZE_SCALE,
    HALO_SIZE_BINS,
    galaxy_point_sizes,
    size_bin_mask,
)

ColorMode = Literal[
    "stellar_mass", "ssfr", "sfr", "cold_gas", "bulge_mass", "density", "type"
]

_RANGES = {
    "stellar_mass": (8.0,  12.5),   # log10(Msun)
    "bulge_mass":   (7.0,  12.0),   # log10(Msun)
    "cold_gas":     (7.0,  11.5),   # log10(Msun)
    "sfr":          (-3.0,  2.0),   # log10(Msun/yr)
    "ssfr":         (-14.0, -8.0),  # log10(yr^-1)
}

_GALAXY_SIZE_BINS    = [s * GALAXY_SIZE_SCALE for s in HALO_SIZE_BINS]
_GALAXY_GAUSSIAN_BINS = [0.5, 0.625, 0.75, 0.875, 1.0]   # render sizes for gaussian mode
_CENTRAL_CMAP    = "Blues"
_SATELLITE_CMAP  = "Reds"


class GalaxyLayer:
    """Manages the galaxy point-cloud actor(s) inside a PyVista Plotter."""

    def __init__(
        self,
        plotter: pv.Plotter,
        color_mode: ColorMode = "density",
        colormap: str = "plasma",
        opacity: float = 0.40,
        visible: bool = True,
    ) -> None:
        self._pl = plotter
        self._color_mode: ColorMode = color_mode
        self._colormap = colormap
        self._opacity = opacity
        self._visible = visible
        self._actors: list = []
        self._snapshot: GalaxySnapshot | None = None
        self._mask: np.ndarray | None = None

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

    @property
    def colormap(self) -> str:
        return self._colormap

    @colormap.setter
    def colormap(self, value: str) -> None:
        self._colormap = value
        if self._snapshot is not None:
            self._redraw()

    def update(self, snapshot: GalaxySnapshot) -> None:
        self._snapshot = snapshot
        self._redraw()

    def set_mask(self, mask: "np.ndarray | None") -> None:
        """Boolean mask selecting which points to render. None = show all."""
        self._mask = mask
        if self._snapshot is not None:
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

        # Apply spatial focus mask if set
        if self._mask is not None and len(self._mask) == snap.count:
            from sage_viewer.io.galaxy_reader import GalaxySnapshot as _GS
            snap = _GS(
                positions=snap.positions[self._mask],
                stellar_mass=snap.stellar_mass[self._mask],
                mvir=snap.mvir[self._mask],
                sfr=snap.sfr[self._mask],
                ssfr=snap.ssfr[self._mask],
                cold_gas=snap.cold_gas[self._mask],
                bulge_mass=snap.bulge_mass[self._mask],
                gal_type=snap.gal_type[self._mask],
                snap_num=snap.snap_num,
            )
            if snap.count == 0:
                return

        sizes = galaxy_point_sizes(snap.stellar_mass)

        if self._color_mode == "type":
            self._render_by_type(snap, sizes)
        else:
            colors = self._compute_colors(snap)
            self._render_gaussian(snap.positions, colors, sizes, self._colormap)

    def _render_by_type(self, snap: GalaxySnapshot, sizes: np.ndarray) -> None:
        mass_colors = normalize_log(snap.stellar_mass, *_RANGES["stellar_mass"])
        for mask, cmap in [
            (snap.gal_type == 0, _CENTRAL_CMAP),
            (snap.gal_type > 0,  _SATELLITE_CMAP),
        ]:
            if not np.any(mask):
                continue
            self._render_gaussian(
                snap.positions[mask], mass_colors[mask], sizes[mask], cmap
            )

    def _render_gaussian(
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
                style="points_gaussian",
                point_size=_GALAXY_GAUSSIAN_BINS[i],
                emissive=False,
                opacity=self._opacity,
                show_scalar_bar=False,
            )
            if not self._visible:
                actor.SetVisibility(False)
            self._actors.append(actor)

    def _compute_colors(self, snap: GalaxySnapshot) -> np.ndarray:
        if self._color_mode == "density":
            return compute_density_colors(snap.positions)
        if self._color_mode == "ssfr":
            return normalize_log(snap.ssfr, *_RANGES["ssfr"])
        if self._color_mode == "sfr":
            return normalize_log(np.maximum(snap.sfr, 1e-6), *_RANGES["sfr"])
        if self._color_mode == "cold_gas":
            return normalize_log(np.maximum(snap.cold_gas, 1.0), *_RANGES["cold_gas"])
        if self._color_mode == "bulge_mass":
            return normalize_log(np.maximum(snap.bulge_mass, 1.0), *_RANGES["bulge_mass"])
        return normalize_log(snap.stellar_mass, *_RANGES["stellar_mass"])

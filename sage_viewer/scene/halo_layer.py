from __future__ import annotations

from typing import Literal

import numpy as np
import pyvista as pv

from sage_viewer.io.halo_reader import HaloSnapshot
from sage_viewer.utils.colormap import compute_density_colors, normalize_log
from sage_viewer.utils.sizing import halo_world_radii

ColorMode = Literal["mvir", "rvir", "vvir"]

_RANGES = {
    "mvir": (10.0, 15.0),   # log10(Msun)
    "rvir": (-1.5, 0.5),    # log10(Mpc/h)
    "vvir": (1.5, 3.0),     # log10(km/s)
}

class HaloLayer:
    """Manages the halo point-cloud actor(s) inside a PyVista Plotter."""

    def __init__(
        self,
        plotter: pv.Plotter,
        color_mode: ColorMode = "mvir",
        colormap: str = "viridis",
        opacity: float = 0.10,
        visible: bool = True,
    ) -> None:
        self._pl = plotter
        self._color_mode: ColorMode = color_mode
        self._colormap = colormap
        self._opacity = opacity
        self._visible = visible
        self._actors: list = []
        self._snapshot: HaloSnapshot | None = None
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

    def update(self, snapshot: HaloSnapshot) -> None:
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
            import dataclasses
            from sage_viewer.io.halo_reader import HaloSnapshot as _HS
            snap = _HS(
                positions=snap.positions[self._mask],
                masses=snap.masses[self._mask],
                vmax=snap.vmax[self._mask],
                rvir=snap.rvir[self._mask],
                vvir=snap.vvir[self._mask],
                snap_num=snap.snap_num,
            )
            if snap.count == 0:
                return

        colors = self._compute_colors(snap)
        radii  = halo_world_radii(snap.masses)

        self._render_gaussian(snap.positions, colors, radii)

    def _render_gaussian(
        self,
        positions: np.ndarray,
        colors: np.ndarray,
        radii: np.ndarray,
    ) -> None:
        if len(positions) == 0:
            return
        cloud = pv.PolyData(positions)
        cloud["scalar"] = colors
        cloud["radius"] = radii
        actor = self._pl.add_mesh(
            cloud,
            scalars="scalar",
            cmap=self._colormap,
            clim=[0.0, 1.0],
            style="points_gaussian",
            emissive=False,
            opacity=self._opacity,
            show_scalar_bar=False,
        )
        # Size each splat in world coordinates (Mpc/h) rather than screen pixels.
        mapper = actor.mapper
        mapper.SetScaleArray("radius")
        mapper.SetScaleFactor(1.0)
        if not self._visible:
            actor.SetVisibility(False)
        self._actors.append(actor)

    def _compute_colors(self, snap: HaloSnapshot) -> np.ndarray:
        vmin, vmax = _RANGES[self._color_mode]
        if self._color_mode == "mvir":
            return normalize_log(snap.masses, vmin, vmax)
        if self._color_mode == "rvir":
            return normalize_log(snap.rvir, vmin, vmax)
        if self._color_mode == "vvir":
            return normalize_log(snap.vvir, vmin, vmax)
        return normalize_log(snap.masses, *_RANGES["mvir"])

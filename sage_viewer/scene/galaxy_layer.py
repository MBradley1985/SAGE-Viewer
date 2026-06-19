from __future__ import annotations

from typing import Literal

import numpy as np
import pyvista as pv

from sage_viewer.io.galaxy_reader import GalaxySnapshot
from sage_viewer.utils.colormap import compute_density_colors, normalize_log
from sage_viewer.utils.sizing import galaxy_world_radii

ColorMode = Literal[
    "stellar_mass", "ssfr", "sfr", "cold_gas", "bulge_mass", "bt",
    "bh_mass", "ics_mass", "age", "density", "type", "structure",
]

_RANGES = {
    "stellar_mass": (8.0,  12.5),   # log10(Msun)
    "bulge_mass":   (7.0,  12.0),   # log10(Msun)
    "cold_gas":     (7.0,  11.5),   # log10(Msun)
    "sfr":          (-3.0,  2.0),   # log10(Msun/yr)
    "ssfr":         (-14.0, -8.0),  # log10(yr^-1)
    "bh_mass":      (4.0,  10.0),   # log10(Msun)
    "ics_mass":     (6.0,  12.0),   # log10(Msun)
    "bt":           (0.0,   1.0),   # linear ratio
    "age":          (0.0,  14.0),   # Gyr (linear)
}

_CENTRAL_CMAP    = "Blues"
_SATELLITE_CMAP  = "Reds"


class GalaxyLayer:
    """Manages the galaxy point-cloud actor(s) inside a PyVista Plotter."""

    def __init__(
        self,
        plotter: pv.Plotter,
        color_mode: ColorMode = "structure",
        colormap: str = "plasma",
        opacity: float = 1.0,
        visible: bool = True,
    ) -> None:
        self._pl = plotter
        self._color_mode: ColorMode = color_mode
        self._colormap = colormap
        self._opacity = opacity
        self._visible = visible
        self._actors: list = []
        self._cloud:  pv.PolyData | None = None   # persistent geometry
        self._render_params: tuple = ()           # tracks need-to-rebuild
        self._snapshot: GalaxySnapshot | None = None
        self._focus_mask: np.ndarray | None = None
        self._filter_mask: np.ndarray | None = None

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
        """Backwards-compatible: sets the focus mask."""
        self.set_focus_mask(mask)

    def set_focus_mask(self, mask: "np.ndarray | None") -> None:
        """Spatial focus mask (from sphere/box zoom). None = no focus."""
        self._focus_mask = mask
        if self._snapshot is not None:
            self._redraw()

    def set_filter_mask(self, mask: "np.ndarray | None") -> None:
        """Property filter mask (from Filters tab). None = no filtering."""
        self._filter_mask = mask
        if self._snapshot is not None:
            self._redraw()

    def _combined_mask(self) -> "np.ndarray | None":
        if self._focus_mask is None:
            return self._filter_mask
        if self._filter_mask is None:
            return self._focus_mask
        return self._focus_mask & self._filter_mask

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _clear_actors(self) -> None:
        for actor in self._actors:
            self._pl.remove_actor(actor, render=False)
        self._actors.clear()

    def _redraw(self) -> None:
        snap = self._snapshot
        if snap is None or snap.count == 0:
            self._clear_actors()
            self._cloud = None
            return

        # Combined focus + filter mask
        mask = self._combined_mask()
        if mask is not None and len(mask) == snap.count:
            from sage_viewer.io.galaxy_reader import GalaxySnapshot as _GS
            snap = _GS(
                positions=snap.positions[mask],
                stellar_mass=snap.stellar_mass[mask],
                mvir=snap.mvir[mask],
                sfr=snap.sfr[mask],
                ssfr=snap.ssfr[mask],
                cold_gas=snap.cold_gas[mask],
                bulge_mass=snap.bulge_mass[mask],
                gal_type=snap.gal_type[mask],
                bh_mass=snap.bh_mass[mask],
                ics_mass=snap.ics_mass[mask],
                ffb_regime=snap.ffb_regime[mask],
                cgm_regime=snap.cgm_regime[mask],
                central_mvir=snap.central_mvir[mask],
                h2_mass=snap.h2_mass[mask],
                cgm_gas=snap.cgm_gas[mask],
                hot_gas=snap.hot_gas[mask],
                galaxy_id=snap.galaxy_id[mask],
                central_id=snap.central_id[mask],
                time_of_infall=snap.time_of_infall[mask],
                mean_age=snap.mean_age[mask],
                len_particles=snap.len_particles[mask],
                vmax=snap.vmax[mask],
                concentration=snap.concentration[mask],
                spin=snap.spin[mask],
                disk_radius=snap.disk_radius[mask],
                bulge_radius=snap.bulge_radius[mask],
                merger_bulge_mass=snap.merger_bulge_mass[mask],
                merger_bulge_radius=snap.merger_bulge_radius[mask],
                instability_bulge_mass=snap.instability_bulge_mass[mask],
                instability_bulge_radius=snap.instability_bulge_radius[mask],
                h1_gas=snap.h1_gas[mask],
                ejected_mass=snap.ejected_mass[mask],
                outflow_rate=snap.outflow_rate[mask],
                mass_loading=snap.mass_loading[mask],
                cooling=snap.cooling[mask],
                heating=snap.heating[mask],
                sfr_bulge=snap.sfr_bulge[mask],
                sfr_disk=snap.sfr_disk[mask],
                sfr_bulge_z=snap.sfr_bulge_z[mask],
                sfr_disk_z=snap.sfr_disk_z[mask],
                metals_cold_gas=snap.metals_cold_gas[mask],
                metals_stellar_mass=snap.metals_stellar_mass[mask],
                metals_bulge_mass=snap.metals_bulge_mass[mask],
                metals_hot_gas=snap.metals_hot_gas[mask],
                metals_ejected_mass=snap.metals_ejected_mass[mask],
                metals_ics=snap.metals_ics[mask],
                metals_cgm_gas=snap.metals_cgm_gas[mask],
                sage_indices=snap.sage_indices[mask],
                snap_num=snap.snap_num,
            )
            if snap.count == 0:
                self._clear_actors()
                self._cloud = None
                return

        radii = galaxy_world_radii(snap.stellar_mass)

        # Every mode shares the same Structure composition (BH core, cold-gas
        # envelope, stellar particles, CGM/Hot outer envelope).  When the
        # mode isn't 'structure', we add ONE more outermost layer whose
        # colour comes from the active Colour-by + the galaxy colormap.
        self._clear_actors()
        self._cloud = None
        self._render_params = ()
        self._render_structure(snap, radii)

        if self._color_mode == "structure":
            return

        if self._color_mode == "type":
            mass_colors = normalize_log(snap.stellar_mass, *_RANGES["stellar_mass"])
            for tmask, cmap in [
                (snap.gal_type == 0, _CENTRAL_CMAP),
                (snap.gal_type > 0,  _SATELLITE_CMAP),
            ]:
                if not np.any(tmask):
                    continue
                self._render_outer_property(
                    snap.positions[tmask], mass_colors[tmask], radii[tmask], cmap,
                )
            return

        colors = self._compute_colors(snap)
        self._render_outer_property(snap.positions, colors, radii, self._colormap)

    def _update_in_place(
        self,
        positions: np.ndarray,
        colors: np.ndarray,
        radii: np.ndarray,
    ) -> None:
        cloud = self._cloud
        if cloud is None:
            return
        cloud.points    = positions
        cloud["scalar"] = colors
        cloud["radius"] = radii
        cloud.Modified()

    def _render_by_type(self, snap: GalaxySnapshot, radii: np.ndarray) -> None:
        mass_colors = normalize_log(snap.stellar_mass, *_RANGES["stellar_mass"])
        for mask, cmap in [
            (snap.gal_type == 0, _CENTRAL_CMAP),
            (snap.gal_type > 0,  _SATELLITE_CMAP),
        ]:
            if not np.any(mask):
                continue
            self._render_gaussian(
                snap.positions[mask], mass_colors[mask], radii[mask], cmap
            )

    def _render_structure(
        self,
        snap: GalaxySnapshot,
        radii: np.ndarray,
    ) -> None:
        """Multi-layer physically-suggestive galaxy rendering.

        For every galaxy:
          • a black "BH" core sized by BlackHoleMass
          • a blue cold-gas envelope sized by ColdGas
          • scattered "stellar" particles (coolwarm) inside the envelope,
            count scaled by stellar mass
          • a green CGM (Regime == 0) or red HotGas (Regime == 1) outer
            envelope, sized by CGMgas / HotGas respectively
          • coolwarm scatter through the outer envelope, fewer than the
            inner one

        All layers share the per-galaxy world-space `radii` envelope so the
        overall splat size stays consistent with the standard rendering.
        """
        if snap.count == 0:
            return

        pos = snap.positions
        # ---- Per-galaxy radii (Mpc/h) keyed off the default scaling -----
        r_outer = np.maximum(radii, 1e-4)         # default 0.025–0.25 Mpc/h
        r_cold  = 0.45 * r_outer

        # Convenience clamped log10
        def _logn(x, vmin, vmax):
            log = np.log10(np.maximum(x, 1.0))
            return np.clip((log - vmin) / (vmax - vmin + 1e-10), 0.0, 1.0)

        cold_scalar = _logn(snap.cold_gas,  7.0, 11.5)
        # CGM vs Hot: split galaxies by regime
        cgm_mask = (snap.cgm_regime == 0) if snap.cgm_regime.size else np.zeros(snap.count, bool)
        hot_mask = ~cgm_mask
        # Outer envelope: CGM galaxies sized/coloured by CGMgas;
        # Hot-atmosphere galaxies by HotGas. (cold_gas is reserved for
        # the inner cold-gas envelope; H2 currently unused at this layer.)
        outer_mass = np.where(cgm_mask, snap.cgm_gas, snap.hot_gas)
        outer_scalar = _logn(outer_mass, 7.0, 11.5)

        # ---- (1) Outer envelope ---------------------------------------
        # CGM galaxies → green, Hot atmosphere → red.
        # Sized by outer mass, very low opacity.
        for mask, cmap in [(cgm_mask, "Greens"), (hot_mask, "Reds")]:
            if not np.any(mask):
                continue
            cloud = pv.PolyData(pos[mask])
            cloud["scalar"] = outer_scalar[mask]
            cloud["radius"] = (r_outer[mask] * (0.5 + 0.5 * outer_scalar[mask])).astype(np.float32)
            actor = self._pl.add_mesh(
                cloud, scalars="scalar", cmap=cmap, clim=[0.0, 1.0],
                style="points_gaussian", emissive=False,
                opacity=max(0.15, self._opacity * 0.3),
                show_scalar_bar=False, render=False, reset_camera=False,
            )
            mp = actor.mapper
            mp.SetScaleArray("radius"); mp.SetScaleFactor(1.0)
            if not self._visible:
                actor.SetVisibility(False)
            self._actors.append(actor)

        # ---- (2) Cold-gas blue envelope -------------------------------
        cloud = pv.PolyData(pos)
        cloud["scalar"] = cold_scalar.astype(np.float32)
        cloud["radius"] = (r_cold * (0.5 + 0.5 * cold_scalar)).astype(np.float32)
        actor = self._pl.add_mesh(
            cloud, scalars="scalar", cmap="Blues", clim=[0.0, 1.0],
            style="points_gaussian", emissive=False,
            opacity=max(0.2, self._opacity * 0.5),
            show_scalar_bar=False, render=False, reset_camera=False,
        )
        mp = actor.mapper
        mp.SetScaleArray("radius"); mp.SetScaleFactor(1.0)
        if not self._visible:
            actor.SetVisibility(False)
        self._actors.append(actor)

        # (Per-galaxy star scatter and BH accretion-disk cores both
        # removed — invisible / negligible at typical zoom levels and
        # together they were the bulk of the per-frame splat cost.)

    def _render_outer_property(
        self,
        positions: np.ndarray,
        colors: np.ndarray,
        radii: np.ndarray,
        cmap: str,
    ) -> None:
        """Outermost halo around the Structure composition, coloured by the
        active galaxy Colour-by mode + chosen colormap.  Slightly larger and
        more transparent than the CGM/Hot envelope so the inner Structure
        layers stay visible."""
        if len(positions) == 0:
            return
        cloud = pv.PolyData(positions)
        cloud["scalar"] = colors.astype(np.float32)
        # Sit ~30% beyond the standard envelope.  This is the "Colour-by" halo.
        cloud["radius"] = (radii * 1.3).astype(np.float32)
        actor = self._pl.add_mesh(
            cloud,
            scalars="scalar",
            cmap=cmap,
            clim=[0.0, 1.0],
            style="points_gaussian",
            emissive=False,
            # Subtle so the inner Structure detail isn't drowned
            opacity=max(0.12, self._opacity * 0.25),
            show_scalar_bar=False,
            render=False,
            reset_camera=False,
        )
        mp = actor.mapper
        mp.SetScaleArray("radius"); mp.SetScaleFactor(1.0)
        if not self._visible:
            actor.SetVisibility(False)
        self._actors.append(actor)

    def _render_gaussian(
        self,
        positions: np.ndarray,
        colors: np.ndarray,
        radii: np.ndarray,
        cmap: str,
    ) -> None:
        if len(positions) == 0:
            return
        cloud = pv.PolyData(positions)
        cloud["scalar"] = colors
        cloud["radius"] = radii
        actor = self._pl.add_mesh(
            cloud,
            scalars="scalar",
            cmap=cmap,
            clim=[0.0, 1.0],
            style="points_gaussian",
            emissive=False,
            opacity=self._opacity,
            show_scalar_bar=False,
            render=False,
            reset_camera=False,
        )
        # Make the gaussian splats sized in world coordinates (Mpc/h) via
        # the per-point "radius" array rather than fixed screen pixels.
        mapper = actor.mapper
        mapper.SetScaleArray("radius")
        mapper.SetScaleFactor(1.0)
        if not self._visible:
            actor.SetVisibility(False)
        self._cloud = cloud
        self._actors.append(actor)

    def _compute_colors(self, snap: GalaxySnapshot) -> np.ndarray:
        m = self._color_mode
        if m == "density":
            return compute_density_colors(snap.positions)
        if m == "ssfr":
            return normalize_log(snap.ssfr, *_RANGES["ssfr"])
        if m == "sfr":
            return normalize_log(np.maximum(snap.sfr, 1e-6), *_RANGES["sfr"])
        if m == "cold_gas":
            return normalize_log(np.maximum(snap.cold_gas, 1.0), *_RANGES["cold_gas"])
        if m == "bulge_mass":
            return normalize_log(np.maximum(snap.bulge_mass, 1.0), *_RANGES["bulge_mass"])
        if m == "bh_mass":
            return normalize_log(np.maximum(snap.bh_mass, 1.0), *_RANGES["bh_mass"])
        if m == "ics_mass":
            return normalize_log(np.maximum(snap.ics_mass, 1.0), *_RANGES["ics_mass"])
        if m == "bt":
            bt = snap.bulge_mass / np.where(snap.stellar_mass > 0, snap.stellar_mass, np.inf)
            vmin, vmax = _RANGES["bt"]
            return np.clip((bt - vmin) / (vmax - vmin + 1e-10), 0.0, 1.0).astype(np.float32)
        if m == "age":
            ages = snap.mean_age.astype(np.float32)
            vmin, vmax = _RANGES["age"]
            return np.clip((ages - vmin) / (vmax - vmin + 1e-10), 0.0, 1.0)
        return normalize_log(snap.stellar_mass, *_RANGES["stellar_mass"])

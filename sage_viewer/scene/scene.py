from __future__ import annotations

from pathlib import Path
from typing import Callable

import pyvista as pv

from sage_viewer.scene.camera import CameraController
from sage_viewer.scene.galaxy_layer import GalaxyLayer
from sage_viewer.scene.halo_layer import HaloLayer
from sage_viewer.scene.model import Model


class Scene:
    """Owner of the PyVista plotter and a dict of Models.

    One model is the *primary* (its layers are exposed via `scene.halo_layer` /
    `scene.galaxy_layer` so all existing UI code keeps working). Additional
    models can be loaded and made visible as overlays if they share the same
    box size and snapshot count.

    Playback animation is driven externally by the Trame async event loop
    (see toolbar.py) so that all VTK calls stay on the main thread.
    """

    def __init__(
        self,
        primary_par_path: str | Path,
        off_screen: bool = False,
        initial_snap: int | None = None,
        n_jobs: int = -1,
        min_halo_mass: float = 1.0e10,
        min_stellar_mass: float = 1.0e8,
        max_halos: int = 100_000,
        max_galaxies: int = 100_000,
    ) -> None:
        self._plotter = pv.Plotter(off_screen=off_screen, window_size=[1600, 900])
        self._plotter.set_background("black")
        self._plotter.renderer.SetNearClippingPlaneTolerance(0.00001)

        # Loader kwargs reused when adding additional models later
        self._loader_kwargs = dict(
            n_jobs=n_jobs,
            min_halo_mass=min_halo_mass,
            min_stellar_mass=min_stellar_mass,
            max_halos=max_halos,
            max_galaxies=max_galaxies,
        )

        self._models: dict[str, Model] = {}
        self._primary_name: str = ""

        # Build the primary model
        primary = Model(primary_par_path, self._plotter, self._loader_kwargs)
        self._models[primary.name] = primary
        self._primary_name = primary.name

        self._camera = CameraController(self._plotter, primary.box_size)

        self._current_snap: int = (
            initial_snap if initial_snap is not None else primary.snap_count - 1
        )

        self._on_snap_change: list[Callable[[int], None]] = []
        self._on_model_change: list[Callable[[], None]] = []
        self._focus_region: dict | None = None

        self.set_snapshot(self._current_snap)
        self._camera.reset()

    # ------------------------------------------------------------------
    # Primary model & layer access (compatibility surface)
    # ------------------------------------------------------------------

    @property
    def primary(self) -> Model:
        return self._models[self._primary_name]

    @property
    def primary_name(self) -> str:
        return self._primary_name

    @property
    def halo_layer(self) -> HaloLayer:
        return self.primary.halo_layer

    @property
    def galaxy_layer(self) -> GalaxyLayer:
        return self.primary.galaxy_layer

    @property
    def fof_links_visible(self) -> bool:
        return self.primary.fof_layer.visible

    def set_fof_links_visible(self, visible: bool) -> None:
        """Toggle FoF-link lines for the primary model."""
        self.primary.fof_layer.visible = bool(visible)

    @property
    def camera(self) -> CameraController:
        return self._camera

    @property
    def plotter(self) -> pv.Plotter:
        return self._plotter

    @property
    def current_snap(self) -> int:
        return self._current_snap

    @property
    def snap_label(self) -> str:
        return self.primary.snap_table.label(self._current_snap)

    # Backward-compat — some callers still reach into these
    @property
    def _cfg(self):
        return self.primary.cfg

    @property
    def _snap_table(self):
        return self.primary.snap_table

    @property
    def _loader(self):
        return self.primary.loader

    @property
    def snap_count(self) -> int:
        return self.primary.snap_count

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    def list_models(self) -> list[Model]:
        return list(self._models.values())

    def has_model(self, name: str) -> bool:
        return name in self._models

    def add_model(self, par_path: str | Path) -> Model:
        """Load a new model alongside the primary. Starts hidden by default."""
        model = Model(par_path, self._plotter, self._loader_kwargs)
        if model.name in self._models:
            return self._models[model.name]
        model.set_snapshot(self._current_snap)
        model.visible = False
        self._models[model.name] = model
        for cb in self._on_model_change:
            cb()
        return model

    def remove_model(self, name: str) -> None:
        """Remove a non-primary model from the scene entirely."""
        if name == self._primary_name or name not in self._models:
            return
        model = self._models.pop(name)
        model.visible = False
        # Drop the layer actors so they don't linger in the plotter
        model.halo_layer._clear_actors()
        model.galaxy_layer._clear_actors()
        model.shutdown()
        for cb in self._on_model_change:
            cb()

    def switch_primary(self, name: str) -> None:
        """Switch the active primary model.

        Works for any model regardless of box size / snapshot count.
        Hides the previous primary; any currently overlaid models that are
        no longer compatible with the new primary are automatically hidden.
        Returns silently if `name` is already primary or unknown.
        """
        if name == self._primary_name or name not in self._models:
            return
        old_primary_box = self.primary.box_size
        # Hide the old primary (including any FoF links it was showing)
        self._models[self._primary_name].visible = False
        self._models[self._primary_name].fof_layer.visible = False
        self._primary_name = name
        # Hide any overlay that is now incompatible with the new primary
        for other_name, m in self._models.items():
            if other_name == self._primary_name:
                continue
            if m.visible and not self.is_compatible_for_overlay(other_name):
                m.visible = False
        # Show the new primary
        self.primary.visible = True
        # Always start the new primary at z=0 (its last snapshot).
        snap = self.primary.snap_count - 1
        self._current_snap = snap
        self.primary.set_snapshot(snap)
        # Camera box may have changed — reset if the box is significantly different
        new_box = self.primary.box_size
        self._camera._box_size = new_box
        if abs(new_box - old_primary_box) > 1e-3:
            self._camera.reset()
        # Re-apply focus mask in new model's coordinates
        if self._focus_region is not None:
            halos, galaxies = self.primary.loader.get(self._current_snap)
            self._apply_focus_masks_for_layer(
                self.primary.halo_layer, self.primary.galaxy_layer,
                halos.positions, galaxies.positions,
            )
        for cb in self._on_snap_change:
            cb(self._current_snap)
        for cb in self._on_model_change:
            cb()

    def set_overlay_visible(self, name: str, vis: bool) -> str | None:
        """Show or hide a non-primary model as an overlay.

        Returns None on success, or an error message string if the request
        was rejected (e.g. trying to overlay an incompatible model).
        Turning OFF is always allowed.
        """
        if name == self._primary_name or name not in self._models:
            return None
        m = self._models[name]
        if vis:
            # Turning ON: enforce compatibility
            if not self.is_compatible_for_overlay(name):
                primary = self.primary
                cand = self._models[name]
                if abs(primary.box_size - cand.box_size) > 1e-3:
                    detail = (
                        f"box size {cand.box_size:.1f} ≠ "
                        f"{primary.box_size:.1f} Mpc/h"
                    )
                elif primary.snap_count != cand.snap_count:
                    detail = (
                        f"snapshot count {cand.snap_count} ≠ "
                        f"{primary.snap_count}"
                    )
                else:
                    detail = "incompatible simulation parameters"
                return (
                    f"Can't overlay '{name}' on '{primary.name}': {detail}. "
                    f"Use Switch instead."
                )
            m.set_snapshot(self._current_snap)
        m.visible = vis
        for cb in self._on_model_change:
            cb()
        return None

    def is_compatible_for_overlay(self, name: str) -> bool:
        """Overlay only allowed if box size and snap count match the primary."""
        if name == self._primary_name or name not in self._models:
            return False
        primary = self.primary
        candidate = self._models[name]
        return (
            abs(primary.box_size - candidate.box_size) < 1e-3
            and primary.snap_count == candidate.snap_count
        )

    # ------------------------------------------------------------------
    # Snapshot control (drives every visible model)
    # ------------------------------------------------------------------

    def set_snapshot(self, snap_num: int) -> None:
        snap_num = max(0, min(int(snap_num), self.primary.snap_count - 1))
        self._current_snap = snap_num

        # Always update the primary so its layer reflects the new data
        self.primary.set_snapshot(snap_num)
        # Update any visible overlays too (if compatible)
        for name, m in self._models.items():
            if name == self._primary_name:
                continue
            if m.visible:
                m.set_snapshot(min(snap_num, m.snap_count - 1))

        # Camera indices follow primary
        halos, galaxies = self.primary.loader.get(snap_num)
        self._camera.update_halo_index(halos.positions)
        self._camera.update_galaxy_positions(galaxies.positions)

        if self._focus_region is not None:
            self._apply_focus_masks_for_layer(
                self.primary.halo_layer, self.primary.galaxy_layer,
                halos.positions, galaxies.positions,
            )

        for cb in self._on_snap_change:
            cb(snap_num)

    # ------------------------------------------------------------------
    # Focus / spatial masking (applies to primary only for now)
    # ------------------------------------------------------------------

    def set_focus_box(
        self,
        xmin: float, xmax: float,
        ymin: float, ymax: float,
        zmin: float, zmax: float,
    ) -> None:
        self._focus_region = dict(type="box", xmin=xmin, xmax=xmax,
                                  ymin=ymin, ymax=ymax, zmin=zmin, zmax=zmax)
        halos, galaxies = self.primary.loader.get(self._current_snap)
        self._apply_focus_masks_for_layer(
            self.primary.halo_layer, self.primary.galaxy_layer,
            halos.positions, galaxies.positions,
        )

    def set_focus_sphere(
        self,
        center: tuple[float, float, float],
        radius: float,
    ) -> None:
        self._focus_region = dict(type="sphere", center=center, radius=radius)
        halos, galaxies = self.primary.loader.get(self._current_snap)
        self._apply_focus_masks_for_layer(
            self.primary.halo_layer, self.primary.galaxy_layer,
            halos.positions, galaxies.positions,
        )

    def clear_focus(self) -> None:
        self._focus_region = None
        self.primary.halo_layer.set_mask(None)
        self.primary.galaxy_layer.set_mask(None)

    def _apply_focus_masks_for_layer(
        self,
        halo_layer: HaloLayer,
        gal_layer: GalaxyLayer,
        halo_pos: "np.ndarray",
        gal_pos: "np.ndarray",
    ) -> None:
        import numpy as np
        r = self._focus_region
        if r is None:
            return
        if r["type"] == "box":
            def _box_mask(pos):
                if len(pos) == 0:
                    return np.array([], dtype=bool)
                return (
                    (pos[:, 0] >= r["xmin"]) & (pos[:, 0] <= r["xmax"]) &
                    (pos[:, 1] >= r["ymin"]) & (pos[:, 1] <= r["ymax"]) &
                    (pos[:, 2] >= r["zmin"]) & (pos[:, 2] <= r["zmax"])
                )
            halo_layer.set_mask(_box_mask(halo_pos))
            gal_layer.set_mask(_box_mask(gal_pos))
        elif r["type"] == "sphere":
            cx, cy, cz = r["center"]
            rad = r["radius"]
            def _sphere_mask(pos):
                if len(pos) == 0:
                    return np.array([], dtype=bool)
                return np.linalg.norm(pos - np.array([cx, cy, cz]), axis=1) <= rad
            halo_layer.set_mask(_sphere_mask(halo_pos))
            gal_layer.set_mask(_sphere_mask(gal_pos))

    # Back-compat: still used by some callers
    def _apply_focus_masks(self, halo_pos, gal_pos) -> None:
        self._apply_focus_masks_for_layer(
            self.primary.halo_layer, self.primary.galaxy_layer, halo_pos, gal_pos
        )

    def next_snap_num(self) -> int:
        return (self._current_snap + 1) % self.primary.snap_count

    def prev_snap_num(self) -> int:
        return (self._current_snap - 1) % self.primary.snap_count

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def register_snap_change_callback(self, cb: Callable[[int], None]) -> None:
        self._on_snap_change.append(cb)

    def register_model_change_callback(self, cb: Callable[[], None]) -> None:
        self._on_model_change.append(cb)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self) -> None:
        for m in self._models.values():
            m.shutdown()
        self._plotter.close()

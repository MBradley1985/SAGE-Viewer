from __future__ import annotations

import numpy as np

from sage_viewer.utils.colormap import HALO_MASS_RANGE, STELLAR_MASS_RANGE

# Point size bounds in screen pixels
HALO_SIZE_BINS = [25.0, 30.0, 35.0, 40.0, 60.0]
GALAXY_SIZE_SCALE = 0.17


def halo_point_sizes(
    masses: np.ndarray,
    size_min: float = HALO_SIZE_BINS[0],
    size_max: float = HALO_SIZE_BINS[-1],
    mass_range: tuple[float, float] = HALO_MASS_RANGE,
) -> np.ndarray:
    """Scale halo point sizes by Mvir (Msun) using a fixed log10 range.

    Fixed range prevents flickering when the mass distribution changes
    between snapshots.
    """
    if len(masses) == 0:
        return np.array([], dtype=np.float32)
    log_m = np.log10(np.maximum(masses, 1.0))
    vmin, vmax = mass_range
    norm = np.clip((log_m - vmin) / (vmax - vmin + 1e-10), 0.0, 1.0)
    return (size_min + norm * (size_max - size_min)).astype(np.float32)


def galaxy_point_sizes(
    stellar_mass: np.ndarray,
    size_min: float = HALO_SIZE_BINS[0] * GALAXY_SIZE_SCALE,
    size_max: float = HALO_SIZE_BINS[-1] * GALAXY_SIZE_SCALE,
    mass_range: tuple[float, float] = STELLAR_MASS_RANGE,
) -> np.ndarray:
    """Scale galaxy point sizes by stellar mass (Msun) using a fixed log10 range."""
    if len(stellar_mass) == 0:
        return np.array([], dtype=np.float32)
    log_m = np.log10(np.maximum(stellar_mass, 1.0))
    vmin, vmax = mass_range
    norm = np.clip((log_m - vmin) / (vmax - vmin + 1e-10), 0.0, 1.0)
    return (size_min + norm * (size_max - size_min)).astype(np.float32)


def galaxy_world_radii(
    stellar_mass: np.ndarray,
    r_min: float = 0.025,   # Mpc/h  (low-mass end)
    r_max: float = 0.25,    # Mpc/h  (high-mass end)
    mass_range: tuple[float, float] = STELLAR_MASS_RANGE,
) -> np.ndarray:
    """Per-galaxy world-space gaussian radius (Mpc/h), scaling with stellar mass."""
    if len(stellar_mass) == 0:
        return np.array([], dtype=np.float32)
    log_m = np.log10(np.maximum(stellar_mass, 1.0))
    vmin, vmax = mass_range
    norm = np.clip((log_m - vmin) / (vmax - vmin + 1e-10), 0.0, 1.0)
    return (r_min + norm * (r_max - r_min)).astype(np.float32)


def halo_world_radii(
    masses: np.ndarray,
    r_min: float = 0.15,    # Mpc/h  (low-mass end)
    r_max: float = 1.5,     # Mpc/h  (high-mass end)
    mass_range: tuple[float, float] = HALO_MASS_RANGE,
) -> np.ndarray:
    """Per-halo world-space gaussian radius (Mpc/h), scaling with Mvir."""
    if len(masses) == 0:
        return np.array([], dtype=np.float32)
    log_m = np.log10(np.maximum(masses, 1.0))
    vmin, vmax = mass_range
    norm = np.clip((log_m - vmin) / (vmax - vmin + 1e-10), 0.0, 1.0)
    return (r_min + norm * (r_max - r_min)).astype(np.float32)


def size_bin_mask(
    sizes: np.ndarray, bin_edges: list[float]
) -> list[np.ndarray]:
    """Return a boolean mask per size bin for split-bin rendering."""
    masks = []
    for i, edge in enumerate(bin_edges):
        lo = bin_edges[i - 1] if i > 0 else 0.0
        if i < len(bin_edges) - 1:
            masks.append((sizes >= lo) & (sizes < edge))
        else:
            masks.append(sizes >= lo)
    return masks

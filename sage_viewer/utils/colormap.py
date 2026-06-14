from __future__ import annotations

import numpy as np
from scipy.stats import gaussian_kde


# Default scalar ranges (log10 units)
HALO_MASS_RANGE = (10.0, 15.0)       # log10(Msun)
STELLAR_MASS_RANGE = (8.0, 12.5)     # log10(Msun)
SSFR_RANGE = (-14.0, -8.0)           # log10(yr^-1)


def normalize_log(
    values: np.ndarray,
    vmin: float,
    vmax: float,
) -> np.ndarray:
    """Generic log10 normalisation to [0, 1]."""
    log_v = np.log10(np.maximum(values, 1e-30))
    return np.clip((log_v - vmin) / (vmax - vmin + 1e-10), 0.0, 1.0).astype(np.float32)


def normalize_log_mass(
    mass: np.ndarray,
    vmin: float = STELLAR_MASS_RANGE[0],
    vmax: float = STELLAR_MASS_RANGE[1],
) -> np.ndarray:
    """Map stellar or halo masses (Msun) to [0, 1] via log10."""
    log_m = np.log10(np.maximum(mass, 1.0))
    return np.clip((log_m - vmin) / (vmax - vmin + 1e-10), 0.0, 1.0)


def normalize_log_halo_mass(
    mass: np.ndarray,
    vmin: float = HALO_MASS_RANGE[0],
    vmax: float = HALO_MASS_RANGE[1],
) -> np.ndarray:
    """Map halo masses (Msun) to [0, 1] via log10."""
    log_m = np.log10(np.maximum(mass, 1.0))
    return np.clip((log_m - vmin) / (vmax - vmin + 1e-10), 0.0, 1.0)


def normalize_log_ssfr(
    ssfr: np.ndarray,
    vmin: float = SSFR_RANGE[0],
    vmax: float = SSFR_RANGE[1],
) -> np.ndarray:
    """Map specific SFR (yr^-1) to [0, 1] via log10."""
    ssfr_safe = np.maximum(ssfr, 1e-14)
    log_ssfr = np.log10(ssfr_safe)
    return np.clip((log_ssfr - vmin) / (vmax - vmin + 1e-10), 0.0, 1.0)


def compute_density_colors(
    positions: np.ndarray,
    kde_subsample: int = 5000,
    vmin: float | None = None,
    vmax: float | None = None,
) -> np.ndarray:
    """KDE-based local density mapped to [0, 1].

    Subsamples the KDE fit for performance; evaluates on all points.
    Returns zeros for empty or near-empty point sets.
    """
    if len(positions) < 10:
        return np.zeros(len(positions), dtype=np.float32)

    rng = np.random.default_rng(42)
    if len(positions) > kde_subsample:
        idx = rng.choice(len(positions), kde_subsample, replace=False)
        kde_data = positions[idx].T
    else:
        kde_data = positions.T

    try:
        kde = gaussian_kde(kde_data)
        density = kde(positions.T)
        density = np.log10(density + 1e-10)

        d_min = vmin if vmin is not None else density.min()
        d_max = vmax if vmax is not None else density.max()

        if d_max > d_min:
            density = (density - d_min) / (d_max - d_min)
        else:
            density = np.zeros_like(density)

        return np.clip(density, 0.0, 1.0).astype(np.float32)
    except Exception:
        return np.zeros(len(positions), dtype=np.float32)

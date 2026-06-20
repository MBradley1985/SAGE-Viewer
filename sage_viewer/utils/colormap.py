from __future__ import annotations

import numpy as np


def cmap_css_gradient(name: str, n: int = 12) -> str:
    """CSS linear-gradient string for a matplotlib colormap."""
    import matplotlib.pyplot as plt
    cmap = plt.get_cmap(name)
    stops = []
    for i in range(n):
        t = i / (n - 1)
        r, g, b, a = cmap(float(t))
        stops.append(
            f"rgba({int(r*255)},{int(g*255)},{int(b*255)},{a:.2f}) {int(t*100)}%"
        )
    return "linear-gradient(to right, " + ", ".join(stops) + ")"


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



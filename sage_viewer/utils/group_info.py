from __future__ import annotations

import numpy as np

from sage_viewer.io.galaxy_reader import GalaxySnapshot


def _classify(host_mvir_msun: float, n_members: int) -> str:
    if n_members <= 1:
        return "Isolated"
    if n_members == 2:
        return "Pair"
    if host_mvir_msun >= 1e14:
        return "Cluster"
    if host_mvir_msun >= 1e13:
        return "Group"
    return "Small group"


def member_indices(galaxies: GalaxySnapshot, idx: int) -> np.ndarray:
    """Return the array of indices belonging to the same FOF group as idx."""
    if galaxies.count == 0 or idx < 0 or idx >= galaxies.count:
        return np.array([], dtype=np.int64)
    cid = galaxies.central_id[idx]
    return np.where(galaxies.central_id == cid)[0]


def build_group_info(
    galaxies: GalaxySnapshot,
    fields_available: dict[str, bool],
    idx: int,
    hubble_h: float,
) -> dict:
    """Aggregate FOF-group properties for the group containing galaxy `idx`."""
    if galaxies.count == 0 or idx < 0 or idx >= galaxies.count:
        return {}

    members = member_indices(galaxies, idx)
    n_members = len(members)
    if n_members == 0:
        return {}

    sm   = galaxies.stellar_mass[members]
    sfr  = galaxies.sfr[members]
    bmm  = galaxies.bulge_mass[members]
    cgm  = galaxies.cold_gas[members]
    gt   = galaxies.gal_type[members]
    pos  = galaxies.positions[members]

    total_sm   = float(sm.sum())
    total_sfr  = float(sfr.sum())
    total_cgm  = float(cgm.sum())
    mean_bt    = float((bmm / np.maximum(sm, 1.0)).mean())
    n_central  = int((gt == 0).sum())
    n_sat      = n_members - n_central
    is_central = bool(galaxies.gal_type[idx] == 0)

    # Host Mvir from CentralMvir (Msun) if available, else from picked galaxy's mvir
    if fields_available.get("central_mvir", False):
        host_mvir = float(galaxies.central_mvir[idx])
    else:
        host_mvir = float(galaxies.mvir[idx]) * 1.0e10 / max(hubble_h, 1e-6)

    classification = _classify(host_mvir, n_members)

    # Spatial extent — max separation between members in Mpc/h.  For a
    # single-member group it's 0; for a pair it's the inter-galaxy distance.
    if n_members >= 2:
        center = pos.mean(axis=0)
        radial = np.linalg.norm(pos - center, axis=1)
        extent = float(radial.max())
    else:
        extent = 0.0

    info: dict = {
        "Classification": classification,
        "Members":        f"{n_members}  ({n_central} central, {n_sat} sat.)",
        "Host Mvir":      f"{host_mvir:.2e} Msun",
        "Total Stellar Mass": f"{total_sm:.2e} Msun",
        "Total Cold Gas":     f"{total_cgm:.2e} Msun",
        "Total SFR":          f"{total_sfr:.2e} Msun/yr",
        "Mean B/T":       f"{mean_bt:.2f}",
        "Extent":         f"{extent:.2f} Mpc/h",
        "Target role":    "Central" if is_central else "Satellite",
    }

    # Optional: brightest / most massive member (the central, by definition)
    cidx_local = int(np.argmin(gt))   # smallest type → most likely central (0)
    bcg_sm = float(sm[cidx_local])
    info["BCG Stellar Mass"] = f"{bcg_sm:.2e} Msun"

    return info

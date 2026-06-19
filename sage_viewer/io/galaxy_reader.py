from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np


@dataclass
class GalaxySnapshot:
    positions: np.ndarray       # (N, 3) float32, Mpc/h
    stellar_mass: np.ndarray    # (N,)   float32, Msun
    mvir: np.ndarray            # (N,)   float32, 10^10 Msun/h (raw)
    sfr: np.ndarray             # (N,)   float32, Msun/yr
    ssfr: np.ndarray            # (N,)   float32, yr^-1
    cold_gas: np.ndarray        # (N,)   float32, Msun
    bulge_mass: np.ndarray      # (N,)   float32, Msun
    gal_type: np.ndarray        # (N,)   int32, 0=central 1+=satellite
    bh_mass: np.ndarray         # (N,)   float32, Msun
    ics_mass: np.ndarray        # (N,)   float32, Msun (intra-cluster stars)
    ffb_regime: np.ndarray      # (N,)   int32, FFB regime flag
    cgm_regime: np.ndarray      # (N,)   int32, 0=cold 1=hot (Regime field)
    central_mvir: np.ndarray    # (N,)   float32, Msun (host FOF Mvir)
    h2_mass: np.ndarray         # (N,)   float32, Msun
    cgm_gas: np.ndarray         # (N,)   float32, Msun — CGMgas (CGM-regime envelope)
    hot_gas: np.ndarray         # (N,)   float32, Msun — HotGas (Hot-regime atmosphere)
    galaxy_id: np.ndarray       # (N,)   int64 — SAGE GalaxyIndex
    central_id: np.ndarray      # (N,)   int64 — SAGE CentralGalaxyIndex
    time_of_infall: np.ndarray  # (N,)   int32 — snapshot index of infall
    mean_age: np.ndarray        # (N,)   float32 — mass-weighted stellar age, Gyr
    sage_indices: np.ndarray    # (N,)   int64  — row indices in the raw HDF5 snap group
    snap_num: int

    @property
    def count(self) -> int:
        return len(self.positions)

    @classmethod
    def empty(cls, snap_num: int) -> "GalaxySnapshot":
        z = np.empty(0, dtype=np.float32)
        zi = np.empty(0, dtype=np.int32)
        zi64 = np.empty(0, dtype=np.int64)
        return cls(
            positions=np.empty((0, 3), dtype=np.float32),
            stellar_mass=z, mvir=z, sfr=z, ssfr=z,
            cold_gas=z, bulge_mass=z,
            gal_type=zi,
            bh_mass=z, ics_mass=z, central_mvir=z,
            ffb_regime=zi, cgm_regime=zi,
            h2_mass=z, cgm_gas=z, hot_gas=z,
            galaxy_id=zi64, central_id=zi64,
            time_of_infall=zi,
            mean_age=z,
            sage_indices=np.empty(0, dtype=np.int64),
            snap_num=snap_num,
        )


VERBOSE = True


def load_galaxy_snapshot(
    hdf5_path: str | Path,
    snap_num: int,
    min_stellar_mass: float = 1.0e8,
    max_galaxies: int = 100_000,
    hubble_h: float | None = None,
    scale_factors: np.ndarray | None = None,
    omega_m: float | None = None,
    omega_l: float | None = None,
) -> GalaxySnapshot:
    # Prefer the cosmology + scale factors that are written into the HDF5
    # header.  Arguments are now overrides / fallbacks only.
    from sage_viewer.io.sage_header import read_sage_header
    hdr = read_sage_header(hdf5_path)
    if hubble_h is None:      hubble_h      = hdr.get("hubble_h",      0.73)
    if omega_m  is None:      omega_m       = hdr.get("omega_m",       0.315)
    if omega_l  is None:      omega_l       = hdr.get("omega_l",       0.685)
    if scale_factors is None: scale_factors = hdr.get("scale_factors", None)
    """Load galaxy positions and properties for one snapshot from SAGE HDF5 output.

    Parameters
    ----------
    hdf5_path:        path to SAGE HDF5 output (e.g. model_0.hdf5)
    snap_num:         snapshot index
    min_stellar_mass: minimum stellar mass in Msun (after h correction)
    max_galaxies:     random downsample if more galaxies than this are found
    hubble_h:         Hubble parameter h (from par file)
    """
    hdf5_path = Path(hdf5_path)
    group_key = f"Snap_{snap_num}"

    if VERBOSE:
        print(f"  Galaxies: reading {hdf5_path.name} / {group_key}...")
    with h5py.File(hdf5_path, "r") as f:
        if group_key not in f:
            if VERBOSE:
                print(f"  Galaxies: group {group_key} not found — empty snapshot")
            return GalaxySnapshot.empty(snap_num)

        grp = f[group_key]

        def _get(field: str) -> np.ndarray:
            return np.array(grp[field])

        try:
            posx          = _get("Posx")
            posy          = _get("Posy")
            posz          = _get("Posz")
            stellar_raw   = _get("StellarMass")
            bulge_raw     = _get("BulgeMass")
            cold_gas_raw  = _get("ColdGas")
            mvir_raw      = _get("Mvir")
            sfr_disk      = _get("SfrDisk")
            sfr_bulge     = _get("SfrBulge")
            gal_type      = _get("Type").astype(np.int32)
        except KeyError as e:
            raise KeyError(
                f"Missing field {e} in {hdf5_path}:{group_key}"
            ) from e

        # Optional fields — present in current SAGE outputs but tolerate absence
        def _opt(field: str, default_dtype) -> np.ndarray:
            if field in grp:
                return np.array(grp[field])
            return np.zeros(len(posx), dtype=default_dtype)

        bh_raw         = _opt("BlackHoleMass", np.float32)
        ics_raw        = _opt("IntraClusterStars", np.float32)
        ffb_regime_raw = _opt("FFBRegime", np.int32).astype(np.int32)
        cgm_regime_raw = _opt("Regime", np.int32).astype(np.int32)
        cmvir_raw      = _opt("CentralMvir", np.float32)
        h2_raw         = _opt("H2gas", np.float32)
        cgm_gas_raw    = _opt("CGMgas", np.float32)
        hot_gas_raw    = _opt("HotGas", np.float32)
        galid_raw      = _opt("GalaxyIndex", np.int64).astype(np.int64)
        cid_raw        = _opt("CentralGalaxyIndex", np.int64).astype(np.int64)
        tinfall_raw    = _opt("TimeOfInfall", np.int32).astype(np.int32)

        # SFH arrays (one row per galaxy × ~64 time bins).  Only read if
        # present; the age computation tolerates absent SFH gracefully.
        has_sfh = ("SFHMassDisk" in grp) and ("SFHMassBulge" in grp)
        sfh_disk_raw  = np.asarray(grp["SFHMassDisk"])  if has_sfh else None
        sfh_bulge_raw = np.asarray(grp["SFHMassBulge"]) if has_sfh else None

    # All mass fields stored as 10^10 Msun/h → convert to Msun
    f = 1.0e10 / hubble_h
    stellar_mass  = stellar_raw.astype(np.float32) * f
    bulge_mass    = bulge_raw.astype(np.float32) * f
    cold_gas      = cold_gas_raw.astype(np.float32) * f
    bh_mass       = bh_raw.astype(np.float32) * f
    ics_mass      = ics_raw.astype(np.float32) * f
    central_mvir  = cmvir_raw.astype(np.float32) * f
    h2_mass       = h2_raw.astype(np.float32) * f
    cgm_gas       = cgm_gas_raw.astype(np.float32) * f
    hot_gas       = hot_gas_raw.astype(np.float32) * f
    sfr           = (sfr_disk + sfr_bulge).astype(np.float32)
    ssfr          = sfr / np.where(stellar_mass > 0, stellar_mass, np.inf)

    mask    = (stellar_mass > min_stellar_mass) & (mvir_raw > 0)
    indices = np.where(mask)[0]

    if len(indices) > max_galaxies:
        rng = np.random.default_rng(42)
        indices = rng.choice(indices, max_galaxies, replace=False)

    if VERBOSE:
        print(f"  Galaxies: {len(indices):,} loaded")
    positions = np.column_stack(
        [posx[indices], posy[indices], posz[indices]]
    ).astype(np.float32)

    # Mass-weighted stellar age, Gyr (one value per galaxy).  Needs SFH arrays
    # and scale factors; otherwise filled with zeros.
    mean_age = _compute_mean_ages(
        sfh_disk=sfh_disk_raw, sfh_bulge=sfh_bulge_raw,
        indices=indices, snap_num=snap_num,
        scale_factors=scale_factors,
        hubble_h=hubble_h, omega_m=omega_m, omega_l=omega_l,
    )

    return GalaxySnapshot(
        positions=positions,
        stellar_mass=stellar_mass[indices],
        mvir=mvir_raw[indices].astype(np.float32),
        sfr=sfr[indices],
        ssfr=ssfr[indices],
        cold_gas=cold_gas[indices],
        bulge_mass=bulge_mass[indices],
        gal_type=gal_type[indices],
        bh_mass=bh_mass[indices],
        ics_mass=ics_mass[indices],
        ffb_regime=ffb_regime_raw[indices],
        cgm_regime=cgm_regime_raw[indices],
        central_mvir=central_mvir[indices],
        h2_mass=h2_mass[indices],
        cgm_gas=cgm_gas[indices],
        hot_gas=hot_gas[indices],
        galaxy_id=galid_raw[indices],
        central_id=cid_raw[indices],
        time_of_infall=tinfall_raw[indices],
        mean_age=mean_age,
        sage_indices=indices.astype(np.int64),
        snap_num=snap_num,
    )


def _age_lcdm(a: np.ndarray | float, h: float, om: float, ol: float) -> np.ndarray:
    """Cosmic age (Gyr) at scale factor a, flat ΛCDM."""
    a = np.asarray(a, dtype=np.float64)
    H0_inv = 9.778 / max(h, 0.01)   # Gyr
    return (2.0 / 3.0) / np.sqrt(ol) * np.arcsinh(np.sqrt(ol / om) * a ** 1.5) * H0_inv


def _compute_mean_ages(
    sfh_disk: np.ndarray | None,
    sfh_bulge: np.ndarray | None,
    indices: np.ndarray,
    snap_num: int,
    scale_factors: np.ndarray | None,
    hubble_h: float, omega_m: float, omega_l: float,
) -> np.ndarray:
    """Mass-weighted stellar age (Gyr) per galaxy from SFH arrays + cosmology.

    Returns zeros if SFH arrays or scale factors aren't available.
    """
    if (sfh_disk is None or sfh_bulge is None or scale_factors is None
            or len(scale_factors) == 0):
        return np.zeros(len(indices), dtype=np.float32)

    # Per-galaxy SFH = disk + bulge.  Shape (N, n_bins)
    sfh = sfh_disk[indices].astype(np.float64) + sfh_bulge[indices].astype(np.float64)

    # SFH bin i ↔ snapshot i in SAGE's standard layout.  Use the snapshot's
    # scale factor as the formation time of that bin.
    n_bins = sfh.shape[1] if sfh.ndim == 2 else 0
    if n_bins == 0:
        return np.zeros(len(indices), dtype=np.float32)
    n = min(n_bins, len(scale_factors))
    a_bin = scale_factors[:n]
    age_bin = _age_lcdm(a_bin, hubble_h, omega_m, omega_l)
    age_now = _age_lcdm(scale_factors[min(snap_num, len(scale_factors) - 1)],
                        hubble_h, omega_m, omega_l)
    lookback = age_now - age_bin                          # (n,)
    # Mass-weighted lookback ≈ mean stellar age
    sfh_clipped = sfh[:, :n]
    total = sfh_clipped.sum(axis=1)
    weighted = (sfh_clipped * lookback).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        ages = np.where(total > 0, weighted / total, 0.0)
    return ages.astype(np.float32)

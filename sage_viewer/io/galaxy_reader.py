from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np


@dataclass
class GalaxySnapshot:
    positions: np.ndarray     # (N, 3) float32, Mpc/h
    stellar_mass: np.ndarray  # (N,)   float32, Msun
    mvir: np.ndarray          # (N,)   float32, 10^10 Msun/h (raw)
    sfr: np.ndarray           # (N,)   float32, Msun/yr
    ssfr: np.ndarray          # (N,)   float32, yr^-1
    cold_gas: np.ndarray      # (N,)   float32, Msun
    bulge_mass: np.ndarray    # (N,)   float32, Msun
    gal_type: np.ndarray      # (N,)   int32, 0=central 1+=satellite
    snap_num: int

    @property
    def count(self) -> int:
        return len(self.positions)

    @classmethod
    def empty(cls, snap_num: int) -> "GalaxySnapshot":
        z = np.empty(0, dtype=np.float32)
        return cls(
            positions=np.empty((0, 3), dtype=np.float32),
            stellar_mass=z, mvir=z, sfr=z, ssfr=z,
            cold_gas=z, bulge_mass=z,
            gal_type=np.empty(0, dtype=np.int32),
            snap_num=snap_num,
        )


def load_galaxy_snapshot(
    hdf5_path: str | Path,
    snap_num: int,
    min_stellar_mass: float = 1.0e8,
    max_galaxies: int = 100_000,
    hubble_h: float = 0.73,
) -> GalaxySnapshot:
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

    print(f"  Galaxies: reading {hdf5_path.name} / {group_key}...")
    with h5py.File(hdf5_path, "r") as f:
        if group_key not in f:
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

    # All mass fields stored as 10^10 Msun/h → convert to Msun
    f = 1.0e10 / hubble_h
    stellar_mass = stellar_raw.astype(np.float32) * f
    bulge_mass   = bulge_raw.astype(np.float32) * f
    cold_gas     = cold_gas_raw.astype(np.float32) * f
    sfr          = (sfr_disk + sfr_bulge).astype(np.float32)
    ssfr         = sfr / np.where(stellar_mass > 0, stellar_mass, np.inf)

    mask    = (stellar_mass > min_stellar_mass) & (mvir_raw > 0)
    indices = np.where(mask)[0]

    if len(indices) > max_galaxies:
        rng = np.random.default_rng(42)
        indices = rng.choice(indices, max_galaxies, replace=False)

    print(f"  Galaxies: {len(indices):,} loaded")
    positions = np.column_stack(
        [posx[indices], posy[indices], posz[indices]]
    ).astype(np.float32)

    return GalaxySnapshot(
        positions=positions,
        stellar_mass=stellar_mass[indices],
        mvir=mvir_raw[indices].astype(np.float32),
        sfr=sfr[indices],
        ssfr=ssfr[indices],
        cold_gas=cold_gas[indices],
        bulge_mass=bulge_mass[indices],
        gal_type=gal_type[indices],
        snap_num=snap_num,
    )

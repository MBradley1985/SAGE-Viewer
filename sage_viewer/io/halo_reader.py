from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed


# Matches the C struct written by lhalo_binary tree code
HALO_DTYPE = np.dtype([
    ("Descendant", np.int32),
    ("FirstProgenitor", np.int32),
    ("NextProgenitor", np.int32),
    ("FirstHaloInFOFgroup", np.int32),
    ("NextHaloInFOFgroup", np.int32),
    ("Len", np.int32),
    ("M_Mean200", np.float32),
    ("Mvir", np.float32),
    ("M_TopHat", np.float32),
    ("Pos", np.float32, (3,)),
    ("Vel", np.float32, (3,)),
    ("VelDisp", np.float32),
    ("Vmax", np.float32),
    ("Spin", np.float32, (3,)),
    ("MostBoundID", np.int64),
    ("SnapNum", np.int32),
    ("FileNr", np.int32),
    ("SubhaloIndex", np.int32),
    ("SubHalfMass", np.float32),
])


@dataclass
class HaloSnapshot:
    positions: np.ndarray   # (N, 3) float32, Mpc/h
    masses: np.ndarray      # (N,) float32, Msun
    snap_num: int

    @property
    def count(self) -> int:
        return len(self.positions)

    @classmethod
    def empty(cls, snap_num: int) -> "HaloSnapshot":
        return cls(
            positions=np.empty((0, 3), dtype=np.float32),
            masses=np.empty(0, dtype=np.float32),
            snap_num=snap_num,
        )


def _read_tree_file(
    tree_file: Path,
    snap_num: int,
    mass_cut_msun: float,
    hubble_h: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Read one lhalo_binary tree file and return (positions, masses) for snap_num."""
    if not tree_file.exists():
        return np.empty((0, 3), dtype=np.float32), np.empty(0, dtype=np.float32)

    with open(tree_file, "rb") as f:
        nforests = np.fromfile(f, dtype=np.int32, count=1)[0]
        nhalos_total = np.fromfile(f, dtype=np.int32, count=1)[0]

        if nhalos_total == 0:
            return np.empty((0, 3), dtype=np.float32), np.empty(0, dtype=np.float32)

        # Skip the per-forest halo counts header
        np.fromfile(f, dtype=np.int32, count=nforests)
        halos = np.fromfile(f, dtype=HALO_DTYPE, count=nhalos_total)

    snap_mask = halos["SnapNum"] == snap_num
    halos = halos[snap_mask]
    if len(halos) == 0:
        return np.empty((0, 3), dtype=np.float32), np.empty(0, dtype=np.float32)

    # Mvir in tree files is in units of 1e10 Msun/h
    masses = halos["Mvir"].astype(np.float32) * 1.0e10 / hubble_h
    mass_mask = masses > mass_cut_msun
    return halos["Pos"][mass_mask], masses[mass_mask]


def load_halo_snapshot(
    tree_dir: str | Path,
    tree_name: str,
    snap_num: int,
    first_file: int = 0,
    last_file: int = 7,
    mass_cut: float = 1.0e10,
    max_halos: int = 100_000,
    hubble_h: float = 0.73,
    n_jobs: int = -1,
) -> HaloSnapshot:
    """Load halo positions and masses for one snapshot from lhalo_binary tree files.

    Parameters
    ----------
    tree_dir:  directory containing the tree files
    tree_name: base name (e.g. 'trees_063'); files are tree_name.{first_file..last_file}
    snap_num:  snapshot index to extract
    mass_cut:  minimum halo mass in Msun (after h correction)
    max_halos: random downsample if more haloes than this are found
    n_jobs:    joblib parallel workers (-1 = all CPUs)
    """
    tree_dir = Path(tree_dir)
    tree_files = [
        tree_dir / f"{tree_name}.{i}"
        for i in range(first_file, last_file + 1)
    ]

    results = Parallel(n_jobs=n_jobs)(
        delayed(_read_tree_file)(tf, snap_num, mass_cut, hubble_h)
        for tf in tree_files
    )

    positions_list = [r[0] for r in results if len(r[0]) > 0]
    masses_list = [r[1] for r in results if len(r[1]) > 0]

    if not positions_list:
        return HaloSnapshot.empty(snap_num)

    positions = np.vstack(positions_list)
    masses = np.concatenate(masses_list)

    if len(positions) > max_halos:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(positions), max_halos, replace=False)
        positions = positions[idx]
        masses = masses[idx]

    return HaloSnapshot(positions=positions, masses=masses, snap_num=snap_num)

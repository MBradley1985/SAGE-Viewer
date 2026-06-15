from __future__ import annotations

import os
from concurrent.futures import Future, ThreadPoolExecutor
from functools import lru_cache
from threading import Lock
from typing import Optional

from sage_viewer.config import SimConfig
from sage_viewer.io.galaxy_reader import GalaxySnapshot, load_galaxy_snapshot
from sage_viewer.io.halo_reader import HaloSnapshot, load_halo_snapshot
from sage_viewer.io.snapshot_table import SnapshotTable


class SnapshotLoader:
    """Prefetch and cache haloes + galaxies around the current snapshot.

    Uses a thread pool so the main render thread never blocks on disk I/O.
    Keeps an LRU in-memory cache of recently loaded snapshots.

    Parameters
    ----------
    config:          parsed SimConfig
    snap_table:      SnapshotTable for the simulation
    n_jobs:          worker threads for parallel halo file reads (default: CPUs-1)
    prefetch_radius: number of snapshots ahead/behind to prefetch
    cache_size:      max snapshots kept in memory
    min_halo_mass:   Msun halo mass floor
    min_stellar_mass: Msun stellar mass floor
    max_halos:       downsample ceiling per snapshot
    max_galaxies:    downsample ceiling per snapshot
    """

    def __init__(
        self,
        config: SimConfig,
        snap_table: SnapshotTable,
        n_jobs: int = max(1, os.cpu_count() - 1),
        prefetch_radius: int = 2,
        cache_size: int = 8,
        min_halo_mass: float = 1.0e10,
        min_stellar_mass: float = 1.0e8,
        max_halos: int = 100_000,
        max_galaxies: int = 100_000,
    ) -> None:
        self._cfg = config
        self._snap_table = snap_table
        self._n_jobs = n_jobs
        self._prefetch_radius = prefetch_radius
        self._min_halo_mass = min_halo_mass
        self._min_stellar_mass = min_stellar_mass
        self._max_halos = max_halos
        self._max_galaxies = max_galaxies

        self._executor = ThreadPoolExecutor(max_workers=max(2, prefetch_radius * 2))
        self._futures: dict[int, Future] = {}
        self._lock = Lock()

        # Wrap the actual load call in an LRU cache so repeated requests
        # for the same snapshot skip disk entirely.
        self._cached_load = lru_cache(maxsize=cache_size)(self._load)

    def _load(
        self, snap_num: int
    ) -> tuple[HaloSnapshot, GalaxySnapshot]:
        halos = load_halo_snapshot(
            tree_dir=self._cfg.tree_dir,
            tree_name=self._cfg.tree_name,
            snap_num=snap_num,
            first_file=self._cfg.first_file,
            last_file=self._cfg.last_file,
            mass_cut=self._min_halo_mass,
            max_halos=self._max_halos,
            hubble_h=self._cfg.hubble_h,
            n_jobs=self._n_jobs,
        )
        galaxies = load_galaxy_snapshot(
            hdf5_path=self._cfg.hdf5_path,
            snap_num=snap_num,
            min_stellar_mass=self._min_stellar_mass,
            max_galaxies=self._max_galaxies,
            hubble_h=self._cfg.hubble_h,
            scale_factors=self._snap_table.scale_factors,
            omega_m=self._cfg.omega,
            omega_l=self._cfg.omega_lambda,
        )
        return halos, galaxies

    def get(self, snap_num: int) -> tuple[HaloSnapshot, GalaxySnapshot]:
        """Return (HaloSnapshot, GalaxySnapshot) for snap_num.

        Blocks only on a cold-cache miss; otherwise returns from memory.
        Triggers background prefetch of neighbouring snapshots as a side-effect.
        """
        result = self._cached_load(snap_num)
        self._prefetch_neighbours(snap_num)
        return result

    def _prefetch_neighbours(self, current: int) -> None:
        n = self._snap_table.count
        with self._lock:
            for offset in range(1, self._prefetch_radius + 1):
                for snap in (current - offset, current + offset):
                    if 0 <= snap < n and snap not in self._futures:
                        self._futures[snap] = self._executor.submit(
                            self._cached_load, snap
                        )

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

from __future__ import annotations

from pathlib import Path

import numpy as np


class SnapshotTable:
    """Maps snapshot indices ↔ redshifts ↔ scale factors.

    Reads a plain-text file of scale factor values (one per line), such as
    millennium.a_list or Uchuu100_scalefactor.txt.
    """

    def __init__(self, a_list_path: str | Path) -> None:
        self._path = Path(a_list_path)
        self._a = self._load(self._path)
        self._z = 1.0 / self._a - 1.0

    @staticmethod
    def _load(path: Path) -> np.ndarray:
        values = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Some files have multiple whitespace-separated values per line
                for token in line.split():
                    try:
                        values.append(float(token))
                    except ValueError:
                        pass
        return np.array(values, dtype=np.float64)

    @property
    def count(self) -> int:
        return len(self._a)

    @property
    def scale_factors(self) -> np.ndarray:
        return self._a.copy()

    @property
    def redshifts(self) -> np.ndarray:
        return self._z.copy()

    def snap_to_a(self, snap: int) -> float:
        return float(self._a[snap])

    def snap_to_z(self, snap: int) -> float:
        return float(self._z[snap])

    def z_to_snap(self, z: float) -> int:
        """Return the snapshot index closest to redshift z."""
        return int(np.argmin(np.abs(self._z - z)))

    def a_to_snap(self, a: float) -> int:
        """Return the snapshot index closest to scale factor a."""
        return int(np.argmin(np.abs(self._a - a)))

    def label(self, snap: int) -> str:
        z = self.snap_to_z(snap)
        a = self.snap_to_a(snap)
        return f"Snap {snap:02d}  |  z = {z:.2f}  |  a = {a:.4f}"

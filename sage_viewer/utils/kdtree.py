from __future__ import annotations

import numpy as np
from scipy.spatial import KDTree


class NearestHaloIndex:
    """Thin wrapper around scipy KDTree for nearest-halo spatial queries.

    Rebuilt automatically when positions change (i.e. on snapshot change).
    """

    def __init__(self, positions: np.ndarray | None = None) -> None:
        self._tree: KDTree | None = None
        self._positions: np.ndarray | None = None
        if positions is not None and len(positions) > 0:
            self.update(positions)

    def update(self, positions: np.ndarray, tree: KDTree | None = None) -> None:
        self._positions = positions
        self._tree = tree if tree is not None else KDTree(positions)

    def nearest(self, point: tuple[float, float, float]) -> int:
        """Return index of the closest halo/point to the given (x, y, z)."""
        if self._tree is None:
            raise RuntimeError("Index is empty — call update() first.")
        _, idx = self._tree.query(point)
        return int(idx)

    def within_radius(
        self, center: tuple[float, float, float], radius: float
    ) -> np.ndarray:
        """Return indices of all points within radius of center."""
        if self._tree is None:
            return np.array([], dtype=np.int64)
        return np.array(
            self._tree.query_ball_point(center, radius), dtype=np.int64
        )

    def position_of(self, idx: int) -> np.ndarray:
        if self._positions is None:
            raise RuntimeError("Index is empty — call update() first.")
        return self._positions[idx]

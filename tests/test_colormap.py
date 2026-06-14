import numpy as np
import pytest

from sage_viewer.utils.colormap import (
    normalize_log_mass,
    normalize_log_ssfr,
    compute_density_colors,
)


def test_normalize_log_mass_range():
    masses = np.array([1e8, 1e10, 1e12])
    out = normalize_log_mass(masses)
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def test_normalize_log_ssfr_range():
    ssfr = np.array([1e-14, 1e-11, 1e-8])
    out = normalize_log_ssfr(ssfr)
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def test_density_colors_length():
    rng = np.random.default_rng(0)
    pos = rng.uniform(0, 62.5, (50, 3)).astype(np.float32)
    out = compute_density_colors(pos)
    assert len(out) == 50
    assert out.min() >= 0.0
    assert out.max() <= 1.0


def test_density_colors_empty():
    out = compute_density_colors(np.zeros((3, 3), dtype=np.float32))
    assert np.all(out == 0)

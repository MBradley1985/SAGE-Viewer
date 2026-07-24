import numpy as np
import pytest

from visage.utils.colormap import (
    normalize_log_mass,
    normalize_log_ssfr,
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

import numpy as np
import pytest

from sage_viewer.utils.sizing import (
    HALO_SIZE_BINS,
    halo_point_sizes,
    galaxy_point_sizes,
    size_bin_mask,
)


def test_halo_sizes_range():
    masses = np.array([1e10, 1e12, 1e14])
    sizes = halo_point_sizes(masses)
    assert sizes.min() >= HALO_SIZE_BINS[0]
    assert sizes.max() <= HALO_SIZE_BINS[-1]


def test_galaxy_sizes_smaller_than_halos():
    masses = np.array([1e9, 1e10, 1e11])
    g = galaxy_point_sizes(masses)
    h = halo_point_sizes(masses)
    assert np.all(g <= h)


def test_empty_returns_empty():
    assert len(halo_point_sizes(np.array([]))) == 0
    assert len(galaxy_point_sizes(np.array([]))) == 0


def test_size_bin_mask_covers_all():
    rng = np.random.default_rng(0)
    sizes = rng.uniform(HALO_SIZE_BINS[0], HALO_SIZE_BINS[-1], 100).astype(np.float32)
    masks = size_bin_mask(sizes, HALO_SIZE_BINS)
    # Every element should appear in exactly one bin
    covered = np.zeros(len(sizes), dtype=bool)
    for m in masks:
        covered |= m
    assert np.all(covered)

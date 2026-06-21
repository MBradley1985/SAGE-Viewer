import numpy as np
import pytest

from sage_viewer.io.galaxy_reader import load_galaxy_snapshot


def test_loads_correct_snap(mini_hdf5_path):
    snap = load_galaxy_snapshot(
        mini_hdf5_path, snap_num=63, min_stellar_mass=0.0
    )
    assert snap.snap_num == 63
    assert snap.count > 0
    assert snap.positions.shape[1] == 3


def test_fields_present(mini_hdf5_path):
    snap = load_galaxy_snapshot(
        mini_hdf5_path, snap_num=63, min_stellar_mass=0.0
    )
    assert snap.stellar_mass.shape == (snap.count,)
    assert snap.ssfr.shape == (snap.count,)
    assert snap.gal_type.shape == (snap.count,)


def test_mass_cut_filters(mini_hdf5_path):
    snap_all = load_galaxy_snapshot(
        mini_hdf5_path, snap_num=63, min_stellar_mass=0.0
    )
    snap_cut = load_galaxy_snapshot(
        mini_hdf5_path, snap_num=63, min_stellar_mass=1.0e20
    )
    assert snap_all.count > snap_cut.count


def test_missing_snap_returns_empty(mini_hdf5_path):
    snap = load_galaxy_snapshot(
        mini_hdf5_path, snap_num=0, min_stellar_mass=0.0
    )
    assert snap.count == 0

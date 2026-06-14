import numpy as np
import pytest

from sage_viewer.io.halo_reader import load_halo_snapshot


def test_loads_correct_snap(mini_tree_path):
    snap = load_halo_snapshot(
        tree_dir=mini_tree_path.parent,
        tree_name="trees_063",
        snap_num=63,
        first_file=0,
        last_file=0,
        mass_cut=0.0,
        n_jobs=1,
    )
    assert snap.snap_num == 63
    assert snap.count > 0
    assert snap.positions.shape[1] == 3


def test_mass_cut_filters(mini_tree_path):
    snap_all = load_halo_snapshot(
        tree_dir=mini_tree_path.parent,
        tree_name="trees_063",
        snap_num=63,
        first_file=0,
        last_file=0,
        mass_cut=0.0,
        n_jobs=1,
    )
    snap_cut = load_halo_snapshot(
        tree_dir=mini_tree_path.parent,
        tree_name="trees_063",
        snap_num=63,
        first_file=0,
        last_file=0,
        mass_cut=1.0e15,  # nothing passes
        n_jobs=1,
    )
    assert snap_all.count > snap_cut.count


def test_empty_snap_returns_empty(mini_tree_path):
    snap = load_halo_snapshot(
        tree_dir=mini_tree_path.parent,
        tree_name="trees_063",
        snap_num=0,  # not in fixture
        first_file=0,
        last_file=0,
        mass_cut=0.0,
        n_jobs=1,
    )
    assert snap.count == 0


def test_max_halos_downsamples(mini_tree_path):
    snap = load_halo_snapshot(
        tree_dir=mini_tree_path.parent,
        tree_name="trees_063",
        snap_num=63,
        first_file=0,
        last_file=0,
        mass_cut=0.0,
        max_halos=5,
        n_jobs=1,
    )
    assert snap.count <= 5

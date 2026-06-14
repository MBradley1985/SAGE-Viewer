import numpy as np
import pytest

from sage_viewer.io.snapshot_table import SnapshotTable


def test_count(mini_a_list_path):
    t = SnapshotTable(mini_a_list_path)
    assert t.count == 64


def test_last_snap_is_z0(mini_a_list_path):
    t = SnapshotTable(mini_a_list_path)
    assert t.snap_to_a(63) == pytest.approx(1.0)
    assert t.snap_to_z(63) == pytest.approx(0.0, abs=1e-6)


def test_z_to_snap_roundtrip(mini_a_list_path):
    t = SnapshotTable(mini_a_list_path)
    snap = t.z_to_snap(0.0)
    assert snap == 63


def test_label_format(mini_a_list_path):
    t = SnapshotTable(mini_a_list_path)
    label = t.label(63)
    assert "Snap 63" in label
    assert "z = 0.00" in label

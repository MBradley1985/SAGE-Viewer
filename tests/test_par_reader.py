from sage_viewer.io.par_reader import parse_par


def test_parse_par_basic(mini_par_path):
    cfg = parse_par(mini_par_path)
    assert cfg.hubble_h == pytest.approx(0.73)
    assert cfg.box_size == pytest.approx(62.5)
    assert cfg.omega == pytest.approx(0.25)
    assert cfg.first_file == 0
    assert cfg.last_file == 0
    assert cfg.tree_name == "trees_063"


def test_parse_par_paths_are_absolute(mini_par_path):
    cfg = parse_par(mini_par_path)
    assert cfg.output_dir.is_absolute()
    assert cfg.snap_list_path.is_absolute()
    assert cfg.simulation_dir.is_absolute()


import pytest

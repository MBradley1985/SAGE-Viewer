# Contributing to SAGE-Viewer

## Development setup

```bash
git clone https://github.com/MBradley1985/SAGE-Viewer
cd SAGE-Viewer
pip install -e ".[dev]"
pre-commit install
```

## Running tests

```bash
pytest tests/ -v
```

Tests use synthetic fixtures in `tests/data/` — no real simulation data required.

## Code style

- Line length: 79 characters
- Formatter: `black`
- Linter: `ruff`
- Comments only where the *why* is non-obvious

Run checks:


```bash
ruff check sage_viewer tests
black --check sage_viewer tests
```

## Adding a new simulation

1. Add a reader in `sage_viewer/io/` if the tree format differs from lhalo_binary
2. Add the snapshot list file (scale factors, one per line) to `sage_viewer/io/snapshot_table.py`
3. Test with a `.par` file from the new simulation

## Adding a new colormap mode

1. Add scalar computation in `sage_viewer/utils/colormap.py`
2. Register the mode in `sage_viewer/scene/halo_layer.py` and `galaxy_layer.py`
3. Add the colormap dropdown option in `sage_viewer/ui/layer_panel.py`

## Submitting changes

Open a pull request against `main`. CI must pass before merging.

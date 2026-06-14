from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SimConfig:
    """Parsed representation of a SAGE .par file."""

    par_path: Path

    # Output
    output_dir: Path = Path("output")
    file_name_galaxies: str = "model"
    first_file: int = 0
    last_file: int = 7
    output_format: str = "sage_hdf5"

    # Trees
    tree_name: str = "trees_063"
    tree_type: str = "lhalo_binary"
    simulation_dir: Path = Path("input/millennium/trees")
    snap_list_path: Path = Path("input/millennium/trees/millennium.a_list")
    last_snapshot_nr: int = 63
    num_sim_tree_files: int = 8

    # Cosmology / box
    omega: float = 0.25
    omega_lambda: float = 0.75
    hubble_h: float = 0.73
    box_size: float = 62.5
    part_mass: float = 0.086

    # Extra raw keys (anything not explicitly parsed)
    extra: dict = field(default_factory=dict)

    @property
    def hdf5_path(self) -> Path:
        return self.output_dir / f"{self.file_name_galaxies}_0.hdf5"

    @property
    def tree_dir(self) -> Path:
        return self.simulation_dir

    @property
    def n_output_files(self) -> int:
        return self.last_file - self.first_file + 1

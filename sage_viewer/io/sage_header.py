from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np


def read_sage_header(hdf5_path: str | Path) -> dict:
    """Read cosmology and simulation metadata from a SAGE HDF5 file.

    Returns a dict with these keys (all best-effort — keys may be absent if
    the file uses an older SAGE format):

        hubble_h     : H/100
        omega_m      : matter density parameter
        omega_l      : cosmological constant density parameter
        box_size     : Mpc/h
        n_snapshots  : number of snapshots
        scale_factors: np.ndarray of scale factors (one per snapshot, ascending
                       in cosmic time order)
        redshifts    : np.ndarray of redshifts
        snap_list    : np.ndarray of snapshot numbers (matches the scale_factors
                       ordering)
        tree_dir     : path to halo-tree directory (raw string from file)
        tree_name    : tree file basename
        first_file   : first tree file index
        last_file    : last tree file index
        h2_radial    : True if H₂ radial integration was enabled
    """
    out: dict = {}
    try:
        with h5py.File(str(hdf5_path), "r") as f:
            sim = f.get("Header/Simulation", None)
            run = f.get("Header/Runtime",    None)

            def _g(grp, k, default=None):
                if grp is None or k not in grp.attrs:
                    return default
                v = grp.attrs[k]
                if isinstance(v, bytes):
                    return v.decode("utf-8", errors="replace")
                return v

            out["hubble_h"]    = float(_g(sim, "hubble_h",    0.73))
            out["omega_m"]     = float(_g(sim, "omega_matter", 0.25))
            out["omega_l"]     = float(_g(sim, "omega_lambda", 0.75))
            out["box_size"]    = float(_g(sim, "box_size",     62.5))
            out["n_snapshots"] = int(_g(sim, "SimMaxSnaps",
                                        _g(sim, "LastSnapshotNr", 64) + 1))
            out["tree_dir"]    = _g(sim, "SimulationDir", "")
            out["tree_name"]   = _g(sim, "TreeName",
                                    _g(sim, "FileWithSnapList", ""))
            out["first_file"]  = int(_g(run, "FirstFile", 0))
            out["last_file"]   = int(_g(run, "LastFile",
                                        int(_g(sim, "num_simulation_tree_files", 1)) - 1))
            out["h2_radial"]   = bool(int(_g(run, "H2RadialIntegrationOn", 0)))

            # Per-snapshot tables (preferred — bypasses the .a_list file)
            if "Header/snapshot_redshifts" in f:
                z = np.asarray(f["Header/snapshot_redshifts"])
                # Convert to scale factor and sort ascending (oldest → newest)
                a = 1.0 / (1.0 + z)
                order = np.argsort(a)
                a_sorted = a[order]
                z_sorted = z[order]
                snap_sorted = (
                    np.asarray(f["Header/output_snapshots"])[order]
                    if "Header/output_snapshots" in f
                    else np.arange(len(a_sorted))
                )
                out["scale_factors"] = a_sorted.astype(np.float64)
                out["redshifts"]     = z_sorted.astype(np.float64)
                out["snap_list"]     = snap_sorted.astype(np.int32)
    except Exception:
        pass
    return out

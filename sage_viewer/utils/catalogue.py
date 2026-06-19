from __future__ import annotations

import datetime
from pathlib import Path

import h5py
import numpy as np

# Mass fields stored as 10^10 Msun/h in SAGE HDF5 — converted to Msun on export
_MASS_FIELDS = {
    "StellarMass", "BulgeMass", "ColdGas", "Mvir", "CentralMvir",
    "BlackHoleMass", "IntraClusterStars", "H2gas", "CGMgas", "HotGas",
}
_POS_FIELDS = {"Posx", "Posy", "Posz"}
_SFR_FIELDS = {"SfrDisk", "SfrBulge"}
# 2D arrays — included in HDF5 output only
_2D_KEYS = {"SFHMassDisk", "SFHMassBulge"}


def _read_snap_fields(
    hdf5_path: Path,
    snap_num: int,
    sage_indices: np.ndarray,
    hubble_h: float,
) -> tuple[dict[str, np.ndarray], dict[str, str]]:
    """Read ALL dataset fields from a SAGE HDF5 snapshot group for the given rows.

    Returns (data, units) where mass fields are already converted to Msun.
    2D arrays (SFH) are included with key preserved for HDF5-only formats.
    """
    data: dict[str, np.ndarray] = {}
    units: dict[str, str] = {}
    f_mass = 1.0e10 / max(float(hubble_h), 1e-6)

    with h5py.File(str(hdf5_path), "r") as hf:
        grp = hf[f"Snap_{snap_num}"]
        # Determine N from Posx (always present)
        n_total = len(grp["Posx"]) if "Posx" in grp else None

        for key in sorted(grp.keys()):
            raw = np.asarray(grp[key])

            if raw.ndim == 1:
                if n_total is not None and len(raw) != n_total:
                    continue
                arr = raw[sage_indices]
                if key in _MASS_FIELDS:
                    arr = (arr.astype(np.float64) * f_mass).astype(np.float32)
                    units[key] = "Msun"
                elif key in _POS_FIELDS:
                    units[key] = "Mpc/h"
                elif key in _SFR_FIELDS:
                    units[key] = "Msun/yr"
                else:
                    units[key] = ""
                data[key] = arr

            elif raw.ndim == 2 and key in _2D_KEYS:
                if n_total is None or raw.shape[0] == n_total:
                    data[key] = raw[sage_indices]
                    units[key] = "10^10 Msun/h"

    # Derived: total SFR and sSFR
    if "SfrDisk" in data and "SfrBulge" in data:
        data["SFR"] = (data["SfrDisk"] + data["SfrBulge"]).astype(np.float32)
        units["SFR"] = "Msun/yr"
    if "SFR" in data and "StellarMass" in data:
        with np.errstate(divide="ignore", invalid="ignore"):
            data["sSFR"] = np.where(
                data["StellarMass"] > 0,
                data["SFR"] / data["StellarMass"],
                0.0,
            ).astype(np.float32)
        units["sSFR"] = "yr^-1"

    return data, units


def _scalar_only(data: dict) -> dict[str, np.ndarray]:
    return {k: v for k, v in data.items() if np.ndim(v) == 1}


def write_catalogue(
    hdf5_path: Path,
    snap_num: int,
    snap_label: str,
    sage_indices: np.ndarray,
    out_path: Path,
    fmt: str,
    hubble_h: float = 0.73,
    scope_label: str = "",
) -> str:
    """Export galaxy rows to *out_path* in format *fmt* (csv/hdf5/fits/txt).

    Returns the resolved output path string.
    """
    sage_indices = np.asarray(sage_indices, dtype=np.int64)
    if len(sage_indices) == 0:
        raise ValueError("No galaxies match the selected scope.")

    data, units = _read_snap_fields(hdf5_path, snap_num, sage_indices, hubble_h)

    meta = {
        "sage_viewer": "SAGE-Viewer Galaxy Catalogue",
        "scope": scope_label,
        "snapshot": snap_num,
        "snap_label": snap_label,
        "n_galaxies": len(sage_indices),
        "hubble_h": hubble_h,
        "exported": datetime.datetime.now().isoformat(timespec="seconds"),
    }

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "csv":
        _write_csv(data, units, meta, out_path)
    elif fmt == "hdf5":
        _write_hdf5(data, units, meta, out_path)
    elif fmt == "fits":
        _write_fits(data, units, meta, out_path)
    elif fmt == "txt":
        _write_txt(data, units, meta, out_path)
    else:
        raise ValueError(f"Unknown format: {fmt!r}")

    return str(out_path)


# ── Format writers ────────────────────────────────────────────────────────────

def _write_csv(data: dict, units: dict, meta: dict, out_path: Path) -> None:
    import csv
    scalar = _scalar_only(data)
    with open(out_path, "w", newline="") as f:
        for k, v in meta.items():
            f.write(f"# {k}: {v}\n")
        unit_notes = ", ".join(
            f"{k}={u}" for k, u in units.items() if u and k in scalar
        )
        if unit_notes:
            f.write(f"# units: {unit_notes}\n")
        writer = csv.writer(f)
        writer.writerow(list(scalar.keys()))
        n = len(next(iter(scalar.values())))
        for i in range(n):
            writer.writerow([
                int(v[i]) if v.dtype.kind in ("i", "u") else float(v[i])
                for v in scalar.values()
            ])


def _write_txt(data: dict, units: dict, meta: dict, out_path: Path) -> None:
    scalar = _scalar_only(data)
    cols = list(scalar.keys())
    arrs = [scalar[c] for c in cols]
    with open(out_path, "w") as f:
        for k, v in meta.items():
            f.write(f"# {k}: {v}\n")
        unit_notes = "  ".join(
            f"{c}[{units.get(c, '')}]" for c in cols
        )
        f.write(f"# columns: {unit_notes}\n")
        np.savetxt(
            f,
            np.column_stack([a.astype(np.float64) for a in arrs]),
            fmt="%.6e",
            header="  ".join(cols),
            comments="# ",
        )


def _write_hdf5(data: dict, units: dict, meta: dict, out_path: Path) -> None:
    with h5py.File(str(out_path), "w") as hf:
        mg = hf.create_group("Metadata")
        for k, v in meta.items():
            mg.attrs[k] = str(v)
        gg = hf.create_group("Galaxies")
        for key, arr in data.items():
            ds = gg.create_dataset(key, data=arr, compression="gzip",
                                   compression_opts=4)
            u = units.get(key, "")
            if u:
                ds.attrs["units"] = u


def _write_fits(data: dict, units: dict, meta: dict, out_path: Path) -> None:
    from astropy.io import fits
    from astropy.table import Table

    scalar = _scalar_only(data)
    tbl = Table()
    for col, arr in scalar.items():
        tbl[col] = arr
        u = units.get(col, "")
        if u:
            tbl[col].unit = u

    hdr = fits.Header()
    for k, v in meta.items():
        fits_key = k.upper().replace(" ", "_")[:8]
        hdr[fits_key] = str(v)[:72]

    hdu = fits.BinTableHDU(tbl, header=hdr, name="GALAXIES")
    fits.HDUList([fits.PrimaryHDU(), hdu]).writeto(str(out_path), overwrite=True)

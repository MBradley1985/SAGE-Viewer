# Galaxies

## Source

Galaxy data is read from the SAGE HDF5 output file (`model_0.hdf5`). The file is structured as one HDF5 group per snapshot: `Snap_0`, `Snap_1`, …, `Snap_63`.

## Fields loaded by SAGE-Viewer

| HDF5 field | Type | Raw units | Viewer units |
|---|---|---|---|
| `Posx`, `Posy`, `Posz` | float32 | Mpc/h | Mpc/h |
| `StellarMass` | float32 | 10¹⁰ Msun/h | Msun (×1e10/h) |
| `Mvir` | float32 | 10¹⁰ Msun/h | kept raw for masking |
| `SfrDisk` + `SfrBulge` | float32 | Msun/yr | summed → total SFR |
| `Type` | int32 | — | 0=central, 1+=satellite |

Derived quantity: `sSFR = (SfrDisk + SfrBulge) / StellarMass` in yr⁻¹.

## Galaxy types

| Type value | Meaning |
|---|---|
| 0 | Central galaxy — sits at the potential minimum of its FOF group |
| 1 | Satellite — orbiting within another halo |
| 2+ | Orphan satellite — lost its subhalo, tracked by SAGE26 merger timer |

In `type` colour mode, centrals are shown in Blues and satellites in Reds.

## Mass floor

The default stellar mass floor is `1e8 Msun`. Galaxies with `Mvir = 0` are also excluded (they have no associated halo). Adjust with `--min-stellar-mass`.

## SAGE26 output format reference

The full 84-field SAGE HDF5 schema is documented in the [SAGE26 output reference](https://github.com/MBradley1985/SAGE26). SAGE-Viewer uses only the 8 fields above; all others are available in the file for custom scripting via the Python API.

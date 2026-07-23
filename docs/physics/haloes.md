# Dark Matter Haloes

## Source

Halo data is read from lhalo_binary merger tree files (`trees_063.N`). These are the same files consumed by SAGE26 at runtime.

## Fields loaded by ViSAGE

| Field | Type | Units (raw) | Units (viewer) |
|---|---|---|---|
| `Pos[3]` | float32 | Mpc/h | Mpc/h (unchanged) |
| `Mvir` | float32 | 10¹⁰ Msun/h | Msun (×1e10/h) |
| `SnapNum` | int32 | — | — |

Only `Pos` and `Mvir` are used for rendering. All other fields in the struct (`Vel`, `Spin`, `VelDisp`, `Vmax`, etc.) are read but discarded after the per-snapshot filter.

## Mass floor

The default mass floor is `1e10 Msun`. This removes very low-mass substructure that would otherwise dominate point count without contributing visible structure. Adjust with `--min-halo-mass`.

## lhalo_binary file format

Each tree file has the following binary layout:

```
int32   nforests
int32   nhalos_total
int32[nforests]  nhalos_per_forest
HaloStruct[nhalos_total]
```

`HaloStruct` is 19 fields; the full dtype is defined in `visage/io/halo_reader.py:HALO_DTYPE`.

## Parallel loading

ViSAGE reads the N tree files in parallel (joblib). For miniMillennium with 8 files and 8 CPUs, all files load simultaneously.

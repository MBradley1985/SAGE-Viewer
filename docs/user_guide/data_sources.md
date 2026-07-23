# Data Sources

## miniMillennium

- Box size: 62.5 Mpc/h
- Snapshots: 64 (z ≈ 127 → 0)
- Tree format: lhalo_binary (`trees_063.0` – `trees_063.7`)
- Scale factor file: `millennium.a_list`
- SAGE output: `model_0.hdf5` with groups `Snap_0` – `Snap_63`

Launch:

```bash
visage --par input/millennium.par
```

## microUchuu

- Box size: 96 Mpc/h
- Snapshots: 50 (z ≈ 13.9 → 0)
- Tree format: lhalo_binary (`tree_0_0_0.dat`)
- Scale factor file: `Uchuu100_scalefactor.txt`

Launch:

```bash
visage --par input/microuchuu.par
```

## How the par file is used

ViSAGE's `parse_par()` reads the `.par` file you pass to the CLI. Relative paths in the par file are resolved relative to the par file's parent directory (your SAGE26 root), so you can run `visage` from anywhere as long as you give it the absolute or correctly relative path to the par file.

## Data that is never committed

Tree files, HDF5 outputs, and scale-factor lists are all listed in `.gitignore`. ViSAGE only reads them at runtime.

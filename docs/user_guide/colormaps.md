# Colormaps

## Colour modes

Both the halo and galaxy layers support four colour modes, selectable from the layer panel dropdowns.

### `mass`

| Layer | Scalar | Colourmap | Range |
|---|---|---|---|
| Haloes | log₁₀(Mvir / Msun) | Blues | 10 – 15 |
| Galaxies | log₁₀(M★ / Msun) | plasma | 8 – 12.5 |

### `ssfr`

| Layer | Scalar | Colourmap | Range |
|---|---|---|---|
| Haloes | log₁₀(Mvir / Msun) | coolwarm_r | 10 – 15 |
| Galaxies | log₁₀(sSFR / yr⁻¹) | coolwarm_r | -14 – -8 |

Blue = quiescent, red = star-forming.

### `density`

Both layers use a KDE-estimated local density (log-scaled) mapped to the `magma` colourmap. Bright yellow = high-density environment.

### `type`

| Layer | Scalar | Colourmap |
|---|---|---|
| Haloes | log₁₀(Mvir / Msun) | Blues |
| Central galaxies (Type=0) | log₁₀(M★ / Msun) | Blues |
| Satellite galaxies (Type>0) | log₁₀(M★ / Msun) | Reds |

## Point sizes

Point sizes scale monotonically with mass within fixed log₁₀ ranges so that the visual size distribution does not flicker between snapshots.

- Haloes: 25 – 60 px (5 size bins)
- Galaxies: ~4.25 – 10.2 px (scaled by `GALAXY_SIZE_SCALE = 0.17`)

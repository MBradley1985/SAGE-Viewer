# Quickstart

## Launch on miniMillennium

From your SAGE26 root directory:

```bash
sage-viewer --par input/millennium.par
```

Open the printed URL (default `http://localhost:8080`) in any browser.

## Launch on microUchuu

```bash
sage-viewer --par input/microuchuu.par --snap 49
```

## Common options

```bash
# Start at a specific snapshot
sage-viewer --par input/millennium.par --snap 32

# Use a specific port
sage-viewer --par input/millennium.par --port 8888

# Limit haloes per snapshot (faster on slower machines)
sage-viewer --par input/millennium.par --max-halos 20000

# Use all CPUs for loading
sage-viewer --par input/millennium.par --n-jobs -1
```

## First steps in the viewer

1. The scene loads at the requested snapshot (default: z=0, snap 63).
2. Use the **timeline slider** in the toolbar to jump to any snapshot.
3. Press **▶ Play** to animate through cosmic time.
4. Toggle **Dark Matter Haloes** or **Galaxies** off in the **Structure** tab (right panel).
5. Change **Colour by** to `ssfr` to highlight star-forming galaxies.
6. In the **Target** tab, enter a halo index and press **Go** to fly there.
7. **Double-click** any point in the scene to select the nearest galaxy and see its properties in the info bar.

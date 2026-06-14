# Interface

SAGE-Viewer's browser UI has four regions:

```
┌─────────────────────────────────────────────────────────┐
│  Toolbar: ▶ ⏸ ⏹  ──snapshot slider──  Snap 63 | z=0.00 │
├──────────┬──────────────────────────────┬───────────────┤
│  Layer   │                              │  Navigation   │
│  Panel   │     PyVista render window    │  Panel        │
│  (left)  │                              │  (right)      │
├──────────┴──────────────────────────────┴───────────────┤
│  Info bar: click-to-inspect output                      │
└─────────────────────────────────────────────────────────┘
```

## Toolbar

| Control | Action |
|---|---|
| ▶ Play | Begin animating through snapshots at selected speed |
| ⏸ Pause | Freeze on current snapshot |
| ⏹ Stop | Stop and jump back to z=0 (last snapshot) |
| Snapshot slider | Jump directly to any snapshot |
| Snapshot chip | Shows `Snap N | z = X.XX | a = X.XXXX` |
| Speed selector | 1× / 2× / 5× playback speed |

## Layer panel (left)

| Control | Action |
|---|---|
| Haloes toggle | Show or hide the DM halo point cloud |
| Haloes opacity | Adjust halo transparency (0–0.3 range) |
| Haloes colour by | Switch between mass / sSFR / density / type modes |
| Galaxies toggle | Show or hide the galaxy point cloud |
| Galaxies opacity | Adjust galaxy transparency (0–1 range) |
| Galaxies colour by | Switch between mass / sSFR / density / type modes |

## Navigation panel (right)

See [Navigation](navigation.md) for full details.

## Info bar (bottom)

Displays position, nearest halo Mvir, and nearest galaxy stellar mass / sSFR / type when you click a point in the render window.

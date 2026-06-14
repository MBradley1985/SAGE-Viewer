# SAGE-Viewer

An interactive 3D visualization package for [SAGE26](https://github.com/MBradley1985/SAGE26) and [SAGE-PSO](https://github.com/MBradley1985/SAGE-PSO) semi-analytic galaxy formation outputs.

Renders dark matter haloes and SAGE galaxies together in a browser-based interactive viewer powered by [PyVista](https://pyvista.org) and [Trame](https://kitware.github.io/trame/).

## Features

- Simultaneous halo (lhalo_binary trees) and galaxy (SAGE HDF5) point cloud rendering
- Toggle halo/galaxy layers independently with live opacity and colormap controls
- Snapshot timeline with play/pause/stop and adjustable speed
- Free camera navigation plus fly-to by halo ID, galaxy index, or coordinates
- Zoom to arbitrary radius or sub-box
- Point-pick info panel showing halo mass and galaxy stellar mass/sSFR/type
- Multi-CPU snapshot prefetching for smooth playback
- Mass cuts for interactive performance at any resolution

## Supported simulations

| Simulation | Box size | Snapshots | Tree format |
|---|---|---|---|
| miniMillennium | 62.5 Mpc/h | 64 | lhalo_binary |
| microUchuu | 96 Mpc/h | 50 | lhalo_binary |

## Quick start

```bash
pip install sage-viewer
sage-viewer --par /path/to/millennium.par
```

Open the printed URL in any browser. To launch on a remote cluster and view locally, use SSH port-forwarding:

```bash
# On the cluster
sage-viewer --par millennium.par --port 8080

# In a local terminal
ssh -L 8080:localhost:8080 user@cluster
# Then open http://localhost:8080 in your browser
```

## Installation

```bash
# From PyPI
pip install sage-viewer

# From source
git clone https://github.com/MBradley1985/SAGE-Viewer
cd SAGE-Viewer
pip install -e ".[dev]"
```

Requires Python >= 3.10.

## Documentation

Full documentation at [mbradley1985.github.io/SAGE-Viewer](https://mbradley1985.github.io/SAGE-Viewer).

## Integration with SAGE26

SAGE-Viewer reads SAGE output directories and `.par` files directly. No conversion step needed:

```bash
# From your SAGE26 root
sage-viewer --par input/millennium.par --snap 63
```

## Colormap modes

| Mode | Haloes | Galaxies |
|---|---|---|
| `mass` | Halo Mvir | Stellar mass |
| `ssfr` | Halo mass | Specific SFR |
| `density` | Local density | Local density |
| `type` | Halo mass | Central (Blues) / Satellite (Reds) |

## License

MIT — see [LICENSE](LICENSE).

## Citation

If you use SAGE-Viewer in published work, please cite:

```bibtex
@software{bradley_sage_viewer_2026,
  author = {Bradley, Michael},
  title  = {{SAGE-Viewer}: Interactive 3D Visualization for SAGE Galaxy Formation Outputs},
  year   = {2026},
  url    = {https://github.com/MBradley1985/SAGE-Viewer}
}
```

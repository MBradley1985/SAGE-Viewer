# SAGE-Viewer

**Interactive 3D visualization for SAGE semi-analytic galaxy formation outputs.**

SAGE-Viewer renders dark matter haloes and SAGE galaxies together in a browser-based interactive viewer, powered by [PyVista](https://pyvista.org) and [Trame](https://kitware.github.io/trame/). It is designed to work directly with the output of [SAGE26](https://github.com/MBradley1985/SAGE26) and [SAGE-PSO](https://github.com/MBradley1985/SAGE-PSO).

---

## Key features

| Feature | Description |
|---|---|
| Dual layers | Haloes and galaxies rendered simultaneously as point clouds |
| Timeline | Scrub, play, pause, and step through all 64 Millennium snapshots |
| Layer controls | Toggle visibility, adjust opacity, and change colourmap mode live |
| Navigation | Fly to any halo index, galaxy index, or coordinate; zoom to sub-box |
| Point picking | Click any point to inspect its halo mass or galaxy properties |
| Multi-CPU loading | Snapshot prefetch pool keeps playback smooth |
| Remote use | Trame web server — run on a cluster, view in any browser |

---

## Quick example

```bash
pip install sage-viewer
sage-viewer --par input/millennium.par
# → Open http://localhost:8080
```

---

## Supported simulations

- **miniMillennium** — 62.5 Mpc/h box, 64 snapshots, lhalo_binary trees
- **microUchuu** — 96 Mpc/h box, 50 snapshots, lhalo_binary trees

---

## Documentation sections

- **[Getting Started](getting_started/installation.md)** — install and launch
- **[User Guide](user_guide/interface.md)** — UI reference and navigation controls
- **[Physics Reference](physics/haloes.md)** — field definitions and units
- **[API Reference](api/index.md)** — Python API for scripting and integration

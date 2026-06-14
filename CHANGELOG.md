# Changelog

All notable changes to SAGE-Viewer are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Initial package structure with PyVista + Trame stack
- `io/` layer: lhalo_binary halo reader, SAGE HDF5 galaxy reader, snapshot table, par file parser
- `scene/` layer: Scene, HaloLayer, GalaxyLayer, CameraController
- `parallel/` loader with joblib prefetch pool and LRU snapshot cache
- `ui/` Trame frontend: toolbar, layer panel, navigation panel, info panel
- `sage-viewer` CLI entry point
- Mass, sSFR, density, and type colormap modes
- Fly-to halo ID, galaxy index, coordinates, and zoom-to-box navigation
- miniMillennium and microUchuu support
- MkDocs Material documentation site
- GitHub Actions CI (lint + tests) and docs deployment

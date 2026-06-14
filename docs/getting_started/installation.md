# Installation

## Requirements

- Python >= 3.10
- A SAGE26 or SAGE-PSO output directory (HDF5 format) and lhalo_binary merger trees

## From PyPI

```bash
pip install sage-viewer
```

## From source

```bash
git clone https://github.com/MBradley1985/SAGE-Viewer
cd SAGE-Viewer
pip install -e ".[dev]"
```

## Verifying the install

```bash
sage-viewer --version
```

## Remote / HPC installation

Install into a conda or virtualenv on the cluster node where the simulation data lives:

```bash
conda create -n sage-viewer python=3.11
conda activate sage-viewer
pip install sage-viewer
```

Then use SSH port-forwarding to view in your local browser:

```bash
# On the cluster
sage-viewer --par /path/to/millennium.par --port 8080

# Locally
ssh -L 8080:localhost:8080 user@cluster
# Open http://localhost:8080
```

## Dependencies

| Package | Purpose |
|---|---|
| pyvista | 3D rendering (VTK wrapper) |
| trame | Web UI server |
| trame-vtk | Streams PyVista render window to browser |
| trame-vuetify | Vuetify 3 UI components |
| h5py | Reads SAGE HDF5 galaxy output |
| numpy | Array operations |
| scipy | KDE density computation, KDTree navigation |
| joblib | Parallel halo file loading |

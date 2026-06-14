from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sage_viewer._version import __version__


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sage-viewer",
        description="Interactive 3D viewer for SAGE galaxy formation outputs.",
    )
    p.add_argument(
        "--par",
        required=True,
        metavar="FILE",
        help="Path to SAGE .par file (e.g. input/millennium.par)",
    )
    p.add_argument(
        "--snap",
        type=int,
        default=None,
        metavar="N",
        help="Initial snapshot number (default: last snapshot)",
    )
    p.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for the Trame web server (default: 8080)",
    )
    p.add_argument(
        "--n-jobs",
        type=int,
        default=max(1, (os.cpu_count() or 2) - 1),
        metavar="N",
        help="Worker threads for parallel halo loading (default: CPUs-1)",
    )
    p.add_argument(
        "--min-halo-mass",
        type=float,
        default=1.0e10,
        metavar="MSUN",
        help="Minimum halo mass in Msun (default: 1e10)",
    )
    p.add_argument(
        "--min-stellar-mass",
        type=float,
        default=1.0e8,
        metavar="MSUN",
        help="Minimum stellar mass in Msun (default: 1e8)",
    )
    p.add_argument(
        "--max-halos",
        type=int,
        default=100_000,
        metavar="N",
        help="Downsample ceiling for haloes per snapshot (default: 100000)",
    )
    p.add_argument(
        "--max-galaxies",
        type=int,
        default=100_000,
        metavar="N",
        help="Downsample ceiling for galaxies per snapshot (default: 100000)",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"sage-viewer {__version__}",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    par_path = Path(args.par)
    if not par_path.exists():
        print(f"Error: par file not found: {par_path}", file=sys.stderr)
        sys.exit(1)

    print(f"\nSAGE-Viewer {__version__}")
    print(f"Par file : {par_path.resolve()}")
    print(f"Workers  : {args.n_jobs}")
    print("\n[1/4] Parsing par file and snapshot table...")

    # Import here so CLI --help/--version are fast
    from sage_viewer.app import create_app

    print("[2/4] Loading initial snapshot (haloes + galaxies)...")
    server, scene = create_app(
        par_path=par_path,
        initial_snap=args.snap,
        n_jobs=args.n_jobs,
        min_halo_mass=args.min_halo_mass,
        min_stellar_mass=args.min_stellar_mass,
        max_halos=args.max_halos,
        max_galaxies=args.max_galaxies,
    )
    print("[3/4] Building scene and Trame UI...")

    print(f"Snapshot : {scene.snap_label}")
    print(f"[4/4] Starting server on port {args.port}...")
    print(f"\n  --> Open http://localhost:{args.port} in your browser\n")

    server.start(port=args.port, open_browser=False)


if __name__ == "__main__":
    main()

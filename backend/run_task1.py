from __future__ import annotations

import argparse
import json

from physics import Task1Config
from physics import run_task1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Task 1 Bott-index data from a finite real-space topological-insulator Hamiltonian."
    )
    parser.add_argument("--nx", type=int, default=Task1Config.nx)
    parser.add_argument("--ny", type=int, default=Task1Config.ny)
    parser.add_argument("--mass", type=float, default=Task1Config.mass)
    parser.add_argument("--disorder", type=float, default=Task1Config.disorder)
    parser.add_argument("--disorder-seed", type=int, default=Task1Config.disorder_seed)
    parser.add_argument("--fermi", type=float, default=Task1Config.fermi)
    parser.add_argument("--periodic-x", type=int, choices=(0, 1), default=int(Task1Config.periodic_x))
    parser.add_argument("--periodic-y", type=int, choices=(0, 1), default=int(Task1Config.periodic_y))
    parser.add_argument("--cache-dir", default=Task1Config.cache_dir)
    parser.add_argument("--export-path", default=Task1Config.export_path)
    parser.add_argument("--physics-log-dir", default=Task1Config.physics_log_dir)
    parser.add_argument("--performance-log-dir", default=Task1Config.performance_log_dir)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = Task1Config(
        nx=args.nx,
        ny=args.ny,
        mass=args.mass,
        disorder=args.disorder,
        disorder_seed=args.disorder_seed,
        fermi=args.fermi,
        periodic_x=bool(args.periodic_x),
        periodic_y=bool(args.periodic_y),
        cache_dir=args.cache_dir,
        export_path=args.export_path,
        physics_log_dir=args.physics_log_dir,
        performance_log_dir=args.performance_log_dir,
    ).validated()

    payload = run_task1(config)
    summary = {
        "export_path": payload["metadata"]["export_path"],
        "bott_index": payload["bott_index"],
        "occupied_dimension": payload["metadata"]["occupied_dimension"],
        "validation": payload["metadata"]["validation"],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

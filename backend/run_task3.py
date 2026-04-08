from __future__ import annotations

import argparse
import json
from datetime import datetime

from physics.config import Task1Config
from physics.export import write_json
from physics.localizer import run_task3_physics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Task 3 spectral-localizer heatmap data with open-boundary edge-state density."
    )
    parser.add_argument("--nx", type=int, default=8)
    parser.add_argument("--ny", type=int, default=8)
    parser.add_argument("--mass", type=float, default=-1.0)
    parser.add_argument("--disorder", type=float, default=0.8)
    parser.add_argument("--disorder-seed", type=int, default=7)
    parser.add_argument("--fermi", type=float, default=0.0)
    parser.add_argument("--grid-points-x", type=int, default=13)
    parser.add_argument("--grid-points-y", type=int, default=13)
    parser.add_argument("--kappa", type=float, default=0.35)
    parser.add_argument("--window-count", type=int, default=6)
    parser.add_argument("--export-path", default="data/exports/task3.json")
    parser.add_argument("--physics-log-dir", default="logs/physics_checks")
    parser.add_argument("--performance-log-dir", default="logs/performance")
    return parser.parse_args()


def log_json(directory: str, stem: str, payload: dict) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config = Task1Config()
    path = config.resolve_path(directory)
    path.mkdir(parents=True, exist_ok=True)
    target = path / f"{stem}_{timestamp}.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(target)


def main() -> None:
    args = parse_args()
    result = run_task3_physics(
        nx=args.nx,
        ny=args.ny,
        mass=args.mass,
        disorder=args.disorder,
        disorder_seed=args.disorder_seed,
        fermi=args.fermi,
        grid_points_x=args.grid_points_x,
        grid_points_y=args.grid_points_y,
        kappa=args.kappa,
        window_count=args.window_count,
    )
    config = result["config"]

    payload = {
        "lattice_size": int(config.lattice_size),
        "hamiltonian_shape": [int(result["hamiltonian"].shape[0]), int(result["hamiltonian"].shape[1])],
        "eigenvalues": [float(value) for value in result["eigenvalues"].tolist()],
        "U_V_matrices": {
            "U": [],
            "V": [],
        },
        "localizer_gap_grid": result["localizer"]["gap_grid"],
        "bott_index": int(result["bott_index"]),
        "winding_phases": [float(value) for value in result["winding_phases"].tolist()],
        "parameters": {
            "mass": float(config.mass),
            "disorder": float(config.disorder),
            "fermi": float(config.fermi),
        },
        "metadata": {
            "task": "task3",
            "boundary_conditions": {
                "periodic_x": False,
                "periodic_y": False,
            },
            "grid_axes": {
                "x_axis": result["localizer"]["x_axis"],
                "y_axis": result["localizer"]["y_axis"],
            },
            "spectral_localizer": {
                "kappa": float(args.kappa),
                "minimum_gap": float(result["localizer"]["minimum_gap"]),
                "maximum_gap": float(result["localizer"]["maximum_gap"]),
            },
            "edge_density": result["edge_density"],
            "solver": result["solver"],
            "validation": result["validation"],
            "performance": result["performance"],
            "disorder_realization": [float(value) for value in result["disorder_values"].tolist()],
        },
    }

    physics_log = log_json(args.physics_log_dir, "task3_validation", payload["metadata"]["validation"])
    performance_log = log_json(args.performance_log_dir, "task3_performance", payload["metadata"]["performance"])
    payload["metadata"]["log_files"] = {
      "physics": physics_log,
      "performance": performance_log,
    }

    export_path = str(config.resolve_path(args.export_path))
    write_json(export_path, payload)
    payload["metadata"]["export_path"] = export_path
    write_json(export_path, payload)

    summary = {
        "export_path": export_path,
        "bott_index": payload["bott_index"],
        "minimum_gap": payload["metadata"]["spectral_localizer"]["minimum_gap"],
        "edge_weight": payload["metadata"]["edge_density"]["edge_weight"],
        "validation": payload["metadata"]["validation"],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
from datetime import datetime

from physics.clifford_spectrum import run_bonus_clifford_spectrum
from physics.config import Task1Config
from physics.export import matrix_to_serializable
from physics.export import write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Clifford-spectrum point cloud from near-zero spectral-localizer regions."
    )
    parser.add_argument("--nx", type=int, default=8)
    parser.add_argument("--ny", type=int, default=8)
    parser.add_argument("--mass", type=float, default=-1.0)
    parser.add_argument("--disorder", type=float, default=0.8)
    parser.add_argument("--disorder-seed", type=int, default=7)
    parser.add_argument("--fermi", type=float, default=0.0)
    parser.add_argument("--x-points", type=int, default=10)
    parser.add_argument("--y-points", type=int, default=10)
    parser.add_argument("--energy-min", type=float, default=-1.4)
    parser.add_argument("--energy-max", type=float, default=1.4)
    parser.add_argument("--energy-points", type=int, default=13)
    parser.add_argument("--kappa", type=float, default=0.45)
    parser.add_argument("--export-path", default="data/exports/bonus_task.json")
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
    result = run_bonus_clifford_spectrum(
        nx=args.nx,
        ny=args.ny,
        mass=args.mass,
        disorder=args.disorder,
        disorder_seed=args.disorder_seed,
        fermi=args.fermi,
        x_points=args.x_points,
        y_points=args.y_points,
        energy_min=args.energy_min,
        energy_max=args.energy_max,
        energy_points=args.energy_points,
        kappa=args.kappa,
    )

    config = result["config"]
    payload = {
        "lattice_size": int(config.lattice_size),
        "hamiltonian_shape": [int(config.hilbert_dim), int(config.hilbert_dim)],
        "eigenvalues": [float(value) for value in result["eigenvalues"].tolist()],
        "U_V_matrices": {
            "U": matrix_to_serializable(result["u_matrix"], config.zero_tolerance),
            "V": matrix_to_serializable(result["v_matrix"], config.zero_tolerance),
        },
        "localizer_gap_grid": result["scalar_field"]["representative_slice"],
        "bott_index": int(result["bott_index"]),
        "winding_phases": [float(value) for value in result["winding_phases"].tolist()],
        "parameters": {
            "mass": float(config.mass),
            "disorder": float(config.disorder),
            "fermi": float(config.fermi),
        },
        "metadata": {
            "view": "clifford_spectrum_point_cloud",
            "boundary_conditions": {
                "periodic_x": False,
                "periodic_y": False,
            },
            "scalar_field": result["scalar_field"],
            "point_cloud": result["point_cloud"],
            "solver": result["solver"],
            "validation": result["validation"],
            "performance": result["performance"],
            "disorder_realization": [float(value) for value in result["disorder_realization"]],
            "kappa": float(args.kappa),
        },
    }

    physics_log = log_json(args.physics_log_dir, "bonus_validation", payload["metadata"]["validation"])
    performance_log = log_json(args.performance_log_dir, "bonus_performance", payload["metadata"]["performance"])
    payload["metadata"]["log_files"] = {
        "physics": physics_log,
        "performance": performance_log,
    }

    export_path = str(config.resolve_path(args.export_path))
    payload["metadata"]["export_path"] = export_path
    write_json(export_path, payload)

    default_level = payload["metadata"]["point_cloud"]["threshold_levels"][payload["metadata"]["point_cloud"]["default_index"]]
    summary = {
        "export_path": export_path,
        "bott_index": payload["bott_index"],
        "default_percentile": default_level["percentile"],
        "default_point_count": default_level["point_count"],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

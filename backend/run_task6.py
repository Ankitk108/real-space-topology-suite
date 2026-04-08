from __future__ import annotations

import argparse
import json
from datetime import datetime

from physics.config import Task1Config
from physics.export import matrix_to_serializable
from physics.export import write_json
from physics.phase_diagram import run_task6_phase_diagram


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Bott-index phase diagram over mass and disorder in real space."
    )
    parser.add_argument("--nx", type=int, default=10)
    parser.add_argument("--ny", type=int, default=10)
    parser.add_argument("--disorder-seed", type=int, default=7)
    parser.add_argument("--fermi", type=float, default=0.0)
    parser.add_argument("--mass-min", type=float, default=-3.2)
    parser.add_argument("--mass-max", type=float, default=3.2)
    parser.add_argument("--mass-points", type=int, default=15)
    parser.add_argument("--disorder-min", type=float, default=0.0)
    parser.add_argument("--disorder-max", type=float, default=2.4)
    parser.add_argument("--disorder-points", type=int, default=11)
    parser.add_argument("--export-path", default="data/exports/task6.json")
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
    result = run_task6_phase_diagram(
        nx=args.nx,
        ny=args.ny,
        disorder_seed=args.disorder_seed,
        fermi=args.fermi,
        mass_min=args.mass_min,
        mass_max=args.mass_max,
        mass_points=args.mass_points,
        disorder_min=args.disorder_min,
        disorder_max=args.disorder_max,
        disorder_points=args.disorder_points,
    )

    representative = result["representative"]
    config = representative["config"]

    payload = {
        "lattice_size": int(config.lattice_size),
        "hamiltonian_shape": representative["hamiltonian_shape"],
        "eigenvalues": [float(value) for value in representative["eigenvalues"].tolist()],
        "U_V_matrices": {
            "U": matrix_to_serializable(representative["u_matrix"], config.zero_tolerance),
            "V": matrix_to_serializable(representative["v_matrix"], config.zero_tolerance),
        },
        "localizer_gap_grid": result["phase_diagram"]["gap_grid"],
        "bott_index": int(representative["bott_index"]),
        "winding_phases": [float(value) for value in representative["winding_phases"].tolist()],
        "parameters": {
            "mass": float(config.mass),
            "disorder": float(config.disorder),
            "fermi": float(config.fermi),
        },
        "metadata": {
            "view": "bott_phase_diagram",
            "boundary_conditions": {
                "periodic_x": True,
                "periodic_y": True,
            },
            "phase_diagram": result["phase_diagram"],
            "solver": representative["solver"],
            "validation": representative["validation"],
            "performance": result["performance"],
            "disorder_realization": [float(value) for value in representative["disorder_realization"]],
        },
    }

    physics_log = log_json(args.physics_log_dir, "task6_validation", payload["metadata"]["validation"])
    performance_log = log_json(args.performance_log_dir, "task6_performance", payload["metadata"]["performance"])
    payload["metadata"]["log_files"] = {
        "physics": physics_log,
        "performance": performance_log,
    }

    export_path = str(config.resolve_path(args.export_path))
    payload["metadata"]["export_path"] = export_path
    write_json(export_path, payload)

    summary = {
        "export_path": export_path,
        "plateau_counts": payload["metadata"]["phase_diagram"]["plateau_counts"],
        "representative_bott_index": payload["bott_index"],
        "representative_gap": representative["spectral_gap"],
        "grid_shape": [
            len(payload["metadata"]["phase_diagram"]["disorder_axis"]),
            len(payload["metadata"]["phase_diagram"]["mass_axis"]),
        ],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

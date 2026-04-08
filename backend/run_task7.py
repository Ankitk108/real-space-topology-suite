from __future__ import annotations

import argparse
import json
from datetime import datetime

from physics.config import Task1Config
from physics.export import matrix_to_serializable
from physics.export import write_json
from physics.eigenflow import run_task7_eigenflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate eigenvalue flow data for W = UVU^daggerV^dagger across a parameter path."
    )
    parser.add_argument("--nx", type=int, default=10)
    parser.add_argument("--ny", type=int, default=10)
    parser.add_argument("--disorder-seed", type=int, default=7)
    parser.add_argument("--fermi", type=float, default=0.0)
    parser.add_argument("--mass-start", type=float, default=-3.0)
    parser.add_argument("--mass-end", type=float, default=3.0)
    parser.add_argument("--disorder-start", type=float, default=0.0)
    parser.add_argument("--disorder-end", type=float, default=1.2)
    parser.add_argument("--frame-count", type=int, default=36)
    parser.add_argument("--export-path", default="data/exports/task7.json")
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
    result = run_task7_eigenflow(
        nx=args.nx,
        ny=args.ny,
        disorder_seed=args.disorder_seed,
        fermi=args.fermi,
        mass_start=args.mass_start,
        mass_end=args.mass_end,
        disorder_start=args.disorder_start,
        disorder_end=args.disorder_end,
        frame_count=args.frame_count,
    )

    representative = result["representative"]
    config = representative["config"]

    payload = {
        "lattice_size": int(config.lattice_size),
        "hamiltonian_shape": [int(config.hilbert_dim), int(config.hilbert_dim)],
        "eigenvalues": [float(value) for value in representative["eigenvalues"].tolist()],
        "U_V_matrices": {
            "U": matrix_to_serializable(representative["u_matrix"], config.zero_tolerance),
            "V": matrix_to_serializable(representative["v_matrix"], config.zero_tolerance),
        },
        "localizer_gap_grid": [[0.0]],
        "bott_index": int(representative["bott_index"]),
        "winding_phases": [float(value) for value in representative["phases"].tolist()],
        "parameters": {
            "mass": float(config.mass),
            "disorder": float(config.disorder),
            "fermi": float(config.fermi),
        },
        "metadata": {
            "view": "eigenvalue_flow",
            "boundary_conditions": {
                "periodic_x": True,
                "periodic_y": True,
            },
            "flow": result["flow"],
            "solver": representative["solver"],
            "validation": representative["validation"],
            "performance": result["performance"],
            "disorder_realization": [float(value) for value in representative["disorder_realization"]],
        },
    }

    physics_log = log_json(args.physics_log_dir, "task7_validation", payload["metadata"]["validation"])
    performance_log = log_json(args.performance_log_dir, "task7_performance", payload["metadata"]["performance"])
    payload["metadata"]["log_files"] = {
        "physics": physics_log,
        "performance": performance_log,
    }

    export_path = str(config.resolve_path(args.export_path))
    payload["metadata"]["export_path"] = export_path
    write_json(export_path, payload)

    summary = {
        "export_path": export_path,
        "frame_count": len(payload["metadata"]["flow"]["frames"]),
        "bott_matches_winding_all_frames": payload["metadata"]["flow"]["bott_matches_winding_all_frames"],
        "representative_bott_index": payload["bott_index"],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

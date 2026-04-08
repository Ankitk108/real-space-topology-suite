from __future__ import annotations

import argparse
import json
from datetime import datetime

from physics.comparative_topology import run_task9_comparison
from physics.config import Task1Config
from physics.export import matrix_to_serializable
from physics.export import write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a comparative real-space topology view for the Haldane and disordered Chern models."
    )
    parser.add_argument("--nx", type=int, default=8)
    parser.add_argument("--ny", type=int, default=8)
    parser.add_argument("--fermi", type=float, default=0.0)
    parser.add_argument("--disorder-seed", type=int, default=7)
    parser.add_argument("--frame-count", type=int, default=21)
    parser.add_argument("--export-path", default="data/exports/task9.json")
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
    result = run_task9_comparison(
        nx=args.nx,
        ny=args.ny,
        fermi=args.fermi,
        disorder_seed=args.disorder_seed,
        frame_count=args.frame_count,
    )

    representative = result["representative"]
    parameters = representative["parameters"]
    config = Task1Config(
        nx=args.nx,
        ny=args.ny,
        mass=parameters["mass"],
        disorder=parameters["disorder"],
        disorder_seed=args.disorder_seed,
        fermi=args.fermi,
        periodic_x=False,
        periodic_y=False,
    ).validated()

    comparison_payload = {
        "haldane": {
            "name": result["comparison"]["haldane"]["name"],
            "bott_index": int(result["comparison"]["haldane"]["bott_index"]),
            "density_grid": result["comparison"]["haldane"]["density_grid"],
            "radial_profile": result["comparison"]["haldane"]["radial_profile"],
            "parameters": result["comparison"]["haldane"]["parameters"],
            "validation": result["comparison"]["haldane"]["validation"],
        },
        "chern": {
            "name": result["comparison"]["chern"]["name"],
            "bott_index": int(result["comparison"]["chern"]["bott_index"]),
            "density_grid": result["comparison"]["chern"]["density_grid"],
            "radial_profile": result["comparison"]["chern"]["radial_profile"],
            "parameters": result["comparison"]["chern"]["parameters"],
            "validation": result["comparison"]["chern"]["validation"],
        },
        "deformation_frames": result["comparison"]["deformation_frames"],
        "bott_trace": result["comparison"]["bott_trace"],
        "invariant_match": bool(result["comparison"]["invariant_match"]),
    }

    payload = {
        "lattice_size": int(config.lattice_size),
        "hamiltonian_shape": [int(config.hilbert_dim), int(config.hilbert_dim)],
        "eigenvalues": [float(value) for value in representative["eigenvalues"].tolist()],
        "U_V_matrices": {
            "U": matrix_to_serializable(representative["u_matrix"], config.zero_tolerance),
            "V": matrix_to_serializable(representative["v_matrix"], config.zero_tolerance),
        },
        "localizer_gap_grid": representative["density_grid"],
        "bott_index": int(representative["bott_index"]),
        "winding_phases": [float(value) for value in representative["winding_phases"].tolist()],
        "parameters": {
            "mass": float(parameters["mass"]),
            "disorder": float(parameters["disorder"]),
            "fermi": float(parameters["fermi"]),
        },
        "metadata": {
            "view": "comparative_topological_analysis",
            "boundary_conditions": {
                "periodic_x": False,
                "periodic_y": False,
            },
            "comparison": comparison_payload,
            "solver": representative["solver"],
            "validation": {
                "haldane": result["comparison"]["haldane"]["validation"],
                "chern": result["comparison"]["chern"]["validation"],
            },
            "performance": result["performance"],
            "disorder_realization": representative["disorder_realization"],
        },
    }

    physics_log = log_json(args.physics_log_dir, "task9_validation", payload["metadata"]["validation"])
    performance_log = log_json(args.performance_log_dir, "task9_performance", payload["metadata"]["performance"])
    payload["metadata"]["log_files"] = {
        "physics": physics_log,
        "performance": performance_log,
    }

    export_path = str(config.resolve_path(args.export_path))
    payload["metadata"]["export_path"] = export_path
    write_json(export_path, payload)

    summary = {
        "export_path": export_path,
        "haldane_bott_index": result["comparison"]["haldane"]["bott_index"],
        "chern_bott_index": result["comparison"]["chern"]["bott_index"],
        "invariant_match": result["comparison"]["invariant_match"],
        "frame_count": len(result["comparison"]["deformation_frames"]),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

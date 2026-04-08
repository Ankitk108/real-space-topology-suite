from __future__ import annotations

import argparse
import json
from datetime import datetime

from physics.config import Task1Config
from physics.export import matrix_to_serializable
from physics.export import write_json
from physics.wannier import run_task5_physics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate projected real-space state comparison data for trivial and topological phases."
    )
    parser.add_argument("--nx", type=int, default=20)
    parser.add_argument("--ny", type=int, default=20)
    parser.add_argument("--trivial-mass", type=float, default=3.0)
    parser.add_argument("--topological-mass", type=float, default=-1.0)
    parser.add_argument("--disorder", type=float, default=0.0)
    parser.add_argument("--disorder-seed", type=int, default=7)
    parser.add_argument("--fermi", type=float, default=0.0)
    parser.add_argument("--export-path", default="data/exports/task5.json")
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
    result = run_task5_physics(
        nx=args.nx,
        ny=args.ny,
        trivial_mass=args.trivial_mass,
        topological_mass=args.topological_mass,
        disorder=args.disorder,
        disorder_seed=args.disorder_seed,
        fermi=args.fermi,
    )

    primary = result["primary"]
    config = primary["config"]
    comparison = result["comparison"]
    topological = comparison["topological"]
    trivial = comparison["trivial"]

    payload = {
        "lattice_size": int(config.lattice_size),
        "hamiltonian_shape": [int(primary["hamiltonian"].shape[0]), int(primary["hamiltonian"].shape[1])],
        "eigenvalues": [float(value) for value in primary["eigenvalues"].tolist()],
        "U_V_matrices": {
            "U": matrix_to_serializable(primary["u_matrix"], config.zero_tolerance),
            "V": matrix_to_serializable(primary["v_matrix"], config.zero_tolerance),
        },
        "localizer_gap_grid": [[0.0]],
        "bott_index": int(primary["bott_index"]),
        "winding_phases": [float(value) for value in primary["winding_phases"].tolist()],
        "parameters": {
            "mass": float(config.mass),
            "disorder": float(config.disorder),
            "fermi": float(config.fermi),
        },
        "metadata": {
            "view": "wannier_obstruction",
            "boundary_conditions": {
                "periodic_x": False,
                "periodic_y": False,
            },
            "comparison": {
                "trivial": {
                    "mass": float(trivial["config"].mass),
                    "bott_index": int(trivial["bott_index"]),
                    "annotation": "Wannier state localizable -> Bott index = 0",
                    "construction": trivial["construction"],
                    "density_grid": trivial["density_grid"],
                    "peak_site": trivial["peak_site"],
                    "center_density": float(trivial["center_density"]),
                    "center_to_mean_ratio": float(trivial["center_to_mean_ratio"]),
                    "radial_profile": trivial["radial_profile"],
                    "validation": trivial["validation"],
                },
                "topological": {
                    "mass": float(topological["config"].mass),
                    "bott_index": int(topological["bott_index"]),
                    "annotation": "Wannier obstruction -> Bott index = -1",
                    "construction": topological["construction"],
                    "density_grid": topological["density_grid"],
                    "peak_site": topological["peak_site"],
                    "center_density": float(topological["center_density"]),
                    "center_to_mean_ratio": float(topological["center_to_mean_ratio"]),
                    "radial_profile": topological["radial_profile"],
                    "validation": topological["validation"],
                },
            },
            "rho_trivial": result["rho_trivial"],
            "rho_topological": result["rho_topological"],
            "solver": primary["solver"],
            "validation": {
                "primary": primary["validation"],
                "trivial": trivial["validation"],
                "topological": topological["validation"],
                "density_shapes": result["density_validation"],
            },
            "performance": {
                "primary": primary["performance"],
                "trivial": trivial["performance"],
                "topological": topological["performance"],
                "comparison": result["performance"],
            },
            "disorder_realization": [],
        },
    }

    physics_log = log_json(args.physics_log_dir, "task5_validation", payload["metadata"]["validation"])
    performance_log = log_json(args.performance_log_dir, "task5_performance", payload["metadata"]["performance"])
    payload["metadata"]["log_files"] = {
        "physics": physics_log,
        "performance": performance_log,
    }

    export_path = str(config.resolve_path(args.export_path))
    payload["metadata"]["export_path"] = export_path
    write_json(export_path, payload)

    summary = {
        "export_path": export_path,
        "trivial_bott_index": payload["metadata"]["comparison"]["trivial"]["bott_index"],
        "topological_bott_index": payload["metadata"]["comparison"]["topological"]["bott_index"],
        "trivial_center_to_mean_ratio": payload["metadata"]["comparison"]["trivial"]["center_to_mean_ratio"],
        "topological_center_to_mean_ratio": payload["metadata"]["comparison"]["topological"]["center_to_mean_ratio"],
        "topological_peak_radius": payload["metadata"]["comparison"]["topological"]["peak_site"]["radius"],
        "topological_center_patch": payload["metadata"]["rho_topological"][8:13],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

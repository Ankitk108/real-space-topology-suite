from __future__ import annotations

import numpy as np

from .bott import bott_index
from .bott import diagonalize_hamiltonian
from .bott import fermi_projection
from .bott import projected_unitaries
from .config import Task1Config
from .hamiltonian import build_hamiltonian
from .hamiltonian import real_space_coordinates
from .localizer_slicing import build_localizer_scalar_field
from .validation import validate_physics


def build_clifford_point_cloud(field: dict, percentile_levels: list[float]) -> dict:
    field_grid = np.asarray(field["field_grid"], dtype=np.float64)
    x_axis = np.asarray(field["x_axis"], dtype=np.float64)
    y_axis = np.asarray(field["y_axis"], dtype=np.float64)
    energy_axis = np.asarray(field["energy_axis"], dtype=np.float64)
    flattened = field_grid.reshape(-1)

    threshold_payloads = []
    for percentile in percentile_levels:
        threshold = float(np.percentile(flattened, percentile))
        indices = np.argwhere(field_grid <= threshold)
        points = []
        for energy_index, y_index, x_index in indices.tolist():
            gap_value = float(field_grid[energy_index, y_index, x_index])
            closeness = float(1.0 - (gap_value / max(threshold, 1.0e-12)))
            points.append(
                {
                    "x": float(x_axis[x_index]),
                    "y": float(y_axis[y_index]),
                    "energy": float(energy_axis[energy_index]),
                    "gap": gap_value,
                    "closeness": max(0.0, min(1.0, closeness)),
                }
            )
        threshold_payloads.append(
            {
                "percentile": float(percentile),
                "threshold_gap": threshold,
                "point_count": len(points),
                "points": points,
            }
        )

    default_index = min(len(threshold_payloads) - 1, 1)
    return {
        "threshold_levels": threshold_payloads,
        "default_index": int(default_index),
    }


def run_bonus_clifford_spectrum(
    nx: int,
    ny: int,
    mass: float,
    disorder: float,
    disorder_seed: int,
    fermi: float,
    x_points: int,
    y_points: int,
    energy_min: float,
    energy_max: float,
    energy_points: int,
    kappa: float,
) -> dict:
    config = Task1Config(
        nx=nx,
        ny=ny,
        mass=mass,
        disorder=disorder,
        disorder_seed=disorder_seed,
        fermi=fermi,
        periodic_x=False,
        periodic_y=False,
    ).validated()

    hamiltonian, disorder_values, cache_details = build_hamiltonian(config)
    dense_hamiltonian = hamiltonian.toarray().astype(np.complex128)
    eigenvalues, eigenvectors, solver_details = diagonalize_hamiltonian(dense_hamiltonian)
    projector, occupied_vectors = fermi_projection(eigenvalues, eigenvectors, config.fermi)
    del projector
    x_values, y_values = real_space_coordinates(config)
    u_matrix, v_matrix = projected_unitaries(config, occupied_vectors, x_values, y_values)
    bott_integer, winding_phases, bott_details = bott_index(u_matrix, v_matrix)
    validation = validate_physics(
        config=config,
        u_matrix=u_matrix,
        v_matrix=v_matrix,
        eigenvalues=eigenvalues,
        bott_integer=bott_integer,
        raw_bott=bott_details["raw_bott"],
    )
    scalar_field = build_localizer_scalar_field(
        config=config,
        hamiltonian=hamiltonian,
        x_points=x_points,
        y_points=y_points,
        energy_min=energy_min,
        energy_max=energy_max,
        energy_points=energy_points,
        kappa=kappa,
    )
    point_cloud = build_clifford_point_cloud(
        field=scalar_field,
        percentile_levels=[1.0, 2.5, 5.0, 10.0],
    )

    return {
        "config": config,
        "eigenvalues": eigenvalues,
        "u_matrix": u_matrix,
        "v_matrix": v_matrix,
        "bott_index": int(bott_integer),
        "winding_phases": winding_phases,
        "validation": validation,
        "solver": solver_details,
        "scalar_field": scalar_field,
        "point_cloud": point_cloud,
        "disorder_realization": disorder_values.tolist(),
        "performance": {
            "cache_hit": bool(cache_details["cache_hit"]),
            "hamiltonian_build_seconds": float(cache_details["build_seconds"]),
            "scalar_field_seconds": float(scalar_field["compute_seconds"]),
            "bott_seconds": float(bott_details["bott_seconds"]),
            "memory_mb": float(scalar_field["memory_mb"]),
        },
    }

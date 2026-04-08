from __future__ import annotations

from time import perf_counter

import numpy as np

from .bott import bott_index
from .bott import diagonalize_hamiltonian
from .bott import fermi_projection
from .bott import projected_unitaries
from .config import Task1Config
from .hamiltonian import build_hamiltonian
from .hamiltonian import real_space_coordinates
from .localizer import position_operators
from .localizer import smallest_localizer_gap
from .localizer import spectral_localizer_matrix
from .validation import validate_physics


def build_localizer_scalar_field(
    config: Task1Config,
    hamiltonian,
    x_points: int,
    y_points: int,
    energy_min: float,
    energy_max: float,
    energy_points: int,
    kappa: float,
) -> dict:
    x_operator, y_operator = position_operators(config)
    x_axis = np.linspace(0.0, max(config.nx - 1, 1), x_points, dtype=np.float64)
    y_axis = np.linspace(0.0, max(config.ny - 1, 1), y_points, dtype=np.float64)
    energy_axis = np.linspace(energy_min, energy_max, energy_points, dtype=np.float64)

    field_grid = np.zeros((energy_points, y_points, x_points), dtype=np.float64)
    slice_summaries: list[dict] = []
    compute_start = perf_counter()

    for energy_index, energy_value in enumerate(energy_axis.tolist()):
        slice_grid = np.zeros((y_points, x_points), dtype=np.float64)
        for y_index, y_value in enumerate(y_axis.tolist()):
            for x_index, x_value in enumerate(x_axis.tolist()):
                localizer = spectral_localizer_matrix(
                    hamiltonian=hamiltonian,
                    x_operator=x_operator,
                    y_operator=y_operator,
                    x0=float(x_value),
                    y0=float(y_value),
                    energy=float(energy_value),
                    kappa=float(kappa),
                )
                slice_grid[y_index, x_index] = smallest_localizer_gap(localizer)
        field_grid[energy_index] = slice_grid
        minimum_index = int(np.argmin(slice_grid))
        minimum_y, minimum_x = np.unravel_index(minimum_index, slice_grid.shape)
        slice_summaries.append(
            {
                "energy": float(energy_value),
                "minimum_gap": float(np.min(slice_grid)),
                "maximum_gap": float(np.max(slice_grid)),
                "mean_gap": float(np.mean(slice_grid)),
                "minimum_location": {
                    "x": float(x_axis[minimum_x]),
                    "y": float(y_axis[minimum_y]),
                },
            }
        )

    compute_seconds = perf_counter() - compute_start
    global_index = int(np.argmin(field_grid))
    global_energy_index, global_y_index, global_x_index = np.unravel_index(global_index, field_grid.shape)
    mid_energy_index = int(energy_points // 2)

    return {
        "x_axis": [float(value) for value in x_axis.tolist()],
        "y_axis": [float(value) for value in y_axis.tolist()],
        "energy_axis": [float(value) for value in energy_axis.tolist()],
        "field_grid": field_grid.tolist(),
        "representative_slice": field_grid[mid_energy_index].tolist(),
        "representative_slice_energy": float(energy_axis[mid_energy_index]),
        "global_minimum": {
            "gap": float(field_grid[global_energy_index, global_y_index, global_x_index]),
            "x": float(x_axis[global_x_index]),
            "y": float(y_axis[global_y_index]),
            "energy": float(energy_axis[global_energy_index]),
        },
        "minimum_gap": float(np.min(field_grid)),
        "maximum_gap": float(np.max(field_grid)),
        "slice_summaries": slice_summaries,
        "compute_seconds": float(compute_seconds),
        "memory_mb": float(field_grid.nbytes / (1024.0 * 1024.0)),
    }


def run_task8_localizer_slicing(
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
        "disorder_realization": disorder_values.tolist(),
        "performance": {
            "cache_hit": bool(cache_details["cache_hit"]),
            "hamiltonian_build_seconds": float(cache_details["build_seconds"]),
            "localizer_field_seconds": float(scalar_field["compute_seconds"]),
            "bott_seconds": float(bott_details["bott_seconds"]),
            "memory_mb": float(scalar_field["memory_mb"]),
        },
    }

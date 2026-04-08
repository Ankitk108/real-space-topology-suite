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
from .validation import validate_physics


def spectral_gap(eigenvalues: np.ndarray, fermi: float) -> float:
    return float(np.min(np.abs(eigenvalues - fermi)))


def evaluate_phase_point(
    nx: int,
    ny: int,
    mass: float,
    disorder: float,
    disorder_seed: int,
    fermi: float,
) -> dict:
    config = Task1Config(
        nx=nx,
        ny=ny,
        mass=mass,
        disorder=disorder,
        disorder_seed=disorder_seed,
        fermi=fermi,
        periodic_x=True,
        periodic_y=True,
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

    return {
        "config": config,
        "hamiltonian_shape": [int(hamiltonian.shape[0]), int(hamiltonian.shape[1])],
        "eigenvalues": eigenvalues,
        "u_matrix": u_matrix,
        "v_matrix": v_matrix,
        "bott_index": int(bott_integer),
        "winding_phases": winding_phases,
        "validation": validation,
        "solver": solver_details,
        "performance": {
            "cache_hit": bool(cache_details["cache_hit"]),
            "hamiltonian_build_seconds": float(cache_details["build_seconds"]),
            "bott_seconds": float(bott_details["bott_seconds"]),
        },
        "spectral_gap": spectral_gap(eigenvalues, config.fermi),
        "disorder_realization": disorder_values.tolist(),
    }


def run_task6_phase_diagram(
    nx: int,
    ny: int,
    disorder_seed: int,
    fermi: float,
    mass_min: float,
    mass_max: float,
    mass_points: int,
    disorder_min: float,
    disorder_max: float,
    disorder_points: int,
    collapse_mass: float,
    collapse_realizations: int,
    collapse_disorder_min: float,
    collapse_disorder_max: float,
    collapse_disorder_points: int,
) -> dict:
    start = perf_counter()
    mass_values = np.linspace(mass_min, mass_max, mass_points, dtype=np.float64)
    disorder_values = np.linspace(disorder_min, disorder_max, disorder_points, dtype=np.float64)

    bott_grid = np.zeros((disorder_points, mass_points), dtype=np.int64)
    gap_grid = np.zeros((disorder_points, mass_points), dtype=np.float64)
    sample_points: list[dict] = []
    bott_seconds = []
    build_seconds = []
    cache_hits = 0

    representative_point = None

    for disorder_index, disorder in enumerate(disorder_values.tolist()):
        for mass_index, mass in enumerate(mass_values.tolist()):
            point = evaluate_phase_point(
                nx=nx,
                ny=ny,
                mass=float(mass),
                disorder=float(disorder),
                disorder_seed=disorder_seed,
                fermi=fermi,
            )
            representative_point = point
            bott_grid[disorder_index, mass_index] = int(point["bott_index"])
            gap_grid[disorder_index, mass_index] = float(point["spectral_gap"])
            bott_seconds.append(point["performance"]["bott_seconds"])
            build_seconds.append(point["performance"]["hamiltonian_build_seconds"])
            cache_hits += int(point["performance"]["cache_hit"])
            sample_points.append(
                {
                    "mass": float(mass),
                    "disorder": float(disorder),
                    "bott_index": int(point["bott_index"]),
                    "spectral_gap": float(point["spectral_gap"]),
                    "integer_error": float(point["validation"]["integer_check"]["integer_error"]),
                    "commutator_norm": float(point["validation"]["commutator_bounds"]["measured_norm"]),
                }
            )

    if representative_point is None:
        raise ValueError("Phase diagram sweep produced no sample points.")

    collapse_axis = np.linspace(
        collapse_disorder_min,
        collapse_disorder_max,
        collapse_disorder_points,
        dtype=np.float64,
    )
    collapse_realization_curves: list[list[float]] = []
    collapse_gap_curves: list[list[float]] = []
    collapse_bott_seconds = []
    collapse_build_seconds = []
    collapse_cache_hits = 0

    for realization_index in range(collapse_realizations):
        realization_bott = []
        realization_gap = []
        seed = disorder_seed + 1000 * realization_index
        for disorder in collapse_axis.tolist():
            point = evaluate_phase_point(
                nx=nx,
                ny=ny,
                mass=float(collapse_mass),
                disorder=float(disorder),
                disorder_seed=seed,
                fermi=fermi,
            )
            realization_bott.append(float(point["bott_index"]))
            realization_gap.append(float(point["spectral_gap"]))
            collapse_bott_seconds.append(point["performance"]["bott_seconds"])
            collapse_build_seconds.append(point["performance"]["hamiltonian_build_seconds"])
            collapse_cache_hits += int(point["performance"]["cache_hit"])
        collapse_realization_curves.append(realization_bott)
        collapse_gap_curves.append(realization_gap)

    collapse_bott_array = np.asarray(collapse_realization_curves, dtype=np.float64)
    collapse_gap_array = np.asarray(collapse_gap_curves, dtype=np.float64)
    collapse_bott_magnitude = np.abs(collapse_bott_array)
    collapse_mean = np.mean(collapse_bott_magnitude, axis=0)
    collapse_std = np.std(collapse_bott_magnitude, axis=0)
    collapse_gap_mean = np.mean(collapse_gap_array, axis=0)
    collapse_gap_std = np.std(collapse_gap_array, axis=0)
    collapse_topological_fraction = np.mean(np.isclose(collapse_bott_magnitude, 1.0), axis=0)

    collapse_threshold = None
    for disorder, mean_value in zip(collapse_axis.tolist(), collapse_mean.tolist()):
        if mean_value < 0.5:
            collapse_threshold = float(disorder)
            break

    total_seconds = perf_counter() - start
    bott_unique, bott_counts = np.unique(bott_grid, return_counts=True)
    plateau_counts = {
        str(int(bott_value)): int(count)
        for bott_value, count in zip(bott_unique.tolist(), bott_counts.tolist())
    }

    return {
        "representative": representative_point,
        "phase_diagram": {
            "mass_axis": mass_values.tolist(),
            "disorder_axis": disorder_values.tolist(),
            "bott_grid": bott_grid.tolist(),
            "gap_grid": gap_grid.tolist(),
            "sample_points": sample_points,
            "plateau_counts": plateau_counts,
        },
        "disorder_collapse": {
            "mass": float(collapse_mass),
            "disorder_axis": collapse_axis.tolist(),
            "realizations": int(collapse_realizations),
            "bott_realizations": collapse_bott_array.tolist(),
            "bott_magnitude_realizations": collapse_bott_magnitude.tolist(),
            "gap_realizations": collapse_gap_array.tolist(),
            "mean_bott_magnitude": collapse_mean.tolist(),
            "std_bott_magnitude": collapse_std.tolist(),
            "mean_gap": collapse_gap_mean.tolist(),
            "std_gap": collapse_gap_std.tolist(),
            "topological_fraction": collapse_topological_fraction.tolist(),
            "critical_disorder_estimate": collapse_threshold,
        },
        "performance": {
            "total_seconds": float(total_seconds),
            "mean_bott_seconds": float(
                np.mean(np.asarray(bott_seconds + collapse_bott_seconds, dtype=np.float64))
            ),
            "mean_hamiltonian_build_seconds": float(
                np.mean(np.asarray(build_seconds + collapse_build_seconds, dtype=np.float64))
            ),
            "cache_hit_ratio": float(
                (cache_hits + collapse_cache_hits)
                / max((mass_points * disorder_points) + (collapse_disorder_points * collapse_realizations), 1)
            ),
            "memory_mb": float(
                (
                    bott_grid.nbytes
                    + gap_grid.nbytes
                    + collapse_bott_array.nbytes
                    + collapse_gap_array.nbytes
                )
                / (1024.0 * 1024.0)
            ),
        },
    }

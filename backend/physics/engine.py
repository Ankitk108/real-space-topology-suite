from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from time import perf_counter
import tracemalloc

import numpy as np

from .bott import bott_index
from .bott import diagonalize_hamiltonian
from .bott import fermi_projection
from .bott import projected_unitaries
from .config import Task1Config
from .export import matrix_to_serializable
from .export import write_json
from .hamiltonian import build_hamiltonian
from .hamiltonian import real_space_coordinates
from .validation import validate_physics


def _log_json(directory: str, stem: str, payload: dict) -> Path:
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = path / f"{stem}_{timestamp}.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def _default_localizer_grid() -> list[list[float]]:
    return [[0.0]]


def run_task1(config: Task1Config) -> dict:
    config = config.validated()
    total_start = perf_counter()

    track_memory = max(config.nx, config.ny) > 100
    if track_memory:
        tracemalloc.start()

    hamiltonian, disorder_values, cache_details = build_hamiltonian(config)
    dense_hamiltonian = hamiltonian.toarray().astype(np.complex128)
    x_values, y_values = real_space_coordinates(config)

    diag_start = perf_counter()
    eigenvalues, eigenvectors, solver_details = diagonalize_hamiltonian(dense_hamiltonian)
    diagonalization_seconds = perf_counter() - diag_start

    projector, occupied_vectors = fermi_projection(eigenvalues, eigenvectors, config.fermi)
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

    total_seconds = perf_counter() - total_start
    performance_log = {
        "cache_hit": bool(cache_details["cache_hit"]),
        "hamiltonian_build_seconds": float(cache_details["build_seconds"]),
        "diagonalization_seconds": float(diagonalization_seconds),
        "bott_seconds": float(bott_details["bott_seconds"]),
        "total_seconds": float(total_seconds),
        "memory_tracking_enabled": bool(track_memory),
        "memory_peak_mb": 0.0,
    }
    if track_memory:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        performance_log["memory_peak_mb"] = float(peak / (1024.0 * 1024.0))

    payload = {
        "lattice_size": int(config.lattice_size),
        "hamiltonian_shape": [int(hamiltonian.shape[0]), int(hamiltonian.shape[1])],
        "eigenvalues": [float(value) for value in eigenvalues.tolist()],
        "U_V_matrices": {
            "U": matrix_to_serializable(u_matrix, config.zero_tolerance),
            "V": matrix_to_serializable(v_matrix, config.zero_tolerance),
        },
        "localizer_gap_grid": _default_localizer_grid(),
        "bott_index": int(bott_integer),
        "winding_phases": [float(value) for value in winding_phases.tolist()],
        "parameters": {
            "mass": float(config.mass),
            "disorder": float(config.disorder),
            "fermi": float(config.fermi),
        },
        "metadata": {
            "disorder_seed": int(config.disorder_seed),
            "boundary_conditions": {
                "periodic_x": bool(config.periodic_x),
                "periodic_y": bool(config.periodic_y),
            },
            "occupied_dimension": int(occupied_vectors.shape[1]),
            "projector_shape": [int(projector.shape[0]), int(projector.shape[1])],
            "solver": solver_details,
            "validation": validation,
            "performance": performance_log,
            "disorder_realization": [float(value) for value in disorder_values.tolist()],
        },
    }

    physics_log_path = _log_json(
        str(config.resolve_path(config.physics_log_dir)),
        "task1_validation",
        payload["metadata"]["validation"],
    )
    performance_log_path = _log_json(
        str(config.resolve_path(config.performance_log_dir)),
        "task1_performance",
        performance_log,
    )
    payload["metadata"]["log_files"] = {
        "physics": str(physics_log_path),
        "performance": str(performance_log_path),
    }

    output_path = write_json(str(config.resolve_path(config.export_path)), payload)
    payload["metadata"]["export_path"] = str(output_path)
    write_json(str(config.resolve_path(config.export_path)), payload)
    return payload

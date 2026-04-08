from __future__ import annotations

from time import perf_counter

import numpy as np
from scipy import sparse

from .bott import bott_index
from .bott import diagonalize_hamiltonian
from .bott import fermi_projection
from .bott import projected_unitaries
from .config import Task1Config
from .hamiltonian import build_hamiltonian
from .hamiltonian import real_space_coordinates
from .validation import validate_physics


def centered_position_operators(config: Task1Config) -> tuple[np.ndarray, np.ndarray]:
    x_values, y_values = real_space_coordinates(config)
    x_center = 0.5 * float(max(config.nx - 1, 1))
    y_center = 0.5 * float(max(config.ny - 1, 1))
    x_scale = max(x_center, 1.0)
    y_scale = max(y_center, 1.0)
    x_operator = np.diag(((x_values - x_center) / x_scale).astype(np.complex128))
    y_operator = np.diag(((y_values - y_center) / y_scale).astype(np.complex128))
    return x_operator, y_operator


def normalized_hamiltonian_operator(hamiltonian: np.ndarray) -> tuple[np.ndarray, float]:
    spectral_radius = float(np.max(np.abs(np.linalg.eigvalsh(hamiltonian.astype(np.complex128)))))
    scale = spectral_radius if spectral_radius > 1.0e-12 else 1.0
    return (hamiltonian.astype(np.complex128) / scale), scale


def operator_expectation_cloud(
    eigenvectors: np.ndarray,
    operators: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> dict:
    h1, h2, h3 = operators
    points = []
    thickness_values = []

    for state_index in range(eigenvectors.shape[1]):
        vector = eigenvectors[:, state_index].astype(np.complex128)
        expectations = []
        variances = []
        for operator in operators:
            mean_value = np.vdot(vector, operator @ vector)
            centered = operator @ vector - mean_value * vector
            variance = float(np.real(np.vdot(centered, centered)))
            expectations.append(float(np.real(mean_value)))
            variances.append(max(variance, 0.0))

        thickness = float(np.sqrt(np.sum(variances)))
        thickness_values.append(thickness)
        points.append(
            {
                "state_index": int(state_index),
                "h1": expectations[0],
                "h2": expectations[1],
                "h3": expectations[2],
                "variance_h1": variances[0],
                "variance_h2": variances[1],
                "variance_h3": variances[2],
                "thickness": thickness,
            }
        )

    thickness_array = np.asarray(thickness_values, dtype=np.float64)
    return {
        "points": points,
        "thickness_mean": float(np.mean(thickness_array)),
        "thickness_max": float(np.max(thickness_array)),
        "thickness_min": float(np.min(thickness_array)),
    }


def commutator_norm(left: np.ndarray, right: np.ndarray) -> float:
    commutator = left @ right - right @ left
    return float(np.linalg.norm(commutator, ord=2))


def run_task4_physics(
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

    hamiltonian_sparse, disorder_values, cache_details = build_hamiltonian(config)
    dense_hamiltonian = hamiltonian_sparse.toarray().astype(np.complex128)
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

    expectation_start = perf_counter()
    h1_operator, h2_operator = centered_position_operators(config)
    h3_operator, h3_scale = normalized_hamiltonian_operator(dense_hamiltonian)
    cloud_payload = operator_expectation_cloud(
        eigenvectors=eigenvectors,
        operators=(h1_operator, h2_operator, h3_operator),
    )
    expectation_seconds = perf_counter() - expectation_start

    commutators = {
        "norm_h1_h2": commutator_norm(h1_operator, h2_operator),
        "norm_h2_h3": commutator_norm(h2_operator, h3_operator),
        "norm_h3_h1": commutator_norm(h3_operator, h1_operator),
    }

    return {
        "config": config,
        "hamiltonian": dense_hamiltonian,
        "eigenvalues": eigenvalues,
        "eigenvectors": eigenvectors,
        "projector": projector,
        "u_matrix": u_matrix,
        "v_matrix": v_matrix,
        "bott_index": int(bott_integer),
        "winding_phases": winding_phases,
        "disorder_values": disorder_values,
        "validation": validation,
        "solver": solver_details,
        "cloud": cloud_payload,
        "commutators": commutators,
        "operator_scales": {
            "h1_range": [-1.0, 1.0],
            "h2_range": [-1.0, 1.0],
            "h3_spectral_radius": float(h3_scale),
        },
        "performance": {
            "cache_hit": bool(cache_details["cache_hit"]),
            "hamiltonian_build_seconds": float(cache_details["build_seconds"]),
            "expectation_compute_seconds": float(expectation_seconds),
            "bott_seconds": float(bott_details["bott_seconds"]),
            "memory_mb": float(dense_hamiltonian.nbytes / (1024.0 * 1024.0)),
        },
    }

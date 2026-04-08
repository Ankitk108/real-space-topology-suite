from __future__ import annotations

from time import perf_counter

import numpy as np

from .config import Task1Config
from .hamiltonian import build_hamiltonian


def _operator_norm(matrix: np.ndarray) -> float:
    return float(np.linalg.norm(matrix, ord=2))


def _spectral_gap(eigenvalues: np.ndarray, fermi: float) -> float:
    below = eigenvalues[eigenvalues <= fermi]
    above = eigenvalues[eigenvalues > fermi]
    if below.size == 0 or above.size == 0:
        return 0.0
    return float(np.min(above) - np.max(below))


def validate_physics(
    config: Task1Config,
    u_matrix: np.ndarray,
    v_matrix: np.ndarray,
    eigenvalues: np.ndarray,
    bott_integer: int,
    raw_bott: float,
) -> dict:
    ident_u = np.eye(u_matrix.shape[0], dtype=np.complex128)
    ident_v = np.eye(v_matrix.shape[0], dtype=np.complex128)
    unitarity_u = _operator_norm(u_matrix.conj().T @ u_matrix - ident_u)
    unitarity_v = _operator_norm(v_matrix.conj().T @ v_matrix - ident_v)
    commutator = u_matrix @ v_matrix - v_matrix @ u_matrix
    commutator_norm = _operator_norm(commutator)
    theoretical_scale = float((2.0 * np.pi) / max(config.nx, config.ny))
    integer_error = abs(raw_bott - round(raw_bott))

    start = perf_counter()
    perturbations = []
    for delta_mass, delta_disorder in (
        (config.gap_probe_delta, 0.0),
        (-config.gap_probe_delta, 0.0),
        (0.0, config.gap_probe_delta),
    ):
        probe_config = Task1Config(
            nx=config.nx,
            ny=config.ny,
            mass=config.mass + delta_mass,
            disorder=max(0.0, config.disorder + delta_disorder),
            disorder_seed=config.disorder_seed,
            fermi=config.fermi,
            periodic_x=config.periodic_x,
            periodic_y=config.periodic_y,
            cache_dir=config.cache_dir,
            export_path=config.export_path,
            physics_log_dir=config.physics_log_dir,
            performance_log_dir=config.performance_log_dir,
            gap_probe_delta=config.gap_probe_delta,
            zero_tolerance=config.zero_tolerance,
        )
        probe_hamiltonian, _, _ = build_hamiltonian(probe_config)
        probe_values = np.linalg.eigvalsh(probe_hamiltonian.toarray().astype(np.complex128))
        perturbations.append(
            {
                "mass": float(probe_config.mass),
                "disorder": float(probe_config.disorder),
                "spectral_gap": _spectral_gap(probe_values, config.fermi),
            }
        )
    perturbation_seconds = perf_counter() - start

    base_gap = _spectral_gap(eigenvalues, config.fermi)
    persistent = base_gap > 0.0 and all(item["spectral_gap"] > 0.0 for item in perturbations)
    return {
        "unitarity": {
            "u_norm_error": unitarity_u,
            "v_norm_error": unitarity_v,
            "epsilon": 1.0e-6,
            "u_pass": bool(unitarity_u < 1.0e-6),
            "v_pass": bool(unitarity_v < 1.0e-6),
        },
        "commutator_bounds": {
            "measured_norm": commutator_norm,
            "predicted_scale": theoretical_scale,
            "pass": bool(commutator_norm <= max(1.0, 8.0 * theoretical_scale)),
        },
        "integer_check": {
            "bott_index": int(bott_integer),
            "raw_bott": float(raw_bott),
            "integer_error": float(integer_error),
            "pass": bool(integer_error < 1.0e-6),
        },
        "spectral_gap_persistence": {
            "base_gap": base_gap,
            "perturbations": perturbations,
            "pass": bool(persistent),
            "probe_seconds": perturbation_seconds,
        },
    }

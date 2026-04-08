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


def evaluate_flow_frame(
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
    w_matrix = u_matrix @ v_matrix @ u_matrix.conj().T @ v_matrix.conj().T
    w_eigenvalues = np.linalg.eigvals(w_matrix.astype(np.complex128))
    phases = np.angle(w_eigenvalues).astype(np.float64)
    ordering = np.argsort(phases)
    ordered_phases = phases[ordering]
    ordered_eigenvalues = w_eigenvalues[ordering]
    winding_number = int(np.rint(np.sum(ordered_phases) / (2.0 * np.pi)))

    return {
        "config": config,
        "eigenvalues": eigenvalues,
        "u_matrix": u_matrix,
        "v_matrix": v_matrix,
        "w_eigenvalues": ordered_eigenvalues.astype(np.complex128),
        "phases": ordered_phases,
        "bott_index": int(bott_integer),
        "winding_number": int(winding_number),
        "validation": validation,
        "solver": solver_details,
        "performance": {
            "cache_hit": bool(cache_details["cache_hit"]),
            "hamiltonian_build_seconds": float(cache_details["build_seconds"]),
            "bott_seconds": float(bott_details["bott_seconds"]),
        },
        "disorder_realization": disorder_values.tolist(),
    }


def run_task7_eigenflow(
    nx: int,
    ny: int,
    disorder_seed: int,
    fermi: float,
    mass_start: float,
    mass_end: float,
    disorder_start: float,
    disorder_end: float,
    frame_count: int,
) -> dict:
    start = perf_counter()
    mass_values = np.linspace(mass_start, mass_end, frame_count, dtype=np.float64)
    disorder_values = np.linspace(disorder_start, disorder_end, frame_count, dtype=np.float64)

    frames: list[dict] = []
    representative = None
    bott_matches = []
    bott_seconds = []

    for index, (mass, disorder) in enumerate(zip(mass_values.tolist(), disorder_values.tolist())):
        frame = evaluate_flow_frame(
            nx=nx,
            ny=ny,
            mass=float(mass),
            disorder=float(disorder),
            disorder_seed=disorder_seed,
            fermi=fermi,
        )
        representative = frame
        bott_matches.append(int(frame["bott_index"]) == int(frame["winding_number"]))
        bott_seconds.append(frame["performance"]["bott_seconds"])
        frames.append(
            {
                "frame_index": int(index),
                "mass": float(mass),
                "disorder": float(disorder),
                "bott_index": int(frame["bott_index"]),
                "winding_number": int(frame["winding_number"]),
                "phases": [float(value) for value in frame["phases"].tolist()],
                "eigenvalues": [
                    [float(np.real(value)), float(np.imag(value))]
                    for value in frame["w_eigenvalues"].tolist()
                ],
                "validation": {
                    "integer_error": float(frame["validation"]["integer_check"]["integer_error"]),
                    "commutator_norm": float(frame["validation"]["commutator_bounds"]["measured_norm"]),
                },
            }
        )

    if representative is None:
        raise ValueError("Eigenvalue flow produced no frames.")

    total_seconds = perf_counter() - start
    return {
        "representative": representative,
        "flow": {
            "frames": frames,
            "mass_path": mass_values.tolist(),
            "disorder_path": disorder_values.tolist(),
            "bott_matches_winding_all_frames": bool(all(bott_matches)),
        },
        "performance": {
            "total_seconds": float(total_seconds),
            "mean_bott_seconds": float(np.mean(np.asarray(bott_seconds, dtype=np.float64))),
            "memory_mb": float(len(frames) * len(frames[0]["eigenvalues"]) * 16 / (1024.0 * 1024.0)),
        },
    }

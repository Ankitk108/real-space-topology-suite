from __future__ import annotations

from time import perf_counter

import numpy as np

from .config import Task1Config


def diagonalize_hamiltonian(hamiltonian: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict]:
    details = {"eigensolver": "numpy.linalg.eigh", "fallback_used": False, "warning": ""}
    hermitian = 0.5 * (hamiltonian + hamiltonian.conj().T)
    try:
        eigenvalues, eigenvectors = np.linalg.eigh(hermitian)
    except np.linalg.LinAlgError:
        details["fallback_used"] = True
        details["warning"] = "Primary Hermitian eigensolver failed; retrying after realignment."
        retry = hermitian.astype(np.complex128, copy=True)
        retry += 1.0e-12 * np.eye(retry.shape[0], dtype=np.complex128)
        try:
            eigenvalues, eigenvectors = np.linalg.eigh(retry)
            details["eigensolver"] = "numpy.linalg.eigh(retry)"
        except np.linalg.LinAlgError:
            details["eigensolver"] = "failed"
            details["warning"] = (
                "Dense eigensolver did not converge; returning zero spectrum and identity eigenvectors."
            )
            size = hamiltonian.shape[0]
            eigenvalues = np.zeros(size, dtype=np.float64)
            eigenvectors = np.eye(size, dtype=np.complex128)
    return eigenvalues.astype(np.float64), eigenvectors.astype(np.complex128), details


def fermi_projection(
    eigenvalues: np.ndarray,
    eigenvectors: np.ndarray,
    fermi: float,
) -> tuple[np.ndarray, np.ndarray]:
    occupied_mask = eigenvalues <= fermi
    occupied_vectors = eigenvectors[:, occupied_mask]
    if occupied_vectors.size == 0:
        projector = np.zeros((eigenvectors.shape[0], eigenvectors.shape[0]), dtype=np.complex128)
        return projector, occupied_vectors.astype(np.complex128)
    projector = occupied_vectors @ occupied_vectors.conj().T
    return projector.astype(np.complex128), occupied_vectors.astype(np.complex128)


def projected_unitaries(
    config: Task1Config,
    occupied_vectors: np.ndarray,
    x_values: np.ndarray,
    y_values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    occupied_dim = occupied_vectors.shape[1]
    if occupied_dim == 0:
        empty = np.zeros((1, 1), dtype=np.complex128)
        return empty, empty

    x_phase = np.exp(1.0j * 2.0 * np.pi * x_values / float(config.nx))
    y_phase = np.exp(1.0j * 2.0 * np.pi * y_values / float(config.ny))
    exp_x = np.diag(x_phase.astype(np.complex128))
    exp_y = np.diag(y_phase.astype(np.complex128))
    q_dagger = occupied_vectors.conj().T
    compressed_u = q_dagger @ exp_x @ occupied_vectors
    compressed_v = q_dagger @ exp_y @ occupied_vectors
    u_left, _, u_right = np.linalg.svd(compressed_u, full_matrices=False)
    v_left, _, v_right = np.linalg.svd(compressed_v, full_matrices=False)
    u_matrix = u_left @ u_right
    v_matrix = v_left @ v_right
    return u_matrix.astype(np.complex128), v_matrix.astype(np.complex128)


def bott_index(u_matrix: np.ndarray, v_matrix: np.ndarray) -> tuple[int, np.ndarray, dict]:
    start = perf_counter()
    w_matrix = u_matrix @ v_matrix @ u_matrix.conj().T @ v_matrix.conj().T
    eigenvalues = np.linalg.eigvals(w_matrix.astype(np.complex128))
    phases = np.angle(eigenvalues)
    raw_value = float(np.imag(np.sum(np.log(eigenvalues + 0.0j))) / (2.0 * np.pi))
    bott_integer = int(np.rint(raw_value))
    elapsed = perf_counter() - start
    return bott_integer, phases.astype(np.float64), {
        "raw_bott": raw_value,
        "bott_seconds": elapsed,
    }

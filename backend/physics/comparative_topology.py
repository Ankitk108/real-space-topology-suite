from __future__ import annotations

from time import perf_counter

import numpy as np

from .bott import bott_index
from .bott import diagonalize_hamiltonian
from .bott import fermi_projection
from .config import Task1Config
from .hamiltonian import build_hamiltonian
from .hamiltonian import real_space_coordinates
from .validation import validate_physics


def projected_unitaries_irregular(
    occupied_vectors: np.ndarray,
    x_values: np.ndarray,
    y_values: np.ndarray,
    x_period: float,
    y_period: float,
) -> tuple[np.ndarray, np.ndarray]:
    occupied_dim = occupied_vectors.shape[1]
    if occupied_dim == 0:
        empty = np.zeros((1, 1), dtype=np.complex128)
        return empty, empty

    x_phase = np.exp(1.0j * 2.0 * np.pi * x_values / float(max(x_period, 1.0)))
    y_phase = np.exp(1.0j * 2.0 * np.pi * y_values / float(max(y_period, 1.0)))
    exp_x = np.diag(x_phase.astype(np.complex128))
    exp_y = np.diag(y_phase.astype(np.complex128))
    q_dagger = occupied_vectors.conj().T
    compressed_u = q_dagger @ exp_x @ occupied_vectors
    compressed_v = q_dagger @ exp_y @ occupied_vectors
    u_left, _, u_right = np.linalg.svd(compressed_u, full_matrices=False)
    v_left, _, v_right = np.linalg.svd(compressed_v, full_matrices=False)
    return (u_left @ u_right).astype(np.complex128), (v_left @ v_right).astype(np.complex128)


def build_haldane_hamiltonian(
    nx: int,
    ny: int,
    mass: float,
    t1: float,
    t2: float,
    phi: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cell_count = nx * ny
    dim = 2 * cell_count
    hamiltonian = np.zeros((dim, dim), dtype=np.complex128)

    def cell_index(x_idx: int, y_idx: int) -> int:
        return x_idx * ny + y_idx

    def site_index(x_idx: int, y_idx: int, sublattice: int) -> int:
        return 2 * cell_index(x_idx, y_idx) + sublattice

    x_coordinates = np.zeros(dim, dtype=np.float64)
    y_coordinates = np.zeros(dim, dtype=np.float64)

    for x_idx in range(nx):
        for y_idx in range(ny):
            a_site = site_index(x_idx, y_idx, 0)
            b_site = site_index(x_idx, y_idx, 1)
            x_coordinates[a_site] = float(x_idx)
            y_coordinates[a_site] = float(y_idx)
            x_coordinates[b_site] = float(x_idx) + 0.5
            y_coordinates[b_site] = float(y_idx) + (np.sqrt(3.0) / 6.0)

            hamiltonian[a_site, a_site] += mass
            hamiltonian[b_site, b_site] -= mass

            nn_targets = [
                (x_idx, y_idx),
                (x_idx - 1, y_idx),
                (x_idx, y_idx - 1),
            ]
            for target_x, target_y in nn_targets:
                if 0 <= target_x < nx and 0 <= target_y < ny:
                    neighbor = site_index(target_x, target_y, 1)
                    hamiltonian[a_site, neighbor] += t1
                    hamiltonian[neighbor, a_site] += t1

            a_nnn = [
                (x_idx + 1, y_idx, +1.0),
                (x_idx, y_idx + 1, +1.0),
                (x_idx + 1, y_idx - 1, -1.0),
            ]
            b_nnn = [
                (x_idx + 1, y_idx, -1.0),
                (x_idx, y_idx + 1, -1.0),
                (x_idx + 1, y_idx - 1, +1.0),
            ]
            for target_x, target_y, sign in a_nnn:
                if 0 <= target_x < nx and 0 <= target_y < ny:
                    neighbor = site_index(target_x, target_y, 0)
                    amplitude = t2 * np.exp(1.0j * sign * phi)
                    hamiltonian[a_site, neighbor] += amplitude
                    hamiltonian[neighbor, a_site] += np.conj(amplitude)
            for target_x, target_y, sign in b_nnn:
                if 0 <= target_x < nx and 0 <= target_y < ny:
                    neighbor = site_index(target_x, target_y, 1)
                    amplitude = t2 * np.exp(1.0j * sign * phi)
                    hamiltonian[b_site, neighbor] += amplitude
                    hamiltonian[neighbor, b_site] += np.conj(amplitude)

    return hamiltonian.astype(np.complex128), x_coordinates, y_coordinates


def honeycomb_density_map(
    eigenvalues: np.ndarray,
    eigenvectors: np.ndarray,
    nx: int,
    ny: int,
    fermi: float,
    window_count: int,
) -> np.ndarray:
    distances = np.abs(eigenvalues - fermi)
    selected = np.argsort(distances)[: max(1, min(window_count, eigenvalues.size))]
    density_grid = np.zeros((ny, nx), dtype=np.float64)

    for state_index in selected.tolist():
        vector = eigenvectors[:, state_index]
        for x_idx in range(nx):
            for y_idx in range(ny):
                cell = x_idx * ny + y_idx
                a_site = 2 * cell
                b_site = a_site + 1
                density_grid[y_idx, x_idx] += float(np.abs(vector[a_site]) ** 2 + np.abs(vector[b_site]) ** 2)

    total = float(np.sum(density_grid))
    if total > 0.0:
        density_grid /= total
    return density_grid


def square_density_map(
    eigenvalues: np.ndarray,
    eigenvectors: np.ndarray,
    nx: int,
    ny: int,
    fermi: float,
    window_count: int,
) -> np.ndarray:
    distances = np.abs(eigenvalues - fermi)
    selected = np.argsort(distances)[: max(1, min(window_count, eigenvalues.size))]
    density_grid = np.zeros((ny, nx), dtype=np.float64)

    for state_index in selected.tolist():
        vector = eigenvectors[:, state_index]
        for x_idx in range(nx):
            for y_idx in range(ny):
                site = x_idx * ny + y_idx
                block = vector[2 * site : 2 * (site + 1)]
                density_grid[y_idx, x_idx] += float(np.sum(np.abs(block) ** 2))

    total = float(np.sum(density_grid))
    if total > 0.0:
        density_grid /= total
    return density_grid


def radial_profile(density_grid: np.ndarray) -> list[dict]:
    rows, cols = density_grid.shape
    center_x = cols / 2.0 - 0.5
    center_y = rows / 2.0 - 0.5
    max_radius = int(np.ceil(max(rows, cols) / 2.0))
    profile = []
    for radius in range(max_radius + 1):
        values = []
        for row in range(rows):
            for col in range(cols):
                distance = np.sqrt((col - center_x) ** 2 + (row - center_y) ** 2)
                if int(np.rint(distance)) == radius:
                    values.append(float(density_grid[row, col]))
        if values:
            profile.append(
                {
                    "radius": int(radius),
                    "mean_density": float(np.mean(np.asarray(values, dtype=np.float64))),
                }
            )
    return profile


def interpolation_frames(
    haldane_grid: np.ndarray,
    cern_grid: np.ndarray,
    frame_count: int,
    bott_value: int,
) -> list[dict]:
    frames = []
    lambdas = np.linspace(0.0, 1.0, frame_count, dtype=np.float64)
    for index, lam in enumerate(lambdas.tolist()):
        blended = ((1.0 - lam) * haldane_grid) + (lam * cern_grid)
        total = float(np.sum(blended))
        if total > 0.0:
            blended = blended / total
        peak_index = int(np.argmax(blended))
        peak_row, peak_col = np.unravel_index(peak_index, blended.shape)
        frames.append(
            {
                "frame_index": int(index),
                "lambda": float(lam),
                "density_grid": blended.tolist(),
                "bott_index": int(bott_value),
                "peak_location": {
                    "x": int(peak_col),
                    "y": int(peak_row),
                },
            }
        )
    return frames


def evaluate_haldane_endpoint(
    nx: int,
    ny: int,
    mass: float,
    t1: float,
    t2: float,
    phi: float,
    fermi: float,
    window_count: int,
) -> dict:
    hamiltonian, x_values, y_values = build_haldane_hamiltonian(nx, ny, mass, t1, t2, phi)
    eigenvalues, eigenvectors, solver_details = diagonalize_hamiltonian(hamiltonian)
    projector, occupied_vectors = fermi_projection(eigenvalues, eigenvectors, fermi)
    del projector
    u_matrix, v_matrix = projected_unitaries_irregular(
        occupied_vectors=occupied_vectors,
        x_values=x_values,
        y_values=y_values,
        x_period=float(nx),
        y_period=float(ny),
    )
    bott_integer, winding_phases, bott_details = bott_index(u_matrix, v_matrix)
    validation = validate_physics(
        config=Task1Config(nx=nx, ny=ny, mass=mass, disorder=0.0, fermi=fermi, periodic_x=False, periodic_y=False),
        u_matrix=u_matrix,
        v_matrix=v_matrix,
        eigenvalues=eigenvalues,
        bott_integer=bott_integer,
        raw_bott=bott_details["raw_bott"],
    )
    density_grid = honeycomb_density_map(
        eigenvalues=eigenvalues,
        eigenvectors=eigenvectors,
        nx=nx,
        ny=ny,
        fermi=fermi,
        window_count=window_count,
    )
    return {
        "name": "Haldane Model",
        "hamiltonian": hamiltonian,
        "eigenvalues": eigenvalues,
        "u_matrix": u_matrix,
        "v_matrix": v_matrix,
        "bott_index": int(bott_integer),
        "winding_phases": winding_phases,
        "validation": validation,
        "solver": solver_details,
        "density_grid": density_grid.tolist(),
        "radial_profile": radial_profile(density_grid),
        "parameters": {
            "mass": float(mass),
            "t1": float(t1),
            "t2": float(t2),
            "phi": float(phi),
            "fermi": float(fermi),
        },
        "performance": {
            "bott_seconds": float(bott_details["bott_seconds"]),
        },
    }


def evaluate_disordered_chern_endpoint(
    nx: int,
    ny: int,
    mass: float,
    disorder: float,
    disorder_seed: int,
    fermi: float,
    window_count: int,
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

    hamiltonian_sparse, disorder_values, cache_details = build_hamiltonian(config)
    hamiltonian = hamiltonian_sparse.toarray().astype(np.complex128)
    eigenvalues, eigenvectors, solver_details = diagonalize_hamiltonian(hamiltonian)
    projector, occupied_vectors = fermi_projection(eigenvalues, eigenvectors, fermi)
    del projector
    x_values, y_values = real_space_coordinates(config)
    u_matrix, v_matrix = projected_unitaries_irregular(
        occupied_vectors=occupied_vectors,
        x_values=x_values,
        y_values=y_values,
        x_period=float(nx),
        y_period=float(ny),
    )
    bott_integer, winding_phases, bott_details = bott_index(u_matrix, v_matrix)
    validation = validate_physics(
        config=config,
        u_matrix=u_matrix,
        v_matrix=v_matrix,
        eigenvalues=eigenvalues,
        bott_integer=bott_integer,
        raw_bott=bott_details["raw_bott"],
    )
    density_grid = square_density_map(
        eigenvalues=eigenvalues,
        eigenvectors=eigenvectors,
        nx=nx,
        ny=ny,
        fermi=fermi,
        window_count=window_count,
    )
    return {
        "name": "Disordered Chern Insulator",
        "hamiltonian": hamiltonian,
        "eigenvalues": eigenvalues,
        "u_matrix": u_matrix,
        "v_matrix": v_matrix,
        "bott_index": int(bott_integer),
        "winding_phases": winding_phases,
        "validation": validation,
        "solver": solver_details,
        "density_grid": density_grid.tolist(),
        "radial_profile": radial_profile(density_grid),
        "parameters": {
            "mass": float(mass),
            "disorder": float(disorder),
            "fermi": float(fermi),
        },
        "disorder_realization": disorder_values.tolist(),
        "performance": {
            "bott_seconds": float(bott_details["bott_seconds"]),
            "cache_hit": bool(cache_details["cache_hit"]),
            "hamiltonian_build_seconds": float(cache_details["build_seconds"]),
        },
    }


def run_task9_comparison(
    nx: int,
    ny: int,
    fermi: float,
    disorder_seed: int,
    frame_count: int,
) -> dict:
    start = perf_counter()
    haldane = evaluate_haldane_endpoint(
        nx=nx,
        ny=ny,
        mass=0.2,
        t1=1.0,
        t2=0.24,
        phi=-0.5 * np.pi,
        fermi=fermi,
        window_count=6,
    )
    chern = evaluate_disordered_chern_endpoint(
        nx=nx,
        ny=ny,
        mass=-1.0,
        disorder=0.45,
        disorder_seed=disorder_seed,
        fermi=fermi,
        window_count=6,
    )

    invariant_bott = int(chern["bott_index"])
    invariant_match = int(haldane["bott_index"]) == int(chern["bott_index"])
    deformation_frames = interpolation_frames(
        haldane_grid=np.asarray(haldane["density_grid"], dtype=np.float64),
        cern_grid=np.asarray(chern["density_grid"], dtype=np.float64),
        frame_count=frame_count,
        bott_value=invariant_bott,
    )

    return {
        "representative": chern,
        "comparison": {
            "haldane": haldane,
            "chern": chern,
            "deformation_frames": deformation_frames,
            "bott_trace": [int(invariant_bott) for _ in deformation_frames],
            "invariant_match": bool(invariant_match),
        },
        "performance": {
            "total_seconds": float(perf_counter() - start),
            "memory_mb": float(
                (
                    np.asarray(haldane["density_grid"], dtype=np.float64).nbytes
                    + np.asarray(chern["density_grid"], dtype=np.float64).nbytes
                )
                / (1024.0 * 1024.0)
            ),
        },
    }

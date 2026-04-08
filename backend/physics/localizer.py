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


def position_operators(config: Task1Config) -> tuple[sparse.csr_matrix, sparse.csr_matrix]:
    x_values, y_values = real_space_coordinates(config)
    x_operator = sparse.diags(x_values.astype(np.complex128), offsets=0, format="csr")
    y_operator = sparse.diags(y_values.astype(np.complex128), offsets=0, format="csr")
    return x_operator, y_operator


def spectral_localizer_matrix(
    hamiltonian: sparse.csr_matrix,
    x_operator: sparse.csr_matrix,
    y_operator: sparse.csr_matrix,
    x0: float,
    y0: float,
    energy: float,
    kappa: float,
) -> sparse.csr_matrix:
    dim = hamiltonian.shape[0]
    ident = sparse.identity(dim, dtype=np.complex128, format="csr")
    upper_left = hamiltonian - energy * ident
    displacement = kappa * ((x_operator - x0 * ident) - 1.0j * (y_operator - y0 * ident))
    return sparse.bmat(
        [[upper_left, displacement], [displacement.getH(), -upper_left]],
        format="csr",
        dtype=np.complex128,
    )


def smallest_localizer_gap(localizer: sparse.csr_matrix) -> float:
    dense = localizer.toarray().astype(np.complex128)
    eigenvalues = np.linalg.eigvalsh(dense)
    return float(np.min(np.abs(eigenvalues)))


def localizer_gap_grid(
    config: Task1Config,
    hamiltonian: sparse.csr_matrix,
    grid_points_x: int,
    grid_points_y: int,
    kappa: float,
) -> dict:
    x_operator, y_operator = position_operators(config)
    x_axis = np.linspace(0.0, max(config.nx - 1, 1), grid_points_x, dtype=np.float64)
    y_axis = np.linspace(0.0, max(config.ny - 1, 1), grid_points_y, dtype=np.float64)
    gap_grid = np.zeros((grid_points_y, grid_points_x), dtype=np.float64)

    start = perf_counter()
    for y_index, y_value in enumerate(y_axis):
        for x_index, x_value in enumerate(x_axis):
            localizer = spectral_localizer_matrix(
                hamiltonian=hamiltonian,
                x_operator=x_operator,
                y_operator=y_operator,
                x0=float(x_value),
                y0=float(y_value),
                energy=float(config.fermi),
                kappa=float(kappa),
            )
            gap_grid[y_index, x_index] = smallest_localizer_gap(localizer)
    elapsed = perf_counter() - start
    return {
        "x_axis": [float(value) for value in x_axis.tolist()],
        "y_axis": [float(value) for value in y_axis.tolist()],
        "gap_grid": gap_grid.tolist(),
        "minimum_gap": float(np.min(gap_grid)),
        "maximum_gap": float(np.max(gap_grid)),
        "compute_seconds": float(elapsed),
    }


def edge_state_density(
    config: Task1Config,
    eigenvalues: np.ndarray,
    eigenvectors: np.ndarray,
    window_count: int,
) -> dict:
    site_count = config.lattice_size
    orbital_dim = 2
    distances = np.abs(eigenvalues - config.fermi)
    order = np.argsort(distances)
    selected = order[: max(1, min(window_count, eigenvalues.size))]

    density_grid = np.zeros((config.ny, config.nx), dtype=np.float64)
    per_state = []
    for state_index in selected.tolist():
        vector = eigenvectors[:, state_index]
        density_per_site = np.zeros(site_count, dtype=np.float64)
        for site in range(site_count):
            block = vector[orbital_dim * site : orbital_dim * (site + 1)]
            density_per_site[site] = float(np.sum(np.abs(block) ** 2))
        density_grid += density_per_site.reshape(config.nx, config.ny).T
        per_state.append(
            {
                "state_index": int(state_index),
                "energy": float(eigenvalues[state_index]),
                "distance_to_fermi": float(distances[state_index]),
            }
        )

    total_weight = float(np.sum(density_grid))
    if total_weight > 0.0:
        density_grid /= total_weight

    edge_mask = np.zeros((config.ny, config.nx), dtype=bool)
    edge_mask[0, :] = True
    edge_mask[-1, :] = True
    edge_mask[:, 0] = True
    edge_mask[:, -1] = True
    edge_weight = float(np.sum(density_grid[edge_mask]))

    return {
        "density_grid": density_grid.tolist(),
        "selected_states": per_state,
        "edge_weight": edge_weight,
        "max_density": float(np.max(density_grid)),
    }


def run_task3_physics(
    nx: int,
    ny: int,
    mass: float,
    disorder: float,
    disorder_seed: int,
    fermi: float,
    grid_points_x: int,
    grid_points_y: int,
    kappa: float,
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
    gap_payload = localizer_gap_grid(
        config=config,
        hamiltonian=hamiltonian,
        grid_points_x=grid_points_x,
        grid_points_y=grid_points_y,
        kappa=kappa,
    )
    density_payload = edge_state_density(
        config=config,
        eigenvalues=eigenvalues,
        eigenvectors=eigenvectors,
        window_count=window_count,
    )
    return {
        "config": config,
        "hamiltonian": hamiltonian,
        "eigenvalues": eigenvalues,
        "eigenvectors": eigenvectors,
        "projector": projector,
        "u_matrix": u_matrix,
        "v_matrix": v_matrix,
        "bott_index": int(bott_integer),
        "winding_phases": winding_phases,
        "disorder_values": disorder_values,
        "validation": validation,
        "localizer": gap_payload,
        "edge_density": density_payload,
        "performance": {
            "cache_hit": bool(cache_details["cache_hit"]),
            "hamiltonian_build_seconds": float(cache_details["build_seconds"]),
            "localizer_compute_seconds": float(gap_payload["compute_seconds"]),
            "bott_seconds": float(bott_details["bott_seconds"]),
        },
        "solver": solver_details,
    }

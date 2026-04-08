from __future__ import annotations

from time import perf_counter

import numpy as np

from .bott import bott_index
from .bott import diagonalize_hamiltonian
from .bott import fermi_projection
from .bott import projected_unitaries
from .config import Task1Config
from .hamiltonian import real_space_coordinates
from .validation import validate_physics


def build_open_boundary_qwz(config: Task1Config, hopping: float = 1.0) -> np.ndarray:
    sigma_x = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)
    sigma_y = np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype=np.complex128)
    sigma_z = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=np.complex128)

    hop_x = 0.5 * hopping * sigma_z - 0.5j * hopping * sigma_x
    hop_y = 0.5 * hopping * sigma_z - 0.5j * hopping * sigma_y

    hamiltonian = np.zeros((config.hilbert_dim, config.hilbert_dim), dtype=np.complex128)

    def site_index(x_idx: int, y_idx: int) -> int:
        return x_idx * config.ny + y_idx

    for x_idx in range(config.nx):
        for y_idx in range(config.ny):
            site = site_index(x_idx, y_idx)
            block = slice(2 * site, 2 * (site + 1))
            hamiltonian[block, block] = config.mass * sigma_z

            if x_idx + 1 < config.nx:
                neighbor = site_index(x_idx + 1, y_idx)
                neighbor_block = slice(2 * neighbor, 2 * (neighbor + 1))
                hamiltonian[block, neighbor_block] = hop_x
                hamiltonian[neighbor_block, block] = hop_x.conj().T

            if y_idx + 1 < config.ny:
                neighbor = site_index(x_idx, y_idx + 1)
                neighbor_block = slice(2 * neighbor, 2 * (neighbor + 1))
                hamiltonian[block, neighbor_block] = hop_y
                hamiltonian[neighbor_block, block] = hop_y.conj().T

    return hamiltonian.astype(np.complex128)


def _density_grid_from_state(config: Task1Config, state: np.ndarray) -> np.ndarray:
    density = np.zeros(config.lattice_size, dtype=np.float64)
    for site in range(config.lattice_size):
        block = state[2 * site : 2 * (site + 1)]
        density[site] = float(np.sum(np.abs(block) ** 2))
    density_grid = density.reshape(config.nx, config.ny).T
    total = float(np.sum(density_grid))
    if total > 0.0:
        density_grid /= total
    return density_grid


def _radial_profile(config: Task1Config, density_grid: np.ndarray) -> list[dict]:
    center_x = config.nx // 2
    center_y = config.ny // 2
    yy, xx = np.indices(density_grid.shape, dtype=np.float64)
    integer_radius = np.rint(np.sqrt((xx - center_x) ** 2 + (yy - center_y) ** 2)).astype(int)

    profile = []
    for radius in range(0, min(config.nx, config.ny) // 2 + 1):
        mask = integer_radius == radius
        if not np.any(mask):
            continue
        profile.append(
            {
                "radius": int(radius),
                "mean_density": float(np.mean(density_grid[mask])),
                "max_density": float(np.max(density_grid[mask])),
            }
        )
    return profile


def _center_site(config: Task1Config) -> tuple[int, int, int]:
    center_x = config.nx // 2
    center_y = config.ny // 2
    site = center_x * config.ny + center_y
    return center_x, center_y, site


def _delta_trial_state(config: Task1Config, orbital_index: int) -> np.ndarray:
    center_x, center_y, site = _center_site(config)
    del center_x, center_y
    state = np.zeros(config.hilbert_dim, dtype=np.complex128)
    state[(2 * site) + orbital_index] = 1.0 + 0.0j
    return state


def _phase_wound_ring_seed(config: Task1Config, radius: int, orbital_index: int) -> np.ndarray:
    center_x, center_y, _ = _center_site(config)
    state = np.zeros(config.hilbert_dim, dtype=np.complex128)
    phase_sites = (
        (center_x + radius, center_y, 1.0 + 0.0j),
        (center_x, center_y + radius, 0.0 + 1.0j),
        (center_x - radius, center_y, -1.0 + 0.0j),
        (center_x, center_y - radius, 0.0 - 1.0j),
    )
    for x_idx, y_idx, phase in phase_sites:
        site = x_idx * config.ny + y_idx
        state[(2 * site) + orbital_index] = phase
    state /= np.linalg.norm(state)
    return state.astype(np.complex128)


def _normalize_state(state: np.ndarray, zero_tolerance: float) -> np.ndarray:
    norm = float(np.linalg.norm(state))
    if norm <= zero_tolerance:
        raise ValueError("Projected state norm vanished; cannot normalize Wannier state.")
    return (state / norm).astype(np.complex128)


def _density_metrics(config: Task1Config, density_grid: np.ndarray) -> dict:
    center_x, center_y, _ = _center_site(config)
    center_density = float(density_grid[center_y, center_x])
    mean_density = float(np.mean(density_grid))
    yy, xx = np.indices(density_grid.shape, dtype=np.float64)
    radii = np.sqrt((xx - center_x) ** 2 + (yy - center_y) ** 2)
    peak_index = np.unravel_index(np.argmax(density_grid), density_grid.shape)
    peak_radius = float(radii[peak_index])

    return {
        "center_density": center_density,
        "mean_density": mean_density,
        "center_to_mean_ratio": float(center_density / max(mean_density, 1.0e-12)),
        "peak_site": {
            "x": int(peak_index[1]),
            "y": int(peak_index[0]),
            "density": float(density_grid[peak_index]),
            "radius": peak_radius,
        },
    }


def _build_phase_payload(
    config: Task1Config,
    trial_state: np.ndarray,
    label: str,
    construction: str,
) -> dict:
    hamiltonian = build_open_boundary_qwz(config)
    eigenvalues, eigenvectors, solver_details = diagonalize_hamiltonian(hamiltonian)
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

    wannier_state = _normalize_state(projector @ trial_state, config.zero_tolerance)
    density_grid = _density_grid_from_state(config, wannier_state)
    metrics = _density_metrics(config, density_grid)

    return {
        "label": label,
        "construction": construction,
        "config": config,
        "hamiltonian": hamiltonian,
        "eigenvalues": eigenvalues,
        "u_matrix": u_matrix,
        "v_matrix": v_matrix,
        "bott_index": int(bott_integer),
        "winding_phases": winding_phases,
        "validation": validation,
        "solver": solver_details,
        "density_grid": density_grid.tolist(),
        "radial_profile": _radial_profile(config, density_grid),
        **metrics,
        "performance": {
            "hamiltonian_build_seconds": 0.0,
            "bott_seconds": float(bott_details["bott_seconds"]),
        },
    }


def _validation_summary(trivial: dict, topological: dict) -> dict:
    trivial_pass = bool(trivial["center_to_mean_ratio"] > 10.0)
    topological_center_pass = bool(topological["center_to_mean_ratio"] < 2.0)
    topological_ring_pass = bool(2.0 < topological["peak_site"]["radius"] < 6.0)
    return {
        "trivial_center_localization": {
            "center_to_mean_ratio": float(trivial["center_to_mean_ratio"]),
            "pass": trivial_pass,
        },
        "topological_center_suppression": {
            "center_to_mean_ratio": float(topological["center_to_mean_ratio"]),
            "pass": topological_center_pass,
        },
        "topological_ring_location": {
            "peak_radius": float(topological["peak_site"]["radius"]),
            "pass": topological_ring_pass,
        },
    }


def run_task5_physics(
    nx: int,
    ny: int,
    trivial_mass: float,
    topological_mass: float,
    disorder: float,
    disorder_seed: int,
    fermi: float,
) -> dict:
    del disorder_seed
    start = perf_counter()
    if disorder != 0.0:
        raise ValueError("Task 5 rewrite requires disorder = 0.0 to cleanly expose the obstruction.")

    trivial_config = Task1Config(
        nx=nx,
        ny=ny,
        mass=trivial_mass,
        disorder=0.0,
        disorder_seed=0,
        fermi=fermi,
        periodic_x=False,
        periodic_y=False,
    ).validated()
    topological_config = Task1Config(
        nx=nx,
        ny=ny,
        mass=topological_mass,
        disorder=0.0,
        disorder_seed=0,
        fermi=fermi,
        periodic_x=False,
        periodic_y=False,
    ).validated()

    # In this lattice basis the second orbital aligns with the localized trivial projector.
    trivial_seed = _delta_trial_state(trivial_config, orbital_index=1)
    topological_seed = _phase_wound_ring_seed(topological_config, radius=3, orbital_index=0)

    trivial = _build_phase_payload(
        config=trivial_config,
        trial_state=trivial_seed,
        label="Trivial Phase",
        construction="Projected center-site delta state on the local orbital.",
    )
    topological = _build_phase_payload(
        config=topological_config,
        trial_state=topological_seed,
        label="Topological Phase",
        construction="Projected phase-wound ring trial state exposing the Wannier obstruction.",
    )
    density_validation = _validation_summary(trivial, topological)
    total_seconds = perf_counter() - start

    return {
        "primary": topological,
        "comparison": {
            "trivial": trivial,
            "topological": topological,
        },
        "rho_trivial": trivial["density_grid"],
        "rho_topological": topological["density_grid"],
        "density_validation": density_validation,
        "performance": {
            "total_seconds": float(total_seconds),
            "memory_mb": float(
                (trivial["hamiltonian"].nbytes + topological["hamiltonian"].nbytes) / (1024.0 * 1024.0)
            ),
        },
    }

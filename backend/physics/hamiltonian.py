from __future__ import annotations

from time import perf_counter

import numpy as np
from scipy import sparse

from .cache import load_sparse_matrix
from .cache import save_sparse_matrix
from .config import Task1Config


def _site_index(x_idx: int, y_idx: int, ny: int) -> int:
    return x_idx * ny + y_idx


def _disorder_realization(config: Task1Config) -> np.ndarray:
    rng = np.random.default_rng(config.disorder_seed)
    values = rng.uniform(
        low=-0.5 * config.disorder,
        high=0.5 * config.disorder,
        size=config.lattice_size,
    )
    return values.astype(np.float64)


def _model_blocks() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sigma_x = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.complex128)
    sigma_y = np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype=np.complex128)
    sigma_z = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=np.complex128)

    hop_x = 0.5 * sigma_z - 0.5j * sigma_x
    hop_y = 0.5 * sigma_z - 0.5j * sigma_y
    return sigma_z, hop_x, hop_y


def build_hamiltonian(config: Task1Config) -> tuple[sparse.csr_matrix, np.ndarray, dict]:
    config = config.validated()
    cache_path = config.cache_path()
    cache_metadata = {
        "nx": config.nx,
        "ny": config.ny,
        "mass": config.mass,
        "disorder": config.disorder,
        "disorder_seed": config.disorder_seed,
        "periodic_x": config.periodic_x,
        "periodic_y": config.periodic_y,
    }

    if cache_path.exists():
        cached_matrix, cached_metadata = load_sparse_matrix(cache_path)
        if cached_metadata == cache_metadata:
            return cached_matrix, _disorder_realization(config), {"cache_hit": True, "build_seconds": 0.0}

    start = perf_counter()
    sigma_z, hop_x, hop_y = _model_blocks()
    dim = config.hilbert_dim
    disorder_values = _disorder_realization(config)
    matrix = sparse.lil_matrix((dim, dim), dtype=np.complex128)

    for x_idx in range(config.nx):
        for y_idx in range(config.ny):
            site = _site_index(x_idx, y_idx, config.ny)
            block = slice(2 * site, 2 * (site + 1))
            onsite = (config.mass * sigma_z) + disorder_values[site] * np.eye(2, dtype=np.complex128)
            matrix[block, block] = onsite

            right_x = (x_idx + 1) % config.nx
            if x_idx + 1 < config.nx or config.periodic_x:
                neighbor = _site_index(right_x, y_idx, config.ny)
                neighbor_block = slice(2 * neighbor, 2 * (neighbor + 1))
                matrix[block, neighbor_block] = hop_x
                matrix[neighbor_block, block] = hop_x.conj().T

            up_y = (y_idx + 1) % config.ny
            if y_idx + 1 < config.ny or config.periodic_y:
                neighbor = _site_index(x_idx, up_y, config.ny)
                neighbor_block = slice(2 * neighbor, 2 * (neighbor + 1))
                matrix[block, neighbor_block] = hop_y
                matrix[neighbor_block, block] = hop_y.conj().T

    hamiltonian = matrix.tocsr()
    build_seconds = perf_counter() - start
    save_sparse_matrix(cache_path, hamiltonian, cache_metadata)
    return hamiltonian, disorder_values, {"cache_hit": False, "build_seconds": build_seconds}


def real_space_coordinates(config: Task1Config) -> tuple[np.ndarray, np.ndarray]:
    x_sites = np.repeat(np.arange(config.nx, dtype=np.float64), config.ny)
    y_sites = np.tile(np.arange(config.ny, dtype=np.float64), config.nx)
    x_values = np.repeat(x_sites, 2)
    y_values = np.repeat(y_sites, 2)
    return x_values, y_values

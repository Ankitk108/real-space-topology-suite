from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import sparse


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def save_sparse_matrix(path: Path, matrix: sparse.csr_matrix, metadata: dict) -> None:
    ensure_parent(path)
    np.savez_compressed(
        path,
        data=matrix.data,
        indices=matrix.indices,
        indptr=matrix.indptr,
        shape=np.asarray(matrix.shape, dtype=np.int64),
        metadata=np.asarray([metadata], dtype=object),
    )


def load_sparse_matrix(path: Path) -> tuple[sparse.csr_matrix, dict]:
    payload = np.load(path, allow_pickle=True)
    matrix = sparse.csr_matrix(
        (payload["data"], payload["indices"], payload["indptr"]),
        shape=tuple(payload["shape"].tolist()),
        dtype=np.complex128,
    )
    metadata = payload["metadata"].item()
    return matrix, metadata

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Task1Config:
    nx: int = 12
    ny: int = 12
    mass: float = -1.0
    disorder: float = 0.8
    disorder_seed: int = 7
    fermi: float = 0.0
    periodic_x: bool = True
    periodic_y: bool = True
    cache_dir: str = "data/cache"
    export_path: str = "data/exports/task1.json"
    physics_log_dir: str = "logs/physics_checks"
    performance_log_dir: str = "logs/performance"
    gap_probe_delta: float = 1.0e-2
    zero_tolerance: float = 1.0e-12

    def validated(self) -> "Task1Config":
        if self.nx < 2 or self.ny < 2:
            raise ValueError("nx and ny must both be at least 2.")
        if self.disorder < 0.0:
            raise ValueError("disorder must be non-negative.")
        if self.gap_probe_delta <= 0.0:
            raise ValueError("gap_probe_delta must be positive.")
        return self

    @property
    def lattice_size(self) -> int:
        return self.nx * self.ny

    @property
    def hilbert_dim(self) -> int:
        return 2 * self.lattice_size

    def as_dict(self) -> dict:
        return asdict(self)

    def cache_path(self) -> Path:
        return self.resolve_path(self.cache_dir) / self.cache_file_name()

    def cache_file_name(self) -> str:
        boundary_tag = f"px{int(self.periodic_x)}_py{int(self.periodic_y)}"
        return (
            f"hamiltonian_nx{self.nx}_ny{self.ny}_m{self.mass:+.6f}"
            f"_w{self.disorder:.6f}_seed{self.disorder_seed}_{boundary_tag}.npz"
        )

    def resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return PROJECT_ROOT / path

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def matrix_to_serializable(matrix: np.ndarray, zero_tolerance: float) -> list[list[list[float]]]:
    rows = []
    for row in matrix:
        rows.append(
            [
                [float(np.real(value)), float(np.imag(value))]
                if abs(value) > zero_tolerance
                else [0.0, 0.0]
                for value in row
            ]
        )
    return rows


def write_json(path: str, payload: dict) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path

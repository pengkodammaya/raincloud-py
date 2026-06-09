"""The 'rain': jittered raw data points offset from the cloud."""

from __future__ import annotations

import numpy as np


def jittered_positions(
    n: int,
    position: float,
    jitter: float = 0.08,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Uniform jitter around ``position`` for ``n`` points."""
    rng = rng or np.random.default_rng()
    return position + rng.uniform(-jitter, jitter, size=n)

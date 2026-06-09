"""The 'cloud': a one-sided (half) violin built from a Gaussian KDE."""

from __future__ import annotations

import numpy as np


def gaussian_kde_1d(
    values: np.ndarray,
    grid: np.ndarray,
    bw_adjust: float = 1.0,
) -> np.ndarray:
    """Evaluate a Gaussian KDE on ``grid``.

    Self-contained so we don't pull in scipy. Uses Silverman's rule for the
    base bandwidth, scaled by ``bw_adjust`` (mirrors ggdist's ``adjust``).
    """
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    n = values.size
    if n < 2:
        return np.zeros_like(grid)

    std = np.std(values, ddof=1)
    iqr = np.subtract(*np.percentile(values, [75, 25]))
    spread = min(std, iqr / 1.349) if iqr > 0 else std
    if spread == 0:
        spread = std if std > 0 else 1.0

    bw = 0.9 * spread * n ** (-1 / 5) * bw_adjust  # Silverman
    if bw == 0:
        bw = 1.0

    # (grid - values) broadcast -> (len(grid), n)
    u = (grid[:, None] - values[None, :]) / bw
    kernel = np.exp(-0.5 * u**2) / np.sqrt(2 * np.pi)
    return kernel.sum(axis=1) / (n * bw)


def half_violin_path(
    values: np.ndarray,
    position: float,
    width: float = 0.4,
    bw_adjust: float = 1.0,
    side: str = "left",
    n_points: int = 256,
    cut: float = 2.0,
):
    """Return (axis_coords, density_offsets) tracing one half-violin.

    ``position`` is the categorical-axis location. The returned offsets are
    already placed relative to ``position`` and scaled to ``width``.
    """
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 2:
        return np.array([]), np.array([])

    lo, hi = values.min(), values.max()
    pad = cut * np.std(values, ddof=1) if values.size > 1 else 0.0
    grid = np.linspace(lo - pad, hi + pad, n_points)

    dens = gaussian_kde_1d(values, grid, bw_adjust=bw_adjust)
    if dens.max() > 0:
        dens = dens / dens.max() * width

    offsets = position + dens if side == "right" else position - dens
    return grid, offsets

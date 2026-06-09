"""Public ``raincloud`` plotting function."""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from ._cloud import half_violin_path
from ._data import resolve_groups, resolve_paired
from ._rain import jittered_positions

_CLOUD_SIDE = "right"  # cloud bulges in +category direction; rain/box sit below


def _draw_cloud(ax, values, base, *, orient, color, width_violin, bw_adjust, cloud_alpha):
    """Half-violin for one group at category position ``base``."""
    grid, dens = half_violin_path(
        values, position=base, width=width_violin, bw_adjust=bw_adjust, side=_CLOUD_SIDE
    )
    if not grid.size:
        return
    if orient == "h":
        ax.fill_between(grid, base, dens, color=color, alpha=cloud_alpha, lw=0)
    else:
        ax.fill_betweenx(grid, base, dens, color=color, alpha=cloud_alpha, lw=0)


def _draw_box(ax, values, base, *, orient, width_box, offset):
    """Boxplot summary sitting between cloud and rain."""
    box_pos = base - offset / 2
    box_kwargs = dict(
        positions=[box_pos],
        widths=width_box,
        showfliers=False,
        patch_artist=True,
        boxprops=dict(facecolor="white", color="0.3"),
        medianprops=dict(color="0.1"),
        whiskerprops=dict(color="0.3"),
        capprops=dict(color="0.3"),
        manage_ticks=False,
        zorder=2,
    )
    # matplotlib >=3.9 renamed the `vert` bool to `orientation`
    if tuple(int(p) for p in mpl.__version__.split(".")[:2]) >= (3, 9):
        box_kwargs["orientation"] = "vertical" if orient == "v" else "horizontal"
    else:
        box_kwargs["vert"] = orient == "v"
    ax.boxplot(values, **box_kwargs)


def _scatter(ax, values, cat_positions, *, orient, color, point_size, point_alpha):
    if orient == "h":
        ax.scatter(values, cat_positions, s=point_size, color=color,
                   alpha=point_alpha, edgecolors="none", zorder=3)
    else:
        ax.scatter(cat_positions, values, s=point_size, color=color,
                   alpha=point_alpha, edgecolors="none", zorder=3)


def _set_category_axis(ax, labels, *, orient, x, y):
    ticks = list(range(len(labels)))
    if orient == "h":
        ax.set_yticks(ticks)
        ax.set_yticklabels(labels)
        if x:
            ax.set_xlabel(x)
    else:
        ax.set_xticks(ticks)
        ax.set_xticklabels(labels)
        if y:
            ax.set_ylabel(y)


def raincloud(
    data=None,
    x: str | None = None,
    y: str | None = None,
    *,
    id: str | None = None,  # noqa: A002 - user-facing kwarg
    paired: bool = False,
    ax: plt.Axes | None = None,
    orient: str = "h",
    palette=None,
    width_violin: float = 0.4,
    width_box: float = 0.1,
    jitter: float = 0.08,
    point_size: float = 12.0,
    point_alpha: float = 0.5,
    cloud_alpha: float = 0.7,
    show_boxplot: bool = True,
    bw_adjust: float = 1.0,
    offset: float = 0.20,
    line_color: str = "0.6",
    line_alpha: float = 0.4,
    line_width: float = 0.6,
    seed: int | None = None,
) -> plt.Axes:
    """Draw a raincloud plot.

    A raincloud combines three layers per group:

    * **cloud** - a half-violin (KDE) showing the distribution shape
    * **rain**  - jittered raw data points
    * (optional) **boxplot** - median / IQR summary sitting between them

    Repeated-measures / paired data
    -------------------------------
    Pass ``id=`` (with a long-form frame) or ``paired=True`` (with a wide
    mapping or 2-D array) to draw a **paired raincloud**: the same subject's
    observations are connected by a thin line across conditions, making
    within-subject change visible. This is the feature most requested for
    pre/post and crossover designs.

    Parameters
    ----------
    data, x, y
        Long-form DataFrame with ``x``/``y`` column names, OR a mapping of
        ``{label: values}``, OR a sequence of arrays, OR a single 1-D array.
    id
        Subject/identifier column for paired data (long-form only). Supplying
        it implies ``paired=True``.
    paired
        Force paired mode for wide-mapping or 2-D-array input, where rows are
        aligned by subject.
    orient
        ``"h"`` (default) horizontal; ``"v"`` vertical.
    offset
        Gap between the cloud and the rain, in category-axis units.
    line_color, line_alpha, line_width
        Styling for the connecting lines in paired mode.

    Returns
    -------
    matplotlib.axes.Axes
    """
    if orient not in ("h", "v"):
        raise ValueError("orient must be 'h' or 'v'")

    ax = ax or plt.gca()
    rng = np.random.default_rng(seed)
    is_paired = paired or id is not None

    if is_paired:
        labels, matrix = resolve_paired(data, x=x, y=y, id=id, orient=orient)
        n_cond = len(labels)
    else:
        labels, groups = resolve_groups(data, x=x, y=y, orient=orient)
        n_cond = len(groups)

    if palette is None:
        cmap = plt.get_cmap("tab10")
        palette = [cmap(i % 10) for i in range(n_cond)]

    # ------------------------------------------------------------------
    # Paired mode: clouds/boxes per condition, then connecting lines.
    # ------------------------------------------------------------------
    if is_paired:
        rain_pos = []  # category-axis position of each subject, per condition
        for j in range(len(labels)):
            col = matrix[:, j]
            finite = col[np.isfinite(col)]
            color = palette[j % len(palette)]
            base = float(j)

            if finite.size:
                _draw_cloud(ax, finite, base, orient=orient, color=color,
                            width_violin=width_violin, bw_adjust=bw_adjust,
                            cloud_alpha=cloud_alpha)

            rain_base = base - offset
            jit = jittered_positions(matrix.shape[0], rain_base, jitter=jitter, rng=rng)
            rain_pos.append(jit)

            mask = np.isfinite(col)
            _scatter(ax, col[mask], jit[mask], orient=orient, color=color,
                     point_size=point_size, point_alpha=point_alpha)

            if show_boxplot and finite.size:
                _draw_box(ax, finite, base, orient=orient,
                          width_box=width_box, offset=offset)

        # connecting lines: one polyline per subject across conditions
        rain_pos = np.asarray(rain_pos)  # (n_cond, n_subjects)
        for s in range(matrix.shape[0]):
            vals_s = matrix[s, :]
            cats_s = rain_pos[:, s]
            # NaN in vals_s breaks the line automatically
            if orient == "h":
                ax.plot(vals_s, cats_s, color=line_color, alpha=line_alpha,
                        lw=line_width, zorder=1)
            else:
                ax.plot(cats_s, vals_s, color=line_color, alpha=line_alpha,
                        lw=line_width, zorder=1)

        _set_category_axis(ax, labels, orient=orient, x=x, y=y)
        return ax

    # ------------------------------------------------------------------
    # Unpaired mode.
    # ------------------------------------------------------------------
    for i, (_label, values) in enumerate(zip(labels, groups, strict=True)):
        values = values[np.isfinite(values)]
        if values.size == 0:
            continue
        color = palette[i % len(palette)]
        base = float(i)

        _draw_cloud(ax, values, base, orient=orient, color=color,
                    width_violin=width_violin, bw_adjust=bw_adjust,
                    cloud_alpha=cloud_alpha)

        rain_base = base - offset
        jit = jittered_positions(values.size, rain_base, jitter=jitter, rng=rng)
        _scatter(ax, values, jit, orient=orient, color=color,
                 point_size=point_size, point_alpha=point_alpha)

        if show_boxplot:
            _draw_box(ax, values, base, orient=orient,
                      width_box=width_box, offset=offset)

    _set_category_axis(ax, labels, orient=orient, x=x, y=y)
    return ax

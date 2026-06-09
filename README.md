# raincloud-py

> Raincloud plots for Python — half-violin + jittered points + boxplot, in one call.

[![PyPI](https://img.shields.io/badge/pypi-v0.1.0-blue)](https://pypi.org/project/raincloud-py/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A **raincloud plot** shows a distribution honestly: the *cloud* (a half-violin / KDE)
reveals the shape, the *rain* (jittered raw points) shows every observation, and an
optional boxplot summarises the median and spread. It is a transparent replacement for
the bar-chart-with-error-bars, which hides bimodality, outliers, and sample size.

The technique was popularised by **Allen et al. (2019/2021)**, *"Raincloud plots: a
multi-platform tool for robust data visualization"* (Wellcome Open Research) — widely
adopted in neuroscience, psychology, and clinical research. R has excellent support via
`ggdist` and `ggrain`.

In Python, [`ptitprince`](https://github.com/pog87/PtitPrince) is the established
option. `raincloud-py` differs deliberately on three axes:

- **No seaborn.** `ptitprince` is built on seaborn (→ pandas + scipy + statsmodels) and
  tracks its API churn. `raincloud-py` depends only on `matplotlib` + `numpy`.
- **Dataframe-agnostic.** pandas, polars, dicts, or bare arrays — no pandas requirement.
- **Paired/repeated-measures built in.** Connecting lines for pre/post and crossover
  designs, a frequently requested capability.

## Why

- **Distribution-honest.** Bar charts collapse a distribution to a single mean. Rainclouds don't.
- **One call.** `rc.raincloud(data)` — no manual assembly of three layers.
- **Light.** Hard dependencies are just `matplotlib` and `numpy`. No scipy, no seaborn.
- **Flexible input.** pandas, polars, dict-of-arrays, or a bare list — all work.

## Install

```bash
uv add raincloud-py
# or, with optional dataframe extras:
uv add "raincloud-py[pandas]"
uv add "raincloud-py[polars]"
```

## Quickstart

```python
import numpy as np
import matplotlib.pyplot as plt
import raincloud as rc

rng = np.random.default_rng(0)
data = {
    "control":   rng.normal(0.0, 1.0, 200),
    "treatment": np.concatenate([rng.normal(-1, 0.5, 100),
                                  rng.normal(2.5, 0.6, 100)]),  # bimodal!
}

rc.raincloud(data)
plt.xlabel("response")
plt.tight_layout()
plt.show()
```

The bimodality in `treatment` is obvious in a raincloud and invisible in a bar chart.

### Long-form DataFrame

```python
import polars as pl
df = pl.DataFrame({"group": ["a", "a", "b", "b", "c"],
                   "value": [1.2, 0.8, 3.1, 2.9, 5.0]})
rc.raincloud(df, x="value", y="group")   # horizontal (default)
```

### Vertical orientation

```python
rc.raincloud(data, orient="v")
```

### Paired / repeated-measures rainclouds

The feature most asked for in pre/post and crossover designs: connect each
subject's observations across conditions so within-subject change is visible.

```python
import numpy as np
import raincloud as rc

rng = np.random.default_rng(7)
pre = rng.normal(50, 8, 30)
post = pre + rng.normal(6, 5, 30)   # most subjects improve

# wide form: each array is aligned by subject (row i = same person)
rc.raincloud({"pre": pre, "post": post}, paired=True)
```

Or long form with a subject id column (supplying `id` implies paired mode):

```python
rc.raincloud(df, x="score", y="time", id="subject")
```

Missing measurements (`NaN`) simply break that subject's line. Style the lines
with `line_color`, `line_alpha`, and `line_width`.

## API

```python
raincloud(
    data, x=None, y=None, *,
    id=None, paired=False,           # repeated-measures / paired plots
    ax=None, orient="h", palette=None,
    width_violin=0.4, width_box=0.1, jitter=0.08,
    point_size=12.0, point_alpha=0.5, cloud_alpha=0.7,
    show_boxplot=True, bw_adjust=1.0, offset=0.20,
    line_color="0.6", line_alpha=0.4, line_width=0.6,
    seed=None,
) -> matplotlib.axes.Axes
```

Returns the `Axes`, so you compose normally with the rest of matplotlib.

## Maintained with Codex

This repository uses **OpenAI Codex** in its maintainer automation. Three
workflows under [`.github/workflows`](.github/workflows) run
[`openai/codex-action`](https://github.com/openai/codex-action) in a read-only
sandbox:

- **PR review** (`codex-review.yml`) — every pull request gets a focused review
  of the diff (KDE/geometry correctness, matplotlib version pitfalls, accidental
  new dependencies, missing tests).
- **Issue triage** (`codex-triage.yml`) — new issues are classified and routed to
  the likely source file, with untrusted issue text isolated against prompt
  injection.
- **Release notes** (`codex-release.yml`) — tagging `v*` drafts grouped,
  user-facing release notes from the commit history and publishes the release.

Repo-wide conventions Codex follows live in [`AGENTS.md`](AGENTS.md).

## Citation

If you use raincloud plots in published work, please cite the original method:

> Allen, M., Poggiali, D., Whitaker, K., Marshall, T. R., van Langen, J., & Kievit, R. A.
> (2021). Raincloud plots: a multi-platform tool for robust data visualization.
> *Wellcome Open Research*, 4:63.

## License

MIT

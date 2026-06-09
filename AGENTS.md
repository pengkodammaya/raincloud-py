# AGENTS.md

Repo-level instructions for **Codex** (and other coding agents). Codex reads this
file automatically when working in this repository — both locally via the Codex
CLI and in the GitHub Actions workflows under `.github/workflows/codex-*.yml`.

## What this project is

`raincloud-py` is a small, dependency-light library that draws **raincloud plots**
(half-violin "cloud" + jittered "rain" + optional boxplot) with matplotlib. Hard
dependencies are **only `matplotlib` and `numpy`** — this is a load-bearing
constraint, not an accident. Do not add scipy, seaborn, pandas, or polars to
`dependencies`. pandas/polars are supported via duck typing and live in optional
extras only.

## Architecture

| File | Responsibility |
|------|----------------|
| `src/raincloud/_core.py` | Public `raincloud()` entry point; orchestrates the cloud/rain/box layers; handles orientation and the paired/repeated-measures branch with connecting lines. |
| `src/raincloud/_cloud.py` | Self-contained Gaussian KDE (Silverman bandwidth × `bw_adjust`) and the one-sided half-violin path. No scipy. |
| `src/raincloud/_rain.py` | Uniform jitter around each group's base position. |
| `src/raincloud/_data.py` | Duck-typed input resolution (`resolve_groups`, `resolve_paired`). Detects dataframes via `columns` + `__getitem__` rather than importing pandas/polars. |

## Conventions

- Public API is keyword-only after the data args; return a matplotlib `Axes` and
  **never** call `plt.show()`.
- Keep parameter names echoing `ggdist`/`seaborn` where reasonable.
- Guard KDE edge cases (n < 2, zero variance) by returning empty/flat densities,
  never raising.
- Matplotlib changes APIs across versions (e.g. `boxplot` `vert` → `orientation`
  in 3.9). Use version-aware branches; CI runs Python 3.10–3.13.

## How to verify a change

```bash
uv pip install -e ".[dev]"
ruff check .
pytest -q
```

All of the above must pass before a change is considered done. When you change
plotting geometry, prefer asserting on Axes artifacts (tick labels, line counts,
offsets) the way `tests/test_raincloud.py` already does.

## Review guidance (for the PR-review workflow)

Focus reviews on: correctness of the KDE/geometry math, matplotlib version
pitfalls, accidental new hard dependencies, public-API breaks, and missing test
coverage. Be concise and only flag the changed lines.

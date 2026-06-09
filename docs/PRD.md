# PRD — `raincloud-py`

**Status:** Draft v1.0 · **Owner:** You · **Last updated:** 2026-06-09

---

## 1. Summary

`raincloud-py` is a small, dependency-light Python library that produces **raincloud plots** — a composite visualization combining a half-violin (KDE "cloud"), jittered raw data points ("rain"), and an optional boxplot. It is the Python analogue of R's `ggdist` / `ggrain`, which currently have no clean, maintained equivalent in the matplotlib ecosystem.

The goal is a library that does one thing well: `rc.raincloud(data)` returns a publication-quality raincloud in a single call, while remaining fully composable with matplotlib.

## 2. Problem & motivation

The default scientific chart for comparing groups is the bar chart with error bars. It is actively misleading: it collapses an entire distribution into a mean ± SE, hiding bimodality, skew, outliers, and sample size. Two completely different distributions can produce identical bar charts.

Raincloud plots fix this by showing the distribution shape, every raw observation, and a robust summary simultaneously. The method (Allen et al., *Wellcome Open Research*, 2021) is widely cited and adopted in neuroscience, psychology, and clinical research.

The tooling gap is asymmetric:

- **R** has first-class support: `ggdist::stat_halfeye()`, `ggrain`, `raincloudplots`.
- **Python** has one established package, [`ptitprince`](https://github.com/pog87/PtitPrince)
  (~319★, actively maintained, last release Oct 2025). It is built on **seaborn**, which
  brings a heavy transitive dependency chain (pandas + scipy + statsmodels) and ongoing
  API-churn maintenance (its changelog tracks seaborn 0.13/0.14 breakage).

`raincloud-py` does not claim to fill an empty gap — it competes on a clear wedge:
**(1)** depend only on `matplotlib` + `numpy`; **(2)** be dataframe-agnostic (pandas *or*
polars *or* neither); **(3)** ship **paired/repeated-measures** rainclouds — connecting
lines for pre/post designs — which `ptitprince` lists as an unfinished roadmap item and
no Python package does cleanly.

## 3. Goals / non-goals

### Goals
- One-call API: `raincloud(data, ...)` returning a matplotlib `Axes`.
- Accept pandas, polars, dict-of-arrays, and bare sequences — without forcing any dataframe dependency.
- Hard dependencies limited to `matplotlib` and `numpy`.
- Horizontal and vertical orientation.
- **Paired / repeated-measures rainclouds** with connecting lines (the primary differentiator vs `ptitprince`).
- Sensible defaults that look good with zero tuning, plus knobs for power users.
- Tested on Python 3.10–3.13.

### Non-goals (v1)
- A full grammar-of-graphics layer system (that is `ggdist`'s scope; out of scope here).
- Bayesian posterior visualization, interval families, dotplots (possible later).
- Interactive/web backends (Plotly, Bokeh). Matplotlib only for v1.
- Seaborn integration shim (may revisit if demand appears).

## 4. Users

- **Researchers** writing papers who want honest distribution figures.
- **Data scientists / analysts** comparing groups in notebooks.
- **R-to-Python migrants** who miss `ggdist` and want a familiar capability.

## 5. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F1 | `raincloud(data, x, y)` accepts long-form pandas/polars frames | Must |
| F2 | `raincloud(dict)` accepts `{label: array}` mapping | Must |
| F3 | `raincloud(seq)` accepts a sequence of arrays or a single array | Must |
| F4 | Half-violin KDE with adjustable bandwidth (`bw_adjust`) | Must |
| F5 | Jittered raw points with adjustable jitter/size/alpha | Must |
| F6 | Optional boxplot layer (`show_boxplot`) | Must |
| F7 | Horizontal (default) and vertical orientation | Must |
| F8 | Custom color palette; sensible default (tab10) | Must |
| F9 | Returns `Axes`; accepts an existing `ax` for composition | Must |
| F10 | Deterministic output via `seed` | Should |
| F11 | Per-group color/label ordering preserved from input | Should |
| F12 | Works headless (Agg) for CI image tests | Should |
| F13 | Paired mode via `id` (long-form) or `paired=True` (wide / 2-D) | Must |
| F14 | Connecting lines per subject across conditions | Must |
| F15 | Missing paired observations (`NaN`) break the line, no error | Must |
| F16 | Configurable line color / alpha / width | Should |

## 6. API design

```python
raincloud(
    data, x=None, y=None, *,
    id=None,               # subject column -> paired mode (long-form)
    paired=False,          # force paired mode (wide mapping / 2-D array)
    ax=None,
    orient="h",            # "h" | "v"
    palette=None,          # list of colors; defaults to tab10
    width_violin=0.4,
    width_box=0.1,
    jitter=0.08,
    point_size=12.0,
    point_alpha=0.5,
    cloud_alpha=0.7,
    show_boxplot=True,
    bw_adjust=1.0,         # mirrors ggdist's `adjust`
    offset=0.20,           # gap between cloud and rain
    line_color="0.6",      # paired connecting-line style
    line_alpha=0.4,
    line_width=0.6,
    seed=None,
) -> matplotlib.axes.Axes
```

**Paired input shapes** resolve to an `(n_subjects, n_conditions)` matrix:
long-form frame + `id`, a wide `{condition: aligned_array}` mapping, or a 2-D array
(rows = subjects). `NaN` marks a missing measurement and breaks that subject's line.

Design principles: matplotlib-native (returns `Axes`, never calls `show()`); keyword-only after the data args to keep call sites readable; names chosen to echo `ggdist`/`seaborn` where reasonable to lower the learning curve.

## 7. Technical design

- **`_data.py`** — duck-typed input resolution. `resolve_groups` handles unpaired shapes; `resolve_paired` builds the `(n_subjects, n_conditions)` matrix from long-form+id, wide mapping, or 2-D array. Dataframes are detected via `columns` + `__getitem__` rather than imported, so neither pandas nor polars is a hard dependency.
- **`_cloud.py`** — self-contained Gaussian KDE (Silverman bandwidth × `bw_adjust`) so we avoid a scipy dependency. Produces a one-sided (half) violin path.
- **`_rain.py`** — uniform jitter around each group's base position.
- **`_core.py`** — orchestrates the layers. Shared helpers (`_draw_cloud`, `_draw_box`, `_scatter`) feed two branches: unpaired (per-group loop) and paired (per-condition layers + a connecting polyline per subject). Handles orientation + matplotlib version quirks (e.g. `boxplot` `vert`→`orientation` rename in mpl 3.9).

Layer stacking (per group at category position `i`): cloud bulges in the `+` direction from `i`; boxplot sits at `i − offset/2`; rain at `i − offset`. In paired mode each subject's jittered rain positions are recorded so the connecting line passes through the actual plotted points; `NaN` values segment the polyline automatically.

## 8. Testing strategy

- Unit tests for each input shape (mapping, sequence, single array, pandas, polars).
- Numerical test: KDE integrates to ≈ 1 over a wide grid.
- Geometry test: half-violin stays on one side of its base position.
- End-to-end: `raincloud()` returns an `Axes` with correct tick labels, both orientations.
- Optional: `pytest-mpl` image-regression baselines.
- CI matrix: Python 3.10–3.13 via GitHub Actions + `uv`.

## 9. Packaging & distribution

- Build backend: `hatchling`. Source layout under `src/`.
- Install: `uv add raincloud-py`; extras `[pandas]`, `[polars]`, `[dev]`.
- Publish to PyPI on tagged release; TestPyPI first.

## 10. Milestones

| Milestone | Scope | Effort |
|-----------|-------|--------|
| M0 — Core (done) | Cloud + rain + box, both orientations, all input shapes, **paired/repeated-measures with connecting lines**, tests green | ~1.5 days |
| M1 — Polish | Docs site (MkDocs), gallery of examples, image-regression baselines | ~1 day |
| M2 — Release | PyPI `v0.1.0`, README badges, CITATION.cff, announcement post | ~0.5 day |
| M3 — Stretch | `half_eye` interval option, faceting helper, seaborn-style `hue`, logarithmic density estimate (LDE) cloud | TBD |

## 11. Success metrics

- Installs cleanly with two hard deps and runs the quickstart in < 5 lines.
- PyPI release published with green CI across the version matrix.
- Early traction signals: GitHub stars, an issue or PR from an external user, inbound links from a tutorial or paper.

## 12. Risks

- **Crowded niche perception.** Mitigation: differentiate on light dependencies, polars support, and active maintenance vs. stale alternatives.
- **KDE edge cases** (tiny n, zero variance). Mitigation: guard rails already return empty/flat densities instead of erroring.
- **Matplotlib API drift.** Mitigation: version-aware branches + CI across releases.

## 13. Open questions

- Add a `hue`/sub-grouping dimension in v1, or defer to M3?
- For paired plots, offer optional **color-by-direction** lines (e.g. green if the subject increased, red if decreased)?
- Ship `pytest-mpl` baselines in-repo (size cost) or generate in CI only?
- Expose the KDE as a public helper for users who want just the cloud?

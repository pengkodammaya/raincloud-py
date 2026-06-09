"""Smoke + behaviour tests. Run with: uv run pytest"""

import matplotlib

matplotlib.use("Agg")  # headless

import matplotlib.pyplot as plt
import numpy as np
import pytest

import raincloud as rc
from raincloud._cloud import gaussian_kde_1d, half_violin_path
from raincloud._data import resolve_groups


@pytest.fixture
def two_groups():
    rng = np.random.default_rng(0)
    return {"a": rng.normal(0, 1, 100), "b": rng.normal(2, 1.5, 100)}


# --- data adapter ---------------------------------------------------
def test_resolve_mapping(two_groups):
    labels, groups = resolve_groups(two_groups)
    assert labels == ["a", "b"]
    assert len(groups) == 2 and groups[0].shape == (100,)


def test_resolve_single_array():
    labels, groups = resolve_groups([1.0, 2.0, 3.0])
    assert labels == [""]
    assert groups[0].tolist() == [1.0, 2.0, 3.0]


def test_resolve_sequence_of_arrays():
    labels, groups = resolve_groups([[1, 2, 3], [4, 5, 6]])
    assert labels == ["0", "1"]
    assert len(groups) == 2


def test_resolve_dataframe_requires_xy():
    class FakeDF:
        columns = ["g", "v"]

        def __getitem__(self, k):
            return [1, 2, 3]

    with pytest.raises(ValueError):
        resolve_groups(FakeDF())  # missing x/y


def test_resolve_pandas_long_form():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"grp": ["x", "x", "y", "y"], "val": [1.0, 2.0, 8.0, 9.0]})
    labels, groups = resolve_groups(df, x="val", y="grp", orient="h")
    assert labels == ["x", "y"]
    assert groups[0].tolist() == [1.0, 2.0]


def test_resolve_polars_long_form():
    pl = pytest.importorskip("polars")
    df = pl.DataFrame({"grp": ["x", "x", "y"], "val": [1.0, 2.0, 9.0]})
    labels, groups = resolve_groups(df, x="val", y="grp", orient="h")
    assert labels == ["x", "y"]


# --- kde + cloud ----------------------------------------------------
def test_kde_integrates_to_one():
    rng = np.random.default_rng(1)
    vals = rng.normal(0, 1, 5000)
    grid = np.linspace(-6, 6, 2000)
    dens = gaussian_kde_1d(vals, grid)
    trapezoid = getattr(np, "trapezoid", getattr(np, "trapz", None))
    area = trapezoid(dens, grid)
    assert abs(area - 1.0) < 0.05


def test_half_violin_one_sided():
    vals = np.random.default_rng(2).normal(size=200)
    grid, off = half_violin_path(vals, position=1.0, width=0.4, side="left")
    assert grid.size > 0
    assert (off <= 1.0 + 1e-9).all()  # all offsets on the left of position


# --- end to end -----------------------------------------------------
def test_raincloud_returns_axes(two_groups):
    ax = rc.raincloud(two_groups, seed=0)
    assert ax.get_yticklabels()[0].get_text() == "a"
    plt.close("all")


def test_raincloud_vertical(two_groups):
    ax = rc.raincloud(two_groups, orient="v", seed=0)
    assert ax.get_xticklabels()[1].get_text() == "b"
    plt.close("all")


def test_raincloud_bad_orient(two_groups):
    with pytest.raises(ValueError):
        rc.raincloud(two_groups, orient="diagonal")


# --- paired / repeated-measures -------------------------------------
from raincloud._data import resolve_paired  # noqa: E402


def test_resolve_paired_wide_mapping():
    labels, matrix = resolve_paired({"pre": [1.0, 2.0, 3.0], "post": [2.0, 3.0, 4.0]})
    assert labels == ["pre", "post"]
    assert matrix.shape == (3, 2)
    assert matrix[0].tolist() == [1.0, 2.0]


def test_resolve_paired_unequal_lengths_raises():
    with pytest.raises(ValueError):
        resolve_paired({"pre": [1.0, 2.0], "post": [2.0]})


def test_resolve_paired_2d_array():
    labels, matrix = resolve_paired([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], paired=True) \
        if False else resolve_paired(np.array([[1.0, 2.0], [3.0, 4.0]]))
    assert labels == ["0", "1"]
    assert matrix.shape == (2, 2)


def test_resolve_paired_long_form_with_id():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({
        "subject": ["s1", "s1", "s2", "s2"],
        "cond": ["pre", "post", "pre", "post"],
        "val": [1.0, 2.0, 5.0, 4.0],
    })
    labels, matrix = resolve_paired(df, x="val", y="cond", id="subject", orient="h")
    assert labels == ["pre", "post"]
    assert matrix.shape == (2, 2)
    assert matrix[0].tolist() == [1.0, 2.0]   # s1: pre, post
    assert matrix[1].tolist() == [5.0, 4.0]   # s2: pre, post


def test_resolve_paired_long_form_requires_id():
    class FakeDF:
        columns = ["cond", "val"]

        def __getitem__(self, k):
            return [1, 2]

    with pytest.raises(ValueError):
        resolve_paired(FakeDF(), x="val", y="cond")  # no id


def test_paired_handles_missing_observations():
    # subject 1 missing the 'post' measurement -> NaN, line should break
    labels, matrix = resolve_paired({"pre": [1.0, 2.0], "post": [3.0, np.nan]})
    ax = rc.raincloud({"pre": [1.0, 2.0], "post": [3.0, np.nan]}, paired=True, seed=0)
    assert len(ax.get_yticklabels()) == 2
    plt.close("all")


def test_paired_id_implies_paired_mode():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({
        "subj": ["a", "a", "b", "b"],
        "time": ["t1", "t2", "t1", "t2"],
        "score": [10.0, 12.0, 8.0, 7.0],
    })
    ax = rc.raincloud(df, x="score", y="time", id="subj", show_boxplot=False, seed=0)
    # connecting lines exist (one Line2D per subject = 2)
    assert len(ax.lines) == 2
    plt.close("all")


def test_paired_draws_one_line_per_subject():
    ax = rc.raincloud({"pre": [1.0, 2.0, 3.0], "post": [2.0, 3.0, 4.0]},
                      paired=True, show_boxplot=False, seed=0)
    assert len(ax.lines) == 3  # 3 subjects, no box artifacts
    plt.close("all")

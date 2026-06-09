"""Lightweight input handling.

The goal is to accept long-form data from pandas, polars, or plain
Python/NumPy containers *without* requiring any of them as hard dependencies.
We duck-type instead of importing, so the package installs with just
matplotlib + numpy.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np


def _is_dataframe(obj) -> bool:
    """True for anything that looks like a pandas/polars DataFrame."""
    return hasattr(obj, "columns") and hasattr(obj, "__getitem__")


def _column_as_array(df, name: str) -> np.ndarray:
    """Extract a single column from a pandas or polars frame as ndarray."""
    col = df[name]
    # polars Series -> .to_numpy(); pandas Series -> .to_numpy() too.
    if hasattr(col, "to_numpy"):
        return col.to_numpy()
    return np.asarray(col)


def resolve_groups(
    data=None,
    x: str | None = None,
    y: str | None = None,
    *,
    orient: str = "h",
) -> tuple[list[str], list[np.ndarray]]:
    """Normalise many input shapes into (labels, list_of_value_arrays).

    Supported call styles
    ----------------------
    1. Long-form frame:      resolve_groups(df, x="group", y="value")
    2. Mapping of arrays:    resolve_groups({"a": [...], "b": [...]})
    3. Sequence of arrays:   resolve_groups([[...], [...]])
    4. Single array:         resolve_groups([1, 2, 3])

    ``orient`` only decides which of x/y is the categorical axis when a
    frame is passed: "h" (default) means distributions run horizontally,
    so the category is on y and values on x.
    """
    # --- Style 1: DataFrame (pandas or polars) -------------------------
    if _is_dataframe(data):
        if x is None or y is None:
            raise ValueError(
                "When passing a DataFrame you must supply both `x` and `y`."
            )
        cat_col, val_col = (y, x) if orient == "h" else (x, y)
        cats = _column_as_array(data, cat_col)
        vals = _column_as_array(data, val_col)
        labels = list(dict.fromkeys(cats.tolist()))  # preserve first-seen order
        groups = [np.asarray(vals[cats == lab], dtype=float) for lab in labels]
        return [str(label) for label in labels], groups

    # --- Style 2: Mapping {label: values} ------------------------------
    if isinstance(data, Mapping):
        labels = [str(k) for k in data.keys()]
        groups = [np.asarray(v, dtype=float).ravel() for v in data.values()]
        return labels, groups

    # --- Style 4: single 1-D array -------------------------------------
    arr = np.asarray(data, dtype=float)
    if arr.ndim == 1:
        return [""], [arr]

    # --- Style 3: sequence of arrays / 2-D array -----------------------
    if isinstance(data, Sequence) or arr.ndim == 2:
        groups = [np.asarray(g, dtype=float).ravel() for g in data]
        labels = [str(i) for i in range(len(groups))]
        return labels, groups

    raise TypeError(f"Unsupported data type: {type(data)!r}")


def resolve_paired(
    data=None,
    x: str | None = None,
    y: str | None = None,
    id: str | None = None,  # noqa: A002 - matches user-facing kwarg name
    *,
    orient: str = "h",
) -> tuple[list[str], np.ndarray]:
    """Normalise repeated-measures input into (labels, matrix).

    ``matrix`` has shape ``(n_subjects, n_conditions)``; row ``s`` is one
    subject measured across every condition. Missing measurements are ``NaN``,
    which lets connecting lines break cleanly.

    Supported call styles
    ----------------------
    1. Long-form frame with an id column:
       ``resolve_paired(df, x="value", y="condition", id="subject")``
    2. Wide mapping, aligned by position (subject i = row i in every array):
       ``resolve_paired({"pre": [...], "post": [...]})``
    3. 2-D array, rows = subjects, columns = conditions.
    """
    # --- Style 1: long-form DataFrame with id --------------------------
    if _is_dataframe(data):
        if x is None or y is None or id is None:
            raise ValueError(
                "Paired DataFrame input requires `x`, `y`, and `id`."
            )
        cat_col, val_col = (y, x) if orient == "h" else (x, y)
        cats = _column_as_array(data, cat_col)
        vals = _column_as_array(data, val_col)
        ids = _column_as_array(data, id)

        labels = list(dict.fromkeys(cats.tolist()))
        subjects = list(dict.fromkeys(ids.tolist()))
        cond_ix = {c: j for j, c in enumerate(labels)}
        subj_ix = {s: i for i, s in enumerate(subjects)}

        matrix = np.full((len(subjects), len(labels)), np.nan)
        for v, c, s in zip(vals, cats, ids, strict=True):
            matrix[subj_ix[s], cond_ix[c]] = float(v)
        return [str(label) for label in labels], matrix

    # --- Style 2: wide mapping, aligned by position --------------------
    if isinstance(data, Mapping):
        labels = [str(k) for k in data.keys()]
        cols = [np.asarray(v, dtype=float).ravel() for v in data.values()]
        n = cols[0].size
        if any(c.size != n for c in cols):
            raise ValueError(
                "Paired wide input requires equal-length arrays "
                "(each row is the same subject across conditions)."
            )
        return labels, np.column_stack(cols)

    # --- Style 3: 2-D array (subjects x conditions) --------------------
    arr = np.asarray(data, dtype=float)
    if arr.ndim == 2:
        labels = [str(j) for j in range(arr.shape[1])]
        return labels, arr

    raise TypeError(
        "Paired input must be a long-form frame (+id), a wide mapping, "
        f"or a 2-D array; got {type(data)!r}."
    )

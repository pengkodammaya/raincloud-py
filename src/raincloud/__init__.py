"""raincloud-py: raincloud plots for Python.

A raincloud plot layers a half-violin (cloud), jittered raw points (rain),
and an optional boxplot — a transparent, distribution-honest alternative to
the bar-chart-with-error-bars.

Example
-------
>>> import numpy as np
>>> import matplotlib.pyplot as plt
>>> import raincloud as rc
>>> data = {"control": np.random.normal(0, 1, 200),
...         "treatment": np.random.normal(1, 1.5, 200)}
>>> rc.raincloud(data)
>>> plt.show()
"""

from ._core import raincloud

__all__ = ["raincloud"]
__version__ = "0.1.0"

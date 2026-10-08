"""Shared helpers for the attitude analyses: entropy, generalized JSD, and
plot styling."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# Japanese modifier labels need a CJK-capable font (macOS ships Hiragino)
plt.rcParams["font.family"] = ["Hiragino Sans", "Arial Unicode MS", "DejaVu Sans"]

LANG_COLOR = {"en": "#3b5bdb", "jp": "#c92a2a"}
LANG_NAME = {"en": "English", "jp": "Japanese"}
LN2 = np.log(2.0)


def H(p):
    p = np.asarray(p, float)
    p = p[p > 0]
    return float(-(p * np.log(p)).sum() / LN2)


def jsd(dists, weights=None):
    """Generalized Jensen-Shannon divergence in bits; rows of `dists` sum to 1.
    With weights proportional to how often each row's condition occurs, this
    is the mutual information between condition and outcome."""
    d = np.asarray(dists, float)
    w = (np.full(len(d), 1 / len(d)) if weights is None
         else np.asarray(weights, float) / np.sum(weights))
    return H(np.average(d, axis=0, weights=w)) - float(
        np.average([H(x) for x in d], weights=w))

# features.py
# Turns one EEG trial (16 channels x 1024 samples) into 160 numbers.
# Used by BOTH the training script and (later) the website.

import numpy as np
from scipy.stats import kurtosis, skew

N_CH = 16
N_SAMP = 1024

# Column names expected in an EEG CSV: ch1_s1 ... ch16_s1024
SIGNAL_COLUMNS = [f"ch{c}_s{s}" for c in range(1, N_CH + 1) for s in range(1, N_SAMP + 1)]

FEATURE_NAMES = [
    "mean", "std", "min", "max", "ptp", "rms", "skew", "kurt", "drift", "linelen",
]

# One name per output column, e.g. "ch1_mean", "ch1_std", ...
ALL_FEATURE_NAMES = [f"ch{c}_{f}" for c in range(1, N_CH + 1) for f in FEATURE_NAMES]


def extract_features(x):
    """x has shape (trials, channels, samples).
    Returns an array of shape (trials, channels * 10)."""
    mean = x.mean(axis=2)
    std = x.std(axis=2)
    mn = x.min(axis=2)
    mx = x.max(axis=2)
    ptp = mx - mn
    rms = np.sqrt((x ** 2).mean(axis=2))
    sk = skew(x, axis=2)
    ku = kurtosis(x, axis=2)
    drift = x[:, :, :32].mean(axis=2) - x[:, :, -32:].mean(axis=2)
    linelen = np.abs(np.diff(x, axis=2)).mean(axis=2)

    stacked = np.stack([mean, std, mn, mx, ptp, rms, sk, ku, drift, linelen], axis=2)
    return stacked.reshape(len(x), -1)
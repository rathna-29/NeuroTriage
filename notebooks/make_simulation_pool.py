# make_simulation_pool.py
# Picks the first trial of each subject (10 per class) from the dataset and
# saves them in a small file used by the SIMULATED monitoring feature.
#
# Run from the NeuroTriage folder:
#   python notebooks\make_simulation_pool.py

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from ml.features import N_CH, N_SAMP, SIGNAL_COLUMNS

CLASSES = ["normal", "ischemic", "hemorrhagic", "tia"]
OUT_PATH = ROOT / "backend" / "ml" / "sim_pool.npz"

pool = {}
for name in CLASSES:
    df = pd.read_csv(ROOT / "dataset" / f"{name}.csv", low_memory=False)
    picked = df.groupby("subject", sort=False).head(1)
    x = picked[SIGNAL_COLUMNS].to_numpy(dtype=np.float32).reshape(-1, N_CH, N_SAMP)
    pool[name] = x
    print(f"{name}: {x.shape[0]} trials, shape {x.shape}")

np.savez_compressed(OUT_PATH, **pool)
print("\nSaved:", OUT_PATH, f"({OUT_PATH.stat().st_size // 1024} KB)")
print("These trials were part of the training data: demonstration only.")
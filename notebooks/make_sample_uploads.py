# make_sample_uploads.py
# Cuts single-trial CSV files out of the dataset, for trying the upload page.
# The files contain only the 16384 signal columns (no label/subject/trial).
#
# Run from the NeuroTriage folder:
#   python notebooks\make_sample_uploads.py

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from ml.features import SIGNAL_COLUMNS

CLASSES = ["normal", "ischemic", "hemorrhagic", "tia"]
TRIALS_PER_CLASS = 2

out_dir = ROOT / "dataset" / "samples"
out_dir.mkdir(parents=True, exist_ok=True)

for name in CLASSES:
    df = pd.read_csv(ROOT / "dataset" / f"{name}.csv", nrows=TRIALS_PER_CLASS, low_memory=False)
    for i in range(len(df)):
        path = out_dir / f"sample_{name}_trial{i + 1}.csv"
        df.loc[[i], SIGNAL_COLUMNS].to_csv(path, index=False)
        print(f"Wrote {path.name} ({path.stat().st_size // 1024} KB)")

print("\nThese trials were part of the training data, so predictions on them")
print("are a demonstration, not a test of accuracy.")
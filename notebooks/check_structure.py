# check_structure.py
# Reads the four EEG CSV files and checks their structure.
# It only READS. Nothing is changed.
#
# Run from the NeuroTriage folder:
#   python notebooks\check_structure.py

from pathlib import Path

import numpy as np
import pandas as pd

DATASET_DIR = Path("dataset")
FILES = ["normal.csv", "ischemic.csv", "hemorrhagic.csv", "tia.csv"]
N_CH = 16
N_SAMP = 1024
META = ["label", "subject", "trial"]

# The signal columns should be ch1_s1 ... ch1_s1024, ch2_s1 ... ch16_s1024.
EXPECTED = [f"ch{c}_s{s}" for c in range(1, N_CH + 1) for s in range(1, N_SAMP + 1)]


def check_file(name):
    path = DATASET_DIR / name
    if not path.exists():
        print(f"\n{name}: NOT FOUND in the dataset folder")
        return None

    df = pd.read_csv(path, low_memory=False)
    signal_cols = [c for c in df.columns if c not in META]

    layout_ok = signal_cols == EXPECTED
    if not layout_ok:
        print(f"\n{name}: column layout is NOT ch1_s1..ch16_s1024 in order.")
        print("  Signal columns found:", len(signal_cols))
        return None

    # Shape: (trials, channels, samples)
    x = df[EXPECTED].to_numpy(dtype=np.float32).reshape(len(df), N_CH, N_SAMP)

    labels = sorted(df["label"].unique())
    per_subject = df.groupby("subject")["trial"].agg(["count", "min", "max"])
    duplicates = len(x) - len(np.unique(x.reshape(len(x), -1), axis=0))

    # Spikes: how many trials contain any |value| above 5?
    spike_trials = int((np.abs(x).max(axis=(1, 2)) > 5).sum())

    # Drift: average of the first 32 samples minus the last 32 samples.
    drift = float((x[:, :, :32].mean(axis=2) - x[:, :, -32:].mean(axis=2)).mean())

    print(f"\n{name}")
    print("  labels in file        :", labels)
    print("  shape (trials,ch,samp):", x.shape)
    print("  subjects              :", df["subject"].nunique())
    print("  trials per subject    :", sorted(set(per_subject["count"])))
    print("  trial numbers range   :", int(per_subject["min"].min()),
          "to", int(per_subject["max"].max()))
    print("  all values finite     :", bool(np.isfinite(x).all()))
    print("  duplicate trials      :", duplicates)

    return {
        "file": name,
        "mean": round(float(x.mean()), 3),
        "std": round(float(x.std()), 3),
        "min": round(float(x.min()), 2),
        "max": round(float(x.max()), 2),
        "trials_with_|x|>5": spike_trials,
        "start_minus_end": round(drift, 3),
    }


def main():
    rows = []
    for name in FILES:
        result = check_file(name)
        if result:
            rows.append(result)

    if rows:
        print("\nPER-CLASS SIGNAL SUMMARY")
        print(pd.DataFrame(rows).to_string(index=False))
    print("\nEnd of report. Nothing was changed.")


main()
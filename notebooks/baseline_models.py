# baseline_models.py
# Compares simple models on the EEG dataset using a SUBJECT-WISE split.
# It only READS the CSV files. Nothing in the website is changed.
#
# Run from the NeuroTriage folder:
#   python notebooks\baseline_models.py

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, skew
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, recall_score
from sklearn.model_selection import StratifiedGroupKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

DATASET_DIR = Path("dataset")
FILES = ["normal.csv", "ischemic.csv", "hemorrhagic.csv", "tia.csv"]
CLASSES = ["normal", "ischemic", "hemorrhagic", "tia"]
N_CH = 16
N_SAMP = 1024
META = ["label", "subject", "trial"]
EXPECTED = [f"ch{c}_s{s}" for c in range(1, N_CH + 1) for s in range(1, N_SAMP + 1)]

FEATURE_NAMES = [
    "mean", "std", "min", "max", "ptp", "rms", "skew", "kurt", "drift", "linelen",
]


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

    # Stack to (trials, channels, 10) then flatten to (trials, channels*10).
    stacked = np.stack([mean, std, mn, mx, ptp, rms, sk, ku, drift, linelen], axis=2)
    return stacked.reshape(len(x), -1)


def load_all():
    feature_parts, labels, groups = [], [], []
    for name in FILES:
        df = pd.read_csv(DATASET_DIR / name, low_memory=False)
        x = df[EXPECTED].to_numpy(dtype=np.float64).reshape(len(df), N_CH, N_SAMP)
        feature_parts.append(extract_features(x))
        labels += df["label"].tolist()
        # A group = one subject inside one file, e.g. "ischemic_subject_3".
        groups += (df["label"] + "_" + df["subject"]).tolist()
        print(f"Loaded {name}: {len(df)} trials")
    return np.vstack(feature_parts), np.array(labels), np.array(groups)


def evaluate(title, model, X, y, groups):
    # StratifiedGroupKFold keeps every group on one side of the split
    # and tries to keep the classes balanced in each fold.
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    predicted = cross_val_predict(model, X, y, cv=splitter, groups=groups)

    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    print(f"Accuracy : {accuracy_score(y, predicted):.3f}")
    print(f"Macro F1 : {f1_score(y, predicted, average='macro'):.3f}")

    recalls = recall_score(y, predicted, labels=CLASSES, average=None)
    print("Recall per class:")
    for cls, r in zip(CLASSES, recalls):
        print(f"   {cls:<12} {r:.3f}")

    cm = confusion_matrix(y, predicted, labels=CLASSES)
    print("Confusion matrix (rows = true class, columns = predicted):")
    print("   " + " " * 12 + "".join(f"{c[:8]:>10}" for c in CLASSES))
    for cls, row in zip(CLASSES, cm):
        print(f"   {cls:<12}" + "".join(f"{v:>10}" for v in row))


def main():
    X, y, groups = load_all()
    print("\nFeature table:", X.shape, "| groups:", len(set(groups)))

    names = [f"ch{c}_{f}" for c in range(1, N_CH + 1) for f in FEATURE_NAMES]
    std_columns = [i for i, n in enumerate(names) if n.endswith("_std")]

    evaluate(
        "Logistic Regression, all 160 features",
        make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
        X, y, groups,
    )
    evaluate(
        "Random Forest, all 160 features",
        RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1),
        X, y, groups,
    )
    evaluate(
        "Sanity check: Logistic Regression, ONLY the 16 std features",
        make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
        X[:, std_columns], y, groups,
    )

    print("\nIMPORTANT: these are results on THIS dataset only.")
    print("They are dataset performance, not real-world clinical performance.")


main()
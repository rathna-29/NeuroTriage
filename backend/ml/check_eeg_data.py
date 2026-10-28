
import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

from features import extract_features

BASE_DIR = Path(__file__).resolve().parents[2]
DATASET_DIR = BASE_DIR / "dataset"
FILES = ["normal.csv", "ischemic.csv", "hemorrhagic.csv", "tia.csv"]

SIGNAL_COLUMNS = [
    f"ch{ch}_s{i}"
    for ch in range(1, 17)
    for i in range(1, 1025)
]

all_features = []
all_labels = []
all_subjects = []
all_simple_features = []

for filename in FILES:
    df = pd.read_csv(
        DATASET_DIR / filename,
        usecols=SIGNAL_COLUMNS + ["label", "subject"]
    )

    signals = df[SIGNAL_COLUMNS].to_numpy(dtype=np.float64)

    simple = np.column_stack([
        np.mean(np.abs(signals), axis=1),
        np.std(signals, axis=1),
        np.max(np.abs(signals), axis=1),
    ])

    signals_3d = signals.reshape(len(signals), 16, 1024)
    features = extract_features(signals_3d)
    all_features.append(features)
    all_simple_features.append(simple)
    all_labels.extend(df["label"].astype(str).tolist())
    all_subjects.extend(df["subject"].astype(str).tolist())

X = np.vstack(all_features)
X_simple = np.vstack(all_simple_features)
y = np.asarray(all_labels)
groups = np.asarray(all_subjects)

# Match the exact held-out subjects used by the main evaluation.
test_subjects = {"subject_2", "subject_7"}
test_mask = np.isin(groups, list(test_subjects))
train_mask = ~test_mask

print("Training subjects:", sorted(set(groups[train_mask])))
print("Testing subjects:", sorted(set(groups[test_mask])))
print("Training trials:", int(train_mask.sum()))
print("Testing trials:", int(test_mask.sum()))

models = {
    "3-feature baseline": X_simple,
    "160-feature model": X,
}

for name, data in models.items():
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=3000, random_state=42)
    )

    model.fit(data[train_mask], y[train_mask])
    predictions = model.predict(data[test_mask])

    print(f"\n{name}")
    print(f"Accuracy: {accuracy_score(y[test_mask], predictions):.4f}")
    print(
        "Macro F1:",
        f"{f1_score(y[test_mask], predictions, average='macro'):.4f}"
    )

print(
    "\nNOTE: This is a diagnostic comparison on synthetic EEG data, "
    "not evidence of clinical validity."
)

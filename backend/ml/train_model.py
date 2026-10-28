
# train_model.py
# Evaluates NeuroTriage EEG classification using unseen subjects.
#
# Run from the backend folder:
#   ..\venv\Scripts\python.exe .\ml\train_model.py

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from ml.features import (
    ALL_FEATURE_NAMES,
    N_CH,
    N_SAMP,
    SIGNAL_COLUMNS,
    extract_features,
)

DATASET_DIR = BACKEND_DIR.parent / "dataset"
FILES = ["normal.csv", "ischemic.csv", "hemorrhagic.csv", "tia.csv"]

MODEL_PATH = Path(__file__).resolve().parent / "model.joblib"
INFO_PATH = Path(__file__).resolve().parent / "model_info.json"

# These subjects are reserved for evaluation only.
TEST_SUBJECTS = {"subject_2", "subject_7"}


def main():
    feature_parts = []
    label_parts = []
    subject_parts = []

    for filename in FILES:
        path = DATASET_DIR / filename

        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {path}")

        df = pd.read_csv(path, low_memory=False)

        missing = [
            column for column in SIGNAL_COLUMNS
            if column not in df.columns
        ]
        if missing:
            raise ValueError(
                f"{filename} is missing signal columns: {missing[:3]}"
            )

        for column in ("label", "subject"):
            if column not in df.columns:
                raise ValueError(
                    f"{filename} is missing the {column!r} column."
                )

        if df.empty:
            raise ValueError(f"{filename} contains no trials.")

        if df["label"].isna().any() or df["subject"].isna().any():
            raise ValueError(
                f"{filename} contains missing labels or subject IDs."
            )

        signals = df[SIGNAL_COLUMNS].to_numpy(dtype=np.float64)

        if not np.isfinite(signals).all():
            raise ValueError(
                f"{filename} contains missing or non-finite signal values."
            )

        signals = signals.reshape(len(df), N_CH, N_SAMP)
        features = extract_features(signals)

        if not np.isfinite(features).all():
            raise ValueError(
                f"Feature extraction produced invalid values for {filename}."
            )

        labels = df["label"].astype(str).to_numpy()
        subjects = df["subject"].astype(str).to_numpy()

        feature_parts.append(features)
        label_parts.append(labels)
        subject_parts.append(subjects)

        print(f"Loaded {filename}: {len(df)} trials")

    X = np.vstack(feature_parts)
    y = np.concatenate(label_parts)
    subjects = np.concatenate(subject_parts)

    print("\nFeature table:", X.shape)
    print("Class counts:")
    print(pd.Series(y).value_counts().to_string())

    available_subjects = set(subjects)
    missing_test_subjects = TEST_SUBJECTS - available_subjects
    if missing_test_subjects:
        raise ValueError(
            f"Evaluation subjects not found: {sorted(missing_test_subjects)}"
        )

    train_mask = ~np.isin(subjects, list(TEST_SUBJECTS))
    test_mask = np.isin(subjects, list(TEST_SUBJECTS))

    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]
    train_subjects = sorted(set(subjects[train_mask]))
    test_subjects = sorted(set(subjects[test_mask]))

    if set(train_subjects) & set(test_subjects):
        raise ValueError("Data leakage: training and testing subjects overlap.")

    if len(np.unique(y_train)) < 2:
        raise ValueError("Training data must contain at least two classes.")

    if set(np.unique(y_test)) != set(np.unique(y)):
        raise ValueError(
            "The test split does not contain every dataset class."
        )

    print("\nSUBJECT-WISE SPLIT")
    print("Training subjects:", train_subjects)
    print("Testing subjects:", test_subjects)
    print("Training trials:", len(y_train))
    print("Testing trials:", len(y_test))
    print("\nTraining labels:")
    print(pd.Series(y_train).value_counts().to_string())
    print("\nTesting labels:")
    print(pd.Series(y_test).value_counts().to_string())

    # Evaluate only on subjects never seen during fitting.
    evaluation_model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000),
    )
    evaluation_model.fit(X_train, y_train)
    test_predictions = evaluation_model.predict(X_test)

    accuracy = float(accuracy_score(y_test, test_predictions))
    macro_f1 = float(
        f1_score(y_test, test_predictions, average="macro", zero_division=0)
    )

    class_names = sorted(np.unique(y).tolist())
    matrix = confusion_matrix(
        y_test, test_predictions, labels=class_names
    )
    report = classification_report(
        y_test,
        test_predictions,
        labels=class_names,
        output_dict=True,
        zero_division=0,
    )

    print("\nUNSEEN-SUBJECT TEST RESULTS")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Macro F1: {macro_f1:.4f}")
    print("\nClassification report:")
    print(
        classification_report(
            y_test,
            test_predictions,
            labels=class_names,
            zero_division=0,
        )
    )
    print("Confusion matrix (rows=true, columns=predicted):")
    print(pd.DataFrame(matrix, index=class_names, columns=class_names))

    # Preserve the independent evaluation results, then fit the deployment
    # model on all available data. The saved model is not the test-only model.
    final_model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000),
    )
    final_model.fit(X, y)
    joblib.dump(final_model, MODEL_PATH)

    info = {
        "model": "StandardScaler + LogisticRegression",
        "classes": [str(c) for c in final_model.classes_],
        "n_features": len(ALL_FEATURE_NAMES),
        "feature_names": ALL_FEATURE_NAMES,
        "n_training_trials": int(len(y)),
        "evaluation_training_trials": int(len(y_train)),
        "evaluation_test_trials": int(len(y_test)),
        "evaluation_split": "subject-wise holdout; subject_2 and subject_7 reserved for testing",
        "evaluation_training_subjects": train_subjects,
        "evaluation_test_subjects": test_subjects,
        "test_accuracy": accuracy,
        "test_macro_f1": macro_f1,
        "test_classification_report": report,
        "test_confusion_matrix": matrix.tolist(),
        "test_confusion_matrix_labels": class_names,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "scikit_learn_version": sklearn.__version__,
        "dataset": (
            "Four EEG CSV files, reported as synthetic by an external source"
        ),
        "warning": (
            "Experimental educational prototype using a small synthetic "
            "dataset. Subject-wise testing is more informative than a random "
            "trial split but does not establish clinical validity or "
            "generalization to real patients. Independent external datasets "
            "and clinical validation are required."
        ),
    }

    INFO_PATH.write_text(
        json.dumps(info, indent=2),
        encoding="utf-8",
    )

    print("\nSaved model:", MODEL_PATH)
    print("Saved evaluation info:", INFO_PATH)
    print("Classes:", info["classes"])
    print("\nEvaluation complete. Results are experimental, not clinical.")


if __name__ == "__main__":
    main()

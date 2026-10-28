# check_model.py
# Loads the SAVED model and predicts a few trials.
# NOTE: these trials were part of the training data, so this only proves
# that the saved file loads and runs. It is NOT an accuracy test.
#
# Run from the NeuroTriage folder:
#   python backend\ml\check_model.py

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from ml.features import N_CH, N_SAMP, SIGNAL_COLUMNS, extract_features

DATASET_DIR = BACKEND_DIR.parent / "dataset"
MODEL_PATH = Path(__file__).resolve().parent / "model.joblib"

model = joblib.load(MODEL_PATH)
print("Model loaded. Classes:", list(model.classes_))

for name in ["normal.csv", "ischemic.csv", "hemorrhagic.csv", "tia.csv"]:
    df = pd.read_csv(DATASET_DIR / name, nrows=3, low_memory=False)
    x = df[SIGNAL_COLUMNS].to_numpy(dtype=np.float64).reshape(len(df), N_CH, N_SAMP)
    probs = model.predict_proba(extract_features(x))
    predicted = model.classes_[probs.argmax(axis=1)]
    print(f"\n{name} (true class: {df['label'].iloc[0]})")
    for i, (cls, p) in enumerate(zip(predicted, probs.max(axis=1)), start=1):
        print(f"   trial {i}: predicted {cls:<12} probability {p:.3f}")
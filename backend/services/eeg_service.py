# eeg_service.py
# Checks an uploaded EEG CSV and produces an AI-assisted priority indication.

import io
import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.features import (
    ALL_FEATURE_NAMES,
    N_CH,
    N_SAMP,
    SIGNAL_COLUMNS,
    extract_features,
)

MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB
META_COLUMNS = {"label", "subject", "trial"}
ALLOWED_COLUMNS = set(SIGNAL_COLUMNS) | META_COLUMNS

ML_DIR = Path(__file__).resolve().parent.parent / "ml"
MODEL_PATH = ML_DIR / "model.joblib"
INFO_PATH = ML_DIR / "model_info.json"

_cache = {}


class EEGValidationError(Exception):
    """The uploaded file is not acceptable."""


def read_eeg_csv(data, filename):
    """Validate one EEG CSV trial and return shape (1, 16, 1024)."""

    # 1. Validate file type and size.
    if not filename.lower().endswith(".csv"):
        raise EEGValidationError("Please upload a .csv file.")

    if not data:
        raise EEGValidationError("The uploaded file is empty.")

    if len(data) > MAX_FILE_BYTES:
        raise EEGValidationError(
            f"The file is too large. The maximum size is "
            f"{MAX_FILE_BYTES // (1024 * 1024)} MB."
        )

    # 2. Read the CSV.
    try:
        df = pd.read_csv(io.BytesIO(data))
    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        ValueError,
        UnicodeDecodeError,
    ):
        raise EEGValidationError(
            "Unable to process the uploaded file. "
            "Please check that it is a valid CSV."
        ) from None

    # 3. Validate required and unexpected columns.
    present = set(df.columns)
    missing = [column for column in SIGNAL_COLUMNS if column not in present]

    if missing:
        raise EEGValidationError(
            "EEG file is missing required signal columns. "
            f"Expected {len(SIGNAL_COLUMNS)} columns named "
            f"ch1_s1 through ch{N_CH}_s{N_SAMP}; "
            f"{len(missing)} are missing. "
            f"Examples: {', '.join(missing[:3])}."
        )

    unexpected = [
        str(column)
        for column in df.columns
        if column not in ALLOWED_COLUMNS
    ]

    if unexpected:
        raise EEGValidationError(
            "EEG file contains unexpected columns. "
            f"Examples: {', '.join(unexpected[:3])}. "
            "Only signal columns and optional label, subject, "
            "or trial columns are allowed."
        )

    # 4. This prototype accepts exactly one trial per file.
    if len(df) == 0:
        raise EEGValidationError(
            "The file has a header but no data row."
        )

    if len(df) != 1:
        raise EEGValidationError(
            "This prototype accepts one EEG trial per file. "
            f"Your file contains {len(df)} rows."
        )

    # 5. Validate signal values.
    for column in SIGNAL_COLUMNS:
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise EEGValidationError(
                f"Signal column '{column}' contains non-numeric values."
            )

    try:
        values = df[SIGNAL_COLUMNS].to_numpy(dtype=np.float64)
    except (TypeError, ValueError):
        raise EEGValidationError(
            "EEG signal columns must contain numeric values."
        ) from None

    if np.isnan(values).any():
        missing_count = int(np.isnan(values).sum())
        raise EEGValidationError(
            f"The file contains {missing_count} missing signal values."
        )

    if not np.isfinite(values).all():
        raise EEGValidationError(
            "The file contains infinite or invalid signal values."
        )

    # Keep the feature extractor's expected channel/sample ordering.
    return values.reshape(1, N_CH, N_SAMP)


def _load_model():
    """Load and cache the trained EEG model."""
    if "model" not in _cache:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                "Model file not found. Train it using "
                "the project's ml/train_model.py script."
            )

        model = joblib.load(MODEL_PATH)

        info = {}
        if INFO_PATH.exists():
            info = json.loads(
                INFO_PATH.read_text(encoding="utf-8")
            )

        _cache["model"] = model
        _cache["trained_at"] = info.get(
            "trained_at_utc", "unknown"
        )

    return _cache["model"], _cache["trained_at"]


def analyse_trial(x, conn):
    """
    Predict an EEG class and retrieve its project-defined priority.

    x must have shape (1, 16, 1024).
    The database connection must support SQLite-style execute().
    """
    model, trained_at = _load_model()

    # Validate input dimensions.
    if not isinstance(x, np.ndarray) or x.shape != (1, N_CH, N_SAMP):
        raise EEGValidationError(
            f"EEG input must have shape (1, {N_CH}, {N_SAMP})."
        )

    if not np.isfinite(x).all():
        raise EEGValidationError(
            "EEG input contains invalid or non-finite values."
        )

    # Extract model features while handling numerical warnings.
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore")
        features = extract_features(x)

    if not np.isfinite(features).all():
        raise EEGValidationError(
            "Features could not be computed. "
            "One or more channels may be flat, constant, or invalid."
        )

    # Predict the class.
    probs = model.predict_proba(features)[0]
    best = int(np.argmax(probs))
    predicted_class = str(model.classes_[best])

    # IMPORTANT:
    # The existing database uses 'class_name', not 'model_class'.
    row = conn.execute(
        """
        SELECT priority_label
        FROM priority_mapping
        WHERE class_name = ?
        """,
        (predicted_class,),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            f"No priority mapping found for class "
            f"'{predicted_class}'."
        )

    return {
        "predicted_class": predicted_class,
        "priority_label": row["priority_label"],
        "probability": float(probs[best]),
        "class_probabilities": {
            str(class_name): round(float(probability), 4)
            for class_name, probability in zip(
                model.classes_, probs
            )
        },
        "model_trained_at": trained_at,
        "features": {
            name: float(value)
            for name, value in zip(
                ALL_FEATURE_NAMES, features[0]
            )
        },
    }

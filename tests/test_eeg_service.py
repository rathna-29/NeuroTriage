# test_eeg_service.py
# Tries valid and invalid EEG files against the checking service.
#
# Run from the NeuroTriage folder:
#   python tests\test_eeg_service.py

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from database.db import get_connection
from ml.features import SIGNAL_COLUMNS
from services.eeg_service import (
    MAX_FILE_BYTES,
    EEGValidationError,
    analyse_trial,
    read_eeg_csv,
)

CLASSES = ["normal", "ischemic", "hemorrhagic", "tia"]
counts = {"passed": 0, "failed": 0}


def report(ok, text):
    counts["passed" if ok else "failed"] += 1
    print(("PASS  " if ok else "FAIL  ") + text)


def run(filename, data, conn):
    return analyse_trial(read_eeg_csv(data, filename), conn)


def expect_error(label, filename, data, conn, must_contain=None):
    try:
        run(filename, data, conn)
    except EEGValidationError as error:
        message = str(error)
        ok = must_contain is None or must_contain in message.lower()
        report(ok, f"{label}: {message[:85]}")
    except Exception as error:
        report(False, f"{label}: unexpected {type(error).__name__}: {error}")
    else:
        report(False, f"{label}: file was accepted but should have been rejected")


def edit_first_row(text, change):
    """Change the values of the single data row. 'change' receives the list of values."""
    lines = text.splitlines()
    values = lines[1].split(",")
    change(values)
    lines[1] = ",".join(values)
    return "\n".join(lines).encode("utf-8")


def main():
    conn = get_connection()
    try:
        print("VALID FILES")
        base_text = None
        for name in CLASSES:
            row = pd.read_csv(ROOT / "dataset" / f"{name}.csv", nrows=1, low_memory=False)
            if name == "normal":
                base_text = row[SIGNAL_COLUMNS].to_csv(index=False)
            # Keep label/subject/trial columns here: they must be accepted and ignored.
            data = row.to_csv(index=False).encode("utf-8")
            result = run(f"{name}.csv", data, conn)
            ok = result["predicted_class"] == name
            report(
                ok,
                f"{name} file -> {result['predicted_class']}, {result['priority_label']}, "
                f"probability {result['probability']:.3f}",
            )

        print("\nINVALID FILES (each must be rejected)")
        base_bytes = base_text.encode("utf-8")
        base_df = pd.read_csv(pd.io.common.StringIO(base_text))

        expect_error("wrong extension", "data.txt", base_bytes, conn, "csv")
        expect_error("empty file", "empty.csv", b"", conn, "empty")
        expect_error("too large", "big.csv", b"0" * (MAX_FILE_BYTES + 1), conn, "too large")
        expect_error(
            "missing column", "a.csv",
            base_df.drop(columns=["ch5_s10"]).to_csv(index=False).encode("utf-8"),
            conn, "missing required columns",
        )
        expect_error(
            "unexpected column", "a.csv",
            base_df.assign(extra_col=1).to_csv(index=False).encode("utf-8"),
            conn, "unexpected columns",
        )
        expect_error(
            "two rows", "a.csv",
            pd.concat([base_df, base_df]).to_csv(index=False).encode("utf-8"),
            conn, "one eeg trial",
        )

        def set_text(values):
            values[0] = "abc"

        def set_empty(values):
            values[10] = ""

        def set_inf(values):
            values[20] = "inf"

        def set_flat(values):
            values[2 * 1024:3 * 1024] = ["0.0"] * 1024  # channel 3 all zeros

        expect_error("text value", "a.csv", edit_first_row(base_text, set_text), conn, "non-numeric")
        expect_error("missing value", "a.csv", edit_first_row(base_text, set_empty), conn, "missing values")
        expect_error("infinite value", "a.csv", edit_first_row(base_text, set_inf), conn, "non-finite")
        expect_error("flat channel", "a.csv", edit_first_row(base_text, set_flat), conn, "flat")
        expect_error("random bytes named .csv", "random.csv", os.urandom(2000), conn)
    finally:
        conn.close()

    print(f"\n{counts['passed']} passed, {counts['failed']} failed")
    if counts["failed"]:
        sys.exit(1)


main()
# monitoring_service.py
# SIMULATED monitoring: produces one new measurement per call.

import random
import sqlite3
import uuid
from pathlib import Path

import numpy as np

from ml.features import N_CH, N_SAMP
from services.eeg_service import analyse_trial

POOL_PATH = Path(__file__).resolve().parent.parent / "ml" / "sim_pool.npz"

# key -> (name shown to the user, sequence of source classes)
SCENARIOS = {
    "stable": ("Stable (normal-class trials)", ["normal"] * 6),
    "deterioration": (
        "Simulated deterioration",
        ["normal", "normal", "tia", "tia", "ischemic", "ischemic",
         "hemorrhagic", "hemorrhagic"],
    ),
    "recovery": (
        "Simulated recovery",
        ["ischemic", "ischemic", "tia", "tia", "normal", "normal"],
    ),
}

_pool = {}


def _load_pool():
    if not _pool:
        if not POOL_PATH.exists():
            raise FileNotFoundError(
                "Simulation pool not found. Run: python notebooks\\make_simulation_pool.py"
            )
        data = np.load(POOL_PATH)
        for name in data.files:
            _pool[name] = data[name]
    return _pool


def next_measurement(conn, patient_id, user_db_id, scenario_key):
    """Create, analyse and save the next simulated measurement."""
    if scenario_key not in SCENARIOS:
        raise ValueError("Unknown scenario.")
    sequence = SCENARIOS[scenario_key][1]
    pool = _load_pool()

    # Continue the current run, or start a new one.
    latest = conn.execute(
        "SELECT run_id, scenario, step_index FROM monitoring_records "
        "WHERE patient_id = ? ORDER BY id DESC LIMIT 1",
        (patient_id,),
    ).fetchone()
    if (
        latest is not None
        and latest["scenario"] == scenario_key
        and latest["step_index"] + 1 < len(sequence)
    ):
        run_id = latest["run_id"]
        step = latest["step_index"] + 1
    else:
        run_id = uuid.uuid4().hex
        step = 0

    # "Receive" a measurement and analyse it with the same service as uploads.
    source_class = sequence[step]
    trials = pool[source_class]
    x = trials[random.randrange(len(trials))].astype(np.float64).reshape(1, N_CH, N_SAMP)
    result = analyse_trial(x, conn)

    # One simple context number: average standard deviation over the 16 channels.
    stds = [v for name, v in result["features"].items() if name.endswith("_std")]
    mean_std = float(np.mean(stds))

    try:
        conn.execute(
            "INSERT INTO monitoring_records (patient_id, created_by, run_id, scenario, "
            "step_index, sim_source_class, predicted_class, priority_label, "
            "probability, mean_std) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                patient_id, user_db_id, run_id, scenario_key, step, source_class,
                result["predicted_class"], result["priority_label"],
                result["probability"], mean_std,
            ),
        )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise

    return {
        "step": step + 1,
        "total": len(sequence),
        "finished": step + 1 >= len(sequence),
        "priority_label": result["priority_label"],
    }
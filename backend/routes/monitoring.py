# monitoring.py
# Routes for the SIMULATED monitoring page.

import logging

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from database.db import get_connection
from routes.patients import get_patient_or_404
from services.monitoring_service import SCENARIOS, next_measurement
from utils.auth_utils import login_required

monitoring_bp = Blueprint("monitoring", __name__)
log = logging.getLogger(__name__)


@monitoring_bp.route("/patients/<int:patient_id>/monitoring")
@login_required
def monitoring_page(patient_id):
    conn = get_connection()
    try:
        patient = get_patient_or_404(conn, patient_id)
        rows = conn.execute(
            "SELECT m.*, u.user_id AS created_by_user "
            "FROM monitoring_records m JOIN users u ON m.created_by = u.id "
            "WHERE m.patient_id = ? ORDER BY m.id DESC",
            (patient_id,),
        ).fetchall()
    finally:
        conn.close()

    # Context: compare each record with the previous one in the SAME run.
    records = []
    for i, row in enumerate(rows):
        item = dict(row)
        item["scenario_name"] = SCENARIOS.get(row["scenario"], (row["scenario"],))[0]
        item["run_length"] = len(SCENARIOS.get(row["scenario"], (None, []))[1])
        prev = rows[i + 1] if i + 1 < len(rows) else None
        if prev is not None and prev["run_id"] == row["run_id"]:
            item["has_previous"] = True
            item["priority_changed"] = prev["priority_label"] != row["priority_label"]
            item["previous_priority"] = prev["priority_label"]
            item["delta_std"] = row["mean_std"] - prev["mean_std"]
        else:
            item["has_previous"] = False
        records.append(item)

    return render_template(
        "monitoring.html",
        patient=patient,
        records=records,
        scenarios=SCENARIOS,
        latest=records[0] if records else None,
    )


@monitoring_bp.route("/patients/<int:patient_id>/monitoring/next", methods=["POST"])
@login_required
def monitoring_next(patient_id):
    wants_json = request.headers.get("X-Requested-With") == "fetch"
    scenario = request.form.get("scenario", "")

    conn = get_connection()
    try:
        get_patient_or_404(conn, patient_id)
        if scenario not in SCENARIOS:
            if wants_json:
                return jsonify(ok=False, message="Unknown scenario."), 400
            flash("Please choose a scenario.", "error")
            return redirect(url_for("monitoring.monitoring_page", patient_id=patient_id))

        try:
            out = next_measurement(conn, patient_id, session["db_id"], scenario)
        except Exception:
            log.exception("Simulated measurement failed")
            if wants_json:
                return jsonify(ok=False, message="Unable to create the measurement."), 500
            flash("Unable to create the simulated measurement.", "error")
            return redirect(url_for("monitoring.monitoring_page", patient_id=patient_id))
    finally:
        conn.close()

    if wants_json:
        return jsonify(ok=True, finished=out["finished"])

    if out["finished"]:
        flash(
            f"Simulated run complete ({out['step']} of {out['total']}). "
            "The next click starts a new run.",
            "success",
        )
    return redirect(url_for("monitoring.monitoring_page", patient_id=patient_id))
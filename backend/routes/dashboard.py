# dashboard.py
# The main page after login: summaries for the patients this user may see.

from flask import Blueprint, render_template, session

from database.db import get_connection
from utils.auth_utils import login_required

dashboard_bp = Blueprint("dashboard", __name__)

PRIORITY_ORDER = ["Higher Priority", "Moderate Priority", "Lower Priority"]


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    # Access rule: clinicians see only the patients they created.
    if session["role"] == "clinician":
        scope = "AND p.created_by = ?"
        params = (session["db_id"],)
    else:
        scope = ""
        params = ()

    conn = get_connection()
    try:
        total_patients = conn.execute(
            f"SELECT COUNT(*) FROM patients p WHERE 1 = 1 {scope}", params
        ).fetchone()[0]

        recent_patients = conn.execute(
        "SELECT p.id, p.patient_code, p.age, p.sex, p.created_at, "
        "       pr.priority_label "
        "FROM patients p "
        "LEFT JOIN predictions pr ON pr.id = ("
        "    SELECT id FROM predictions "
        "    WHERE patient_id = p.id "
        "    ORDER BY created_at DESC, id DESC LIMIT 1"
        ") "
        f"WHERE 1 = 1 {scope} "
        "ORDER BY p.created_at DESC, p.id DESC LIMIT 5",
        params,
    ).fetchall()

        # Latest real EEG analysis per patient (for the priority summary).
        latest = conn.execute(
            "SELECT p.id, pr.priority_label "
            "FROM patients p "
            "LEFT JOIN predictions pr ON pr.id = ("
            "    SELECT id FROM predictions WHERE patient_id = p.id "
            "    ORDER BY created_at DESC, id DESC LIMIT 1) "
            f"WHERE 1 = 1 {scope}",
            params,
        ).fetchall()

        recent_analyses = conn.execute(
            "SELECT p.id AS patient_id, p.patient_code, pr.id, pr.priority_label, "
            "       pr.predicted_class, pr.probability, pr.created_at "
            "FROM predictions pr JOIN patients p ON pr.patient_id = p.id "
            f"WHERE 1 = 1 {scope} "
            "ORDER BY pr.created_at DESC, pr.id DESC LIMIT 5",
            params,
        ).fetchall()

        # Last SIMULATED monitoring record per patient.
        monitoring = conn.execute(
            "SELECT p.id AS patient_id, p.patient_code, m.priority_label, "
            "       m.step_index, m.scenario, m.created_at "
            "FROM patients p JOIN monitoring_records m ON m.id = ("
            "    SELECT id FROM monitoring_records WHERE patient_id = p.id "
            "    ORDER BY id DESC LIMIT 1) "
            f"WHERE 1 = 1 {scope} "
            "ORDER BY m.created_at DESC, m.id DESC LIMIT 5",
            params,
        ).fetchall()
    finally:
        conn.close()

    # Count patients per priority label.
    summary = {label: 0 for label in PRIORITY_ORDER}
    no_analysis = 0
    for row in latest:
        if row["priority_label"] is None:
            no_analysis += 1
        else:
            summary[row["priority_label"]] += 1

    return render_template(
        "dashboard.html",
        full_name=session["full_name"],
        user_id=session["user_id"],
        role=session["role"],
        total_patients=total_patients,
        recent_patients=recent_patients,
        summary=summary,
        no_analysis=no_analysis,
        recent_analyses=recent_analyses,
        monitoring=monitoring,
    )
# clinical.py
# Routes for adding and editing clinical information.

import sqlite3

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from database.db import get_connection
from routes.patients import get_patient_or_404
from utils.auth_utils import login_required

clinical_bp = Blueprint("clinical", __name__)

# field name -> (label shown in error messages, maximum length, required?)
CLINICAL_FIELDS = {
    "symptoms": ("symptoms", 1000, True),
    "symptom_onset": ("symptom onset", 100, False),
    "medical_history": ("medical history", 1000, False),
    "existing_conditions": ("existing conditions", 500, False),
    "clinical_observations": ("clinical observations", 1000, False),
}


def read_clinical_form(form):
    """Check the submitted form.
    Returns (values, None) if valid, or (None, "error message")."""
    values = {}
    for key, (label, max_length, required) in CLINICAL_FIELDS.items():
        # Browsers send new lines as \r\n; we store them as \n.
        text = form.get(key, "").replace("\r\n", "\n").strip()

        if required and text == "":
            return None, f"Please enter the {label}."
        if len(text) > max_length:
            return None, f"The {label} must be at most {max_length} characters."

        # Store an empty optional field as NULL (no value).
        values[key] = text if text != "" else None
    return values, None


def show(value):
    """Turn a value into text for the audit log."""
    return "(empty)" if value is None else str(value)


@clinical_bp.route("/patients/<int:patient_id>/clinical/add", methods=["GET", "POST"])
@login_required
def add_clinical(patient_id):
    conn = get_connection()
    try:
        # Also enforces the access rule (404 if not allowed).
        patient = get_patient_or_404(conn, patient_id)

        if request.method == "POST":
            values, error = read_clinical_form(request.form)
            if error:
                flash(error, "error")
                return render_template(
                    "clinical_form.html", patient=patient, form=request.form, mode="add"
                )

            try:
                conn.execute(
                    "INSERT INTO clinical_records (patient_id, recorded_by, symptoms, "
                    "symptom_onset, medical_history, existing_conditions, "
                    "clinical_observations) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        patient_id,
                        session["db_id"],
                        values["symptoms"],
                        values["symptom_onset"],
                        values["medical_history"],
                        values["existing_conditions"],
                        values["clinical_observations"],
                    ),
                )
                conn.commit()
            except sqlite3.Error:
                conn.rollback()
                flash("Unable to save the clinical information. Please try again.", "error")
                return render_template(
                    "clinical_form.html", patient=patient, form=request.form, mode="add"
                )

            flash("Clinical information saved.", "success")
            return redirect(url_for("patients.patient_detail", patient_id=patient_id))

        return render_template("clinical_form.html", patient=patient, form={}, mode="add")
    finally:
        conn.close()


@clinical_bp.route(
    "/patients/<int:patient_id>/clinical/<int:record_id>/edit", methods=["GET", "POST"]
)
@login_required
def edit_clinical(patient_id, record_id):
    conn = get_connection()
    try:
        patient = get_patient_or_404(conn, patient_id)

        # The entry must belong to THIS patient.
        record = conn.execute(
            "SELECT * FROM clinical_records WHERE id = ? AND patient_id = ?",
            (record_id, patient_id),
        ).fetchone()
        if record is None:
            abort(404)

        if request.method == "POST":
            values, error = read_clinical_form(request.form)
            if error:
                flash(error, "error")
                return render_template(
                    "clinical_form.html",
                    patient=patient,
                    form=request.form,
                    mode="edit",
                    record_id=record_id,
                )

            # Find which fields actually changed.
            changes = []
            for key in CLINICAL_FIELDS:
                if values[key] != record[key]:
                    changes.append((key, record[key], values[key]))

            if not changes:
                flash("No changes were made.", "success")
                return redirect(url_for("patients.patient_detail", patient_id=patient_id))

            # Save the edit AND the audit rows together.
            try:
                conn.execute(
                    "UPDATE clinical_records SET symptoms = ?, symptom_onset = ?, "
                    "medical_history = ?, existing_conditions = ?, "
                    "clinical_observations = ? WHERE id = ? AND patient_id = ?",
                    (
                        values["symptoms"],
                        values["symptom_onset"],
                        values["medical_history"],
                        values["existing_conditions"],
                        values["clinical_observations"],
                        record_id,
                        patient_id,
                    ),
                )
                for key, old_value, new_value in changes:
                    conn.execute(
                        "INSERT INTO audit_logs "
                        "(patient_id, changed_by, field_name, old_value, new_value) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            patient_id,
                            session["db_id"],
                            f"clinical #{record_id} {key}",
                            show(old_value),
                            show(new_value),
                        ),
                    )
                conn.commit()
            except sqlite3.Error:
                conn.rollback()
                flash("Unable to save the changes. Please try again.", "error")
                return render_template(
                    "clinical_form.html",
                    patient=patient,
                    form=request.form,
                    mode="edit",
                    record_id=record_id,
                )

            flash("Clinical information updated.", "success")
            return redirect(url_for("patients.patient_detail", patient_id=patient_id))

        # GET: show the form filled with the saved values.
        return render_template(
            "clinical_form.html",
            patient=patient,
            form=dict(record),
            mode="edit",
            record_id=record_id,
        )
    finally:
        conn.close()
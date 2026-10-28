# vitals.py
# Routes for adding and editing vital-sign measurements.

import math
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

vitals_bp = Blueprint("vitals", __name__)

# The columns of a measurement, in a fixed order.
VITAL_FIELDS = [
    "heart_rate",
    "systolic_bp",
    "diastolic_bp",
    "spo2",
    "temperature_c",
    "respiratory_rate",
]


def read_whole_number(text, low, high):
    """Return the number if text is a whole number from low to high, else None."""
    text = text.strip()
    # isascii() blocks look-alike digits such as superscripts.
    if not (text.isascii() and text.isdigit()):
        return None
    number = int(text)
    return number if low <= number <= high else None


def read_vitals_form(form):
    """Check the submitted form.
    Returns (values, None) if everything is valid,
    or (None, "error message") if something is wrong."""
    values = {}

    # --- Required whole-number fields ---
    required = [
        ("heart_rate", "heart rate", 20, 300),
        ("systolic_bp", "systolic blood pressure", 40, 300),
        ("diastolic_bp", "diastolic blood pressure", 20, 200),
        ("spo2", "SpO2", 50, 100),
    ]
    for key, label, low, high in required:
        number = read_whole_number(form.get(key, ""), low, high)
        if number is None:
            return None, f"Please enter a valid {label} (whole number, {low} to {high})."
        values[key] = number

    # Systolic must be higher than diastolic.
    if values["systolic_bp"] <= values["diastolic_bp"]:
        return None, "Systolic blood pressure must be higher than diastolic."

    # --- Temperature (decimal allowed) ---
    try:
        temperature = float(form.get("temperature_c", "").strip())
    except ValueError:
        return None, "Please enter a valid temperature in °C (25.0 to 45.0)."
    # float("nan") and float("inf") are accepted by Python, so block them.
    if not math.isfinite(temperature) or not (25.0 <= temperature <= 45.0):
        return None, "Please enter a valid temperature in °C (25.0 to 45.0)."
    values["temperature_c"] = round(temperature, 1)

    # --- Respiratory rate (optional) ---
    rr_text = form.get("respiratory_rate", "").strip()
    if rr_text == "":
        values["respiratory_rate"] = None
    else:
        rr = read_whole_number(rr_text, 4, 80)
        if rr is None:
            return None, "Please enter a valid respiratory rate (whole number, 4 to 80) or leave it empty."
        values["respiratory_rate"] = rr

    return values, None


def show(value):
    """Turn a value into text for the audit log."""
    return "(empty)" if value is None else str(value)


@vitals_bp.route("/patients/<int:patient_id>/vitals/add", methods=["GET", "POST"])
@login_required
def add_vitals(patient_id):
    conn = get_connection()
    try:
        # Also enforces the access rule (404 if not allowed).
        patient = get_patient_or_404(conn, patient_id)

        if request.method == "POST":
            values, error = read_vitals_form(request.form)
            if error:
                flash(error, "error")
                return render_template(
                    "vitals_form.html", patient=patient, form=request.form, mode="add"
                )

            try:
                conn.execute(
                    "INSERT INTO vitals (patient_id, recorded_by, heart_rate, "
                    "systolic_bp, diastolic_bp, spo2, temperature_c, respiratory_rate) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        patient_id,
                        session["db_id"],
                        values["heart_rate"],
                        values["systolic_bp"],
                        values["diastolic_bp"],
                        values["spo2"],
                        values["temperature_c"],
                        values["respiratory_rate"],
                    ),
                )
                conn.commit()
            except sqlite3.Error:
                conn.rollback()
                flash("Unable to save the vital signs. Please try again.", "error")
                return render_template(
                    "vitals_form.html", patient=patient, form=request.form, mode="add"
                )

            flash("Vital signs saved.", "success")
            return redirect(url_for("patients.patient_detail", patient_id=patient_id))

        return render_template("vitals_form.html", patient=patient, form={}, mode="add")
    finally:
        conn.close()


@vitals_bp.route(
    "/patients/<int:patient_id>/vitals/<int:vital_id>/edit", methods=["GET", "POST"]
)
@login_required
def edit_vitals(patient_id, vital_id):
    conn = get_connection()
    try:
        patient = get_patient_or_404(conn, patient_id)

        # The measurement must belong to THIS patient.
        vital = conn.execute(
            "SELECT * FROM vitals WHERE id = ? AND patient_id = ?",
            (vital_id, patient_id),
        ).fetchone()
        if vital is None:
            abort(404)

        if request.method == "POST":
            values, error = read_vitals_form(request.form)
            if error:
                flash(error, "error")
                return render_template(
                    "vitals_form.html",
                    patient=patient,
                    form=request.form,
                    mode="edit",
                    vital_id=vital_id,
                )

            # Find which fields actually changed.
            changes = []
            for key in VITAL_FIELDS:
                if values[key] != vital[key]:
                    changes.append((key, vital[key], values[key]))

            if not changes:
                flash("No changes were made.", "success")
                return redirect(url_for("patients.patient_detail", patient_id=patient_id))

            # Save the edit AND the audit rows together.
            try:
                conn.execute(
                    "UPDATE vitals SET heart_rate = ?, systolic_bp = ?, "
                    "diastolic_bp = ?, spo2 = ?, temperature_c = ?, "
                    "respiratory_rate = ? WHERE id = ? AND patient_id = ?",
                    (
                        values["heart_rate"],
                        values["systolic_bp"],
                        values["diastolic_bp"],
                        values["spo2"],
                        values["temperature_c"],
                        values["respiratory_rate"],
                        vital_id,
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
                            f"vitals #{vital_id} {key}",
                            show(old_value),
                            show(new_value),
                        ),
                    )
                conn.commit()
            except sqlite3.Error:
                conn.rollback()
                flash("Unable to save the changes. Please try again.", "error")
                return render_template(
                    "vitals_form.html",
                    patient=patient,
                    form=request.form,
                    mode="edit",
                    vital_id=vital_id,
                )

            flash("Vital signs updated.", "success")
            return redirect(url_for("patients.patient_detail", patient_id=patient_id))

        # GET: show the form filled with the saved values.
        return render_template(
            "vitals_form.html",
            patient=patient,
            form=dict(vital),
            mode="edit",
            vital_id=vital_id,
        )
    finally:
        conn.close()
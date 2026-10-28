
# patients.py
# Routes for listing, adding, viewing and editing patients.

import re
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
from utils.auth_utils import login_required

patients_bp = Blueprint("patients", __name__)

# Patient ID rules: 2-20 characters, letters, numbers, dash or underscore.
PATIENT_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{2,20}$")
ALLOWED_SEX = ("Male", "Female", "Other", "Not recorded")


def read_age(text):
    """Return an age from 0 to 120, or None if the text is invalid."""
    text = text.strip()

    # Accept only ordinary ASCII digits, rejecting Unicode look-alike digits.
    if not (text.isascii() and text.isdigit()):
        return None

    age = int(text)
    return age if 0 <= age <= 120 else None


def get_patient_or_404(conn, patient_id):
    """Return a patient if the logged-in user is allowed to access it.

    Doctors can open any patient.
    Clinicians can open only patients they created.
    """
    sql = (
        "SELECT p.id, p.patient_code, p.age, p.sex, p.created_at, "
        "       u.user_id AS created_by_user "
        "FROM patients p JOIN users u ON p.created_by = u.id "
        "WHERE p.id = ?"
    )
    params = [patient_id]

    if session["role"] == "clinician":
        sql += " AND p.created_by = ?"
        params.append(session["db_id"])

    patient = conn.execute(sql, params).fetchone()

    if patient is None:
        abort(404)

    return patient


@patients_bp.route("/patients")
@login_required
def patient_list():
    search = request.args.get("q", "").strip()

    sql = (
        "SELECT p.id, p.patient_code, p.age, p.sex, p.created_at, "
        "       u.user_id AS created_by_user "
        "FROM patients p JOIN users u ON p.created_by = u.id "
    )

    conditions = []
    params = []

    # Clinicians only see patients they created.
    if session["role"] == "clinician":
        conditions.append("p.created_by = ?")
        params.append(session["db_id"])

    # Search by Patient ID; partial matches are allowed.
    if search:
        conditions.append("p.patient_code LIKE ?")
        params.append(f"%{search}%")

    if conditions:
        sql += "WHERE " + " AND ".join(conditions) + " "

    sql += "ORDER BY p.created_at DESC, p.id DESC"

    conn = get_connection()
    try:
        patients = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    return render_template(
        "patients.html",
        patients=patients,
        search=search,
    )


@patients_bp.route("/patients/add", methods=["GET", "POST"])
@login_required
def add_patient():
    if request.method == "POST":
        patient_code = request.form.get("patient_code", "").strip().upper()
        age_text = request.form.get("age", "").strip()
        sex = request.form.get("sex", "")

        # Validate Patient ID.
        if not PATIENT_CODE_PATTERN.fullmatch(patient_code):
            flash(
                "Patient ID must be 2-20 characters: letters, numbers, - or _ only.",
                "error",
            )
            return render_template("add_patient.html", form=request.form)

        # Validate age safely.
        age = read_age(age_text)
        if age is None:
            flash(
                "Please enter a valid age (a whole number from 0 to 120).",
                "error",
            )
            return render_template("add_patient.html", form=request.form)

        # Validate sex.
        if sex not in ALLOWED_SEX:
            flash("Please select a valid sex option.", "error")
            return render_template("add_patient.html", form=request.form)

        # Save the patient.
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO patients (patient_code, age, sex, created_by) "
                "VALUES (?, ?, ?, ?)",
                (patient_code, age, sex, session["db_id"]),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Patient ID already exists.", "error")
            return render_template("add_patient.html", form=request.form)
        finally:
            conn.close()

        flash(f"Patient {patient_code} was added.", "success")
        return redirect(url_for("patients.patient_list"))

    return render_template("add_patient.html", form={})


@patients_bp.route("/patients/<int:patient_id>")
@login_required
def patient_detail(patient_id):
    conn = get_connection()

    try:
        patient = get_patient_or_404(conn, patient_id)

        # Audit history, newest first.
        history = conn.execute(
            "SELECT a.field_name, a.old_value, a.new_value, a.changed_at, "
            "       u.user_id AS changed_by_user "
            "FROM audit_logs a JOIN users u ON a.changed_by = u.id "
            "WHERE a.patient_id = ? "
            "ORDER BY a.changed_at DESC, a.id DESC",
            (patient_id,),
        ).fetchall()

        # Vital-sign measurements, newest first.
        vitals = conn.execute(
            "SELECT v.id, v.heart_rate, v.systolic_bp, v.diastolic_bp, v.spo2, "
            "       v.temperature_c, v.respiratory_rate, v.recorded_at, "
            "       u.user_id AS recorded_by_user "
            "FROM vitals v JOIN users u ON v.recorded_by = u.id "
            "WHERE v.patient_id = ? "
            "ORDER BY v.recorded_at DESC, v.id DESC",
            (patient_id,),
        ).fetchall()

        # Clinical information, newest first.
        clinical = conn.execute(
            "SELECT c.id, c.symptoms, c.symptom_onset, c.medical_history, "
            "       c.existing_conditions, c.clinical_observations, c.recorded_at, "
            "       u.user_id AS recorded_by_user "
            "FROM clinical_records c JOIN users u ON c.recorded_by = u.id "
            "WHERE c.patient_id = ? "
            "ORDER BY c.recorded_at DESC, c.id DESC",
            (patient_id,),
        ).fetchall()

        # AI analyses, newest first.
        predictions = conn.execute(
            "SELECT p.id, p.predicted_class, p.priority_label, p.probability, "
            "       p.created_at, u.user_id AS created_by_user "
            "FROM predictions p JOIN users u ON p.created_by = u.id "
            "WHERE p.patient_id = ? "
            "ORDER BY p.created_at DESC, p.id DESC",
            (patient_id,),
        ).fetchall()

    finally:
        conn.close()

    return render_template(
        "patient_detail.html",
        patient=patient,
        history=history,
        vitals=vitals,
        clinical=clinical,
        predictions=predictions,
    )


@patients_bp.route(
    "/patients/<int:patient_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_patient(patient_id):
    conn = get_connection()

    try:
        patient = get_patient_or_404(conn, patient_id)

        if request.method == "POST":
            age_text = request.form.get("age", "").strip()
            sex = request.form.get("sex", "")

            # Validate age safely.
            new_age = read_age(age_text)

            if new_age is None:
                flash(
                    "Please enter a valid age (a whole number from 0 to 120).",
                    "error",
                )
                return render_template(
                    "edit_patient.html",
                    patient=patient,
                    form=request.form,
                )

            # Validate sex.
            if sex not in ALLOWED_SEX:
                flash("Please select a valid sex option.", "error")
                return render_template(
                    "edit_patient.html",
                    patient=patient,
                    form=request.form,
                )

            # Find which fields actually changed.
            changes = []

            if new_age != patient["age"]:
                changes.append(("age", patient["age"], new_age))

            if sex != patient["sex"]:
                changes.append(("sex", patient["sex"], sex))

            if not changes:
                flash("No changes were made.", "success")
                return redirect(
                    url_for(
                        "patients.patient_detail",
                        patient_id=patient_id,
                    )
                )

            # Save the edit and audit entries together.
            try:
                conn.execute(
                    "UPDATE patients SET age = ?, sex = ? WHERE id = ?",
                    (new_age, sex, patient_id),
                )

                for field_name, old_value, new_value in changes:
                    conn.execute(
                        "INSERT INTO audit_logs "
                        "(patient_id, changed_by, field_name, old_value, new_value) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            patient_id,
                            session["db_id"],
                            field_name,
                            str(old_value),
                            str(new_value),
                        ),
                    )

                conn.commit()

            except sqlite3.Error:
                conn.rollback()
                flash(
                    "Unable to save the changes. Please try again.",
                    "error",
                )
                return render_template(
                    "edit_patient.html",
                    patient=patient,
                    form=request.form,
                )

            flash("Patient record updated.", "success")
            return redirect(
                url_for(
                    "patients.patient_detail",
                    patient_id=patient_id,
                )
            )

        # GET: display the existing patient values.
        return render_template(
            "edit_patient.html",
            patient=patient,
            form=patient,
        )

    finally:
        conn.close()

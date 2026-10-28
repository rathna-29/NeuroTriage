# eeg.py
# Routes for uploading EEG files and viewing AI-assisted results.

import json
import logging
import sqlite3
import uuid

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from database.db import get_connection
from routes.patients import get_patient_or_404
from services.eeg_service import EEGValidationError, analyse_trial, read_eeg_csv
from utils.auth_utils import login_required

eeg_bp = Blueprint("eeg", __name__)
log = logging.getLogger(__name__)


@eeg_bp.route("/patients/<int:patient_id>/eeg/upload", methods=["GET", "POST"])
@login_required
def upload_eeg(patient_id):
    conn = get_connection()
    try:
        patient = get_patient_or_404(conn, patient_id)

        if request.method == "POST":
            file = request.files.get("eeg_file")
            if file is None or file.filename == "":
                flash("Please choose an EEG CSV file.", "error")
                return render_template("upload_eeg.html", patient=patient)

            data = file.read()

            # 1. Validate and analyse (nothing is saved yet).
            try:
                x = read_eeg_csv(data, file.filename)
                result = analyse_trial(x, conn)
            except EEGValidationError as error:
                flash(str(error), "error")
                return render_template("upload_eeg.html", patient=patient)
            except Exception:
                log.exception("EEG analysis failed")
                flash("Unable to process the uploaded file.", "error")
                return render_template("upload_eeg.html", patient=patient)

            # 2. Save the file under a random name (never the user's name).
            stored_name = uuid.uuid4().hex + ".csv"
            upload_dir = current_app.config["UPLOAD_DIR"]
            upload_dir.mkdir(parents=True, exist_ok=True)
            stored_path = upload_dir / stored_name
            stored_path.write_bytes(data)

            # 3. Save the database rows together.
            try:
                cursor = conn.execute(
                    "INSERT INTO eeg_records (patient_id, recorded_by, original_filename, "
                    "stored_filename, n_channels, n_samples, feature_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        patient_id,
                        session["db_id"],
                        file.filename[:200],
                        stored_name,
                        16,
                        1024,
                        json.dumps(result["features"]),
                    ),
                )
                eeg_id = cursor.lastrowid
                conn.execute(
                    "INSERT INTO predictions (patient_id, eeg_record_id, created_by, "
                    "predicted_class, priority_label, probability, "
                    "class_probabilities_json, model_trained_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        patient_id,
                        eeg_id,
                        session["db_id"],
                        result["predicted_class"],
                        result["priority_label"],
                        result["probability"],
                        json.dumps(result["class_probabilities"]),
                        result["model_trained_at"],
                    ),
                )
                prediction_id = conn.execute(
                    "SELECT last_insert_rowid()"
                ).fetchone()[0]
                conn.commit()
            except sqlite3.Error:
                conn.rollback()
                stored_path.unlink(missing_ok=True)  # no orphan file
                log.exception("Saving EEG record failed")
                flash("Unable to save the EEG record. Please try again.", "error")
                return render_template("upload_eeg.html", patient=patient)

            return redirect(
                url_for(
                    "eeg.prediction_result",
                    patient_id=patient_id,
                    prediction_id=prediction_id,
                )
            )

        return render_template("upload_eeg.html", patient=patient)
    finally:
        conn.close()


@eeg_bp.route("/patients/<int:patient_id>/predictions/<int:prediction_id>")
@login_required
def prediction_result(patient_id, prediction_id):
    conn = get_connection()
    try:
        patient = get_patient_or_404(conn, patient_id)

        prediction = conn.execute(
            "SELECT p.*, u.user_id AS created_by_user, e.original_filename "
            "FROM predictions p "
            "JOIN users u ON p.created_by = u.id "
            "JOIN eeg_records e ON p.eeg_record_id = e.id "
            "WHERE p.id = ? AND p.patient_id = ?",
            (prediction_id, patient_id),
        ).fetchone()
        if prediction is None:
            abort(404)
    finally:
        conn.close()

    probabilities = json.loads(prediction["class_probabilities_json"])
    ordered = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)

    return render_template(
        "prediction_result.html",
        patient=patient,
        prediction=prediction,
        probabilities=ordered,
    )
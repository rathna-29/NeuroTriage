# export.py
# Excel export route.

import logging

from flask import Blueprint, flash, redirect, send_file, session, url_for

from database.db import get_connection
from services.export_service import build_workbook, save_workbook
from utils.auth_utils import login_required

export_bp = Blueprint("export", __name__)
log = logging.getLogger(__name__)


# POST so another website cannot trigger exports by linking to this URL.
@export_bp.route("/export/excel", methods=["POST"])
@login_required
def export_excel():
    user = {
        "db_id": session["db_id"],
        "role": session["role"],
        "user_id": session["user_id"],
    }
    conn = get_connection()
    try:
        wb = build_workbook(conn, user)
    except Exception:
        log.exception("Excel export failed")
        flash("Unable to create the Excel file.", "error")
        return redirect(url_for("dashboard.dashboard"))
    finally:
        conn.close()

    try:
        path = save_workbook(wb, user["user_id"])
    except OSError:
        log.exception("Saving Excel export failed")
        flash("Unable to save the Excel file.", "error")
        return redirect(url_for("dashboard.dashboard"))

    return send_file(path, as_attachment=True, download_name=path.name)
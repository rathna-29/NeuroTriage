
# auth.py
# Login and logout routes with rate limiting.

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from database.db import get_connection
from utils import rate_limit

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Already logged in? Go straight to the dashboard.
    if "user_id" in session:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        # 1. Check that required fields are present.
        if not user_id or not password or role not in ("doctor", "clinician"):
            flash("Please enter your User ID, password and role.", "error")
            return render_template("login.html")

        # 2. Track failures by both User ID and client IP address.
        limit_keys = (
            f"user:{user_id.lower()}",
            f"ip:{request.remote_addr or 'unknown'}",
        )

        if any(rate_limit.is_blocked(key) for key in limit_keys):
            flash(
                "Too many failed attempts. Please wait 5 minutes and try again.",
                "error",
            )
            return render_template("login.html"), 429

        # 3. Look up the user safely using a SQL placeholder.
        conn = get_connection()
        try:
            user = conn.execute(
                "SELECT id, user_id, full_name, password_hash, role "
                "FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        finally:
            conn.close()

        # 4. Check the password and role.
        if (
            user is None
            or not check_password_hash(user["password_hash"], password)
            or user["role"] != role
        ):
            for key in limit_keys:
                rate_limit.record_failure(key)

            flash("Invalid login credentials.", "error")
            return render_template("login.html")

        # 5. Successful login: clear failures and start a fresh session.
        for key in limit_keys:
            rate_limit.clear(key)

        session.clear()
        session["user_id"] = user["user_id"]
        session["db_id"] = user["id"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]
        session.permanent = True

        return redirect(url_for("dashboard.dashboard"))

    return render_template("login.html")


# Logout uses POST rather than a plain link.
@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))

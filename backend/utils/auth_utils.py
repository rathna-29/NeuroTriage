# auth_utils.py
# Decorators that protect pages.

from functools import wraps

from flask import abort, flash, redirect, session, url_for


def login_required(view):
    """Allow the page only if the user is logged in."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def role_required(*allowed_roles):
    """Allow the page only for certain roles, e.g. @role_required('doctor').
    Use it together with @login_required (we will use it in a later step)."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") not in allowed_roles:
                abort(403)  # 403 = "Forbidden"
            return view(*args, **kwargs)

        return wrapped

    return decorator
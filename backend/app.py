
# app.py
# Main file of the NeuroTriage backend.

import logging

from flask import Flask, redirect, render_template, session, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect

from config import Config
from routes.auth import auth_bp
from routes.clinical import clinical_bp
from routes.dashboard import dashboard_bp
from routes.eeg import eeg_bp
from routes.export import export_bp
from routes.monitoring import monitoring_bp
from routes.patients import patients_bp
from routes.vitals import vitals_bp

csrf = CSRFProtect()


def create_app():
    """Build and return the Flask application."""
    Config.check()

    logging.basicConfig(level=logging.INFO)

    app = Flask(
        __name__,
        template_folder=str(Config.TEMPLATE_DIR),
        static_folder=str(Config.STATIC_DIR),
    )

    app.config.from_object(Config)

    # Enable CSRF protection for POST requests.
    csrf.init_app(app)

    # Register application routes.
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(vitals_bp)
    app.register_blueprint(clinical_bp)
    app.register_blueprint(eeg_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(monitoring_bp)

    @app.route("/")
    def home():
        if "user_id" in session:
            return redirect(url_for("dashboard.dashboard"))
        return redirect(url_for("auth.login"))

    # Add security headers to every response.
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'; "
            "object-src 'none'"
        )

        # Avoid browser caching of authenticated patient pages.
        if "user_id" in session:
            response.headers["Cache-Control"] = "no-store"

        return response

    # Friendly error pages.
    @app.errorhandler(CSRFError)
    def handle_csrf(error):
        return render_template(
            "error.html",
            code=400,
            title="Form expired",
            message=(
                "Your form expired or was not valid. "
                "Please go back, reload the page and try again."
            ),
        ), 400

    @app.errorhandler(403)
    def handle_403(error):
        return render_template(
            "error.html",
            code=403,
            title="Not allowed",
            message="You do not have permission to open this page.",
        ), 403

    @app.errorhandler(404)
    def handle_404(error):
        return render_template(
            "error.html",
            code=404,
            title="Not found",
            message="This page or record was not found.",
        ), 404

    @app.errorhandler(413)
    def handle_413(error):
        return render_template(
            "error.html",
            code=413,
            title="File too large",
            message=(
                "The uploaded file is too large. "
                "The maximum EEG file size is 2 MB."
            ),
        ), 413

    @app.errorhandler(500)
    def handle_500(error):
        app.logger.error("Unexpected server error: %s", error)
        return render_template(
            "error.html",
            code=500,
            title="Something went wrong",
            message=(
                "An unexpected error occurred. "
                "Please try again later."
            ),
        ), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=Config.DEBUG)

# config.py
# All application settings live here, in one place.

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# BASE_DIR is the main NeuroTriage folder.
BASE_DIR = Path(__file__).resolve().parent.parent

# Read the settings from the .env file into environment variables.
load_dotenv(BASE_DIR / ".env")


class Config:
    # Secret key used by Flask to protect sessions.
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Debug mode is ON only if .env says FLASK_DEBUG=1
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

    # Folders for the web pages and static files (CSS, JS, images).
    TEMPLATE_DIR = BASE_DIR / "frontend" / "templates"
    STATIC_DIR = BASE_DIR / "frontend" / "static"

    # Uploaded EEG files are stored here (outside the static folder,
    # so the browser cannot download them by URL).
    UPLOAD_DIR = BASE_DIR / "backend" / "uploads"

    # Flask rejects any request larger than this (a bit above our 2 MB file limit).
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024

    # --- Session security ---
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    # Cookies only travel over HTTPS when this is 1. Keep 0 for local http://127.0.0.1.
    # Set SESSION_COOKIE_SECURE=1 in .env if you ever deploy with HTTPS.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"

    # --- CSRF (Step 19) ---
    WTF_CSRF_TIME_LIMIT = 3600  # a form token is valid for 1 hour

    @staticmethod
    def check():
        """Stop with a clear message if the secret key is missing."""
        if not Config.SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY is missing. Create a .env file in the NeuroTriage "
                "folder and add a line: SECRET_KEY=your_random_key"
            )
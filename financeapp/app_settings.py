import json
import os
from django.conf import settings

def load_app_settings():
    """
    Load app settings from a JSON file located in the app directory.
    Returns a dictionary of settings. If the file is missing or invalid,
    returns an empty dictionary.
    """
    file_path = os.path.join(settings.BASE_DIR, "financeapp", "settings.json")
    if not os.path.exists(file_path):
        return {}  # Fallback if file doesn't exist

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Optional: log an error here
        return {}  # Fallback if JSON is invalid

# Load once at import time
APP_SETTINGS = load_app_settings()

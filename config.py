"""Read app settings from environment variables (.env locally) or Streamlit secrets (on the cloud)."""

import os

from dotenv import load_dotenv

# Load a local .env file into environment variables, if one exists. Does nothing on the cloud.
load_dotenv()

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"


def get_setting(name: str, default: str = "") -> str:
    """Return a setting from environment variables first, then Streamlit secrets, else the default."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        # Locally there is usually no secrets.toml, and reading st.secrets then raises an error.
        # Missing secrets are normal, so we fall back to the default instead of crashing.
        pass
    return default


def get_openfda_api_key() -> str:
    """Return the optional openFDA API key ("" if not set)."""
    return get_setting("OPENFDA_API_KEY")


def get_gemini_api_key() -> str:
    """Return the optional Gemini API key ("" if not set)."""
    return get_setting("GEMINI_API_KEY")


def get_gemini_model() -> str:
    """Return the Gemini model name, with a sensible default."""
    return get_setting("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

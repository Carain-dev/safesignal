"""All calls to the openFDA drug adverse event API, plus input validation and error handling."""

import re

import requests

import config

BASE_URL = "https://api.fda.gov/drug/event.json"
TIMEOUT_SECONDS = 15
MAX_NAME_LENGTH = 50
ALLOWED_NAME_PATTERN = re.compile(r"^[A-Za-z0-9 -]+$")

REACTION_FIELD = "patient.reaction.reactionmeddrapt.exact"
SERIOUS_FIELD = "serious"
DATE_FIELD = "receivedate"


class FDAError(Exception):
    """An error with a friendly message that the app can show directly to the user."""


def clean_drug_name(raw_name: str) -> str:
    """Trim the input and check it is a safe drug name. Raises ValueError with a friendly message."""
    name = raw_name.strip()
    if not name:
        raise ValueError("Please enter a drug name.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Drug names must be {MAX_NAME_LENGTH} characters or fewer.")
    if not ALLOWED_NAME_PATTERN.match(name):
        raise ValueError("Drug names can only contain letters, numbers, spaces and hyphens.")
    return name


def build_search(drug_name: str) -> str:
    """Build the openFDA search string that matches the generic OR the brand name."""
    name = clean_drug_name(drug_name)
    # In openFDA search syntax, a space between two terms means OR.
    return (
        f'patient.drug.openfda.generic_name:"{name}" '
        f'patient.drug.openfda.brand_name:"{name}"'
    )


def _get(params: dict) -> dict | None:
    """Send one request to openFDA. Return the JSON, or None if openFDA found no matching reports."""
    api_key = config.get_openfda_api_key()
    if api_key:
        params = {**params, "api_key": api_key}

    try:
        # Passing params lets requests handle the URL encoding of quotes, colons and spaces.
        response = requests.get(BASE_URL, params=params, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.Timeout:
        raise FDAError("openFDA took too long to respond. Please try again in a moment.")
    except requests.exceptions.ConnectionError:
        raise FDAError("Could not connect to openFDA. Please check your internet connection.")
    except requests.exceptions.RequestException:
        raise FDAError("Something went wrong while contacting openFDA. Please try again.")

    # openFDA answers "no matches" with HTTP 404, so this is a normal result, not a crash.
    if response.status_code == 404:
        return None
    if response.status_code == 429:
        raise FDAError("openFDA's rate limit was reached. Please wait a minute and try again.")
    if response.status_code >= 500:
        raise FDAError("openFDA is having problems right now. Please try again later.")
    if response.status_code != 200:
        raise FDAError(f"openFDA returned an unexpected error (HTTP {response.status_code}).")
    return response.json()


def get_total_reports(drug_name: str) -> int:
    """Return the total number of adverse event reports that mention the drug."""
    data = _get({"search": build_search(drug_name), "limit": 1})
    if data is None:
        return 0
    return data["meta"]["results"]["total"]


def get_counts(drug_name: str, field: str, limit: int | None = None) -> list[dict]:
    """Ask openFDA to count reports grouped by one field. Returns a list of {"term": ..., "count": ...}."""
    params = {"search": build_search(drug_name), "count": field}
    if limit is not None:
        params["limit"] = limit
    data = _get(params)
    if data is None:
        return []
    return data["results"]


def get_reaction_counts(drug_name: str, limit: int = 10) -> list[dict]:
    """Return the most-reported reactions, e.g. [{"term": "NAUSEA", "count": 1234}, ...]."""
    return get_counts(drug_name, REACTION_FIELD, limit)


def get_seriousness_counts(drug_name: str) -> list[dict]:
    """Return counts of serious (term 1) and non-serious (term 2) reports."""
    return get_counts(drug_name, SERIOUS_FIELD)


def get_date_counts(drug_name: str) -> list[dict]:
    """Return report counts per day received, e.g. [{"time": "20190314", "count": 5}, ...]."""
    return get_counts(drug_name, DATE_FIELD)

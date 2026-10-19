"""Tests for fda.py. requests.get is replaced with fakes, so no test touches the internet."""

import pytest
import requests

import fda


class FakeResponse:
    """Stands in for a requests Response: just a status code and some JSON."""

    def __init__(self, status_code: int, data: dict):
        self.status_code = status_code
        self._data = data

    def json(self) -> dict:
        return self._data


def fake_get_returning(status_code: int, data: dict):
    """Build a fake requests.get that always returns the given response and records its params."""
    calls = []

    def fake_get(url, params, timeout):
        calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(status_code, data)

    return fake_get, calls


def fake_get_raising(error: Exception):
    """Build a fake requests.get that always raises the given error."""

    def fake_get(url, params, timeout):
        raise error

    return fake_get


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    """Make every test run as if no openFDA key is set, whatever is in the local .env file."""
    monkeypatch.setattr(fda.config, "get_openfda_api_key", lambda: "")


# --- input validation ---


def test_clean_drug_name_trims_spaces():
    assert fda.clean_drug_name("  metformin  ") == "metformin"


def test_clean_drug_name_allows_spaces_digits_and_hyphens():
    assert fda.clean_drug_name("insulin glargine-100") == "insulin glargine-100"


@pytest.mark.parametrize("bad_name", ['drug"; drop', "aspirin%00", "metformin*", "a/b"])
def test_clean_drug_name_rejects_unsafe_characters(bad_name):
    with pytest.raises(ValueError):
        fda.clean_drug_name(bad_name)


def test_clean_drug_name_rejects_empty():
    with pytest.raises(ValueError):
        fda.clean_drug_name("   ")


def test_clean_drug_name_rejects_too_long():
    with pytest.raises(ValueError):
        fda.clean_drug_name("a" * 51)


def test_build_search_matches_generic_or_brand_name():
    search = fda.build_search("metformin")
    assert search == (
        'patient.drug.openfda.generic_name:"metformin" '
        'patient.drug.openfda.brand_name:"metformin"'
    )


# --- successful responses ---


def test_get_total_reports_reads_meta_total(monkeypatch):
    fake_get, calls = fake_get_returning(200, {"meta": {"results": {"total": 1234}}})
    monkeypatch.setattr(fda.requests, "get", fake_get)
    assert fda.get_total_reports("metformin") == 1234
    assert calls[0]["params"]["limit"] == 1
    assert calls[0]["timeout"] == fda.TIMEOUT_SECONDS


def test_get_reaction_counts_sends_count_field_and_limit(monkeypatch):
    results = [{"term": "NAUSEA", "count": 10}]
    fake_get, calls = fake_get_returning(200, {"results": results})
    monkeypatch.setattr(fda.requests, "get", fake_get)
    assert fda.get_reaction_counts("metformin", limit=5) == results
    assert calls[0]["params"]["count"] == fda.REACTION_FIELD
    assert calls[0]["params"]["limit"] == 5


def test_api_key_is_sent_when_configured(monkeypatch):
    monkeypatch.setattr(fda.config, "get_openfda_api_key", lambda: "my-key")
    fake_get, calls = fake_get_returning(200, {"meta": {"results": {"total": 1}}})
    monkeypatch.setattr(fda.requests, "get", fake_get)
    fda.get_total_reports("metformin")
    assert calls[0]["params"]["api_key"] == "my-key"


# --- "no reports" and errors ---


def test_404_means_no_reports(monkeypatch):
    fake_get, _ = fake_get_returning(404, {"error": {"code": "NOT_FOUND"}})
    monkeypatch.setattr(fda.requests, "get", fake_get)
    assert fda.get_total_reports("metfromin") == 0
    assert fda.get_reaction_counts("metfromin") == []


def test_timeout_gives_friendly_error(monkeypatch):
    monkeypatch.setattr(fda.requests, "get", fake_get_raising(requests.exceptions.Timeout()))
    with pytest.raises(fda.FDAError, match="too long"):
        fda.get_total_reports("metformin")


def test_connection_error_gives_friendly_error(monkeypatch):
    error = requests.exceptions.ConnectionError()
    monkeypatch.setattr(fda.requests, "get", fake_get_raising(error))
    with pytest.raises(fda.FDAError, match="connect"):
        fda.get_total_reports("metformin")


def test_rate_limit_gives_friendly_error(monkeypatch):
    fake_get, _ = fake_get_returning(429, {})
    monkeypatch.setattr(fda.requests, "get", fake_get)
    with pytest.raises(fda.FDAError, match="rate limit"):
        fda.get_total_reports("metformin")


def test_server_error_gives_friendly_error(monkeypatch):
    fake_get, _ = fake_get_returning(503, {})
    monkeypatch.setattr(fda.requests, "get", fake_get)
    with pytest.raises(fda.FDAError, match="problems"):
        fda.get_total_reports("metformin")


def test_invalid_name_never_calls_the_api(monkeypatch):
    fake_get, calls = fake_get_returning(200, {})
    monkeypatch.setattr(fda.requests, "get", fake_get)
    with pytest.raises(ValueError):
        fda.get_total_reports('drug"; drop')
    assert calls == []

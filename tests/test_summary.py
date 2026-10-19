"""Tests for summary.py. Gemini is replaced with fakes, so no test touches the internet."""

import pandas as pd
import pytest

import analysis
import summary


def sample_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build small reaction, seriousness and trend tables like the app would."""
    reactions = analysis.reactions_table(
        [
            {"term": "NAUSEA", "count": 300},
            {"term": "DIARRHOEA", "count": 200},
            {"term": "HEADACHE", "count": 100},
        ]
    )
    seriousness = analysis.seriousness_table([{"term": 1, "count": 60}, {"term": 2, "count": 40}])
    trend = analysis.yearly_trend(
        [{"time": "20220101", "count": 30}, {"time": "20230101", "count": 70}],
        current_year=2024,
    )
    return reactions, seriousness, trend


def test_template_summary_uses_the_numbers():
    reactions, seriousness, trend = sample_tables()
    text = summary.template_summary("metformin", 1000, reactions, seriousness, trend)
    assert "1,000" in text
    assert "nausea, diarrhoea, headache" in text
    assert "60.0%" in text
    assert "2023" in text


def test_template_summary_no_reports():
    empty = analysis.reactions_table([])
    text = summary.template_summary(
        "metfromin", 0, empty, analysis.seriousness_table([]), analysis.yearly_trend([])
    )
    assert "No adverse event reports were found" in text


def test_format_facts_contains_only_our_numbers():
    reactions, seriousness, trend = sample_tables()
    facts = summary.format_facts("metformin", 1000, reactions, seriousness, trend)
    assert "Total reports: 1000" in facts
    assert "- Nausea: 300" in facts
    assert "Serious reports: 60 (60.0%)" in facts
    assert "- 2023: 70" in facts


def test_make_summary_without_key_uses_template(monkeypatch):
    monkeypatch.setattr(summary.config, "get_gemini_api_key", lambda: "")
    reactions, seriousness, trend = sample_tables()
    text, label = summary.make_summary("metformin", 1000, reactions, seriousness, trend)
    assert label == summary.TEMPLATE_LABEL
    assert "1,000" in text


def test_make_summary_falls_back_when_gemini_fails(monkeypatch):
    def broken_ai_summary(facts, api_key, model):
        raise RuntimeError("quota exceeded")

    monkeypatch.setattr(summary.config, "get_gemini_api_key", lambda: "fake-key")
    monkeypatch.setattr(summary, "ai_summary", broken_ai_summary)
    reactions, seriousness, trend = sample_tables()
    text, label = summary.make_summary("metformin", 1000, reactions, seriousness, trend)
    assert label == summary.TEMPLATE_LABEL
    assert "1,000" in text


def test_make_summary_uses_gemini_when_it_works(monkeypatch):
    monkeypatch.setattr(summary.config, "get_gemini_api_key", lambda: "fake-key")
    monkeypatch.setattr(summary, "ai_summary", lambda facts, api_key, model: "An AI summary.")
    reactions, seriousness, trend = sample_tables()
    text, label = summary.make_summary("metformin", 1000, reactions, seriousness, trend)
    assert (text, label) == ("An AI summary.", summary.AI_LABEL)


class FakeResponse:
    """Stands in for Gemini's response object."""

    def __init__(self, text):
        self.text = text


class FakeClient:
    """Stands in for genai.Client and records what it was asked."""

    last_request = {}

    def __init__(self, api_key, http_options):
        self.models = self

    def generate_content(self, model, contents, config):
        FakeClient.last_request = {"model": model, "contents": contents}
        return FakeResponse("  Summary from the fake model.  ")


def test_ai_summary_sends_facts_and_returns_text(monkeypatch):
    monkeypatch.setattr(summary.genai, "Client", FakeClient)
    text = summary.ai_summary("Total reports: 5", "fake-key", "some-model")
    assert text == "Summary from the fake model."
    assert FakeClient.last_request == {"model": "some-model", "contents": "Total reports: 5"}


def test_ai_summary_empty_text_raises(monkeypatch):
    class EmptyClient(FakeClient):
        def generate_content(self, model, contents, config):
            return FakeResponse(None)

    monkeypatch.setattr(summary.genai, "Client", EmptyClient)
    with pytest.raises(ValueError):
        summary.ai_summary("facts", "fake-key", "some-model")

"""Tests for analysis.py using small hand-made inputs shaped like real openFDA results."""

import analysis


def test_reactions_table_sorts_and_keeps_top_n():
    raw = [
        {"term": "NAUSEA", "count": 50},
        {"term": "HEADACHE", "count": 80},
        {"term": "BLOOD GLUCOSE INCREASED", "count": 20},
    ]
    table = analysis.reactions_table(raw, top_n=2)
    assert list(table.columns) == ["Reaction", "Reports"]
    assert list(table["Reaction"]) == ["Headache", "Nausea"]
    assert list(table["Reports"]) == [80, 50]


def test_reactions_table_empty_input():
    table = analysis.reactions_table([])
    assert table.empty
    assert list(table.columns) == ["Reaction", "Reports"]


def test_seriousness_table_counts_and_percentages():
    raw = [{"term": 1, "count": 75}, {"term": 2, "count": 25}]
    table = analysis.seriousness_table(raw)
    assert list(table["Category"]) == ["Serious", "Non-serious"]
    assert list(table["Reports"]) == [75, 25]
    assert list(table["Percent"]) == [75.0, 25.0]


def test_seriousness_table_missing_term_counts_as_zero():
    table = analysis.seriousness_table([{"term": 1, "count": 10}])
    assert list(table["Reports"]) == [10, 0]
    assert list(table["Percent"]) == [100.0, 0.0]


def test_seriousness_table_empty_input_gives_zero_percent():
    table = analysis.seriousness_table([])
    assert list(table["Reports"]) == [0, 0]
    assert list(table["Percent"]) == [0.0, 0.0]


def test_yearly_trend_adds_days_into_years_and_drops_current_year():
    raw = [
        {"time": "20220105", "count": 3},
        {"time": "20220610", "count": 4},
        {"time": "20230301", "count": 10},
        {"time": "20240101", "count": 99},
    ]
    table = analysis.yearly_trend(raw, current_year=2024)
    assert list(table["Year"]) == [2022, 2023]
    assert list(table["Reports"]) == [7, 10]


def test_yearly_trend_empty_input():
    table = analysis.yearly_trend([])
    assert table.empty
    assert list(table.columns) == ["Year", "Reports"]

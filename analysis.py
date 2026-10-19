"""Pure functions that turn raw openFDA count results into small pandas tables for the charts."""

from datetime import date

import pandas as pd

SERIOUS_TERM = 1
NON_SERIOUS_TERM = 2


def reactions_table(reaction_counts: list[dict], top_n: int = 10) -> pd.DataFrame:
    """Return the top-N reactions as a table with columns Reaction and Reports, largest first."""
    if not reaction_counts:
        return pd.DataFrame(columns=["Reaction", "Reports"])
    table = pd.DataFrame(reaction_counts).rename(columns={"term": "Reaction", "count": "Reports"})
    # openFDA returns names in capitals (e.g. "BLOOD GLUCOSE INCREASED"); make them easier to read.
    table["Reaction"] = table["Reaction"].str.capitalize()
    table = table.sort_values("Reports", ascending=False).head(top_n)
    return table.reset_index(drop=True)


def seriousness_table(serious_counts: list[dict]) -> pd.DataFrame:
    """Return serious vs non-serious report counts with their percentages of the two together."""
    counts_by_term = {row["term"]: row["count"] for row in serious_counts}
    serious = counts_by_term.get(SERIOUS_TERM, 0)
    non_serious = counts_by_term.get(NON_SERIOUS_TERM, 0)
    total = serious + non_serious

    table = pd.DataFrame(
        {"Category": ["Serious", "Non-serious"], "Reports": [serious, non_serious]}
    )
    if total == 0:
        table["Percent"] = 0.0
    else:
        table["Percent"] = (table["Reports"] / total * 100).round(1)
    return table


def yearly_trend(date_counts: list[dict], current_year: int | None = None) -> pd.DataFrame:
    """Add up the per-day counts into reports per year, dropping the current (incomplete) year."""
    if not date_counts:
        return pd.DataFrame(columns=["Year", "Reports"])
    if current_year is None:
        current_year = date.today().year

    days = pd.DataFrame(date_counts)
    # Each "time" looks like "20190314"; the first 4 characters are the year.
    days["Year"] = days["time"].str[:4].astype(int)
    yearly = days.groupby("Year", as_index=False)["count"].sum()
    yearly = yearly.rename(columns={"count": "Reports"})

    # The current year is only partly reported, so including it would look like a sudden drop.
    yearly = yearly[yearly["Year"] < current_year]
    return yearly.reset_index(drop=True)

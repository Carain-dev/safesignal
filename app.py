"""SafeSignal Streamlit UI. Only screen layout lives here; API calls, maths and summaries live in other files."""

import pandas as pd
import streamlit as st

import analysis
import fda
import summary

EXAMPLE_DRUGS = ["metformin", "atorvastatin", "ibuprofen"]
LIMITATIONS_NOTE = (
    "These are voluntary reports. A report does not prove the drug caused the reaction, "
    "and counts do not show how common a reaction is - widely used drugs get more reports. "
    "Not medical advice."
)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_drug_data(drug_name: str, top_n: int) -> dict:
    """Fetch all openFDA counts for one drug. Cached for an hour so repeat searches skip the API."""
    return {
        "total": fda.get_total_reports(drug_name),
        "reactions": fda.get_reaction_counts(drug_name, limit=top_n),
        "seriousness": fda.get_seriousness_counts(drug_name),
        "dates": fda.get_date_counts(drug_name),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def build_summary(
    drug_name: str,
    total: int,
    reactions: pd.DataFrame,
    seriousness: pd.DataFrame,
    trend: pd.DataFrame,
) -> tuple[str, str]:
    """Return (summary text, label). Cached because Streamlit reruns the script on every click."""
    return summary.make_summary(drug_name, total, reactions, seriousness, trend)


def show_results(raw_name: str, top_n: int) -> None:
    """Validate the name, fetch the data and draw the metric, summary and charts."""
    try:
        # Lower-case so "Metformin" and "metformin" share one cache entry.
        drug_name = fda.clean_drug_name(raw_name).lower()
    except ValueError as error:
        st.warning(str(error))
        return

    try:
        with st.spinner(f"Fetching openFDA reports for {drug_name}..."):
            data = fetch_drug_data(drug_name, top_n)
    except fda.FDAError as error:
        st.error(str(error))
        return

    if data["total"] == 0:
        st.warning(
            f"No reports found for '{drug_name}'. Check the spelling, or try the generic name."
        )
        return

    reactions = analysis.reactions_table(data["reactions"], top_n=top_n)
    seriousness = analysis.seriousness_table(data["seriousness"])
    trend = analysis.yearly_trend(data["dates"])

    st.subheader(f"Results for {drug_name}")
    st.metric("Total reports", f"{data['total']:,}")

    with st.spinner("Writing summary..."):
        summary_text, summary_label = build_summary(
            drug_name, data["total"], reactions, seriousness, trend
        )
    with st.container(border=True):
        st.write(summary_text)
        st.caption(summary_label)

    st.markdown(f"#### Top {top_n} reported reactions")
    st.bar_chart(reactions, x="Reaction", y="Reports", horizontal=True, sort="-Reports")

    st.markdown("#### Serious vs non-serious reports")
    serious_column, non_serious_column = st.columns(2)
    for column, (_, row) in zip([serious_column, non_serious_column], seriousness.iterrows()):
        column.metric(row["Category"], f"{row['Reports']:,} ({row['Percent']}%)")
    st.bar_chart(seriousness, x="Category", y="Reports", sort=False, height=250)

    st.markdown("#### Reports per year")
    # Year as text so the axis shows "2019", not "2,019".
    st.line_chart(trend.astype({"Year": str}), x="Year", y="Reports")
    st.caption("The current year is left out because its reports are still coming in.")


st.set_page_config(page_title="SafeSignal", page_icon=":pill:")
st.title("SafeSignal: Drug Side-Effect Explorer")
st.write("Look up real FDA adverse event reports for a drug and see what is most often reported.")

if "drug" not in st.session_state:
    st.session_state.drug = ""

with st.form("search_form"):
    typed_name = st.text_input("Drug name (generic or brand)", placeholder="e.g. metformin")
    if st.form_submit_button("Search"):
        st.session_state.drug = typed_name

st.write("Or try an example:")
for column, example in zip(st.columns(len(EXAMPLE_DRUGS)), EXAMPLE_DRUGS):
    if column.button(example, width="stretch"):
        st.session_state.drug = example

# My change: let the user choose how many reactions the chart shows.
top_n = st.slider("Number of reactions to show", min_value=5, max_value=25, value=10)

st.info(LIMITATIONS_NOTE)

if st.session_state.drug:
    show_results(st.session_state.drug, top_n)

st.divider()
st.caption(
    "Data from openFDA (FDA Adverse Event Reporting System), https://open.fda.gov. "
    "openFDA cannot confirm the searched drug was the suspected cause in each report."
)

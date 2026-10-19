"""Write a short plain-English summary of the numbers: by Gemini if configured, otherwise from a template."""

import pandas as pd
from google import genai
from google.genai import types

import config

AI_LABEL = "AI summary"
TEMPLATE_LABEL = "Template summary"
GEMINI_TIMEOUT_MS = 20_000  # the Gen AI SDK measures timeouts in milliseconds

SYSTEM_INSTRUCTION = (
    "You summarise drug adverse event report counts from the FDA's FAERS database. "
    "Use ONLY the numbers given to you. Do not add any outside facts. "
    "Do not give medical advice. Do not say or imply that the drug caused any reaction, "
    "and do not say how common a reaction is. "
    "Write at most 4 sentences of plain English for a general reader."
)


def format_facts(
    drug_name: str,
    total: int,
    reactions: pd.DataFrame,
    seriousness: pd.DataFrame,
    trend: pd.DataFrame,
) -> str:
    """Turn the computed numbers into short structured text. This is the only thing the LLM sees."""
    lines = [f"Drug searched: {drug_name}", f"Total reports: {total}"]

    lines.append("Top reactions (reaction: number of reports):")
    for _, row in reactions.iterrows():
        lines.append(f"- {row['Reaction']}: {row['Reports']}")

    for _, row in seriousness.iterrows():
        lines.append(f"{row['Category']} reports: {row['Reports']} ({row['Percent']}%)")

    if not trend.empty:
        lines.append("Reports per full year:")
        for _, row in trend.iterrows():
            lines.append(f"- {row['Year']}: {row['Reports']}")
    return "\n".join(lines)


def template_summary(
    drug_name: str,
    total: int,
    reactions: pd.DataFrame,
    seriousness: pd.DataFrame,
    trend: pd.DataFrame,
) -> str:
    """Build a summary from fixed sentences filled in with the numbers. Never fails."""
    if total == 0:
        return (
            f"No adverse event reports were found for '{drug_name}' in openFDA. "
            "Check the spelling, or try the generic name."
        )

    sentences = [f"openFDA holds {total:,} adverse event reports that mention {drug_name}."]

    if not reactions.empty:
        top_three = ", ".join(reactions["Reaction"].head(3).str.lower())
        sentences.append(f"The most frequently reported reactions are {top_three}.")

    if seriousness["Reports"].sum() > 0:
        serious_percent = seriousness.loc[seriousness["Category"] == "Serious", "Percent"].iloc[0]
        sentences.append(f"{serious_percent}% of the reports were classed as serious.")

    if not trend.empty:
        peak = trend.loc[trend["Reports"].idxmax()]
        sentences.append(
            f"The most reports in a full year were received in {peak['Year']} ({peak['Reports']:,})."
        )
    return " ".join(sentences)


def ai_summary(facts: str, api_key: str, model: str) -> str:
    """Ask Gemini to summarise the facts. Raises an exception if anything goes wrong."""
    client = genai.Client(
        api_key=api_key, http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS)
    )
    response = client.models.generate_content(
        model=model,
        contents=facts,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,  # low temperature keeps the wording close to the numbers
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise ValueError("Gemini returned an empty summary.")
    return text


def make_summary(
    drug_name: str,
    total: int,
    reactions: pd.DataFrame,
    seriousness: pd.DataFrame,
    trend: pd.DataFrame,
) -> tuple[str, str]:
    """Return (summary text, label). Uses Gemini when a key is set, otherwise or on any error the template."""
    template = template_summary(drug_name, total, reactions, seriousness, trend)
    api_key = config.get_gemini_api_key()
    if not api_key or total == 0:
        return template, TEMPLATE_LABEL

    facts = format_facts(drug_name, total, reactions, seriousness, trend)
    try:
        return ai_summary(facts, api_key, config.get_gemini_model()), AI_LABEL
    except Exception:
        # Bad key, quota, network or model problems must never break the app, so fall back.
        return template, TEMPLATE_LABEL

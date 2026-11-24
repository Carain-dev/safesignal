# SafeSignal: Drug Side-Effect Explorer

**Live app:** https://safesignal-carain.streamlit.app

A small web app that looks up real FDA adverse-event reports for a drug and shows what is most often reported: the top reactions, how many reports were serious, and how report numbers have changed year by year. A short plain-English summary is written by Google Gemini, with a fixed template as a fallback when no API key is set or the call fails.

Data comes from [openFDA](https://open.fda.gov), which publishes the FDA Adverse Event Reporting System (FAERS).

> **What this is not:** an exploratory tool, not a validated safety-signal detector. These are voluntary reports. A report does not prove the drug caused the reaction, and raw counts do not show how common a reaction is, since widely used drugs simply get more reports. Not medical advice.

## Features

- Search by generic or brand name (e.g. `metformin`, `Lipitor`), or pick an example drug
- Total report count, top N reported reactions (adjustable 5–25), serious vs non-serious split, and a reports-per-year trend
- AI summary that only sees the computed numbers, never raw records, plus a template fallback that never fails
- Input validation and friendly error messages for bad names, no results, and API/network errors
- Results cached for an hour so repeat searches don't hit the API again
- 33 unit tests with pytest; the openFDA and Gemini calls are mocked, so tests run offline

## Tech stack

Python · Streamlit · pandas · requests · openFDA REST API · Google Gemini (`google-genai`) · pytest

## How the code is organised

Each file has one job, which keeps the UI separate from the logic and makes the logic easy to test.

| File | Responsibility |
|---|---|
| `app.py` | Streamlit screen layout only |
| `fda.py` | All openFDA API calls, input validation, error handling |
| `analysis.py` | Pure functions that turn raw counts into pandas tables for the charts |
| `summary.py` | Gemini summary with a template fallback |
| `config.py` | Reads settings from `.env` locally or Streamlit secrets in the cloud |
| `tests/` | pytest tests for `fda`, `analysis` and `summary` |

## Run it locally

Requires Python 3.11+.

```bash
git clone https://github.com/Carain-dev/safesignal.git
cd safesignal
pip install -r requirements.txt
cp .env.example .env      # both keys are optional
streamlit run app.py
```

Both keys in `.env` are optional. Without `OPENFDA_API_KEY` you get openFDA's lower anonymous rate limit, and without `GEMINI_API_KEY` the app uses the template summary.

## Run the tests

```bash
pytest
```

## Possible next steps

- Compare two drugs side by side
- Normalise counts (e.g. disproportionality measures like PRR) instead of showing raw report counts
- Filter by patient age group or sex

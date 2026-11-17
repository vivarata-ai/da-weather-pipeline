# DA Optional Makeup Assignment: Agentic Data Engineering Pipeline

End-to-end agentic data engineering pipeline in simple Python using
Google's Agent Development Kit (ADK). It ingests hourly temperature
forecasts from a public API, processes them, stores the results, and
shows them on a simple HTML page with a visualization.

Due: Tuesday, November 17, 2026, 12 PM ET. The assignment text comes
from the post by Myles Sparks on Nov 12, 2026 in the Data Analytics
channel of O365-FA26: MSIS Core, which points to the full description
on the DA homepage on Canvas.

## How each assignment requirement is met

| Requirement | How this project meets it |
| --- | --- |
| End-to-end agentic pipeline using simple Python and ADK | Three ADK agents (ingestion, processing, storage) run in sequence under a pipeline agent, executed by ADK Runner with an InMemorySessionService. See pipeline/agents.py. |
| Ingests data from a public API | Open-Meteo forecast API, no API key, hourly temperature_2m for 5 US cities. See pipeline/tools.py. |
| Processes it (filtering, grouping/aggregation) | Filters to valid daytime readings, groups by city and date, aggregates mean, min, max, and range. See pipeline/tools.py. |
| Stores it in S3 or GCS | Storage layer uploads to S3 or GCS when configured, and always keeps a local copy. See pipeline/storage.py and the environment variables below. |
| Shows the results on a simple HTML page with a visualization | output/index.html, a static page with a Chart.js bar chart and a full results table. Open it directly in a browser. |
| Public Git repo with code, professor can run it | This folder is the repo. Push it to a public Git repo and share the link. README has the setup and run steps. |
| Short document describing future improvements | FUTURE_IMPROVEMENTS.md. |

## Design, in the terms of the DA class

The method reference is the Virmani Data Engineering Architectural
Patterns decks (Day 1 and Day 1 plus 2), Data Governance (Day 4),
the DA syllabus, and the DA Architecture Assignment. The design
follows those decks:

- Ingestion pattern: batch. The consumer is a daily summary page
  and the data is a bounded forecast, so a scheduled load meets the
  latency the consumer needs. There is no reason to pay for
  streaming.
- Load strategy: kill and fill. Each run overwrites the same output
  files, so a run is idempotent. Re-running it produces the same
  result as running it once.
- Idempotency: outputs are written per run, never appended. The
  processed output was verified identical across two runs.
- File formats: raw API responses land as JSON text in the landing
  zone, and the curated daily summary is a separate JSON file. Raw
  text is never queried directly.
- Data quality at ingestion: rows with a missing temperature are
  dropped and counted, night hours are dropped and counted, and a
  city that fails after one retry is skipped and recorded, so one
  bad response does not stop the whole batch.
- Governance: no credentials in source code. Cloud credentials come
  from the standard AWS or Google Cloud credential chain, and
  storage is least privilege by bucket, not by broad access.

The agents are ADK BaseAgent subclasses, not LlmAgent. The pipeline
is deterministic: ingest, filter, group, aggregate, and store have
one correct answer for a given API response, so an LLM call would
add cost, latency, and nondeterminism without changing the result.
Using BaseAgent also means the pipeline runs with no Gemini API
key, so the professor can run it as is. The agents, the Runner, and
the session are all real ADK, version 2.14.1, verified against the
installed package. ADK docs: https://google.github.io/adk-docs/

## Prerequisites

- Python 3.11 or newer (tested on Python 3.12).
- Internet access, for the Open-Meteo API call and for the Chart.js
  CDN on the results page. The results table works offline, the
  chart needs internet.
- No API key. No cloud account. No Gemini API key.

## Setup and run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Then open `output/index.html` in a browser.

What the run does, in order: the ingestion agent fetches 3 days of
hourly forecasts for New York, Chicago, Los Angeles, Houston, and
Seattle (5 API calls, 360 hourly records), the processing agent
filters to valid daytime readings (06:00 to 21:00 local time) and
aggregates by city and date, and the storage agent writes the
outputs. A sample run kept 240 of 360 rows, dropped 120 night
hours and 0 null temperatures, and produced 15 city-day summaries
for Nov 15 to 17, 2026.

To run the unit tests, which need no network:

```bash
python tests/test_processing.py
```

## Outputs

All outputs are in the `output/` directory:

- `raw.json`: the raw API responses, as received, one entry per
  city. This is the landing zone.
- `processed.json`: the daily summary, one row per city per date,
  with count, mean, min, max, and range in Fahrenheit, plus the
  filter summary and any failed cities.
- `index.html`: the results page. Open it directly, no server
  needed. The data is embedded in the page.

## Cloud storage (optional)

By default, `STORAGE_BACKEND` is `local` and everything is written
to the `output/` directory. To also store in the cloud, set these
environment variables before running:

```bash
# Amazon S3
export STORAGE_BACKEND=s3
export S3_BUCKET=your-bucket-name

# Google Cloud Storage
export STORAGE_BACKEND=gcs
export GCS_BUCKET=your-bucket-name
```

Cloud credentials come from the standard chain: AWS credentials for
S3, Google Application Default Credentials for GCS. No credentials
go in the code or in a config file. Files are uploaded under the
`da-pipeline/` prefix in the bucket. If the cloud upload fails, the
run keeps the local copy, records a warning, and still succeeds.

## Project layout

```text
main.py                  One-command run path, ADK Runner entry point
agent.py                 ADK entry point, module-level root_agent
pipeline/
  config.py              Cities, API settings, storage settings
  tools.py               API calls, filtering, grouping, aggregation
  agents.py              ADK agents: ingest, process, store, pipeline
  storage.py             Local, S3, and GCS storage
  render.py              HTML results page
tests/
  test_processing.py     Unit tests, no network needed
output/
  raw.json               Sample raw output from a real run
  processed.json         Sample processed output from a real run
  index.html             Sample results page from a real run
```

## Notes

- The temperatures are forecasts, not observed values. The page
  and the processed file both say so.
- The Open-Meteo response shape was verified by a live call before
  coding: hourly.time is ISO 8601 strings, hourly.temperature_2m
  is numbers or null, and hourly_units gives the unit.

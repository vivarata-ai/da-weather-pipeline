# Future Improvements

By: Varun Ratakonda
Public Git repository: https://github.com/vivarata-ai/da-weather-pipeline

This document lists what should be improved next in the pipeline, in order of priority.

## 1. Incremental Loads with a High-Water Mark

The pipeline currently uses kill and fill. Every run refetches the full 3 day forecast and overwrites the outputs. To keep a longer history, the pipeline should switch to incremental loads. This means storing the latest timestamp already loaded, fetching only the newer hours, and upserting on city plus timestamp so a re-run still changes nothing. This approach follows the Virmani decks. Incremental loads are cheaper over time and easier to recover from after a partial failure, and the upsert key keeps the pipeline idempotent.

## 2. A Real Warehouse Table Instead of Flat Files

The curated output is currently a JSON file. The next step is to load the daily summary into a warehouse table that is partitioned by date and clustered by city. The decks state the rule directly: partition on the date column the queries filter by, and cluster on the high-cardinality column the queries filter and join by. This makes the summary queryable with SQL instead of being read as a whole file. It also makes the cost argument concrete, since partitioning, clustering, and column projection together are what keep a large table affordable.

## 3. More Metrics and a Second Source

Relative humidity and precipitation probability can be added from the same Open-Meteo call. A second public API, such as the USGS earthquake feed, should be added as a second ingestion agent. Each new source gets its own ingestion agent and its own validation, so a failure in one source does not stop the other. The processing agent would then aggregate per source as well as per city and date.

## 4. Scheduled Runs with Retries and Alerts

The pipeline currently runs once, by hand. It should be put on a schedule with concurrency control so that a slow run cannot overlap the next one. It also needs retries for transient API failures and an alert when a city fails or the null rate spikes. The decks require all four of these: no overlaps, retries, logging and alerts, and a stated time zone.

## 5. A Dead-Letter File for Bad Records

Dropped rows are currently only counted. Each dropped row should be written to a dead-letter file along with the reason it was dropped. This way bad data can be inspected and reprocessed instead of disappearing into a count. This follows the streaming at scale rule from the decks: never retry forever, and always send the bad element somewhere it can be seen.

## 6. An LLM Analyst Agent, When a Key Is Available

The agents are currently deterministic BaseAgent subclasses, which is the right choice for a pipeline with one correct answer. If a Gemini API key is available, an LlmAgent could be added to read the daily summary and write a short plain-language summary of the findings, such as which city had the widest daily range. It should stay separate from the pipeline itself, so the numbers never depend on the model.

## 7. Monitoring and Alerting

Every run should produce structured logging that records the run id, rows received and kept, cities failed, and upload status. An alert should be sent when a run fails, a city fails, or the null rate spikes. A run history table should also be kept, so a missed run is visible the next morning instead of being found when the page looks stale.

## 8. Testing

Tests should cover the ingestion and storage steps, not only processing. The API response parser should be tested against a saved sample response, and the GCS and S3 upload paths should be tested with a mocked client. An end to end test on sample data should check that the HTML page contains the expected city rows. These tests should run in continuous integration on every push.

## 9. Security

The least privilege rule already in the design should stay in place. The storage credential may write only to the one pipeline bucket and prefix, never to other buckets. Cloud credentials should be rotated and never committed, and the bucket should stay private since the HTML page is served from the local copy. A check should also be added so that no credential file is ever added to the repo.

## 10. Cost

The pipeline is cheap today. The API is free, the run is short, and the outputs are small files. To keep it that way, the pipeline should stay on kill and fill for a 3 day window, avoid a warehouse until the history grows, and use a lifecycle rule on the bucket so old raw files expire instead of accumulating. If the window grows, the pipeline should move to the incremental loads in item 1 before paying for a larger run.

## 11. Data Quality

Beyond the current null and night filters, the pipeline should add range checks on temperature, a check that every city returns the expected number of hours, and a comparison of the new daily summary against the previous run. That comparison means a sudden jump is flagged instead of silently published. These data quality checks should be recorded in the processed file alongside the filter summary.

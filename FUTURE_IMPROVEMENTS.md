# Future Improvements

Public Git repository: https://github.com/vivarata-ai/da-weather-pipeline

Short list of what to improve next, in priority order.


## 1. Incremental loads with a high-water mark

Today the pipeline uses kill and fill: every run refetches the full
3 day forecast and overwrites the outputs. For a longer history,
switch to incremental loads. Store the latest timestamp already
loaded, fetch only newer hours, and upsert on city plus timestamp
so a re-run still changes nothing. This follows the Virmani decks:
incremental is cheaper over time and easier to recover from partial
failures, and idempotency still holds through the upsert key.

## 2. A real warehouse table instead of flat files

Today the curated output is a JSON file. The next step is to load
the daily summary into a warehouse table, partitioned by date and
clustered by city, following the decks: partition on the date column
the queries filter by, cluster on the high-cardinality column the
queries filter and join by. That makes the summary queryable with
SQL instead of read as a whole file, and it makes the cost argument
concrete: partition plus clustering plus column projection is what
keeps a large table affordable.

## 3. More metrics and a second source

Add relative humidity and precipitation probability from the same
Open-Meteo call, and add a second public API, such as the USGS
earthquake feed, as a second ingestion agent. Each new source gets
its own ingestion agent and its own validation, so a failure in one
source does not stop the other. The processing agent would then
aggregate per source as well as per city and date.

## 4. Scheduled runs with retries and alerts

Today the pipeline runs once, by hand. Put it on a schedule with
concurrency control so a slow run cannot overlap the next one, add
retries for transient API failures, and add an alert when a city
fails or the null rate spikes. The decks require all four: no
overlaps, retries, logging and alerts, and a stated time zone.

## 5. A dead-letter file for bad records

Today dropped rows are only counted. Write each dropped row to a
dead-letter file with the reason it was dropped, so bad data can be
inspected and reprocessed instead of disappearing into a count.
This is the streaming at scale rule from the decks: never retry
forever, always send the bad element somewhere it can be seen.

## 6. An LLM analyst agent, when a key is available

Today the agents are deterministic BaseAgent subclasses, which is
the right choice for a pipeline with one correct answer. If a
Gemini API key is available, add an LlmAgent that reads the daily
summary and writes a short plain-language summary of the findings,
such as which city had the widest daily range. Keep it separate
from the pipeline itself, so the numbers never depend on the model.

## 7. Monitoring and alerting

Add structured logging for every run, with run id, rows received and kept, cities failed, and upload status, and send an alert when a run fails, a city fails, or the null rate spikes. Keep a run history table so a missed run is visible the next morning instead of being found when the page looks stale.

## 8. Testing

Add tests for the ingestion and storage steps, not only processing. Test the API response parser against a saved sample response, test the GCS and S3 upload paths with a mocked client, and add an end to end test on sample data that checks the HTML page contains the expected city rows. Run the tests in continuous integration on every push.

## 9. Security

Keep the least privilege rule already in the design: the storage credential may write only to the one pipeline bucket and prefix, never to other buckets. Rotate cloud credentials, never commit them, and keep the bucket private, since the HTML page is served from the local copy. Add a check that no credential file is ever added to the repo.

## 10. Cost

The pipeline is cheap today: the API is free, the run is short, and the outputs are small files. Keep it that way by staying on kill and fill for a 3 day window, avoiding a warehouse until the history grows, and setting a lifecycle rule on the bucket so old raw files expire instead of accumulating. If the window grows, move to incremental loads in item 1 before paying for a larger run.

## 11. Data quality

Beyond the current null and night filters, add range checks on temperature, a check that every city returns the expected number of hours, and a comparison of the new daily summary against the previous run so a sudden jump is flagged instead of silently published. Record the data quality checks in the processed file alongside the filter summary.

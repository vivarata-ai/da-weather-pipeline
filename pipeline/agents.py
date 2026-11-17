"""ADK agents for the DA extra credit pipeline.

Google ADK, version 2.14.1, verified against the installed package.
Each step of the pipeline is an agent, a subclass of ADK BaseAgent,
and the pipeline itself is an ADK SequentialAgent, the built-in
workflow agent that runs its sub-agents in order. They are executed by ADK Runner with an
InMemorySessionService, and they share state through the session:
the ingestion agent writes the raw records, the processing agent
reads them and writes the daily summary, and the storage agent
reads the summary and writes the output files.

Why BaseAgent and not LlmAgent: this pipeline is deterministic.
Ingest, filter, group, aggregate, and store have one correct answer
for a given API response, so an LLM call would add cost, latency,
and nondeterminism without changing the result. Using BaseAgent
also means the pipeline runs with no Gemini API key, so the
professor can run it as is. The agents, the Runner, and the session
are all real ADK; only the reasoning step is replaced by code,
which is what the ADK docs describe BaseAgent for.
"""

import json
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types

from . import config, storage, tools
from .render import render_html


def _event(agent_name, text, state_delta=None):
    return Event(
        author=agent_name,
        content=types.Content(parts=[types.Part(text=text)]),
        actions=EventActions(state_delta=state_delta or {}))


class IngestionAgent(BaseAgent):
    """Fetches hourly forecasts for each city from Open-Meteo.

    Ingestion pattern, in the Virmani decks: batch, because the
    consumer is a daily summary page and the data is a bounded
    forecast, not an unbounded stream. Latency of minutes to hours
    is enough, so there is no reason to pay for streaming.
    """

    async def _run_async_impl(
            self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        payloads, failed = tools.fetch_all_cities(config.CITIES)
        records = tools.to_records(payloads)
        ctx.session.state["raw_payloads"] = payloads
        ctx.session.state["records"] = records
        ctx.session.state["failed_cities"] = failed
        yield _event(
            self.name,
            "Ingested %d hourly records from %d cities, %d cities failed."
            % (len(records), len(payloads), len(failed)))


class ProcessingAgent(BaseAgent):
    """Filters, groups, and aggregates the ingested records.

    Data quality, in the Virmani decks: assume missing values will
    happen and design the handling before the pipeline goes live.
    Rows with a missing temperature are dropped and counted, and
    night hours are dropped and counted, so the filter is visible.
    """

    async def _run_async_impl(
            self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        records = ctx.session.state.get("records", [])
        kept, filter_summary = tools.filter_valid_readings(records)
        daily = tools.aggregate_daily(kept)
        processed = tools.build_processed_payload(
            daily, filter_summary, ctx.session.state.get("failed_cities", []))
        ctx.session.state["processed"] = processed
        yield _event(
            self.name,
            "Processed %d kept rows into %d city-day summaries, "
            "kept %d of %d rows."
            % (filter_summary["kept"], len(daily),
               filter_summary["kept"], filter_summary["received"]))


class StorageAgent(BaseAgent):
    """Writes raw data, processed data, and the HTML page.

    Storage pattern, in the Virmani decks: the raw API responses
    land as-is in the landing zone, and the curated daily summary
    sits on top of them. The load is kill and fill, so re-running
    overwrites the same files instead of appending, which makes the
    pipeline idempotent.
    """

    async def _run_async_impl(
            self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        processed = ctx.session.state.get("processed", {})
        raw_payloads = ctx.session.state.get("raw_payloads", [])
        if not processed.get("daily"):
            # Every city failed or every row was filtered out. Keep the
            # last good outputs instead of overwriting them with an
            # empty run, and say so.
            yield _event(
                self.name,
                "No data to store, so the previous outputs were kept. "
                "Failed cities: %s"
                % [f["city"] for f in
                   ctx.session.state.get("failed_cities", [])],
                state_delta={"storage_skipped": True})
            return
        files = {
            "raw.json": json.dumps(raw_payloads, indent=2),
            "processed.json": json.dumps(processed, indent=2),
            "index.html": render_html(processed),
        }
        result = storage.store_outputs(files)
        ctx.session.state["storage_result"] = result
        message = "Stored %d files locally." % len(result["local_paths"])
        if result["cloud_paths"]:
            message += " Uploaded to: %s." % ", ".join(result["cloud_paths"])
        if result["warning"]:
            message += " Warning: %s" % result["warning"]
        yield _event(self.name, message)


def build_pipeline_agent():
    """Build the pipeline: ingest, then process, then store.

    SequentialAgent is ADK's built-in workflow agent. It runs the
    sub-agents in order on one shared session, so each agent reads
    what the previous agent wrote to session state.
    """
    return SequentialAgent(
        name="pipeline_agent",
        description="End-to-end weather data pipeline.",
        sub_agents=[
            IngestionAgent(name="ingestion_agent"),
            ProcessingAgent(name="processing_agent"),
            StorageAgent(name="storage_agent"),
        ],
    )

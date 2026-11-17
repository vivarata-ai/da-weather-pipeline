"""One-command run path for the DA extra credit pipeline.

Run: python main.py

This starts the ADK Runner with an InMemorySessionService, runs the
pipeline agent (ingest, process, store), and prints what each agent
did. No API key and no cloud credentials are needed. With no cloud
configuration, outputs are written to the output directory.
"""

import asyncio

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from pipeline import config
from pipeline.agents import build_pipeline_agent


async def run_pipeline():
    """Run the pipeline. Returns True when outputs were stored."""
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=config.APP_NAME, user_id="da_student", session_id="run_1")
    runner = Runner(
        agent=build_pipeline_agent(),
        app_name=config.APP_NAME,
        session_service=session_service)
    print("Running DA extra credit pipeline...")
    async for event in runner.run_async(
            user_id="da_student",
            session_id="run_1",
            new_message=types.Content(
                parts=[types.Part(text="Run the weather pipeline.")]),
    ):
        if event.content and event.content.parts:
            print("[%s] %s" % (event.author, event.content.parts[0].text))
    session = await session_service.get_session(
        app_name=config.APP_NAME, user_id="da_student", session_id="run_1")
    if session.state.get("storage_skipped"):
        print("Run failed: no data was ingested, so nothing was stored. "
              "Check your internet connection and run again.")
        return False
    # Read the result from the files on disk, not from session state.
    # The storage agent writes the files, and the disk is the record
    # of what was stored.
    import json
    import os

    print("Done. Local files:")
    for name in sorted(os.listdir(config.OUTPUT_DIR)):
        print("  " + os.path.join(config.OUTPUT_DIR, name))
    processed_path = os.path.join(config.OUTPUT_DIR, "processed.json")
    with open(processed_path) as handle:
        processed = json.load(handle)
    print("Daily summaries: %d, dates: %s"
          % (len(processed["daily"]), ", ".join(processed["dates"])))
    return True


def main():
    if not asyncio.run(run_pipeline()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

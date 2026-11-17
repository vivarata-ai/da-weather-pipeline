"""ADK entry point: the module-level root_agent.

The ADK command line tools look for root_agent in agent.py, so this
file exposes the pipeline agent. The normal run path is still
python main.py, which uses the same agent.
"""

from pipeline.agents import build_pipeline_agent

root_agent = build_pipeline_agent()

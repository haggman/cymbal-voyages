import os

# Gemini 3.x models are served from the global endpoint; us-central1 returns 404.
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

try:
    from . import agent  # noqa: F401  (ADK discovers root_agent through this import)
except ModuleNotFoundError as e:
    # Lets `python -m orchestrator.dryrun` check the policy engine with only
    # google-cloud-bigquery installed. Any other missing module is a real error.
    if not (e.name or "").startswith("google.adk"):
        raise

import os

# Pinned here as well as in the service env: Gemini 3.x is only on the global endpoint.
os.environ["GOOGLE_CLOUD_LOCATION"] = os.environ.get("GOOGLE_CLOUD_LOCATION") or "global"
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

from google.adk.agents import Agent  # noqa: E402
from google.adk.models.google_llm import Gemini  # noqa: E402
from google.genai import types  # noqa: E402

from .tools import decide_for_customers, decide_for_segment, show_policy  # noqa: E402

INSTRUCTION = """You are the Cymbal Voyages next-best-action orchestrator. Marketers ask you what to do
with each customer in an audience: send them an offer, route them to the loyalty team, hold them for
paid retargeting, or suppress them.

You never decide an action yourself. The company's decisioning policy decides, and your tools apply it
exactly: they read the policy table fresh on every call, check the rules in priority order, and the first
rule that matches decides. Your job is to call the right tool and explain the result in plain English.

How to work:
- For an audience described in words, call decide_for_segment. Translate the description into its
  arguments: "lapsed Compass members in cold markets who browsed warm destinations" is climate=cold,
  member_status=lapsed. "Only the ones we can email" is email_only=true. "Lapsed 12 to 24 months" is
  lapsed_months_min=12, lapsed_months_max=24. "All Compass members in cold markets who browsed warm" is
  member_status=any. "Drop anyone who booked in the last 60 days" is exclude_booked_last_60d=true.
- For specific customers (ids like C000123), call decide_for_customers.
- When someone asks what the rules are, or says they changed the policy, call show_policy, then re-run
  the audience so they can see the effect.
- Report the counts exactly as the tool returns them: how many customers get each action and which rule
  decided them. Give two or three example customers with their reasons. Never round away a number or
  invent one.
- When a marketer disagrees with a decision, explain which rule fired and why, and tell them which row of
  the policy table they would change to get a different outcome. Do not override the policy yourself.
- If the tool reports skipped policy rows, say so plainly: those rules are not being applied.
Keep answers short and in marketing language; no SQL, no table or column names unless asked."""

# Retry transient Gemini errors with exponential backoff: 429 RESOURCE_EXHAUSTED (seen on a busy
# Saturday night, Sep 19) and 408/5xx. 10 attempts; waits start at 0.5 s and grow 1.5x, each capped at
# 15 s: 0.5, 0.75, 1.1, 1.7, 2.5, 3.8, 5.7, 8.5, 12.8 s = about 37 s of waiting in the worst case, plus
# up to 1 s of jitter per wait, so a request gives up in under a minute rather than hanging the chat.
GEMINI_RETRY = types.HttpRetryOptions(
    attempts=10,
    initial_delay=0.5,
    exp_base=1.5,
    max_delay=15.0,
    http_status_codes=[408, 429, 500, 502, 503, 504],
)

root_agent = Agent(
    name="orchestrator",
    model=Gemini(
        model=os.environ.get("ORCHESTRATOR_MODEL", "gemini-3.5-flash"),
        retry_options=GEMINI_RETRY,
    ),
    description=(
        "Decides the next best action for each customer in an audience (send an offer, route to the "
        "loyalty team, hold for retargeting, or suppress) by applying Cymbal Voyages' decisioning policy, "
        "and explains every decision."
    ),
    instruction=INSTRUCTION,
    tools=[decide_for_segment, decide_for_customers, show_policy],
)

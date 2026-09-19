"""BigQuery access for the orchestrator. Table names come from the environment."""
from __future__ import annotations

import os
import re
from typing import Any

FEATURE_COLUMNS = (
    "customer_id, propensity_score, days_since_last_booking, loyalty_tier, loyalty_status, "
    "home_market_climate, lifetime_bookings, lifetime_value_usd, ltv_band, booked_last_60d, "
    "has_active_reservation, email_contactable, sms_contactable, sessions_last_90d, "
    "warm_views_last_90d, recent_engagement_score"
)

MAX_IDS = 200


def project() -> str:
    return os.environ.get("BQ_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT") or ""


def dataset() -> str:
    return os.environ.get("BQ_DATASET", "cymbal_voyages")


def table(name: str) -> str:
    p = project()
    return f"`{p}.{dataset()}.{name}`" if p else f"`{dataset()}.{name}`"


_client = None


def client():
    global _client
    if _client is None:
        from google.cloud import bigquery
        token = os.environ.get("BQ_ACCESS_TOKEN")  # for local checks run with a gcloud user token
        if token:
            from google.oauth2.credentials import Credentials
            _client = bigquery.Client(project=project() or None, credentials=Credentials(token))
        else:
            _client = bigquery.Client(project=project() or None)
    return _client


def _query(sql: str, params: list) -> list[dict]:
    from google.cloud import bigquery
    job = client().query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params))
    return [dict(r.items()) for r in job.result()]


# ---- argument normalization (never trust how a person or a model typed it) ----

def norm_climate(value: Any) -> str:
    s = str(value or "any").strip().lower()
    for c in ("cold", "mild", "warm"):
        if c in s:
            return c
    return "any"


def norm_member_status(value: Any) -> str:
    s = str(value or "any").strip().lower()
    if "laps" in s:
        return "lapsed"
    if "active" in s or "current" in s:
        return "active"
    if "never" in s:
        return "never"
    return "any"


def norm_customer_id(value: Any) -> str | None:
    s = str(value or "").strip().upper()
    digits = re.sub(r"\D", "", s)
    if not digits:
        return None
    return "C" + digits.zfill(6)


def _int(value: Any) -> int:
    try:
        return max(0, int(round(float(value))))
    except (TypeError, ValueError):
        return 0


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "t", "yes", "y", "1"}


def segment_params(climate, member_status, lapsed_months_min=0, lapsed_months_max=0,
                   email_only=False, exclude_booked_last_60d=False) -> dict:
    return {
        "climate": norm_climate(climate),
        "member_status": norm_member_status(member_status),
        "lapsed_months_min": _int(lapsed_months_min),
        "lapsed_months_max": _int(lapsed_months_max),
        "email_only": _bool(email_only),
        "exclude_booked_last_60d": _bool(exclude_booked_last_60d),
    }


# Same filter as the Toolbox resolve_segment tool (without the destination match).
SEGMENT_WHERE = """
  (@climate = 'any' OR f.home_market_climate = @climate)
  AND f.loyalty_tier != 'none'
  AND f.warm_views_last_90d >= 1
  AND (@member_status = 'any' OR f.loyalty_status = @member_status)
  AND (@lapsed_months_min <= 0 OR f.days_since_last_booking >= CAST(ROUND(@lapsed_months_min * 365 / 12) AS INT64))
  AND (@lapsed_months_max <= 0 OR f.days_since_last_booking < CAST(ROUND(@lapsed_months_max * 365 / 12) AS INT64))
  AND (NOT @email_only OR f.email_contactable)
  AND (NOT @exclude_booked_last_60d OR NOT f.booked_last_60d)
"""


def segment_rows(p: dict) -> list[dict]:
    from google.cloud import bigquery as bq
    sql = f"SELECT {FEATURE_COLUMNS} FROM {table('customer_features')} f WHERE {SEGMENT_WHERE}"
    params = [
        bq.ScalarQueryParameter("climate", "STRING", p["climate"]),
        bq.ScalarQueryParameter("member_status", "STRING", p["member_status"]),
        bq.ScalarQueryParameter("lapsed_months_min", "INT64", p["lapsed_months_min"]),
        bq.ScalarQueryParameter("lapsed_months_max", "INT64", p["lapsed_months_max"]),
        bq.ScalarQueryParameter("email_only", "BOOL", p["email_only"]),
        bq.ScalarQueryParameter("exclude_booked_last_60d", "BOOL", p["exclude_booked_last_60d"]),
    ]
    return _query(sql, params)


def customer_rows(ids: list[str]) -> list[dict]:
    from google.cloud import bigquery as bq
    sql = f"SELECT {FEATURE_COLUMNS} FROM {table('customer_features')} f WHERE f.customer_id IN UNNEST(@ids)"
    return _query(sql, [bq.ArrayQueryParameter("ids", "STRING", ids)])


def policy_rows() -> list[dict]:
    return _query(f"SELECT * FROM {table('decisioning_policy')} ORDER BY priority, rule_id", [])

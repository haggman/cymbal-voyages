#!/usr/bin/env python3
"""Render docs/data-dictionary.md from cvgen/schemas.py, out/_manifest.json and the verified queries."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "sql"))
from cvgen import config as C  # noqa: E402
from cvgen.schemas import SCHEMAS  # noqa: E402
from walkthrough_queries import VERIFIED  # noqa: E402

manifest = json.loads((ROOT / "out" / "_manifest.json").read_text())
rows = {t: v["rows"] for t, v in manifest["tables"].items()}
mb = {t: v["bytes"] / 1e6 for t, v in manifest["tables"].items()}
m = manifest["reference_model"]

TABLE_ORDER = ["customers", "customer_month_status", "customer_features", "destinations", "packages", "catalog_embeddings",
               "web_sessions", "bookings", "plan", "ad_performance", "campaign_history", "creative_variants",
               "propensity_training", "decisioning_policy", "activations"]

AGENT_INSTRUCTIONS = """You are the analytics assistant for Cymbal Voyages, an online travel brand, answering marketers' questions from the `cymbal_voyages` dataset. Warm escapes (`category = 'warm_escape'`) are winter and early-spring getaways to sun destinations; they are the signature category and sell mostly to customers in cold-weather markets, who book from late summer onward. A booking is a row in `bookings` with `status = 'confirmed'`; cancelled rows never count, and revenue is `revenue_usd` on confirmed rows. A booking's category comes from `packages` joined to `destinations`. Fiscal months are calendar months: compare actuals against `plan` by the calendar month of `booking_date`, `category` and the customer's `home_market`; variance = actual / plan − 1. The channel taxonomy is fixed: paid_search, paid_social, organic, email, direct, affiliate; `ad_performance` covers only the paid channels. Loyalty: anyone with `loyalty_tier` other than `none` is a Cymbal Compass member; lapsed means at least one booking ever and none in the last 12 months. Use `customer_month_status` for status as of a given month and `customer_features` for status as of Sep 1, 2026. Session conversion rate is `COUNTIF(converted) / COUNT(*)` on `web_sessions`; anonymous sessions (`customer_id IS NULL`) never convert. When asked why a number changed, break it down by category, climate, market and customer cohort before speculating, and say which table each figure came from."""

GLOSSARY = [
    ("warm escapes", "Cymbal Voyages' signature category: winter and early-spring getaways to sun destinations (Caribbean, Mexico, Hawaii, Central America, the Florida Keys). `destinations.category = 'warm_escape'`. Booking season runs August–January; travel runs December–April."),
    ("booking", "A confirmed reservation: a row in `bookings` with `status = 'confirmed'`. Cancelled rows are excluded from booking counts and revenue. Counted by `booking_date`, not travel date."),
    ("lapsed member", "A Cymbal Compass member (`loyalty_tier != 'none'`) with at least one confirmed booking ever and none in the last 12 months (`loyalty_status = 'lapsed'`, equivalently `days_since_last_booking >= 365`). Status is evaluated as of a date: use `customer_month_status` for a past month, `customer_features` for Sep 1, 2026."),
    ("cold-weather markets", "Chicago, Boston, Minneapolis, Detroit, Denver, Toronto, Cleveland, Milwaukee (`home_market_climate = 'cold'`). Warm markets are Miami, Phoenix, Houston, Los Angeles, San Diego; every other metro is mild."),
    ("Compass tier", "Cymbal Compass loyalty tier: none (not enrolled), blue (enrolled), silver (4 bookings or $8,000 lifetime spend), gold (8 bookings or $20,000). `loyalty_tier` on customers, customer_month_status and customer_features."),
    ("retargeting", "Paid-social advertising shown to people who already browsed the site. The always-on Warm Escapes Retargeting program (campaign CMP-002, `target_segment = 'lapsed_compass_cold'`) reaches lapsed Compass members in cold-weather markets who viewed warm destinations. In `ad_performance`, its spend, clicks and attributed conversions appear by day and market."),
    ("propensity score", "`customer_features.propensity_score`: the modeled probability (0–1) that a customer books a warm-escape package in the 60 days after Sep 1, 2026, from the BigQuery ML logistic regression `warm_escape_propensity`. Right-skewed: the median customer scores about 0.08; scores above 0.30 are strong."),
    ("plan", "The `plan` table: planned confirmed bookings and revenue by calendar month, category and home market. Variance = actual / plan − 1; anything within about ±5% is on plan."),
]


def col_table(t: str) -> str:
    out = ["| Column | Type | Description |", "| --- | --- | --- |"]
    for n, typ, mode, d in SCHEMAS[t]["columns"]:
        ty = f"ARRAY<{typ}>" if mode == "REPEATED" else typ
        if mode == "NULLABLE":
            ty += " (nullable)"
        out.append(f"| `{n}` | {ty} | {d} |")
    return "\n".join(out)


def main() -> int:
    P = []
    P.append(f"""# Cymbal Voyages data dictionary

*Dataset `cymbal_voyages` for the mkt016 lab "From Question to Campaign". Generated from `cvgen/` with seed {manifest['seed']}; data window {manifest['window'][0]} to {manifest['window'][1]}; customer snapshot as of {manifest['snapshot_date']}. This file is rendered by `sql/build_dictionary.py`, so the column descriptions here are exactly the ones in `schemas/*.json` that BigQuery and the data agent see.*

## The warehouse at a glance

| Table | Rows | Parquet | Grain | Joins |
| --- | ---: | ---: | --- | --- |""")
    grains = {
        "customers": ("one row per customer account", "→ everything else on `customer_id`"),
        "customer_month_status": ("customer × month (loyalty status at month start)", "`customer_id`, `status_month = DATE_TRUNC(session_date or booking_date, MONTH)`"),
        "customer_features": ("one row per customer as of Sep 1, 2026", "`customer_id`"),
        "destinations": ("one row per destination", "→ packages on `destination_id`; ids appear in `web_sessions.destinations_viewed`"),
        "packages": ("one row per bookable package (5 per destination)", "→ bookings on `package_id`; → destinations on `destination_id`"),
        "catalog_embeddings": ("one row per destination or package", "`item_id` = destination_id or package_id (built by embeddings/build_embeddings.py)"),
        "web_sessions": ("one row per session", "`customer_id` (nullable); `session_id` ← bookings.session_id"),
        "bookings": ("one row per reservation", "`customer_id`, `package_id`, `session_id` (nullable)"),
        "plan": ("month × category × market", "`market` = customers.home_market; `category` = destinations.category"),
        "ad_performance": ("day × campaign × market (paid channels only)", "`campaign_id` → campaign_history; `market` = customers.home_market"),
        "campaign_history": ("one row per campaign", "`campaign_id` ← ad_performance, creative_variants"),
        "creative_variants": ("one row per ad creative variant", "`campaign_id` → campaign_history; `target_segment` shared vocabulary"),
        "propensity_training": ("customer × reference date", "`customer_id`"),
        "decisioning_policy": ("one row per rule", "`feature` names a customer_features column"),
        "activations": ("one row per submitted audience (empty at start)", "—"),
    }
    for t in TABLE_ORDER:
        r = rows.get(t, 360 if t == "catalog_embeddings" else 0)
        size = f"{mb[t]:.1f} MB" if t in mb else "≈ 9 MB"
        g, j = grains[t]
        P.append(f"| `{t}` | {r:,} | {size} | {g} | {j} |")
    P.append(f"""
Total Parquet on disk: {sum(mb.values()):.1f} MB before embeddings. Every table is a folder `out/<table>/part-NNN.parquet` (parts are under 20 MB) so `sql/load.sh` can load each with one wildcard.

**Calendar.** Sessions, bookings and ad spend run from {manifest['window'][0]} through {manifest['window'][1]} (September 2026 is a half month). `plan` covers July 2025 through September 2026 (full month). `customer_features` and every "last 90 days" feature are as of **{manifest['snapshot_date']}** (window Jun 3 – Aug 31, 2026). `customers.loyalty_status` and `last_booking_date` reflect everything through {manifest['window'][1]}. The story is a snapshot: nothing is relative to today's date, so the lab reads the same way for a year.

**What makes the story true.** Customers browse and book from a month-by-month simulation (`cvgen/activity.py`). Each month a customer's loyalty status is read from their booking history; status, climate, tier, season, recent warm-escape views and two latent traits set how much they browse and how often a warm-escape session becomes a booking. Lapsed Compass members in cold-weather markets browsing warm escapes are the target cohort; for sessions on or after **{manifest['anomaly_start']}** their booking odds are multiplied by `ANOMALY_FACTOR = {manifest['anomaly_factor']}`, which takes their tracked conversion from about 6% to about 2.5%. The same random draw is compared against the un-suppressed odds to count "baseline" bookings, and `plan` is that baseline with ±2.5% noise, which is why every other cell reads as on plan. `ad_performance` moves Warm Escapes Retargeting (CMP-002) to a $150/day keep-alive from the same date and gives Fall City Breaks 2026 (CMP-012) exactly the difference, so total paid spend is flat. The cohort's paid-social session share drops from 24% to 3% while its total browsing holds. Two red herrings are planted independently: the Aug 9 incident removes every session between 14:00 and 18:00 UTC (and the bookings those sessions would have produced), and two packages are re-priced +12% on Aug 1 with a 22% demand dip. A two-year burn-in (Jul 2023 – Jun 2025) runs before the window so loyalty status is in steady state when it opens; August 2025 and August 2026 come from the same process.

**Knobs** live at the top of `cvgen/config.py`: `SEED`, row counts (`N_CUSTOMERS`, `N_ANON_SESSIONS`, `KNOWN_SESSION_TARGET`), the calendar, `ANOMALY_FACTOR`, `ANOMALY_START`, `TRACKED_SHARE` (share of bookings completed in a tracked web session, 40%), `PLAN_JITTER`, seasonality tables, and the cohort browsing profile `COHORT_SEASON_LIFT`. `make` regenerates everything in about 30 seconds.

## Tables
""")
    for t in TABLE_ORDER:
        s = SCHEMAS[t]
        part = f"Partitioned by `{s['partition']}`" + (f" ({s.get('partition_type', 'DAY')})" if s.get("partition") else "") if s.get("partition") else "Not partitioned"
        clus = f"; clustered by {', '.join('`' + c + '`' for c in s['cluster'])}" if s.get("cluster") else ""
        P.append(f"### `{t}`\n\n{s['description']}\n\n*{part}{clus}.*\n\n{col_table(t)}\n")

    P.append(f"""## Data agent context (paste into the BigQuery data agent)

### Instructions

{AGENT_INSTRUCTIONS}

### Glossary
""")
    P.append("| Term | Definition |\n| --- | --- |")
    for term, d in GLOSSARY:
        P.append(f"| {term} | {d} |")
    P.append("\n### Verified queries\n")
    for title, sql in VERIFIED:
        P.append(f"**{title}**\n\n```sql\n{sql.strip()}\n```\n")

    P.append(f"""## Propensity model

| | |
| --- | --- |
| Model | `cymbal_voyages.warm_escape_propensity`, BigQuery ML `LOGISTIC_REG` (`sql/train_propensity.sql`) |
| Label | `booked_warm_escape_60d`: confirmed warm-escape booking in the 60 days after the reference date |
| Training table | `propensity_training`: {rows['propensity_training']:,} rows, every customer as of {', '.join(d.isoformat() for d in C.TRAINING_REF_DATES)} (same season, one year before the scoring date) |
| Features | `days_since_last_booking` (NULL → 9999 in `TRANSFORM`), `lifetime_bookings`, `loyalty_tier`, `home_market_climate`, `sessions_last_90d`, `warm_views_last_90d`, `email_optin`, `ltv_band` |
| Positive rate | {100 * m['positive_rate']:.1f}% |
| Reference model (scikit-learn logistic regression on the same table) | holdout AUC **{m['holdout_auc']:.3f}**, log loss {m['holdout_log_loss']:.3f}, {m['holdout']} |
| BigQuery ML result (recorded Sep 17, 2026, fresh project, US multi-region) | `ML.EVALUATE` on the 20% random split: **roc_auc 0.786**, log_loss 0.269, accuracy 0.907, precision 0.657, recall 0.113 at the default 0.5 cutoff (the lab uses probabilities, not the class). **Training time: the `CREATE MODEL` job ran 56 seconds** on the {rows['propensity_training']:,}-row table; 71 seconds wall clock for the whole script including `ML.EVALUATE` and `ML.GLOBAL_EXPLAIN`. Global explain ranks `home_market_climate`, `loyalty_tier` and `ltv_band` (attribution ≈ 0.67 each) above `lifetime_bookings` (0.37), `days_since_last_booking` (0.29), `warm_views_last_90d` (0.19), `sessions_last_90d` (0.12) and `email_optin` (≈ 0). |
| Scoring | `sql/predict_propensity.sql` updates `customer_features.propensity_score` in place. The shipped parquet already carries the reference model's scores so the lab works before BigQuery ML runs. |

Score profile: median customer about 0.08; the target audience (lapsed Compass members in cold markets with a warm view in the last 90 days, 3,838 customers) averages 0.156 with 8.7% at or above 0.30 on the shipped reference scores, and 0.162 with 10.3% at or above 0.30 once `predict_propensity.sql` has written the BigQuery ML scores. See `docs/anomaly-walkthrough.md` for the audience queries.

## Embeddings

`catalog_embeddings` is built by `embeddings/build_embeddings.py` with Vertex AI **`gemini-embedding-001`** at **3,072 dimensions**, task type `RETRIEVAL_DOCUMENT`, one text per request (the same model, dimension and SDK pattern as the mkt013 CymbalGoal lab). The embedded `content` is `"<name>. <region>, <country>. Category: <category>. <description>"` for destinations and `"<package name>. <nights> nights in <destination>. Category: <category>. <description>"` for packages, and is stored alongside the vector so a query can show what matched. Query-side embeddings should use task type `RETRIEVAL_QUERY` with the same model and dimension.

## Decisioning policy defaults

Rules run in ascending `priority`; the first enabled rule whose condition(s) hold decides the action. A rule may carry a second condition (`feature_2`, `operator_2`, `threshold_2`) ANDed with the first. Thresholds are stored as text so one column can hold `60`, `0.30` or `gold`.

| Rule | Priority | Condition | Action | Enabled |
| --- | ---: | --- | --- | --- |""")
    for r in C.POLICY_RULES:
        cond = f"`{r[2]} {r[3]} {r[4]}`" + (f" AND `{r[5]} {r[6]} {r[7]}`" if r[5] else "")
        P.append(f"| {r[0]} | {r[1]} | {cond} | {r[8]} | {'yes' if r[10] else 'no'} |")
    P.append("""
## Brand corpus

Twelve Markdown documents in `brand_corpus/` (source of truth), rendered to `brand_corpus/pdf/` by `build_pdfs.sh` for the Gemini Enterprise Cloud Storage data store: brand voice guide; campaign brief template (nine fixed headings the Brand Studio agent must follow); three past briefs with retrospectives (Winter Sun Early Bird 2025, Spring Flash Sale 2026, Fall City Breaks 2026) whose numbers match `campaign_history`; competitive positioning (three fictional competitors); legal claims list; Cymbal Compass program summary; audience segments glossary (same segment keys as the tables); channel playbook; warm-escapes seasonal calendar; creative production standards.
""")
    text = "\n".join(P)
    (ROOT / "docs" / "data-dictionary.md").write_text(text, encoding="utf-8")
    print(f"wrote docs/data-dictionary.md ({len(text):,} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

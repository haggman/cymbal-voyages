"""
BigQuery schemas with marketer-facing column descriptions.

These descriptions are what the Gemini Enterprise data agent and any NL-to-SQL layer see, so they
are written for a marketer, name the units, and spell out the values a column can hold.
"""
from __future__ import annotations

import json
from pathlib import Path

CHANNEL_VALUES = "one of paid_search, paid_social, organic, email, direct, affiliate"
CATEGORY_VALUES = "one of warm_escape (winter and early-spring sun getaways, our signature category), city_break, ski, adventure, cruise"
CLIMATE_VALUES = "cold (Chicago, Boston, Minneapolis, Detroit, Denver, Toronto, Cleveland, Milwaukee), warm (Miami, Phoenix, Houston, Los Angeles, San Diego) or mild (every other metro)"

# table -> dict(description, columns=[(name, type, mode, description)], partition, partition_type, cluster)
SCHEMAS = {
    "customers": dict(
        description="One row per customer account (50,000). Identity is the customer_id only; there are no names or contact details, just opt-in flags. Loyalty status is as of the end of the data window (Sep 15, 2026).",
        columns=[
            ("customer_id", "STRING", "REQUIRED", "Unique customer identifier, e.g. C000123. Joins to bookings, web_sessions, customer_features and customer_month_status."),
            ("signup_date", "DATE", "REQUIRED", "Date the customer created their account."),
            ("home_market", "STRING", "REQUIRED", "Home metro area, e.g. Chicago, Toronto, Miami. Joins to plan.market and ad_performance.market."),
            ("home_market_climate", "STRING", "REQUIRED", f"Climate group of the home market: {CLIMATE_VALUES}. Warm escapes sell mainly to cold-weather markets."),
            ("loyalty_tier", "STRING", "REQUIRED", "Cymbal Compass tier: none (not enrolled), blue, silver or gold. Anyone with a tier other than none is a Compass member."),
            ("loyalty_status", "STRING", "REQUIRED", "As of Sep 15, 2026: active (booked in the last 12 months), lapsed (booked at least once ever but not in the last 12 months) or never (no confirmed booking on record)."),
            ("last_booking_date", "DATE", "NULLABLE", "Date of the most recent confirmed booking, including bookings before the data window. NULL when the customer has never booked."),
            ("lifetime_bookings", "INT64", "REQUIRED", "Count of confirmed bookings over the customer's lifetime, including bookings before Jul 1, 2025."),
            ("lifetime_value_usd", "FLOAT64", "REQUIRED", "Total confirmed booking revenue over the customer's lifetime, in US dollars."),
            ("email_optin", "BOOL", "REQUIRED", "TRUE when the customer has opted in to marketing email."),
            ("sms_optin", "BOOL", "REQUIRED", "TRUE when the customer has opted in to marketing SMS."),
        ], partition=None, cluster=["home_market_climate", "loyalty_status"]),
    "destinations": dict(
        description="The 60 places and itineraries Cymbal Voyages sells, with the customer-facing description that is embedded for semantic search. About a third are warm escapes.",
        columns=[
            ("destination_id", "STRING", "REQUIRED", "Unique destination identifier, e.g. DST-007. Joins to packages.destination_id and appears in web_sessions.destinations_viewed."),
            ("name", "STRING", "REQUIRED", "Customer-facing destination name, e.g. Aruba, Whistler, Alaska Inside Passage."),
            ("country", "STRING", "REQUIRED", "Country (or countries) of the destination."),
            ("region", "STRING", "REQUIRED", "Marketing region, e.g. Caribbean, Hawaii, Canadian Rockies, Mediterranean."),
            ("category", "STRING", "REQUIRED", f"Product category: {CATEGORY_VALUES}."),
            ("description", "STRING", "REQUIRED", "120–200 word customer-facing description in the brand voice. This text is embedded in catalog_embeddings for semantic search."),
            ("price_band", "STRING", "REQUIRED", "Relative price positioning: budget, mid, premium or luxury."),
            ("best_months", "INT64", "REPEATED", "Calendar months (1–12) when the destination is at its best for travel."),
            ("highlights", "STRING", "REPEATED", "Five short phrases naming the destination's signature experiences."),
            ("good_for", "STRING", "REPEATED", "Traveler types the destination suits, e.g. couples, families, active travelers."),
        ], partition=None, cluster=None),
    "packages": dict(
        description="The 300 bookable trip packages (five per destination): flights, nights and transfers bundled at a per-person price. Two warm-escape packages were re-priced on Aug 1, 2026.",
        columns=[
            ("package_id", "STRING", "REQUIRED", "Unique package identifier, e.g. PKG-0032. Joins to bookings.package_id."),
            ("destination_id", "STRING", "REQUIRED", "The destination this package visits. Joins to destinations.destination_id, which carries the category."),
            ("name", "STRING", "REQUIRED", "Customer-facing package name, e.g. Aruba Classic Week."),
            ("nights", "INT64", "REQUIRED", "Number of nights included."),
            ("description", "STRING", "REQUIRED", "60–120 word customer-facing package description. Embedded in catalog_embeddings for semantic search."),
            ("base_price_usd", "FLOAT64", "REQUIRED", "Current per-person price in US dollars, double occupancy, taxes and fees included."),
            ("previous_base_price_usd", "FLOAT64", "NULLABLE", "The per-person price before the most recent price change. NULL for packages that have not been re-priced during the data window."),
            ("price_effective_date", "DATE", "REQUIRED", "Date the current base_price_usd took effect. Aug 1, 2026 for the two packages re-priced this summer."),
        ], partition=None, cluster=["destination_id"]),
    "web_sessions": dict(
        description="Website and app sessions, one row per session, Jul 1, 2025 – Sep 15, 2026. About half of sessions belong to a signed-in customer; anonymous sessions have no customer_id and cannot convert because booking requires signing in. A 4-hour site incident on Aug 9, 2026 (14:00–18:00 UTC) removed that window's sessions.",
        columns=[
            ("session_id", "STRING", "REQUIRED", "Unique session identifier, e.g. S00012345. bookings.session_id points here when a booking was completed inside a tracked web session."),
            ("session_ts", "TIMESTAMP", "REQUIRED", "Session start time in UTC."),
            ("session_date", "DATE", "REQUIRED", "Calendar date of the session (UTC). Partition column."),
            ("customer_id", "STRING", "NULLABLE", "The signed-in customer, or NULL for an anonymous visitor. Joins to customers.customer_id."),
            ("channel", "STRING", "REQUIRED", f"Marketing channel that brought the session: {CHANNEL_VALUES}. paid_social includes the always-on retargeting program."),
            ("device", "STRING", "REQUIRED", "Device category: mobile, desktop or tablet."),
            ("landing_category", "STRING", "REQUIRED", "Product category of the landing page (warm_escape, city_break, ski, adventure, cruise) or home for the homepage."),
            ("destinations_viewed", "STRING", "REPEATED", "Destination ids viewed during the session, in order, e.g. [DST-007, DST-012]. Joins to destinations.destination_id."),
            ("primary_category_viewed", "STRING", "REQUIRED", f"The product category the session mostly browsed: {CATEGORY_VALUES}."),
            ("viewed_warm_escape", "BOOL", "REQUIRED", "TRUE when at least one warm-escape destination was viewed in the session. Use this to find customers who browsed warm escapes."),
            ("pages_viewed", "INT64", "REQUIRED", "Number of pages viewed in the session."),
            ("searched_travel_month", "DATE", "NULLABLE", "First day of the travel month the visitor searched for (e.g. 2027-02-01 for February 2027), or NULL if no dates were entered."),
            ("added_to_cart", "BOOL", "REQUIRED", "TRUE when the visitor added a package to the cart."),
            ("converted", "BOOL", "REQUIRED", "TRUE when a booking was completed inside this session. Conversion rate = COUNTIF(converted) / COUNT(*). Anonymous sessions are always FALSE."),
        ], partition="session_date", cluster=["customer_id", "channel"]),
    "bookings": dict(
        description="Reservations, one row per booking, Jul 1, 2025 – Sep 15, 2026. A booking in reporting means a row with status = confirmed; cancelled rows are excluded from bookings and revenue. About 40% of bookings complete inside a tracked web session (session_id set); the rest complete in the app or by phone within two days of a browse session.",
        columns=[
            ("booking_id", "STRING", "REQUIRED", "Unique booking identifier, e.g. B0001234."),
            ("customer_id", "STRING", "REQUIRED", "The customer who booked. Joins to customers.customer_id. Every booking belongs to a signed-in customer."),
            ("package_id", "STRING", "REQUIRED", "The package booked. Joins to packages.package_id, and through it to destinations for the category."),
            ("booking_date", "DATE", "REQUIRED", "Date the booking was made. Partition column. Compare to plan by the calendar month of this date."),
            ("travel_start_date", "DATE", "REQUIRED", "First day of travel. Warm escapes booked in late summer typically travel Dec–Apr."),
            ("channel", "STRING", "REQUIRED", f"Last-touch marketing channel credited with the booking: {CHANNEL_VALUES}."),
            ("travelers", "INT64", "REQUIRED", "Number of travelers on the booking."),
            ("revenue_usd", "FLOAT64", "REQUIRED", "Gross booking value in US dollars (per-person price × travelers, less any promotional discount)."),
            ("status", "STRING", "REQUIRED", "confirmed or cancelled. Only confirmed rows count as bookings."),
            ("session_id", "STRING", "NULLABLE", "The web session in which the booking was completed, or NULL when it completed in the app or by phone. Joins to web_sessions.session_id."),
        ], partition="booking_date", cluster=["customer_id", "package_id"]),
    "ad_performance": dict(
        description="Daily paid-media results by campaign and market, Jul 1, 2025 – Sep 15, 2026. Only paid channels (paid_search, paid_social, affiliate) appear here; email and organic have no media spend. Total paid spend is steady across the summer of 2026, but its allocation between campaigns changed on Jul 24, 2026.",
        columns=[
            ("spend_date", "DATE", "REQUIRED", "Calendar date of the spend. Partition column."),
            ("channel", "STRING", "REQUIRED", "Paid channel: paid_search, paid_social or affiliate."),
            ("campaign_id", "STRING", "REQUIRED", "Campaign identifier, e.g. CMP-002. Joins to campaign_history.campaign_id."),
            ("campaign_name", "STRING", "REQUIRED", "Campaign name, e.g. Warm Escapes Retargeting, Fall City Breaks 2026."),
            ("target_segment", "STRING", "REQUIRED", "Audience the campaign targets, e.g. lapsed_compass_cold (lapsed Compass members in cold-weather markets), all_customers, urban_explorers."),
            ("market", "STRING", "REQUIRED", "Metro the spend was targeted to. Joins to customers.home_market and plan.market."),
            ("impressions", "INT64", "REQUIRED", "Ad impressions served."),
            ("clicks", "INT64", "REQUIRED", "Ad clicks."),
            ("spend_usd", "FLOAT64", "REQUIRED", "Media spend in US dollars."),
            ("attributed_conversions", "INT64", "REQUIRED", "Bookings the ad platform attributed to this campaign, market and day (platform attribution, not the bookings table)."),
        ], partition="spend_date", cluster=["campaign_id", "market"]),
    "plan": dict(
        description="The booking and revenue plan by calendar month, product category and market, Jul 2025 – Sep 2026. Fiscal months equal calendar months. Compare confirmed bookings by booking_date month against planned_bookings; variance = actual / plan − 1.",
        columns=[
            ("plan_month", "DATE", "REQUIRED", "First day of the plan month, e.g. 2026-08-01 for August 2026."),
            ("category", "STRING", "REQUIRED", f"Product category: {CATEGORY_VALUES}."),
            ("market", "STRING", "REQUIRED", "Customer home market (metro). Joins to customers.home_market."),
            ("planned_bookings", "INT64", "REQUIRED", "Planned count of confirmed bookings for the month, category and market."),
            ("planned_revenue_usd", "FLOAT64", "REQUIRED", "Planned gross booking revenue in US dollars."),
        ], partition=None, cluster=["category", "market"]),
    "campaign_history": dict(
        description="The 12 marketing campaigns run since Jul 2025, with objective, audience, flight dates, budget, attributed results and a short retrospective. Always-on programs have end_date 2026-12-31 and results to date.",
        columns=[
            ("campaign_id", "STRING", "REQUIRED", "Campaign identifier, e.g. CMP-003. Joins to ad_performance and creative_variants."),
            ("name", "STRING", "REQUIRED", "Campaign name, e.g. Winter Sun Early Bird 2025."),
            ("objective", "STRING", "REQUIRED", "The business outcome the campaign was meant to produce."),
            ("target_segment", "STRING", "REQUIRED", "Audience key, e.g. lapsed_compass (lapsed Compass members), lapsed_compass_cold, all_customers, active_compass, urban_explorers."),
            ("start_date", "DATE", "REQUIRED", "First flight date."),
            ("end_date", "DATE", "REQUIRED", "Last flight date. 2026-12-31 for always-on programs."),
            ("channels", "STRING", "REPEATED", f"Channels used: {CHANNEL_VALUES}."),
            ("budget_usd", "FLOAT64", "REQUIRED", "Approved budget in US dollars for the flight (annual budget for always-on programs)."),
            ("spend_to_date_usd", "FLOAT64", "REQUIRED", "Paid media actually spent through Sep 15, 2026, from ad_performance."),
            ("bookings_attributed", "INT64", "REQUIRED", "Confirmed bookings attributed to the campaign (to date for campaigns still running)."),
            ("roi", "FLOAT64", "NULLABLE", "Contribution ROI as reported in the retrospective: (attributed revenue × 22% contribution margin − campaign cost) ÷ campaign cost. Negative means the campaign lost money."),
            ("retrospective", "STRING", "REQUIRED", "Two to three sentences on what happened and what was learned."),
        ], partition=None, cluster=None),
    "creative_variants": dict(
        description="Performance of 200 ad creative variants across the campaigns, tagged by imagery style, offer framing and call-to-action wording. Use it to learn which creative choices convert for a given target segment.",
        columns=[
            ("variant_id", "STRING", "REQUIRED", "Unique creative variant identifier, e.g. CRV-0042."),
            ("campaign_id", "STRING", "REQUIRED", "Campaign the variant ran in. Joins to campaign_history.campaign_id."),
            ("target_segment", "STRING", "REQUIRED", "Audience the variant was shown to, e.g. lapsed_compass_cold, all_customers, urban_explorers. Can be narrower than the campaign's segment."),
            ("hero_imagery_style", "STRING", "REQUIRED", "Hero image style: beach_couple, family_pool, resort_aerial, city_skyline or adventure."),
            ("offer_framing", "STRING", "REQUIRED", "How the offer was framed: percent_off, bonus_points (Compass points), free_night, urgency (countdown / limited time) or no_offer."),
            ("cta_construction", "STRING", "REQUIRED", "Call-to-action wording: book_now, see_deals, plan_your_escape or claim_offer."),
            ("impressions", "INT64", "REQUIRED", "Impressions served for the variant."),
            ("clicks", "INT64", "REQUIRED", "Clicks on the variant."),
            ("conversions", "INT64", "REQUIRED", "Bookings attributed to the variant."),
            ("conversion_rate", "FLOAT64", "REQUIRED", "conversions ÷ clicks, as a fraction (0.031 = 3.1%). Weight by clicks when averaging across variants."),
        ], partition=None, cluster=["target_segment"]),
    "customer_month_status": dict(
        description="Loyalty status of every customer at the start of each month, Jul 2025 – Sep 2026 (50,000 customers × 15 months). Use it to define a cohort as it stood at the time, e.g. who was lapsed on Aug 1, 2025 versus Aug 1, 2026.",
        columns=[
            ("status_month", "DATE", "REQUIRED", "First day of the month the status applies to. Status is evaluated at 00:00 on this date."),
            ("customer_id", "STRING", "REQUIRED", "Joins to customers.customer_id."),
            ("loyalty_tier", "STRING", "REQUIRED", "Cymbal Compass tier: none, blue, silver or gold."),
            ("loyalty_status", "STRING", "REQUIRED", "active (confirmed booking in the 12 months before status_month), lapsed (booked before that but not in the last 12 months) or never."),
            ("days_since_last_booking", "INT64", "NULLABLE", "Days from the most recent confirmed booking to status_month. NULL when the customer had never booked."),
            ("lifetime_bookings_to_date", "INT64", "REQUIRED", "Confirmed bookings on record before status_month."),
        ], partition="status_month", partition_type="MONTH", cluster=["customer_id"]),
    "customer_features": dict(
        description="One row per customer as of Sep 1, 2026: the audience-building table. Combines loyalty status, recency, contactability, 90-day browsing and the model's warm-escape propensity score. Everything here is computed as of as_of_date; do not join to later sessions.",
        columns=[
            ("customer_id", "STRING", "REQUIRED", "Joins to customers.customer_id."),
            ("as_of_date", "DATE", "REQUIRED", "The snapshot date all features are computed at: 2026-09-01."),
            ("propensity_score", "FLOAT64", "REQUIRED", "Modeled probability (0–1) that the customer books a warm-escape package in the 60 days after as_of_date, from the BigQuery ML logistic regression. Higher is more likely."),
            ("days_since_last_booking", "INT64", "NULLABLE", "Days from the most recent confirmed booking to as_of_date. NULL when the customer has never booked. Lapsed = 365 or more."),
            ("last_booking_date", "DATE", "NULLABLE", "Date of the most recent confirmed booking before as_of_date, or NULL."),
            ("loyalty_tier", "STRING", "REQUIRED", "Cymbal Compass tier: none, blue, silver or gold."),
            ("loyalty_status", "STRING", "REQUIRED", "As of as_of_date: active, lapsed or never."),
            ("home_market_climate", "STRING", "REQUIRED", f"Climate group of the home market: {CLIMATE_VALUES}."),
            ("lifetime_bookings", "INT64", "REQUIRED", "Confirmed bookings on record before as_of_date."),
            ("lifetime_value_usd", "FLOAT64", "REQUIRED", "Confirmed booking revenue before as_of_date, in US dollars."),
            ("ltv_band", "STRING", "REQUIRED", "Lifetime value band: none ($0), low (under $1,500), mid ($1,500–4,999), high ($5,000–11,999) or vip ($12,000 and up)."),
            ("booked_last_60d", "BOOL", "REQUIRED", "TRUE when the customer made a confirmed booking in the 60 days before as_of_date (a common suppression rule)."),
            ("has_active_reservation", "BOOL", "REQUIRED", "TRUE when the customer has a confirmed booking with travel on or after as_of_date."),
            ("email_contactable", "BOOL", "REQUIRED", "TRUE when the customer can be emailed (opted in)."),
            ("sms_contactable", "BOOL", "REQUIRED", "TRUE when the customer can be texted (opted in)."),
            ("sessions_last_90d", "INT64", "REQUIRED", "Signed-in web sessions in the 90 days before as_of_date (Jun 3 – Aug 31, 2026)."),
            ("warm_views_last_90d", "INT64", "REQUIRED", "Sessions in the same 90 days in which a warm-escape destination was viewed."),
            ("recent_engagement_score", "FLOAT64", "REQUIRED", "0–1 score combining 90-day session count and days since the last session; 0 means no recent activity."),
        ], partition=None, cluster=["home_market_climate", "loyalty_status"]),
    "propensity_training": dict(
        description="Training set for the warm-escape propensity model: one snapshot of every customer (50,000 rows) as of the reference date Sep 1, 2025, the same point in the booking season one year before the Sep 1, 2026 scoring snapshot, with features as they stood on that date and whether the customer booked a warm escape in the following 60 days.",
        columns=[
            ("reference_date", "DATE", "REQUIRED", "The as-of date for the features; the label window is the 60 days after it."),
            ("customer_id", "STRING", "REQUIRED", "Joins to customers.customer_id."),
            ("days_since_last_booking", "INT64", "NULLABLE", "Days from the most recent confirmed booking to reference_date; NULL if never booked."),
            ("lifetime_bookings", "INT64", "REQUIRED", "Confirmed bookings before reference_date."),
            ("loyalty_tier", "STRING", "REQUIRED", "none, blue, silver or gold."),
            ("home_market_climate", "STRING", "REQUIRED", "cold, mild or warm."),
            ("sessions_last_90d", "INT64", "REQUIRED", "Signed-in sessions in the 90 days before reference_date."),
            ("warm_views_last_90d", "INT64", "REQUIRED", "Sessions with a warm-escape view in the 90 days before reference_date."),
            ("email_optin", "BOOL", "REQUIRED", "Email opt-in flag."),
            ("ltv_band", "STRING", "REQUIRED", "none, low, mid, high or vip, computed on lifetime value before reference_date."),
            ("booked_warm_escape_60d", "INT64", "REQUIRED", "Label: 1 if the customer made a confirmed warm-escape booking in the 60 days after reference_date, else 0."),
        ], partition=None, cluster=["reference_date"]),
    "decisioning_policy": dict(
        description="Next-best-action rules evaluated per customer against customer_features. Rules run in ascending priority; the first enabled rule whose condition(s) hold decides the action. Marketers edit this table.",
        columns=[
            ("rule_id", "STRING", "REQUIRED", "Rule identifier, e.g. R01."),
            ("priority", "INT64", "REQUIRED", "Evaluation order; lower runs first and the first match wins."),
            ("feature", "STRING", "REQUIRED", "customer_features column the condition tests, e.g. propensity_score, days_since_last_booking, loyalty_tier."),
            ("operator", "STRING", "REQUIRED", "Comparison: one of ==, !=, >=, >, <=, <."),
            ("threshold", "STRING", "REQUIRED", "Value to compare against, stored as text (60, 0.30, gold, true). Cast to the feature's type."),
            ("feature_2", "STRING", "NULLABLE", "Optional second feature; when set, both conditions must hold (AND)."),
            ("operator_2", "STRING", "NULLABLE", "Comparison for the second condition."),
            ("threshold_2", "STRING", "NULLABLE", "Value for the second condition, as text."),
            ("action", "STRING", "REQUIRED", "What to do when the rule matches: send_offer, hold_for_retargeting, route_to_loyalty_team or suppress."),
            ("reason_template", "STRING", "REQUIRED", "Human-readable explanation with {feature} placeholders filled from customer_features."),
            ("enabled", "BOOL", "REQUIRED", "FALSE rules are skipped."),
        ], partition=None, cluster=None),
    "activations": dict(
        description="Receipts written by the activation endpoint when an audience is submitted to a channel. Empty until the lab submits an audience.",
        columns=[
            ("receipt_id", "STRING", "REQUIRED", "Unique receipt identifier returned by the activation endpoint."),
            ("segment_description", "STRING", "REQUIRED", "The natural-language segment definition that was activated."),
            ("audience_size", "INT64", "REQUIRED", "Number of customers in the submitted audience."),
            ("channel", "STRING", "REQUIRED", f"Channel the audience was sent to: {CHANNEL_VALUES}."),
            ("submitted_at", "TIMESTAMP", "REQUIRED", "When the audience was submitted (UTC)."),
            ("status", "STRING", "REQUIRED", "accepted, rejected or pending."),
        ], partition=None, cluster=None),
    "catalog_embeddings": dict(
        description="Vector embeddings of every destination and package description (360 rows) from Vertex AI gemini-embedding-001 at 3,072 dimensions, for semantic search with VECTOR_SEARCH or ML.DISTANCE.",
        columns=[
            ("item_type", "STRING", "REQUIRED", "destination or package."),
            ("item_id", "STRING", "REQUIRED", "destination_id or package_id."),
            ("name", "STRING", "REQUIRED", "Destination or package name."),
            ("category", "STRING", "REQUIRED", f"Product category: {CATEGORY_VALUES}."),
            ("content", "STRING", "REQUIRED", "The exact text that was embedded (name, category and description)."),
            ("embedding", "FLOAT64", "REPEATED", "3,072-dimension embedding vector from gemini-embedding-001 (task type RETRIEVAL_DOCUMENT)."),
            ("model", "STRING", "REQUIRED", "Embedding model name: gemini-embedding-001."),
            ("dimensions", "INT64", "REQUIRED", "Vector length: 3072."),
        ], partition=None, cluster=["item_type"]),
}


def bq_schema(table: str) -> list[dict]:
    return [{"name": n, "type": t, "mode": m, "description": d} for n, t, m, d in SCHEMAS[table]["columns"]]


def write_schemas(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for t in SCHEMAS:
        (out_dir / f"{t}.json").write_text(json.dumps(bq_schema(t), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tables = {t: {"description": s["description"], "partition": s.get("partition"),
                  "partition_type": s.get("partition_type", "DAY"), "cluster": s.get("cluster")} for t, s in SCHEMAS.items()}
    (out_dir / "_tables.json").write_text(json.dumps(tables, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# Cymbal Voyages data dictionary

*Dataset `cymbal_voyages` for the mkt016 lab "From Question to Campaign". Generated from `cvgen/` with seed 20260916; data window 2025-07-01 to 2026-09-15; customer snapshot as of 2026-09-01. This file is rendered by `sql/build_dictionary.py`, so the column descriptions here are exactly the ones in `schemas/*.json` that BigQuery and the data agent see.*

## The warehouse at a glance

| Table | Rows | Parquet | Grain | Joins |
| --- | ---: | ---: | --- | --- |
| `customers` | 50,000 | 0.9 MB | one row per customer account | → everything else on `customer_id` |
| `customer_month_status` | 750,000 | 4.7 MB | customer × month (loyalty status at month start) | `customer_id`, `status_month = DATE_TRUNC(session_date or booking_date, MONTH)` |
| `customer_features` | 50,000 | 1.1 MB | one row per customer as of Sep 1, 2026 | `customer_id` |
| `destinations` | 60 | 0.1 MB | one row per destination | → packages on `destination_id`; ids appear in `web_sessions.destinations_viewed` |
| `packages` | 300 | 0.0 MB | one row per bookable package (5 per destination) | → bookings on `package_id`; → destinations on `destination_id` |
| `catalog_embeddings` | 360 | ≈ 9 MB | one row per destination or package | `item_id` = destination_id or package_id (built by embeddings/build_embeddings.py) |
| `web_sessions` | 569,723 | 11.9 MB | one row per session | `customer_id` (nullable); `session_id` ← bookings.session_id |
| `bookings` | 49,450 | 1.2 MB | one row per reservation | `customer_id`, `package_id`, `session_id` (nullable) |
| `plan` | 1,875 | 0.0 MB | month × category × market | `market` = customers.home_market; `category` = destinations.category |
| `ad_performance` | 34,481 | 0.3 MB | day × campaign × market (paid channels only) | `campaign_id` → campaign_history; `market` = customers.home_market |
| `campaign_history` | 12 | 0.0 MB | one row per campaign | `campaign_id` ← ad_performance, creative_variants |
| `creative_variants` | 200 | 0.0 MB | one row per ad creative variant | `campaign_id` → campaign_history; `target_segment` shared vocabulary |
| `propensity_training` | 50,000 | 0.6 MB | customer × reference date | `customer_id` |
| `decisioning_policy` | 8 | 0.0 MB | one row per rule | `feature` names a customer_features column |
| `activations` | 0 | 0.0 MB | one row per submitted audience (empty at start) | — |

Total Parquet on disk: 20.9 MB before embeddings. Every table is a folder `out/<table>/part-NNN.parquet` (parts are under 20 MB) so `sql/load.sh` can load each with one wildcard.

**Calendar.** Sessions, bookings and ad spend run from 2025-07-01 through 2026-09-15 (September 2026 is a half month). `plan` covers July 2025 through September 2026 (full month). `customer_features` and every "last 90 days" feature are as of **2026-09-01** (window Jun 3 – Aug 31, 2026). `customers.loyalty_status` and `last_booking_date` reflect everything through 2026-09-15. The story is a snapshot: nothing is relative to today's date, so the lab reads the same way for a year.

**What makes the story true.** Customers browse and book from a month-by-month simulation (`cvgen/activity.py`). Each month a customer's loyalty status is read from their booking history; status, climate, tier, season, recent warm-escape views and two latent traits set how much they browse and how often a warm-escape session becomes a booking. Lapsed Compass members in cold-weather markets browsing warm escapes are the target cohort; for sessions on or after **2026-07-24** their booking odds are multiplied by `ANOMALY_FACTOR = 0.36`, which takes their tracked conversion from about 6% to about 2.5%. The same random draw is compared against the un-suppressed odds to count "baseline" bookings, and `plan` is that baseline with ±2.5% noise, which is why every other cell reads as on plan. `ad_performance` moves Warm Escapes Retargeting (CMP-002) to a $150/day keep-alive from the same date and gives Fall City Breaks 2026 (CMP-012) exactly the difference, so total paid spend is flat. The cohort's paid-social session share drops from 24% to 3% while its total browsing holds. Two red herrings are planted independently: the Aug 9 incident removes every session between 14:00 and 18:00 UTC (and the bookings those sessions would have produced), and two packages are re-priced +12% on Aug 1 with a 22% demand dip. A two-year burn-in (Jul 2023 – Jun 2025) runs before the window so loyalty status is in steady state when it opens; August 2025 and August 2026 come from the same process.

**Knobs** live at the top of `cvgen/config.py`: `SEED`, row counts (`N_CUSTOMERS`, `N_ANON_SESSIONS`, `KNOWN_SESSION_TARGET`), the calendar, `ANOMALY_FACTOR`, `ANOMALY_START`, `TRACKED_SHARE` (share of bookings completed in a tracked web session, 40%), `PLAN_JITTER`, seasonality tables, and the cohort browsing profile `COHORT_SEASON_LIFT`. `make` regenerates everything in about 30 seconds.

## Tables

### `customers`

One row per customer account (50,000). Identity is the customer_id only; there are no names or contact details, just opt-in flags. Loyalty status is as of the end of the data window (Sep 15, 2026).

*Not partitioned; clustered by `home_market_climate`, `loyalty_status`.*

| Column | Type | Description |
| --- | --- | --- |
| `customer_id` | STRING | Unique customer identifier, e.g. C000123. Joins to bookings, web_sessions, customer_features and customer_month_status. |
| `signup_date` | DATE | Date the customer created their account. |
| `home_market` | STRING | Home metro area, e.g. Chicago, Toronto, Miami. Joins to plan.market and ad_performance.market. |
| `home_market_climate` | STRING | Climate group of the home market: cold (Chicago, Boston, Minneapolis, Detroit, Denver, Toronto, Cleveland, Milwaukee), warm (Miami, Phoenix, Houston, Los Angeles, San Diego) or mild (every other metro). Warm escapes sell mainly to cold-weather markets. |
| `loyalty_tier` | STRING | Cymbal Compass tier: none (not enrolled), blue, silver or gold. Anyone with a tier other than none is a Compass member. |
| `loyalty_status` | STRING | As of Sep 15, 2026: active (booked in the last 12 months), lapsed (booked at least once ever but not in the last 12 months) or never (no confirmed booking on record). |
| `last_booking_date` | DATE (nullable) | Date of the most recent confirmed booking, including bookings before the data window. NULL when the customer has never booked. |
| `lifetime_bookings` | INT64 | Count of confirmed bookings over the customer's lifetime, including bookings before Jul 1, 2025. |
| `lifetime_value_usd` | FLOAT64 | Total confirmed booking revenue over the customer's lifetime, in US dollars. |
| `email_optin` | BOOL | TRUE when the customer has opted in to marketing email. |
| `sms_optin` | BOOL | TRUE when the customer has opted in to marketing SMS. |

### `customer_month_status`

Loyalty status of every customer at the start of each month, Jul 2025 – Sep 2026 (50,000 customers × 15 months). Use it to define a cohort as it stood at the time, e.g. who was lapsed on Aug 1, 2025 versus Aug 1, 2026.

*Partitioned by `status_month` (MONTH); clustered by `customer_id`.*

| Column | Type | Description |
| --- | --- | --- |
| `status_month` | DATE | First day of the month the status applies to. Status is evaluated at 00:00 on this date. |
| `customer_id` | STRING | Joins to customers.customer_id. |
| `loyalty_tier` | STRING | Cymbal Compass tier: none, blue, silver or gold. |
| `loyalty_status` | STRING | active (confirmed booking in the 12 months before status_month), lapsed (booked before that but not in the last 12 months) or never. |
| `days_since_last_booking` | INT64 (nullable) | Days from the most recent confirmed booking to status_month. NULL when the customer had never booked. |
| `lifetime_bookings_to_date` | INT64 | Confirmed bookings on record before status_month. |

### `customer_features`

One row per customer as of Sep 1, 2026: the audience-building table. Combines loyalty status, recency, contactability, 90-day browsing and the model's warm-escape propensity score. Everything here is computed as of as_of_date; do not join to later sessions.

*Not partitioned; clustered by `home_market_climate`, `loyalty_status`.*

| Column | Type | Description |
| --- | --- | --- |
| `customer_id` | STRING | Joins to customers.customer_id. |
| `as_of_date` | DATE | The snapshot date all features are computed at: 2026-09-01. |
| `propensity_score` | FLOAT64 | Modeled probability (0–1) that the customer books a warm-escape package in the 60 days after as_of_date, from the BigQuery ML logistic regression. Higher is more likely. |
| `days_since_last_booking` | INT64 (nullable) | Days from the most recent confirmed booking to as_of_date. NULL when the customer has never booked. Lapsed = 365 or more. |
| `last_booking_date` | DATE (nullable) | Date of the most recent confirmed booking before as_of_date, or NULL. |
| `loyalty_tier` | STRING | Cymbal Compass tier: none, blue, silver or gold. |
| `loyalty_status` | STRING | As of as_of_date: active, lapsed or never. |
| `home_market_climate` | STRING | Climate group of the home market: cold (Chicago, Boston, Minneapolis, Detroit, Denver, Toronto, Cleveland, Milwaukee), warm (Miami, Phoenix, Houston, Los Angeles, San Diego) or mild (every other metro). |
| `lifetime_bookings` | INT64 | Confirmed bookings on record before as_of_date. |
| `lifetime_value_usd` | FLOAT64 | Confirmed booking revenue before as_of_date, in US dollars. |
| `ltv_band` | STRING | Lifetime value band: none ($0), low (under $1,500), mid ($1,500–4,999), high ($5,000–11,999) or vip ($12,000 and up). |
| `booked_last_60d` | BOOL | TRUE when the customer made a confirmed booking in the 60 days before as_of_date (a common suppression rule). |
| `has_active_reservation` | BOOL | TRUE when the customer has a confirmed booking with travel on or after as_of_date. |
| `email_contactable` | BOOL | TRUE when the customer can be emailed (opted in). |
| `sms_contactable` | BOOL | TRUE when the customer can be texted (opted in). |
| `sessions_last_90d` | INT64 | Signed-in web sessions in the 90 days before as_of_date (Jun 3 – Aug 31, 2026). |
| `warm_views_last_90d` | INT64 | Sessions in the same 90 days in which a warm-escape destination was viewed. |
| `recent_engagement_score` | FLOAT64 | 0–1 score combining 90-day session count and days since the last session; 0 means no recent activity. |

### `destinations`

The 60 places and itineraries Cymbal Voyages sells, with the customer-facing description that is embedded for semantic search. About a third are warm escapes.

*Not partitioned.*

| Column | Type | Description |
| --- | --- | --- |
| `destination_id` | STRING | Unique destination identifier, e.g. DST-007. Joins to packages.destination_id and appears in web_sessions.destinations_viewed. |
| `name` | STRING | Customer-facing destination name, e.g. Aruba, Whistler, Alaska Inside Passage. |
| `country` | STRING | Country (or countries) of the destination. |
| `region` | STRING | Marketing region, e.g. Caribbean, Hawaii, Canadian Rockies, Mediterranean. |
| `category` | STRING | Product category: one of warm_escape (winter and early-spring sun getaways, our signature category), city_break, ski, adventure, cruise. |
| `description` | STRING | 120–200 word customer-facing description in the brand voice. This text is embedded in catalog_embeddings for semantic search. |
| `price_band` | STRING | Relative price positioning: budget, mid, premium or luxury. |
| `best_months` | ARRAY<INT64> | Calendar months (1–12) when the destination is at its best for travel. |
| `highlights` | ARRAY<STRING> | Five short phrases naming the destination's signature experiences. |
| `good_for` | ARRAY<STRING> | Traveler types the destination suits, e.g. couples, families, active travelers. |

### `packages`

The 300 bookable trip packages (five per destination): flights, nights and transfers bundled at a per-person price. Two warm-escape packages were re-priced on Aug 1, 2026.

*Not partitioned; clustered by `destination_id`.*

| Column | Type | Description |
| --- | --- | --- |
| `package_id` | STRING | Unique package identifier, e.g. PKG-0032. Joins to bookings.package_id. |
| `destination_id` | STRING | The destination this package visits. Joins to destinations.destination_id, which carries the category. |
| `name` | STRING | Customer-facing package name, e.g. Aruba Classic Week. |
| `nights` | INT64 | Number of nights included. |
| `description` | STRING | 60–120 word customer-facing package description. Embedded in catalog_embeddings for semantic search. |
| `base_price_usd` | FLOAT64 | Current per-person price in US dollars, double occupancy, taxes and fees included. |
| `previous_base_price_usd` | FLOAT64 (nullable) | The per-person price before the most recent price change. NULL for packages that have not been re-priced during the data window. |
| `price_effective_date` | DATE | Date the current base_price_usd took effect. Aug 1, 2026 for the two packages re-priced this summer. |

### `catalog_embeddings`

Vector embeddings of every destination and package description (360 rows) from Vertex AI gemini-embedding-001 at 3,072 dimensions, for semantic search with VECTOR_SEARCH or ML.DISTANCE.

*Not partitioned; clustered by `item_type`.*

| Column | Type | Description |
| --- | --- | --- |
| `item_type` | STRING | destination or package. |
| `item_id` | STRING | destination_id or package_id. |
| `name` | STRING | Destination or package name. |
| `category` | STRING | Product category: one of warm_escape (winter and early-spring sun getaways, our signature category), city_break, ski, adventure, cruise. |
| `content` | STRING | The exact text that was embedded (name, category and description). |
| `embedding` | ARRAY<FLOAT64> | 3,072-dimension embedding vector from gemini-embedding-001 (task type RETRIEVAL_DOCUMENT). |
| `model` | STRING | Embedding model name: gemini-embedding-001. |
| `dimensions` | INT64 | Vector length: 3072. |

### `web_sessions`

Website and app sessions, one row per session, Jul 1, 2025 – Sep 15, 2026. About half of sessions belong to a signed-in customer; anonymous sessions have no customer_id and cannot convert because booking requires signing in. A 4-hour site incident on Aug 9, 2026 (14:00–18:00 UTC) removed that window's sessions.

*Partitioned by `session_date` (DAY); clustered by `customer_id`, `channel`.*

| Column | Type | Description |
| --- | --- | --- |
| `session_id` | STRING | Unique session identifier, e.g. S00012345. bookings.session_id points here when a booking was completed inside a tracked web session. |
| `session_ts` | TIMESTAMP | Session start time in UTC. |
| `session_date` | DATE | Calendar date of the session (UTC). Partition column. |
| `customer_id` | STRING (nullable) | The signed-in customer, or NULL for an anonymous visitor. Joins to customers.customer_id. |
| `channel` | STRING | Marketing channel that brought the session: one of paid_search, paid_social, organic, email, direct, affiliate. paid_social includes the always-on retargeting program. |
| `device` | STRING | Device category: mobile, desktop or tablet. |
| `landing_category` | STRING | Product category of the landing page (warm_escape, city_break, ski, adventure, cruise) or home for the homepage. |
| `destinations_viewed` | ARRAY<STRING> | Destination ids viewed during the session, in order, e.g. [DST-007, DST-012]. Joins to destinations.destination_id. |
| `primary_category_viewed` | STRING | The product category the session mostly browsed: one of warm_escape (winter and early-spring sun getaways, our signature category), city_break, ski, adventure, cruise. |
| `viewed_warm_escape` | BOOL | TRUE when at least one warm-escape destination was viewed in the session. Use this to find customers who browsed warm escapes. |
| `pages_viewed` | INT64 | Number of pages viewed in the session. |
| `searched_travel_month` | DATE (nullable) | First day of the travel month the visitor searched for (e.g. 2027-02-01 for February 2027), or NULL if no dates were entered. |
| `added_to_cart` | BOOL | TRUE when the visitor added a package to the cart. |
| `converted` | BOOL | TRUE when a booking was completed inside this session. Conversion rate = COUNTIF(converted) / COUNT(*). Anonymous sessions are always FALSE. |

### `bookings`

Reservations, one row per booking, Jul 1, 2025 – Sep 15, 2026. A booking in reporting means a row with status = confirmed; cancelled rows are excluded from bookings and revenue. About 40% of bookings complete inside a tracked web session (session_id set); the rest complete in the app or by phone within two days of a browse session.

*Partitioned by `booking_date` (DAY); clustered by `customer_id`, `package_id`.*

| Column | Type | Description |
| --- | --- | --- |
| `booking_id` | STRING | Unique booking identifier, e.g. B0001234. |
| `customer_id` | STRING | The customer who booked. Joins to customers.customer_id. Every booking belongs to a signed-in customer. |
| `package_id` | STRING | The package booked. Joins to packages.package_id, and through it to destinations for the category. |
| `booking_date` | DATE | Date the booking was made. Partition column. Compare to plan by the calendar month of this date. |
| `travel_start_date` | DATE | First day of travel. Warm escapes booked in late summer typically travel Dec–Apr. |
| `channel` | STRING | Last-touch marketing channel credited with the booking: one of paid_search, paid_social, organic, email, direct, affiliate. |
| `travelers` | INT64 | Number of travelers on the booking. |
| `revenue_usd` | FLOAT64 | Gross booking value in US dollars (per-person price × travelers, less any promotional discount). |
| `status` | STRING | confirmed or cancelled. Only confirmed rows count as bookings. |
| `session_id` | STRING (nullable) | The web session in which the booking was completed, or NULL when it completed in the app or by phone. Joins to web_sessions.session_id. |

### `plan`

The booking and revenue plan by calendar month, product category and market, Jul 2025 – Sep 2026. Fiscal months equal calendar months. Compare confirmed bookings by booking_date month against planned_bookings; variance = actual / plan − 1.

*Not partitioned; clustered by `category`, `market`.*

| Column | Type | Description |
| --- | --- | --- |
| `plan_month` | DATE | First day of the plan month, e.g. 2026-08-01 for August 2026. |
| `category` | STRING | Product category: one of warm_escape (winter and early-spring sun getaways, our signature category), city_break, ski, adventure, cruise. |
| `market` | STRING | Customer home market (metro). Joins to customers.home_market. |
| `planned_bookings` | INT64 | Planned count of confirmed bookings for the month, category and market. |
| `planned_revenue_usd` | FLOAT64 | Planned gross booking revenue in US dollars. |

### `ad_performance`

Daily paid-media results by campaign and market, Jul 1, 2025 – Sep 15, 2026. Only paid channels (paid_search, paid_social, affiliate) appear here; email and organic have no media spend.

*Partitioned by `spend_date` (DAY); clustered by `campaign_id`, `market`.*

| Column | Type | Description |
| --- | --- | --- |
| `spend_date` | DATE | Calendar date of the spend. Partition column. |
| `channel` | STRING | Paid channel: paid_search, paid_social or affiliate. |
| `campaign_id` | STRING | Campaign identifier, e.g. CMP-002. Joins to campaign_history.campaign_id. |
| `campaign_name` | STRING | Campaign name, e.g. Warm Escapes Retargeting, Fall City Breaks 2026. |
| `target_segment` | STRING | Audience the campaign targets, e.g. lapsed_compass_cold (lapsed Compass members in cold-weather markets), all_customers, urban_explorers. |
| `market` | STRING | Metro the spend was targeted to. Joins to customers.home_market and plan.market. |
| `impressions` | INT64 | Ad impressions served. |
| `clicks` | INT64 | Ad clicks. |
| `spend_usd` | FLOAT64 | Media spend in US dollars. |
| `attributed_conversions` | INT64 | Bookings the ad platform attributed to this campaign, market and day (platform attribution, not the bookings table). |

### `campaign_history`

The 12 marketing campaigns run since Jul 2025, with objective, audience, flight dates, budget, attributed results and a short retrospective. Always-on programs have end_date 2026-12-31 and results to date.

*Not partitioned.*

| Column | Type | Description |
| --- | --- | --- |
| `campaign_id` | STRING | Campaign identifier, e.g. CMP-003. Joins to ad_performance and creative_variants. |
| `name` | STRING | Campaign name, e.g. Winter Sun Early Bird 2025. |
| `objective` | STRING | The business outcome the campaign was meant to produce. |
| `target_segment` | STRING | Audience key, e.g. lapsed_compass (lapsed Compass members), lapsed_compass_cold, all_customers, active_compass, urban_explorers. |
| `start_date` | DATE | First flight date. |
| `end_date` | DATE | Last flight date. 2026-12-31 for always-on programs. |
| `channels` | ARRAY<STRING> | Channels used: one of paid_search, paid_social, organic, email, direct, affiliate. |
| `budget_usd` | FLOAT64 | Approved budget in US dollars for the flight (annual budget for always-on programs). |
| `spend_to_date_usd` | FLOAT64 | Paid media actually spent through Sep 15, 2026, from ad_performance. |
| `bookings_attributed` | INT64 | Confirmed bookings attributed to the campaign (to date for campaigns still running). |
| `roi` | FLOAT64 (nullable) | Contribution ROI as reported in the retrospective: (attributed revenue × 22% contribution margin − campaign cost) ÷ campaign cost. Negative means the campaign lost money. |
| `retrospective` | STRING | Two to three sentences on what happened and what was learned. |

### `creative_variants`

Performance of 200 ad creative variants across the campaigns, tagged by imagery style, offer framing and call-to-action wording. Use it to learn which creative choices convert for a given target segment.

*Not partitioned; clustered by `target_segment`.*

| Column | Type | Description |
| --- | --- | --- |
| `variant_id` | STRING | Unique creative variant identifier, e.g. CRV-0042. |
| `campaign_id` | STRING | Campaign the variant ran in. Joins to campaign_history.campaign_id. |
| `target_segment` | STRING | Audience the variant was shown to, e.g. lapsed_compass_cold, all_customers, urban_explorers. Can be narrower than the campaign's segment. |
| `hero_imagery_style` | STRING | Hero image style: beach_couple, family_pool, resort_aerial, city_skyline or adventure. |
| `offer_framing` | STRING | How the offer was framed: percent_off, bonus_points (Compass points), free_night, urgency (countdown / limited time) or no_offer. |
| `cta_construction` | STRING | Call-to-action wording: book_now, see_deals, plan_your_escape or claim_offer. |
| `impressions` | INT64 | Impressions served for the variant. |
| `clicks` | INT64 | Clicks on the variant. |
| `conversions` | INT64 | Bookings attributed to the variant. |
| `conversion_rate` | FLOAT64 | conversions ÷ clicks, as a fraction (0.031 = 3.1%). Weight by clicks when averaging across variants. |

### `propensity_training`

Training set for the warm-escape propensity model: one snapshot of every customer (50,000 rows) as of the reference date Sep 1, 2025, the same point in the booking season one year before the Sep 1, 2026 scoring snapshot, with features as they stood on that date and whether the customer booked a warm escape in the following 60 days.

*Not partitioned; clustered by `reference_date`.*

| Column | Type | Description |
| --- | --- | --- |
| `reference_date` | DATE | The as-of date for the features; the label window is the 60 days after it. |
| `customer_id` | STRING | Joins to customers.customer_id. |
| `days_since_last_booking` | INT64 (nullable) | Days from the most recent confirmed booking to reference_date; NULL if never booked. |
| `lifetime_bookings` | INT64 | Confirmed bookings before reference_date. |
| `loyalty_tier` | STRING | none, blue, silver or gold. |
| `home_market_climate` | STRING | cold, mild or warm. |
| `sessions_last_90d` | INT64 | Signed-in sessions in the 90 days before reference_date. |
| `warm_views_last_90d` | INT64 | Sessions with a warm-escape view in the 90 days before reference_date. |
| `email_optin` | BOOL | Email opt-in flag. |
| `ltv_band` | STRING | none, low, mid, high or vip, computed on lifetime value before reference_date. |
| `booked_warm_escape_60d` | INT64 | Label: 1 if the customer made a confirmed warm-escape booking in the 60 days after reference_date, else 0. |

### `decisioning_policy`

Next-best-action rules evaluated per customer against customer_features. Rules run in ascending priority; the first enabled rule whose condition(s) hold decides the action. Marketers edit this table.

*Not partitioned.*

| Column | Type | Description |
| --- | --- | --- |
| `rule_id` | STRING | Rule identifier, e.g. R01. |
| `priority` | INT64 | Evaluation order; lower runs first and the first match wins. |
| `feature` | STRING | customer_features column the condition tests, e.g. propensity_score, days_since_last_booking, loyalty_tier. |
| `operator` | STRING | Comparison: one of ==, !=, >=, >, <=, <. |
| `threshold` | STRING | Value to compare against, stored as text (60, 0.30, gold, true). Cast to the feature's type. |
| `feature_2` | STRING (nullable) | Optional second feature; when set, both conditions must hold (AND). |
| `operator_2` | STRING (nullable) | Comparison for the second condition. |
| `threshold_2` | STRING (nullable) | Value for the second condition, as text. |
| `action` | STRING | What to do when the rule matches: send_offer, hold_for_retargeting, route_to_loyalty_team or suppress. |
| `reason_template` | STRING | Human-readable explanation with {feature} placeholders filled from customer_features. |
| `enabled` | BOOL | FALSE rules are skipped. |

### `activations`

Receipts written by the activation endpoint when an audience is submitted to a channel. Empty until the lab submits an audience.

*Not partitioned.*

| Column | Type | Description |
| --- | --- | --- |
| `receipt_id` | STRING | Unique receipt identifier returned by the activation endpoint. |
| `segment_description` | STRING | The natural-language segment definition that was activated. |
| `audience_size` | INT64 | Number of customers in the submitted audience. |
| `channel` | STRING | Channel the audience was sent to: one of paid_search, paid_social, organic, email, direct, affiliate. |
| `submitted_at` | TIMESTAMP | When the audience was submitted (UTC). |
| `status` | STRING | accepted, rejected or pending. |

## Data agent context (paste into the BigQuery data agent)

### Instructions

You are the analytics assistant for Cymbal Voyages, an online travel brand, answering marketers' questions from the `cymbal_voyages` dataset. Warm escapes (`category = 'warm_escape'`) are winter and early-spring getaways to sun destinations; they are the signature category and sell mostly to customers in cold-weather markets, who book from late summer onward. A booking is a row in `bookings` with `status = 'confirmed'`; cancelled rows never count, and revenue is `revenue_usd` on confirmed rows. A booking's category comes from `packages` joined to `destinations`. Fiscal months are calendar months: compare actuals against `plan` by the calendar month of `booking_date`, `category` and the customer's `home_market`; variance = actual / plan − 1. The channel taxonomy is fixed: paid_search, paid_social, organic, email, direct, affiliate; `ad_performance` covers only the paid channels. Loyalty: anyone with `loyalty_tier` other than `none` is a Cymbal Compass member; lapsed means at least one booking ever and none in the last 12 months. Use `customer_month_status` for status as of a given month and `customer_features` for status as of Sep 1, 2026. Session conversion rate is `COUNTIF(converted) / COUNT(*)` on `web_sessions`; anonymous sessions (`customer_id IS NULL`) never convert. When asked why a number changed, break it down by category, climate, market and customer cohort before speculating, and say which table each figure came from.

### Glossary

| Term | Definition |
| --- | --- |
| warm escapes | Cymbal Voyages' signature category: winter and early-spring getaways to sun destinations (Caribbean, Mexico, Hawaii, Central America, the Florida Keys). `destinations.category = 'warm_escape'`. Booking season runs August–January; travel runs December–April. |
| booking | A confirmed reservation: a row in `bookings` with `status = 'confirmed'`. Cancelled rows are excluded from booking counts and revenue. Counted by `booking_date`, not travel date. |
| lapsed member | A Cymbal Compass member (`loyalty_tier != 'none'`) with at least one confirmed booking ever and none in the last 12 months (`loyalty_status = 'lapsed'`, equivalently `days_since_last_booking >= 365`). Status is evaluated as of a date: use `customer_month_status` for a past month, `customer_features` for Sep 1, 2026. |
| cold-weather markets | Chicago, Boston, Minneapolis, Detroit, Denver, Toronto, Cleveland, Milwaukee (`home_market_climate = 'cold'`). Warm markets are Miami, Phoenix, Houston, Los Angeles, San Diego; every other metro is mild. |
| Compass tier | Cymbal Compass loyalty tier: none (not enrolled), blue (enrolled), silver (4 bookings or $8,000 lifetime spend), gold (8 bookings or $20,000). `loyalty_tier` on customers, customer_month_status and customer_features. |
| retargeting | Paid-social advertising shown to people who already browsed the site. The always-on Warm Escapes Retargeting program (campaign CMP-002, `target_segment = 'lapsed_compass_cold'`) reaches lapsed Compass members in cold-weather markets who viewed warm destinations. In `ad_performance`, its spend, clicks and attributed conversions appear by day and market. |
| propensity score | `customer_features.propensity_score`: the modeled probability (0–1) that a customer books a warm-escape package in the 60 days after Sep 1, 2026, from the BigQuery ML logistic regression `warm_escape_propensity`. Right-skewed: the median customer scores about 0.08; scores above 0.30 are strong. |
| plan | The `plan` table: planned confirmed bookings and revenue by calendar month, category and home market. Variance = actual / plan − 1; anything within about ±5% is on plan. |

### Verified queries

**Bookings versus plan by month and category**

```sql
WITH actual AS (
  SELECT DATE_TRUNC(b.booking_date, MONTH) AS month, d.category,
         COUNT(*) AS bookings, ROUND(SUM(b.revenue_usd)) AS revenue_usd
  FROM `cymbal_voyages.bookings` b
  JOIN `cymbal_voyages.packages` p USING (package_id)
  JOIN `cymbal_voyages.destinations` d USING (destination_id)
  WHERE b.status = 'confirmed'
  GROUP BY 1, 2
), planned AS (
  SELECT plan_month AS month, category,
         SUM(planned_bookings) AS planned_bookings, ROUND(SUM(planned_revenue_usd)) AS planned_revenue_usd
  FROM `cymbal_voyages.plan`
  GROUP BY 1, 2
)
SELECT month, category, bookings, planned_bookings,
       ROUND(100 * (bookings / planned_bookings - 1), 1) AS bookings_variance_pct,
       revenue_usd, planned_revenue_usd
FROM actual JOIN planned USING (month, category)
ORDER BY month, category
```

**Conversion rate by customer cohort and month**

```sql
SELECT DATE_TRUNC(s.session_date, MONTH) AS month,
       CASE
         WHEN s.customer_id IS NULL THEN 'anonymous'
         WHEN st.loyalty_tier != 'none' AND st.loyalty_status = 'lapsed' AND c.home_market_climate = 'cold' THEN 'lapsed Compass member, cold market'
         WHEN st.loyalty_tier != 'none' AND st.loyalty_status = 'lapsed' THEN 'lapsed Compass member, other market'
         WHEN st.loyalty_tier != 'none' AND st.loyalty_status = 'active' THEN 'active Compass member'
         ELSE 'non-member'
       END AS cohort,
       COUNT(*) AS sessions,
       COUNTIF(s.converted) AS converted_sessions,
       ROUND(100 * SAFE_DIVIDE(COUNTIF(s.converted), COUNT(*)), 2) AS conversion_pct
FROM `cymbal_voyages.web_sessions` s
LEFT JOIN `cymbal_voyages.customers` c USING (customer_id)
LEFT JOIN `cymbal_voyages.customer_month_status` st
  ON st.customer_id = s.customer_id AND st.status_month = DATE_TRUNC(s.session_date, MONTH)
GROUP BY 1, 2
ORDER BY 1, 2
```

**Paid spend by campaign by week**

```sql
SELECT DATE_TRUNC(spend_date, WEEK(MONDAY)) AS week_start,
       campaign_id, campaign_name, channel,
       ROUND(SUM(spend_usd)) AS spend_usd, SUM(impressions) AS impressions, SUM(clicks) AS clicks,
       SUM(attributed_conversions) AS attributed_conversions
FROM `cymbal_voyages.ad_performance`
GROUP BY 1, 2, 3, 4
ORDER BY 1, 2
```

## Propensity model

| | |
| --- | --- |
| Model | `cymbal_voyages.warm_escape_propensity`, BigQuery ML `LOGISTIC_REG` (`sql/train_propensity.sql`) |
| Label | `booked_warm_escape_60d`: confirmed warm-escape booking in the 60 days after the reference date |
| Training table | `propensity_training`: 50,000 rows, every customer as of 2025-09-01 (same season, one year before the scoring date) |
| Features | `days_since_last_booking` (NULL → 9999 in `TRANSFORM`), `lifetime_bookings`, `loyalty_tier`, `home_market_climate`, `sessions_last_90d`, `warm_views_last_90d`, `email_optin`, `ltv_band` |
| Positive rate | 9.7% |
| Reference model (scikit-learn logistic regression on the same table) | holdout AUC **0.780**, log loss 0.270, random 20% of customers |
| BigQuery ML result (recorded Sep 17, 2026, fresh project, US multi-region) | `ML.EVALUATE` on the 20% random split: **roc_auc 0.786**, log_loss 0.269, accuracy 0.907, precision 0.657, recall 0.113 at the default 0.5 cutoff (the lab uses probabilities, not the class). **Training time: the `CREATE MODEL` job ran 56 seconds** on the 50,000-row table; 71 seconds wall clock for the whole script including `ML.EVALUATE` and `ML.GLOBAL_EXPLAIN`. Global explain ranks `home_market_climate`, `loyalty_tier` and `ltv_band` (attribution ≈ 0.67 each) above `lifetime_bookings` (0.37), `days_since_last_booking` (0.29), `warm_views_last_90d` (0.19), `sessions_last_90d` (0.12) and `email_optin` (≈ 0). |
| Scoring | `sql/predict_propensity.sql` updates `customer_features.propensity_score` in place. The shipped parquet already carries the reference model's scores so the lab works before BigQuery ML runs. |

Score profile: median customer about 0.08; the target audience (lapsed Compass members in cold markets with a warm view in the last 90 days, 3,838 customers) averages 0.156 with 8.7% at or above 0.30 on the shipped reference scores, and 0.162 with 10.3% at or above 0.30 once `predict_propensity.sql` has written the BigQuery ML scores. See `docs/anomaly-walkthrough.md` for the audience queries.

## Embeddings

`catalog_embeddings` is built by `embeddings/build_embeddings.py` with Vertex AI **`gemini-embedding-001`** at **3,072 dimensions**, task type `RETRIEVAL_DOCUMENT`, one text per request (the same model, dimension and SDK pattern as the mkt013 CymbalGoal lab). The embedded `content` is `"<name>. <region>, <country>. Category: <category>. <description>"` for destinations and `"<package name>. <nights> nights in <destination>. Category: <category>. <description>"` for packages, and is stored alongside the vector so a query can show what matched. Query-side embeddings should use task type `RETRIEVAL_QUERY` with the same model and dimension.

## Decisioning policy defaults

Rules run in ascending `priority`; the first enabled rule whose condition(s) hold decides the action. A rule may carry a second condition (`feature_2`, `operator_2`, `threshold_2`) ANDed with the first. Thresholds are stored as text so one column can hold `60`, `0.30` or `gold`.

| Rule | Priority | Condition | Action | Enabled |
| --- | ---: | --- | --- | --- |
| R01 | 10 | `days_since_last_booking <= 60` | suppress | yes |
| R02 | 20 | `loyalty_tier == gold` AND `propensity_score >= 0.60` | route_to_loyalty_team | yes |
| R03 | 30 | `propensity_score >= 0.30` AND `email_contactable == true` | send_offer | yes |
| R04 | 40 | `propensity_score >= 0.30` AND `sms_contactable == true` | send_offer | yes |
| R05 | 50 | `propensity_score >= 0.30` | hold_for_retargeting | yes |
| R06 | 60 | `warm_views_last_90d >= 3` | hold_for_retargeting | yes |
| R07 | 70 | `loyalty_status == never` | suppress | no |
| R08 | 99 | `propensity_score >= 0` | hold_for_retargeting | yes |

## Brand corpus

Twelve Markdown documents in `brand_corpus/` (source of truth), rendered to `brand_corpus/pdf/` by `build_pdfs.sh` for the Gemini Enterprise Cloud Storage data store: brand voice guide; campaign brief template (nine fixed headings the Brand Studio agent must follow); three past briefs with retrospectives (Winter Sun Early Bird 2025, Spring Flash Sale 2026, Fall City Breaks 2026) whose numbers match `campaign_history`; competitive positioning (three fictional competitors); legal claims list; Cymbal Compass program summary; audience segments glossary (same segment keys as the tables); channel playbook; warm-escapes seasonal calendar; creative production standards.

"""
The SQL trail from "August missed plan" to the finding, plus the two red herrings and the
audience-sizing and creative queries the later tasks use. Written in BigQuery dialect against
dataset `cymbal_voyages`; sql/verify_local.py runs the same text through DuckDB over out/.
"""

DATASET = "cymbal_voyages"

MARKETS_CTE = """markets AS (
  SELECT DISTINCT home_market AS market, home_market_climate AS climate
  FROM `cymbal_voyages.customers`
)"""

QUERIES = [
    ("q01_aug_vs_plan_by_category", "August 2026 confirmed bookings versus plan, by category", f"""
WITH actual AS (
  SELECT d.category, COUNT(*) AS bookings, ROUND(SUM(b.revenue_usd)) AS revenue_usd
  FROM `cymbal_voyages.bookings` b
  JOIN `cymbal_voyages.packages` p USING (package_id)
  JOIN `cymbal_voyages.destinations` d USING (destination_id)
  WHERE b.status = 'confirmed' AND b.booking_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'
  GROUP BY 1
), planned AS (
  SELECT category, SUM(planned_bookings) AS planned_bookings, ROUND(SUM(planned_revenue_usd)) AS planned_revenue_usd
  FROM `cymbal_voyages.plan`
  WHERE plan_month = DATE '2026-08-01'
  GROUP BY 1
)
SELECT a.category, a.bookings, p.planned_bookings,
       ROUND(100 * (a.bookings / p.planned_bookings - 1), 1) AS bookings_variance_pct,
       a.revenue_usd, p.planned_revenue_usd,
       ROUND(100 * (a.revenue_usd / p.planned_revenue_usd - 1), 1) AS revenue_variance_pct
FROM actual a JOIN planned p USING (category)
ORDER BY bookings_variance_pct
"""),
    ("q02_warm_escapes_by_month", "Warm-escape bookings versus plan by month (seasonality check)", f"""
WITH actual AS (
  SELECT DATE_TRUNC(b.booking_date, MONTH) AS month, COUNT(*) AS bookings
  FROM `cymbal_voyages.bookings` b
  JOIN `cymbal_voyages.packages` p USING (package_id)
  JOIN `cymbal_voyages.destinations` d USING (destination_id)
  WHERE b.status = 'confirmed' AND d.category = 'warm_escape'
  GROUP BY 1
), planned AS (
  SELECT plan_month AS month, SUM(planned_bookings) AS planned_bookings
  FROM `cymbal_voyages.plan` WHERE category = 'warm_escape' GROUP BY 1
)
SELECT a.month, a.bookings, p.planned_bookings,
       ROUND(100 * (a.bookings / p.planned_bookings - 1), 1) AS variance_pct
FROM actual a JOIN planned p USING (month)
WHERE a.month < DATE '2026-09-01'
ORDER BY a.month
"""),
    ("q03_aug_warm_by_climate", "August 2026 warm-escape bookings versus plan, by home-market climate", f"""
WITH {MARKETS_CTE},
actual AS (
  SELECT c.home_market_climate AS climate, COUNT(*) AS bookings
  FROM `cymbal_voyages.bookings` b
  JOIN `cymbal_voyages.customers` c USING (customer_id)
  JOIN `cymbal_voyages.packages` p USING (package_id)
  JOIN `cymbal_voyages.destinations` d USING (destination_id)
  WHERE b.status = 'confirmed' AND d.category = 'warm_escape'
    AND b.booking_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'
  GROUP BY 1
), planned AS (
  SELECT m.climate, SUM(pl.planned_bookings) AS planned_bookings
  FROM `cymbal_voyages.plan` pl JOIN markets m USING (market)
  WHERE pl.category = 'warm_escape' AND pl.plan_month = DATE '2026-08-01'
  GROUP BY 1
)
SELECT a.climate, a.bookings, p.planned_bookings,
       ROUND(100 * (a.bookings / p.planned_bookings - 1), 1) AS variance_pct
FROM actual a JOIN planned p USING (climate)
ORDER BY variance_pct
"""),
    ("q04_aug_warm_by_market", "August 2026 warm-escape bookings versus plan, by market", f"""
WITH {MARKETS_CTE},
actual AS (
  SELECT c.home_market AS market, COUNT(*) AS bookings
  FROM `cymbal_voyages.bookings` b
  JOIN `cymbal_voyages.customers` c USING (customer_id)
  JOIN `cymbal_voyages.packages` p USING (package_id)
  JOIN `cymbal_voyages.destinations` d USING (destination_id)
  WHERE b.status = 'confirmed' AND d.category = 'warm_escape'
    AND b.booking_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'
  GROUP BY 1
), planned AS (
  SELECT market, SUM(planned_bookings) AS planned_bookings
  FROM `cymbal_voyages.plan`
  WHERE category = 'warm_escape' AND plan_month = DATE '2026-08-01'
  GROUP BY 1
)
SELECT m.climate, a.market, a.bookings, p.planned_bookings,
       ROUND(100 * (a.bookings / p.planned_bookings - 1), 1) AS variance_pct
FROM actual a JOIN planned p USING (market) JOIN markets m USING (market)
ORDER BY variance_pct
"""),
    ("q05_incident_daily_sessions", "Red herring 1: daily sessions around the Aug 9 incident", f"""
SELECT session_date, COUNT(*) AS sessions, COUNTIF(converted) AS converted_sessions
FROM `cymbal_voyages.web_sessions`
WHERE session_date BETWEEN DATE '2026-08-05' AND DATE '2026-08-13'
GROUP BY 1 ORDER BY 1
"""),
    ("q06_incident_hourly", "Red herring 1: sessions by hour on Aug 9 versus the other Sundays in August", f"""
SELECT EXTRACT(HOUR FROM session_ts) AS hour_utc,
       COUNTIF(session_date = DATE '2026-08-09') AS aug_9_sessions,
       ROUND(COUNTIF(session_date IN (DATE '2026-08-02', DATE '2026-08-16', DATE '2026-08-23', DATE '2026-08-30')) / 4, 1) AS other_sundays_avg
FROM `cymbal_voyages.web_sessions`
WHERE session_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'
GROUP BY 1 ORDER BY 1
"""),
    ("q07_price_change_packages", "Red herring 2: the two re-priced packages, July versus August 2026", f"""
WITH repriced AS (
  SELECT package_id, name, base_price_usd, previous_base_price_usd, price_effective_date
  FROM `cymbal_voyages.packages`
  WHERE price_effective_date = DATE '2026-08-01'
)
SELECT r.package_id, r.name, r.previous_base_price_usd, r.base_price_usd,
       COUNTIF(b.booking_date BETWEEN DATE '2026-07-01' AND DATE '2026-07-31') AS jul_bookings,
       COUNTIF(b.booking_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31') AS aug_bookings
FROM repriced r
LEFT JOIN `cymbal_voyages.bookings` b ON b.package_id = r.package_id AND b.status = 'confirmed'
GROUP BY 1, 2, 3, 4
ORDER BY 1
"""),
    ("q08_price_change_context", "Red herring 2 in context: all warm-escape bookings, July versus August 2026, by whether the package was re-priced", f"""
SELECT CASE WHEN p.price_effective_date = DATE '2026-08-01' THEN 're-priced Aug 1' ELSE 'unchanged price' END AS package_group,
       COUNTIF(b.booking_date BETWEEN DATE '2026-07-01' AND DATE '2026-07-31') AS jul_bookings,
       COUNTIF(b.booking_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31') AS aug_bookings,
       COUNTIF(b.booking_date BETWEEN DATE '2025-08-01' AND DATE '2025-08-31') AS aug_2025_bookings
FROM `cymbal_voyages.bookings` b
JOIN `cymbal_voyages.packages` p USING (package_id)
JOIN `cymbal_voyages.destinations` d USING (destination_id)
WHERE b.status = 'confirmed' AND d.category = 'warm_escape'
GROUP BY 1 ORDER BY 1
"""),
    ("q09_cohort_conversion", "Conversion of warm-escape browsing sessions by customer cohort, August 2025 versus August 2026", f"""
SELECT
  CASE
    WHEN s.customer_id IS NULL THEN 'anonymous'
    WHEN st.loyalty_tier != 'none' AND st.loyalty_status = 'lapsed' AND c.home_market_climate = 'cold' THEN 'lapsed Compass member, cold market'
    WHEN st.loyalty_tier != 'none' AND st.loyalty_status = 'lapsed' THEN 'lapsed Compass member, other market'
    WHEN st.loyalty_tier != 'none' AND st.loyalty_status = 'active' THEN 'active Compass member'
    ELSE 'non-member'
  END AS cohort,
  COUNTIF(s.session_date BETWEEN DATE '2025-08-01' AND DATE '2025-08-31') AS aug_2025_sessions,
  ROUND(100 * SAFE_DIVIDE(COUNTIF(s.converted AND s.session_date BETWEEN DATE '2025-08-01' AND DATE '2025-08-31'),
                          COUNTIF(s.session_date BETWEEN DATE '2025-08-01' AND DATE '2025-08-31')), 2) AS aug_2025_conv_pct,
  COUNTIF(s.session_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31') AS aug_2026_sessions,
  ROUND(100 * SAFE_DIVIDE(COUNTIF(s.converted AND s.session_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'),
                          COUNTIF(s.session_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31')), 2) AS aug_2026_conv_pct
FROM `cymbal_voyages.web_sessions` s
LEFT JOIN `cymbal_voyages.customers` c USING (customer_id)
LEFT JOIN `cymbal_voyages.customer_month_status` st
  ON st.customer_id = s.customer_id AND st.status_month = DATE_TRUNC(s.session_date, MONTH)
WHERE s.viewed_warm_escape
  AND (s.session_date BETWEEN DATE '2025-08-01' AND DATE '2025-08-31' OR s.session_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31')
GROUP BY 1
ORDER BY 1
"""),
    ("q10_cohort_monthly", "The target cohort month by month: warm-escape sessions, browsing customers, conversion", f"""
SELECT DATE_TRUNC(s.session_date, MONTH) AS month,
       COUNT(*) AS warm_sessions,
       COUNT(DISTINCT s.customer_id) AS browsing_customers,
       COUNTIF(s.converted) AS converted_sessions,
       ROUND(100 * COUNTIF(s.converted) / COUNT(*), 2) AS conversion_pct,
       ROUND(100 * COUNTIF(s.channel = 'paid_social') / COUNT(*), 1) AS paid_social_share_pct
FROM `cymbal_voyages.web_sessions` s
JOIN `cymbal_voyages.customers` c USING (customer_id)
JOIN `cymbal_voyages.customer_month_status` st
  ON st.customer_id = s.customer_id AND st.status_month = DATE_TRUNC(s.session_date, MONTH)
WHERE s.viewed_warm_escape
  AND c.home_market_climate = 'cold' AND st.loyalty_tier != 'none' AND st.loyalty_status = 'lapsed'
GROUP BY 1 ORDER BY 1
"""),
    ("q11_cohort_channel_mix", "The target cohort's warm-escape sessions by channel, August 2025 versus August 2026", f"""
SELECT s.channel,
       COUNTIF(s.session_date BETWEEN DATE '2025-08-01' AND DATE '2025-08-31') AS aug_2025_sessions,
       COUNTIF(s.session_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31') AS aug_2026_sessions
FROM `cymbal_voyages.web_sessions` s
JOIN `cymbal_voyages.customers` c USING (customer_id)
JOIN `cymbal_voyages.customer_month_status` st
  ON st.customer_id = s.customer_id AND st.status_month = DATE_TRUNC(s.session_date, MONTH)
WHERE s.viewed_warm_escape
  AND c.home_market_climate = 'cold' AND st.loyalty_tier != 'none' AND st.loyalty_status = 'lapsed'
  AND (s.session_date BETWEEN DATE '2025-08-01' AND DATE '2025-08-31' OR s.session_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31')
GROUP BY 1 ORDER BY aug_2025_sessions DESC
"""),
    ("q12_total_paid_spend_weekly", "Total paid spend by week, June–September 2026 (the naive 'did we cut spend?' check)", f"""
SELECT DATE_TRUNC(spend_date, WEEK(MONDAY)) AS week_start,
       ROUND(SUM(spend_usd)) AS total_spend_usd,
       ROUND(SUM(IF(channel = 'paid_social', spend_usd, 0))) AS paid_social_usd,
       ROUND(SUM(IF(channel = 'paid_search', spend_usd, 0))) AS paid_search_usd
FROM `cymbal_voyages.ad_performance`
WHERE spend_date BETWEEN DATE '2026-06-29' AND DATE '2026-09-13'
GROUP BY 1 ORDER BY 1
"""),
    ("q13_spend_by_campaign_weekly", "Paid spend by campaign by week around Jul 24, 2026", f"""
SELECT DATE_TRUNC(spend_date, WEEK(MONDAY)) AS week_start, campaign_id, campaign_name, target_segment,
       ROUND(SUM(spend_usd)) AS spend_usd, SUM(clicks) AS clicks, SUM(attributed_conversions) AS attributed_conversions
FROM `cymbal_voyages.ad_performance`
WHERE spend_date BETWEEN DATE '2026-07-06' AND DATE '2026-08-16'
  AND campaign_id IN ('CMP-002', 'CMP-012')
GROUP BY 1, 2, 3, 4 ORDER BY 2, 1
"""),
    ("q14_retargeting_daily", "Warm Escapes Retargeting, daily, the week of the change", f"""
SELECT spend_date, ROUND(SUM(spend_usd)) AS spend_usd, SUM(clicks) AS clicks, SUM(attributed_conversions) AS attributed_conversions
FROM `cymbal_voyages.ad_performance`
WHERE campaign_id = 'CMP-002' AND spend_date BETWEEN DATE '2026-07-20' AND DATE '2026-07-27'
GROUP BY 1 ORDER BY 1
"""),
    ("q15_campaign_history_fcb", "campaign_history: the campaign that took the budget", f"""
SELECT campaign_id, name, target_segment, start_date, end_date, budget_usd, spend_to_date_usd, bookings_attributed, roi
FROM `cymbal_voyages.campaign_history`
WHERE campaign_id IN ('CMP-002', 'CMP-012')
ORDER BY campaign_id
"""),
    ("q16_segment_base", "Audience: lapsed Compass members in cold markets who viewed a warm destination in the last 90 days and did not book", f"""
SELECT COUNT(*) AS customers,
       ROUND(AVG(propensity_score), 3) AS avg_propensity,
       ROUND(100 * COUNTIF(propensity_score >= 0.3) / COUNT(*), 1) AS pct_propensity_ge_030,
       ROUND(100 * COUNTIF(propensity_score >= 0.6) / COUNT(*), 1) AS pct_propensity_ge_060,
       ROUND(100 * COUNTIF(email_contactable) / COUNT(*), 1) AS pct_email_contactable
FROM `cymbal_voyages.customer_features`
WHERE home_market_climate = 'cold'
  AND loyalty_tier != 'none'
  AND loyalty_status = 'lapsed'
  AND warm_views_last_90d >= 1
"""),
    ("q17_segment_variants", "Audience variants: how the size and propensity profile move with each filter", f"""
WITH base AS (
  SELECT * FROM `cymbal_voyages.customer_features`
  WHERE home_market_climate = 'cold' AND loyalty_tier != 'none' AND warm_views_last_90d >= 1
)
SELECT variant, COUNT(*) AS customers, ROUND(AVG(propensity_score), 3) AS avg_propensity,
       ROUND(100 * COUNTIF(propensity_score >= 0.3) / COUNT(*), 1) AS pct_propensity_ge_030
FROM (
  SELECT 'A. lapsed (12+ months), any contactability' AS variant, propensity_score FROM base WHERE loyalty_status = 'lapsed'
  UNION ALL
  SELECT 'B. A, only email-contactable', propensity_score FROM base WHERE loyalty_status = 'lapsed' AND email_contactable
  UNION ALL
  SELECT 'C. A, lapsed 12-24 months only', propensity_score FROM base WHERE loyalty_status = 'lapsed' AND days_since_last_booking < 730
  UNION ALL
  SELECT 'D. A, lapsed 24+ months only', propensity_score FROM base WHERE loyalty_status = 'lapsed' AND days_since_last_booking >= 730
  UNION ALL
  SELECT 'E. all Compass members in cold markets who browsed warm', propensity_score FROM base
  UNION ALL
  SELECT 'F. E, dropping anyone who booked in the last 60 days', propensity_score FROM base WHERE NOT booked_last_60d
)
GROUP BY 1 ORDER BY 1
"""),
    ("q18_creative_offer", "Creative learning for the segment: conversion by offer framing (lapsed_compass_cold variants, click-weighted)", f"""
SELECT offer_framing, COUNT(*) AS variants, SUM(clicks) AS clicks, SUM(conversions) AS conversions,
       ROUND(100 * SUM(conversions) / SUM(clicks), 2) AS conversion_pct
FROM `cymbal_voyages.creative_variants`
WHERE target_segment = 'lapsed_compass_cold'
GROUP BY 1 ORDER BY conversion_pct DESC
"""),
    ("q19_creative_imagery", "Creative learning: conversion by hero imagery style (lapsed_compass_cold)", f"""
SELECT hero_imagery_style, COUNT(*) AS variants, SUM(clicks) AS clicks, SUM(conversions) AS conversions,
       ROUND(100 * SUM(conversions) / SUM(clicks), 2) AS conversion_pct
FROM `cymbal_voyages.creative_variants`
WHERE target_segment = 'lapsed_compass_cold'
GROUP BY 1 ORDER BY conversion_pct DESC
"""),
    ("q20_creative_cta", "Creative learning: conversion by call-to-action construction (lapsed_compass_cold)", f"""
SELECT cta_construction, COUNT(*) AS variants, SUM(clicks) AS clicks, SUM(conversions) AS conversions,
       ROUND(100 * SUM(conversions) / SUM(clicks), 2) AS conversion_pct
FROM `cymbal_voyages.creative_variants`
WHERE target_segment = 'lapsed_compass_cold'
GROUP BY 1 ORDER BY conversion_pct DESC
"""),
    ("q21_creative_contrast", "Creative learning: the same offer framings for the broad all_customers segment (different answer)", f"""
SELECT offer_framing, SUM(clicks) AS clicks, SUM(conversions) AS conversions,
       ROUND(100 * SUM(conversions) / SUM(clicks), 2) AS conversion_pct
FROM `cymbal_voyages.creative_variants`
WHERE target_segment = 'all_customers'
GROUP BY 1 ORDER BY conversion_pct DESC
"""),
    ("q22_policy_dry_run", "Decisioning dry run: what the default policy does to the base audience", f"""
WITH aud AS (
  SELECT * FROM `cymbal_voyages.customer_features`
  WHERE home_market_climate = 'cold' AND loyalty_tier != 'none' AND loyalty_status = 'lapsed' AND warm_views_last_90d >= 1
)
SELECT CASE
         WHEN days_since_last_booking <= 60 THEN 'suppress (R01)'
         WHEN loyalty_tier = 'gold' AND propensity_score >= 0.60 THEN 'route_to_loyalty_team (R02)'
         WHEN propensity_score >= 0.30 AND email_contactable THEN 'send_offer (R03)'
         WHEN propensity_score >= 0.30 AND sms_contactable THEN 'send_offer (R04)'
         WHEN propensity_score >= 0.30 THEN 'hold_for_retargeting (R05)'
         WHEN warm_views_last_90d >= 3 THEN 'hold_for_retargeting (R06)'
         ELSE 'hold_for_retargeting (R08)'
       END AS decision,
       COUNT(*) AS customers
FROM aud GROUP BY 1 ORDER BY customers DESC
"""),
]

# Verified queries for the BigQuery data agent. Each entry: (question, sql, required).
# The data agent UI labels the title field "Question", so titles are phrased as questions.
# Required ones are what the lab's Builder enters in Task 1; optional ones are candidates planning
# may pre-load or drop (they size the two red herrings).
VERIFIED = [
    ("How did bookings compare with plan by month and category?", f"""
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
""", True),
    ("How did warm-escape browsing conversion change by customer cohort, this August versus last?", f"""
SELECT
  CASE
    WHEN s.customer_id IS NULL THEN 'anonymous'
    WHEN st.loyalty_tier != 'none' AND st.loyalty_status = 'lapsed' AND c.home_market_climate = 'cold' THEN 'lapsed Compass member, cold market'
    WHEN st.loyalty_tier != 'none' AND st.loyalty_status = 'lapsed' THEN 'lapsed Compass member, other market'
    WHEN st.loyalty_tier != 'none' AND st.loyalty_status = 'active' THEN 'active Compass member'
    ELSE 'non-member'
  END AS cohort,
  COUNTIF(s.session_date BETWEEN DATE '2025-08-01' AND DATE '2025-08-31') AS aug_2025_sessions,
  ROUND(100 * SAFE_DIVIDE(COUNTIF(s.converted AND s.session_date BETWEEN DATE '2025-08-01' AND DATE '2025-08-31'),
                          COUNTIF(s.session_date BETWEEN DATE '2025-08-01' AND DATE '2025-08-31')), 2) AS aug_2025_conv_pct,
  COUNTIF(s.session_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31') AS aug_2026_sessions,
  ROUND(100 * SAFE_DIVIDE(COUNTIF(s.converted AND s.session_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'),
                          COUNTIF(s.session_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31')), 2) AS aug_2026_conv_pct
FROM `cymbal_voyages.web_sessions` s
LEFT JOIN `cymbal_voyages.customers` c USING (customer_id)
LEFT JOIN `cymbal_voyages.customer_month_status` st
  ON st.customer_id = s.customer_id AND st.status_month = DATE_TRUNC(s.session_date, MONTH)
WHERE s.viewed_warm_escape
  AND (s.session_date BETWEEN DATE '2025-08-01' AND DATE '2025-08-31' OR s.session_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31')
GROUP BY 1
ORDER BY 1
""", True),
    ("How did paid spend move by campaign each week?", f"""
SELECT DATE_TRUNC(spend_date, WEEK(MONDAY)) AS week_start,
       campaign_id, campaign_name, channel,
       ROUND(SUM(spend_usd)) AS spend_usd, SUM(impressions) AS impressions, SUM(clicks) AS clicks,
       SUM(attributed_conversions) AS attributed_conversions
FROM `cymbal_voyages.ad_performance`
GROUP BY 1, 2, 3, 4
ORDER BY 1, 2
""", True),
    ("What did each campaign spend per day in July and August 2026?", f"""
SELECT spend_date, campaign_id, campaign_name,
       ROUND(SUM(spend_usd)) AS spend_usd, SUM(clicks) AS clicks, SUM(attributed_conversions) AS attributed_conversions
FROM `cymbal_voyages.ad_performance`
WHERE spend_date BETWEEN DATE '2026-07-01' AND DATE '2026-08-31'
GROUP BY 1, 2, 3
ORDER BY 2, 1
""", True),
    ("How many sessions and bookings did the August 9 site incident cost?", f"""
WITH daily AS (
  SELECT session_date, COUNT(*) AS sessions, COUNTIF(converted) AS converted_sessions
  FROM `cymbal_voyages.web_sessions`
  WHERE session_date BETWEEN DATE '2026-08-05' AND DATE '2026-08-13'
  GROUP BY 1
), typical AS (
  SELECT AVG(sessions) AS sessions, AVG(converted_sessions) AS converted_sessions
  FROM daily WHERE session_date != DATE '2026-08-09'
)
SELECT d.sessions AS aug_9_sessions, ROUND(t.sessions) AS typical_day_sessions,
       ROUND(t.sessions - d.sessions) AS sessions_lost,
       d.converted_sessions AS aug_9_converted, ROUND(t.converted_sessions) AS typical_day_converted,
       ROUND(t.converted_sessions - d.converted_sessions) AS tracked_bookings_lost,
       ROUND(ROUND(t.converted_sessions - d.converted_sessions) / 0.4) AS estimated_bookings_lost_incl_app_and_phone
FROM daily d CROSS JOIN typical t
WHERE d.session_date = DATE '2026-08-09'
""", False),
    ("How many bookings did the August 1 price change cost?", f"""
SELECT CASE WHEN p.price_effective_date = DATE '2026-08-01' THEN 're-priced Aug 1' ELSE 'unchanged price' END AS package_group,
       COUNTIF(b.booking_date BETWEEN DATE '2025-08-01' AND DATE '2025-08-31') AS aug_2025_bookings,
       COUNTIF(b.booking_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31') AS aug_2026_bookings,
       COUNTIF(b.booking_date BETWEEN DATE '2025-08-01' AND DATE '2025-08-31')
         - COUNTIF(b.booking_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31') AS bookings_lost_vs_last_august
FROM `cymbal_voyages.bookings` b
JOIN `cymbal_voyages.packages` p USING (package_id)
JOIN `cymbal_voyages.destinations` d USING (destination_id)
WHERE b.status = 'confirmed' AND d.category = 'warm_escape'
GROUP BY 1 ORDER BY 1
""", False),
]

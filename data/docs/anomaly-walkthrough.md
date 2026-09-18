# Anomaly walkthrough: why August 2026 missed plan

*Generated from the shipped data by `sql/verify_local.py --write`. Every number below is what the query returns against `out/` (DuckDB) and, once loaded, against `cymbal_voyages` in BigQuery. Regenerating the data with the same seed reproduces these numbers exactly.*

**The finding the trail converges on.** August 2026 warm-escape bookings came in 18.1% under plan (3,175 confirmed bookings against a plan of 3,876, a gap of 701). Every other category landed within a few percent of plan. The whole miss sits in the cold-weather markets (-33.5%, 663 bookings short); mild (-1.7%) and warm (-2.8%) markets were on plan. Inside the cold markets, the miss belongs to one cohort: lapsed Cymbal Compass members who browsed warm destinations. Their browsing held up (5,546 warm-escape sessions in August 2025, 6,050 in August 2026) but their conversion fell from 6.7% to 2.4%, while every other cohort converted the same as last year. The always-on paid-social program that reached that cohort, Warm Escapes Retargeting (CMP-002), had its budget rotated to Fall City Breaks 2026 (CMP-012) on **July 24, 2026**; total paid spend never dropped, which is why a naive spend check says nothing changed. August 2025 was on plan (+1.0%), so seasonality is ruled out. Two red herrings, a 4-hour site incident on Aug 9 and a price increase on two packages on Aug 1, each explain a rounding error's worth of the gap.

The queries are in BigQuery SQL against dataset `cymbal_voyages`. Column names and values are the ones the data agent sees in `schemas/*.json`.

## Step 1: confirm the miss and rule out the other categories

### August 2026 confirmed bookings versus plan, by category

```sql
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
```

| category | bookings | planned_bookings | bookings_variance_pct | revenue_usd | planned_revenue_usd | revenue_variance_pct |
| --- | --- | --- | --- | --- | --- | --- |
| warm_escape | 3,175 | 3,876 | -18.1 | 6,782,751 | 8,403,131 | -19.3 |
| ski | 208 | 214 | -2.8 | 623,343 | 657,307 | -5.2 |
| city_break | 601 | 609 | -1.3 | 863,838 | 898,023 | -3.8 |
| cruise | 264 | 264 | 0 | 585,698 | 566,263 | 3.4 |
| adventure | 244 | 239 | 2.1 | 740,566 | 688,285 | 7.6 |

Warm escapes are the only category materially off plan. The other four are within about ±5% on bookings, which is inside the plan's normal noise. Revenue tells the same story as bookings, so this is a volume problem, not a price-mix problem.

## Step 2: rule out seasonality

### Warm-escape bookings versus plan by month (seasonality check)

```sql
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
```

| month | bookings | planned_bookings | variance_pct |
| --- | --- | --- | --- |
| 2025-07-01 | 1,410 | 1,437 | -1.9 |
| 2025-08-01 | 3,458 | 3,424 | 1 |
| 2025-09-01 | 3,583 | 3,541 | 1.2 |
| 2025-10-01 | 2,766 | 2,709 | 2.1 |
| 2025-11-01 | 2,128 | 2,109 | 0.9 |
| 2025-12-01 | 1,913 | 1,882 | 1.6 |
| 2026-01-01 | 2,544 | 2,540 | 0.2 |
| 2026-02-01 | 1,473 | 1,473 | 0 |
| 2026-03-01 | 954 | 943 | 1.2 |
| 2026-04-01 | 688 | 688 | 0 |
| 2026-05-01 | 498 | 484 | 2.9 |
| 2026-06-01 | 722 | 732 | -1.4 |
| 2026-07-01 | 1,439 | 1,539 | -6.5 |
| 2026-08-01 | 3,175 | 3,876 | -18.1 |

Every month from July 2025 through June 2026 is within about ±3% of plan, including August 2025 at +1.0%. The plan already carries the seasonal shape (August and September are the biggest warm-escape months because cold-weather customers book winter trips from late summer). Note July 2026 at -6.5%: the miss starts in the last week of July, which is the first dated clue.

## Step 3: find where the miss lives

### August 2026 warm-escape bookings versus plan, by home-market climate

```sql
WITH markets AS (
  SELECT DISTINCT home_market AS market, home_market_climate AS climate
  FROM `cymbal_voyages.customers`
),
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
```

| climate | bookings | planned_bookings | variance_pct |
| --- | --- | --- | --- |
| cold | 1,318 | 1,981 | -33.5 |
| warm | 518 | 533 | -2.8 |
| mild | 1,339 | 1,362 | -1.7 |

The cold-weather markets carry the entire gap: 1,318 bookings against a plan of 1,981 (-33.5%). Mild and warm markets are on plan.

### August 2026 warm-escape bookings versus plan, by market

```sql
WITH markets AS (
  SELECT DISTINCT home_market AS market, home_market_climate AS climate
  FROM `cymbal_voyages.customers`
),
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
```

| climate | market | bookings | planned_bookings | variance_pct |
| --- | --- | --- | --- | --- |
| cold | Boston | 188 | 291 | -35.4 |
| cold | Detroit | 143 | 220 | -35 |
| cold | Chicago | 286 | 439 | -34.9 |
| cold | Toronto | 233 | 352 | -33.8 |
| cold | Milwaukee | 71 | 106 | -33 |
| cold | Minneapolis | 129 | 190 | -32.1 |
| cold | Denver | 166 | 241 | -31.1 |
| cold | Cleveland | 102 | 142 | -28.2 |
| mild | Charlotte | 63 | 70 | -10 |
| mild | Vancouver | 71 | 77 | -7.8 |
| warm | Houston | 92 | 96 | -4.2 |
| mild | San Francisco | 136 | 142 | -4.2 |
| mild | Nashville | 58 | 60 | -3.3 |
| warm | Los Angeles | 161 | 166 | -3 |
| warm | Miami | 101 | 104 | -2.9 |
| warm | Phoenix | 106 | 109 | -2.8 |
| mild | New York | 322 | 327 | -1.5 |
| mild | Atlanta | 90 | 91 | -1.1 |
| mild | Seattle | 105 | 106 | -0.9 |
| mild | Dallas | 114 | 115 | -0.9 |
| mild | Philadelphia | 151 | 152 | -0.7 |
| warm | San Diego | 58 | 58 | 0 |
| mild | Washington DC | 120 | 120 | 0 |
| mild | Raleigh | 54 | 51 | 5.9 |
| mild | Portland | 55 | 51 | 7.8 |

All eight cold markets are down by roughly the same proportion and no mild or warm market is down more than plan noise, so this is not one city's problem (a local competitor, a weather event) but something that touched all cold-weather customers at once.

## Step 4: check the two obvious explanations (the red herrings)

### Red herring 1: the August 9 site incident

### Red herring 1: daily sessions around the Aug 9 incident

```sql
SELECT session_date, COUNT(*) AS sessions, COUNTIF(converted) AS converted_sessions
FROM `cymbal_voyages.web_sessions`
WHERE session_date BETWEEN DATE '2026-08-05' AND DATE '2026-08-13'
GROUP BY 1 ORDER BY 1
```

| session_date | sessions | converted_sessions |
| --- | --- | --- |
| 2026-08-05 | 2,043 | 74 |
| 2026-08-06 | 1,919 | 79 |
| 2026-08-07 | 1,831 | 61 |
| 2026-08-08 | 2,022 | 71 |
| 2026-08-09 | 1,527 | 43 |
| 2026-08-10 | 2,014 | 63 |
| 2026-08-11 | 1,995 | 55 |
| 2026-08-12 | 1,933 | 67 |
| 2026-08-13 | 1,968 | 84 |

### Red herring 1: sessions by hour on Aug 9 versus the other Sundays in August

```sql
SELECT EXTRACT(HOUR FROM session_ts) AS hour_utc,
       COUNTIF(session_date = DATE '2026-08-09') AS aug_9_sessions,
       ROUND(COUNTIF(session_date IN (DATE '2026-08-02', DATE '2026-08-16', DATE '2026-08-23', DATE '2026-08-30')) / 4, 1) AS other_sundays_avg
FROM `cymbal_voyages.web_sessions`
WHERE session_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31'
GROUP BY 1 ORDER BY 1
```

| hour_utc | aug_9_sessions | other_sundays_avg |
| --- | --- | --- |
| 0 | 73 | 71 |
| 1 | 66 | 48.3 |
| 2 | 25 | 28.5 |
| 3 | 13 | 17 |
| 4 | 15 | 11.5 |
| 5 | 5 | 12.8 |
| 6 | 20 | 14.5 |
| 7 | 28 | 28.3 |
| 8 | 51 | 45.5 |
| 9 | 84 | 68.5 |
| 10 | 88 | 79.3 |
| 11 | 85 | 97.8 |
| 12 | 131 | 107 |
| 13 | 124 | 126 |
| 14 | 0 | 126.3 |
| 15 | 0 | 114 |
| 16 | 0 | 118.5 |
| 17 | 0 | 99.8 |
| 18 | 97 | 107 |
| 19 | 108 | 112.3 |
| 20 | 140 | 119.3 |
| 21 | 140 | 131.8 |
| 22 | 141 | 131.8 |
| 23 | 93 | 91 |

Sessions on Aug 9 were 1,527 against roughly 1,966 on the surrounding days: about 439 sessions lost during the four hours (14:00–18:00 UTC, 10am–2pm Eastern) when the site was down. Converted sessions were 43 against roughly 69, so the incident cost about 26 tracked bookings, or roughly 65 bookings in total once app and phone bookings are counted (about 40% of bookings complete in a tracked web session). That is a real loss, and it is about 9% of a 701-booking gap.

### Red herring 2: the August 1 price increase

### Red herring 2: the two re-priced packages, July versus August 2026

```sql
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
```

| package_id | name | previous_base_price_usd | base_price_usd | jul_bookings | aug_bookings |
| --- | --- | --- | --- | --- | --- |
| PKG-0032 | Aruba Classic Week | 1,449 | 1,619 | 14 | 22 |
| PKG-0057 | Maui Classic Week | 1,319 | 1,479 | 5 | 16 |

### Red herring 2 in context: all warm-escape bookings, July versus August 2026, by whether the package was re-priced

```sql
SELECT CASE WHEN p.price_effective_date = DATE '2026-08-01' THEN 're-priced Aug 1' ELSE 'unchanged price' END AS package_group,
       COUNTIF(b.booking_date BETWEEN DATE '2026-07-01' AND DATE '2026-07-31') AS jul_bookings,
       COUNTIF(b.booking_date BETWEEN DATE '2026-08-01' AND DATE '2026-08-31') AS aug_bookings,
       COUNTIF(b.booking_date BETWEEN DATE '2025-08-01' AND DATE '2025-08-31') AS aug_2025_bookings
FROM `cymbal_voyages.bookings` b
JOIN `cymbal_voyages.packages` p USING (package_id)
JOIN `cymbal_voyages.destinations` d USING (destination_id)
WHERE b.status = 'confirmed' AND d.category = 'warm_escape'
GROUP BY 1 ORDER BY 1
```

| package_group | jul_bookings | aug_bookings | aug_2025_bookings |
| --- | --- | --- | --- |
| re-priced Aug 1 | 19 | 38 | 56 |
| unchanged price | 1,420 | 3,137 | 3,402 |

Two packages (Aruba Classic Week and Maui Classic Week) went up about 12% on Aug 1. Their August bookings were 38 against 56 the August before, a drop that is real but tiny: 38 bookings is 1.2% of the category, and the 18-booking year-over-year decline is about 3% of the gap. Part of that decline is the cohort effect below anyway, since both packages sell heavily to cold-weather members.

## Step 5: follow the thread into customer behavior

### Conversion of warm-escape browsing sessions by customer cohort, August 2025 versus August 2026

```sql
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
```

| cohort | aug_2025_sessions | aug_2025_conv_pct | aug_2026_sessions | aug_2026_conv_pct |
| --- | --- | --- | --- | --- |
| active Compass member | 5,866 | 13.04 | 5,933 | 13.65 |
| anonymous | 10,316 | 0 | 11,614 | 0 |
| lapsed Compass member, cold market | 5,546 | 6.74 | 6,050 | 2.43 |
| lapsed Compass member, other market | 1,644 | 8.82 | 1,906 | 9.29 |
| non-member | 3,683 | 6.9 | 4,574 | 7.11 |

This is the pivot of the analysis. Warm-escape browsing sessions are split by who was browsing, using each customer's loyalty status as it stood at the start of that month (`customer_month_status`). Lapsed Compass members in cold markets browsed as much as last year (5,546 sessions then, 6,050 now) and converted at 6.74% then versus 2.43% now. Active members (13.0% → 13.7%) and lapsed members in other markets (8.8% → 9.3%) did not move. Anonymous sessions never convert because booking requires signing in.

### The target cohort month by month: warm-escape sessions, browsing customers, conversion

```sql
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
```

| month | warm_sessions | browsing_customers | converted_sessions | conversion_pct | paid_social_share_pct |
| --- | --- | --- | --- | --- | --- |
| 2025-07-01 | 4,143 | 2,529 | 181 | 4.37 | 23.3 |
| 2025-08-01 | 5,546 | 2,943 | 374 | 6.74 | 23 |
| 2025-09-01 | 4,233 | 2,461 | 318 | 7.51 | 24 |
| 2025-10-01 | 2,107 | 1,504 | 145 | 6.88 | 25.2 |
| 2025-11-01 | 1,212 | 956 | 93 | 7.67 | 25.6 |
| 2025-12-01 | 906 | 777 | 56 | 6.18 | 24.8 |
| 2026-01-01 | 1,600 | 1,228 | 99 | 6.19 | 22.3 |
| 2026-02-01 | 811 | 716 | 41 | 5.06 | 24.5 |
| 2026-03-01 | 629 | 561 | 24 | 3.82 | 20.7 |
| 2026-04-01 | 437 | 401 | 18 | 4.12 | 23.3 |
| 2026-05-01 | 400 | 379 | 16 | 4 | 21.8 |
| 2026-06-01 | 2,027 | 1,522 | 77 | 3.8 | 25.2 |
| 2026-07-01 | 4,243 | 2,605 | 148 | 3.49 | 18.1 |
| 2026-08-01 | 6,050 | 3,184 | 147 | 2.43 | 2.6 |
| 2026-09-01 | 2,564 | 1,882 | 92 | 3.59 | 3 |

Month by month, the cohort's conversion runs 6–8% through the 2025 booking season, eases to 4–5% in the off-season (as it did in July 2025), and then, instead of climbing back into the 6–8% range when the season opens, drops to 2.4% in August 2026 and stays down in September. The paid-social share of the cohort's sessions collapses at the same moment, from about 24% to about 3%, with the first partial-month dip in July.

### The target cohort's warm-escape sessions by channel, August 2025 versus August 2026

```sql
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
```

| channel | aug_2025_sessions | aug_2026_sessions |
| --- | --- | --- |
| direct | 1,394 | 1,825 |
| paid_social | 1,277 | 156 |
| organic | 1,222 | 1,680 |
| email | 866 | 1,281 |
| paid_search | 598 | 818 |
| affiliate | 189 | 290 |

The cohort's paid-social sessions fell from 1,277 to 156, while direct, organic and email sessions all rose. Intent was still there; the paid reminder that used to close it was not.

## Step 6: follow the thread into ad spend

### Total paid spend by week, June–September 2026 (the naive 'did we cut spend?' check)

```sql
SELECT DATE_TRUNC(spend_date, WEEK(MONDAY)) AS week_start,
       ROUND(SUM(spend_usd)) AS total_spend_usd,
       ROUND(SUM(IF(channel = 'paid_social', spend_usd, 0))) AS paid_social_usd,
       ROUND(SUM(IF(channel = 'paid_search', spend_usd, 0))) AS paid_search_usd
FROM `cymbal_voyages.ad_performance`
WHERE spend_date BETWEEN DATE '2026-06-29' AND DATE '2026-09-13'
GROUP BY 1 ORDER BY 1
```

| week_start | total_spend_usd | paid_social_usd | paid_search_usd |
| --- | --- | --- | --- |
| 2026-06-29 | 54,995 | 18,590 | 27,992 |
| 2026-07-06 | 57,378 | 20,943 | 28,025 |
| 2026-07-13 | 57,167 | 20,894 | 27,873 |
| 2026-07-20 | 57,247 | 20,897 | 27,955 |
| 2026-07-27 | 59,070 | 22,654 | 28,005 |
| 2026-08-03 | 63,812 | 27,309 | 28,091 |
| 2026-08-10 | 63,890 | 27,384 | 28,098 |
| 2026-08-17 | 63,687 | 27,318 | 27,953 |
| 2026-08-24 | 63,858 | 27,327 | 28,108 |
| 2026-08-31 | 63,712 | 27,249 | 28,042 |
| 2026-09-07 | 63,763 | 27,400 | 27,962 |

The naive check. Total paid spend did not fall in late July; it rose with the season into August (the retargeting budget carried a seasonal uplift, and Fall City Breaks inherited it), and paid social specifically rose. Anyone who stops here concludes spend is not the problem.

### Paid spend by campaign by week around Jul 24, 2026

```sql
SELECT DATE_TRUNC(spend_date, WEEK(MONDAY)) AS week_start, campaign_id, campaign_name, target_segment,
       ROUND(SUM(spend_usd)) AS spend_usd, SUM(clicks) AS clicks, SUM(attributed_conversions) AS attributed_conversions
FROM `cymbal_voyages.ad_performance`
WHERE spend_date BETWEEN DATE '2026-07-06' AND DATE '2026-08-16'
  AND campaign_id IN ('CMP-002', 'CMP-012')
GROUP BY 1, 2, 3, 4 ORDER BY 2, 1
```

| week_start | campaign_id | campaign_name | target_segment | spend_usd | clicks | attributed_conversions |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-07-06 | CMP-002 | Warm Escapes Retargeting | lapsed_compass_cold | 20,943 | 9,986 | 112 |
| 2026-07-13 | CMP-002 | Warm Escapes Retargeting | lapsed_compass_cold | 20,894 | 10,003 | 98 |
| 2026-07-20 | CMP-002 | Warm Escapes Retargeting | lapsed_compass_cold | 12,392 | 5,804 | 60 |
| 2026-07-27 | CMP-002 | Warm Escapes Retargeting | lapsed_compass_cold | 1,047 | 537 | 9 |
| 2026-08-03 | CMP-002 | Warm Escapes Retargeting | lapsed_compass_cold | 1,052 | 512 | 3 |
| 2026-08-10 | CMP-002 | Warm Escapes Retargeting | lapsed_compass_cold | 1,049 | 476 | 3 |
| 2026-07-20 | CMP-012 | Fall City Breaks 2026 | urban_explorers | 8,505 | 4,025 | 22 |
| 2026-07-27 | CMP-012 | Fall City Breaks 2026 | urban_explorers | 21,607 | 10,295 | 69 |
| 2026-08-03 | CMP-012 | Fall City Breaks 2026 | urban_explorers | 26,257 | 12,436 | 54 |
| 2026-08-10 | CMP-012 | Fall City Breaks 2026 | urban_explorers | 26,335 | 12,377 | 62 |

By campaign, the story is plain: Warm Escapes Retargeting (CMP-002), the always-on program aimed at `lapsed_compass_cold`, drops to a token keep-alive in the week of July 20, and Fall City Breaks 2026 (CMP-012) starts the same week with the same money. Attributed conversions for CMP-002 go from roughly 100 a week to single digits.

### Warm Escapes Retargeting, daily, the week of the change

```sql
SELECT spend_date, ROUND(SUM(spend_usd)) AS spend_usd, SUM(clicks) AS clicks, SUM(attributed_conversions) AS attributed_conversions
FROM `cymbal_voyages.ad_performance`
WHERE campaign_id = 'CMP-002' AND spend_date BETWEEN DATE '2026-07-20' AND DATE '2026-07-27'
GROUP BY 1 ORDER BY 1
```

| spend_date | spend_usd | clicks | attributed_conversions |
| --- | --- | --- | --- |
| 2026-07-20 | 2,979 | 1,374 | 15 |
| 2026-07-21 | 3,032 | 1,482 | 12 |
| 2026-07-22 | 2,951 | 1,345 | 14 |
| 2026-07-23 | 2,982 | 1,398 | 16 |
| 2026-07-24 | 150 | 65 | 1 |
| 2026-07-25 | 149 | 70 | 0 |
| 2026-07-26 | 149 | 70 | 2 |
| 2026-07-27 | 150 | 73 | 0 |

Daily grain pins the date: July 23 is the last full day, July 24 is the first day at the $150 keep-alive.

### campaign_history: the campaign that took the budget

```sql
SELECT campaign_id, name, target_segment, start_date, end_date, budget_usd, spend_to_date_usd, bookings_attributed, roi
FROM `cymbal_voyages.campaign_history`
WHERE campaign_id IN ('CMP-002', 'CMP-012')
ORDER BY campaign_id
```

| campaign_id | name | target_segment | start_date | end_date | budget_usd | spend_to_date_usd | bookings_attributed | roi |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CMP-002 | Warm Escapes Retargeting | lapsed_compass_cold | 2025-07-01 | 2026-12-31 | 1,500,000 | 1,173,155 | 7,748 | 2.1 |
| CMP-012 | Fall City Breaks 2026 | urban_explorers | 2026-07-24 | 2026-10-31 | 367,800 | 195,281.2 | 640 | 0.1 |

`campaign_history` supplies the context without stating the cause: CMP-012 starts on Jul 24 with a $367,800 budget and has delivered 640 bookings at an ROI of 0.1 through mid-September, and CMP-002's retrospective calls it the most efficient always-on program. Neither retrospective mentions the rotation; that is deliberate, so the date and the money have to be found in `ad_performance`. (The brand corpus brief for Fall City Breaks does state it in its budget section, which the data agent cannot see.)

## What the trail adds up to

1. Warm escapes missed plan by 18.1% in August 2026; nothing else did, and August 2025 was on plan.
2. The gap is entirely in cold-weather markets, spread across all eight of them.
3. Neither the Aug 9 incident (about 65 bookings) nor the Aug 1 price change (about 18 bookings) is more than a few percent of the 701-booking gap.
4. Lapsed Compass members in cold markets browsed warm escapes as much as last year but converted at 2.4% instead of 6.7%; every other cohort converted normally.
5. Their paid-social sessions fell by roughly 90% because Warm Escapes Retargeting was defunded on July 24, 2026 to launch Fall City Breaks; total spend stayed flat so the change is invisible at the top line.

## Later tasks: sizing the audience, learning from creative, dry-running the policy

### The audience in one query

### Audience: lapsed Compass members in cold markets who viewed a warm destination in the last 90 days and did not book

```sql
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
```

| customers | avg_propensity | pct_propensity_ge_030 | pct_propensity_ge_060 | pct_email_contactable |
| --- | --- | --- | --- | --- |
| 3,838 | 0.16 | 8.7 | 2.1 | 85.2 |

"Lapsed Compass members in cold markets who viewed a warm destination in the last 90 days and did not book" resolves to **3,838 customers** from `customer_features` alone (as of Sep 1, 2026; the 90-day window is Jun 3 – Aug 31). A lapsed customer by definition has not booked in 12 months, so "did not book" is implied by `loyalty_status = 'lapsed'`. Average propensity is 0.16 and 8.7% score 0.30 or higher; 85% are email-contactable. Those are the reference scores shipped in the Parquet; after `sql/predict_propensity.sql` replaces them with the BigQuery ML model's scores, the same query returns 3,838 customers, average 0.162 and 10.3% at or above 0.30 (recorded Sep 17, 2026). Lab text should quote whichever state the lab is in at that point.

### Audience variants: how the size and propensity profile move with each filter

```sql
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
```

| variant | customers | avg_propensity | pct_propensity_ge_030 |
| --- | --- | --- | --- |
| A. lapsed (12+ months), any contactability | 3,838 | 0.16 | 8.7 |
| B. A, only email-contactable | 3,271 | 0.16 | 8.6 |
| C. A, lapsed 12-24 months only | 2,242 | 0.19 | 13.5 |
| D. A, lapsed 24+ months only | 1,596 | 0.11 | 2 |
| E. all Compass members in cold markets who browsed warm | 8,152 | 0.19 | 14.9 |
| F. E, dropping anyone who booked in the last 60 days | 6,049 | 0.15 | 9.1 |

Each edit to the segment definition moves both the size and the propensity profile, which is what the lab's audience task needs to show: restricting to email-contactable trims the size and leaves propensity alone; splitting by how long ago they lapsed separates a higher-propensity recently-lapsed group (12–24 months) from a colder long-lapsed group (24+ months); widening to all Compass members in cold markets who browsed warm roughly doubles the audience and raises average propensity because it pulls in active members; dropping recent bookers from that wider set takes it back down.

### Which creative converted this segment

### Creative learning for the segment: conversion by offer framing (lapsed_compass_cold variants, click-weighted)

```sql
SELECT offer_framing, COUNT(*) AS variants, SUM(clicks) AS clicks, SUM(conversions) AS conversions,
       ROUND(100 * SUM(conversions) / SUM(clicks), 2) AS conversion_pct
FROM `cymbal_voyages.creative_variants`
WHERE target_segment = 'lapsed_compass_cold'
GROUP BY 1 ORDER BY conversion_pct DESC
```

| offer_framing | variants | clicks | conversions | conversion_pct |
| --- | --- | --- | --- | --- |
| bonus_points | 13 | 60,531 | 2,881 | 4.76 |
| free_night | 15 | 104,604 | 3,231 | 3.09 |
| no_offer | 19 | 108,597 | 2,682 | 2.47 |
| percent_off | 12 | 85,376 | 1,268 | 1.49 |
| urgency | 9 | 57,141 | 850 | 1.49 |

### Creative learning: conversion by hero imagery style (lapsed_compass_cold)

```sql
SELECT hero_imagery_style, COUNT(*) AS variants, SUM(clicks) AS clicks, SUM(conversions) AS conversions,
       ROUND(100 * SUM(conversions) / SUM(clicks), 2) AS conversion_pct
FROM `cymbal_voyages.creative_variants`
WHERE target_segment = 'lapsed_compass_cold'
GROUP BY 1 ORDER BY conversion_pct DESC
```

| hero_imagery_style | variants | clicks | conversions | conversion_pct |
| --- | --- | --- | --- | --- |
| beach_couple | 15 | 103,957 | 3,626 | 3.49 |
| resort_aerial | 20 | 116,567 | 3,218 | 2.76 |
| family_pool | 8 | 34,719 | 888 | 2.56 |
| city_skyline | 10 | 59,634 | 1,181 | 1.98 |
| adventure | 15 | 101,372 | 1,999 | 1.97 |

### Creative learning: conversion by call-to-action construction (lapsed_compass_cold)

```sql
SELECT cta_construction, COUNT(*) AS variants, SUM(clicks) AS clicks, SUM(conversions) AS conversions,
       ROUND(100 * SUM(conversions) / SUM(clicks), 2) AS conversion_pct
FROM `cymbal_voyages.creative_variants`
WHERE target_segment = 'lapsed_compass_cold'
GROUP BY 1 ORDER BY conversion_pct DESC
```

| cta_construction | variants | clicks | conversions | conversion_pct |
| --- | --- | --- | --- | --- |
| plan_your_escape | 16 | 76,868 | 3,040 | 3.95 |
| book_now | 19 | 130,923 | 3,268 | 2.5 |
| see_deals | 18 | 110,855 | 2,559 | 2.31 |
| claim_offer | 15 | 97,603 | 2,045 | 2.1 |

For `lapsed_compass_cold`, bonus points (4.76%) beat percent-off (1.49%) and urgency (1.49%) by a wide margin; beach-couple imagery (3.49%) leads and city skyline trails; "Plan your escape" (3.95%) is the best call to action and "Claim offer" the worst. Loyalty members respond to recognition, not discounts, which is also what the Winter Sun Early Bird 2025 retrospective in the brand corpus says.

### Creative learning: the same offer framings for the broad all_customers segment (different answer)

```sql
SELECT offer_framing, SUM(clicks) AS clicks, SUM(conversions) AS conversions,
       ROUND(100 * SUM(conversions) / SUM(clicks), 2) AS conversion_pct
FROM `cymbal_voyages.creative_variants`
WHERE target_segment = 'all_customers'
GROUP BY 1 ORDER BY conversion_pct DESC
```

| offer_framing | clicks | conversions | conversion_pct |
| --- | --- | --- | --- |
| percent_off | 127,604 | 2,077 | 1.63 |
| urgency | 39,592 | 609 | 1.54 |
| bonus_points | 35,777 | 529 | 1.48 |
| free_night | 28,222 | 379 | 1.34 |
| no_offer | 18,227 | 211 | 1.16 |

The same table gives a different answer for the broad `all_customers` segment, where percent-off does fine. The learning is segment-specific, which is the point.

### Decisioning dry run

### Decisioning dry run: what the default policy does to the base audience

```sql
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
```

| decision | customers |
| --- | --- |
| hold_for_retargeting (R08) | 2,801 |
| hold_for_retargeting (R06) | 703 |
| send_offer (R03) | 269 |
| hold_for_retargeting (R05) | 31 |
| send_offer (R04) | 20 |
| route_to_loyalty_team (R02) | 14 |

With the default `decisioning_policy` (suppress if booked in the last 60 days; route gold members with propensity ≥ 0.60 to the loyalty team; send an offer at propensity ≥ 0.30 when contactable; otherwise hold for retargeting), most of the base audience is held for retargeting because the score distribution is right-skewed (median about 0.12). Lowering the offer threshold to 0.15 sends offers to roughly a third of the audience; that edit is the natural thing for students to try.

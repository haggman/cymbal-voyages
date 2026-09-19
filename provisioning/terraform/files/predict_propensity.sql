-- Score every customer as of Sep 1, 2026 and write the result into customer_features.propensity_score.
--
-- customer_features ships with a propensity_score already filled by the reference model in
-- generate_warehouse.py, so the lab works before this runs; running it replaces those values with
-- the BigQuery ML model's scores (they agree closely, typically within a few hundredths).
--
-- Replace PROJECT_ID before running.

UPDATE `PROJECT_ID.cymbal_voyages.customer_features` f
SET propensity_score = p.propensity_score
FROM (
  SELECT
    customer_id,
    ROUND((SELECT prob FROM UNNEST(predicted_booked_warm_escape_60d_probs) WHERE label = 1), 4) AS propensity_score
  FROM ML.PREDICT(
    MODEL `PROJECT_ID.cymbal_voyages.warm_escape_propensity`,
    (
      SELECT
        customer_id,
        days_since_last_booking,
        lifetime_bookings,
        loyalty_tier,
        home_market_climate,
        sessions_last_90d,
        warm_views_last_90d,
        email_contactable AS email_optin,
        ltv_band
      FROM `PROJECT_ID.cymbal_voyages.customer_features`
    )
  )
) p
WHERE f.customer_id = p.customer_id;

-- Sanity check: the target audience and its score profile.
SELECT
  COUNT(*) AS customers,
  ROUND(AVG(propensity_score), 3) AS avg_propensity,
  ROUND(100 * COUNTIF(propensity_score >= 0.30) / COUNT(*), 1) AS pct_ge_030
FROM `PROJECT_ID.cymbal_voyages.customer_features`
WHERE home_market_climate = 'cold' AND loyalty_tier != 'none' AND loyalty_status = 'lapsed' AND warm_views_last_90d >= 1;

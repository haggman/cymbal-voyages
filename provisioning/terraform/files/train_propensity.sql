-- Warm-escape propensity model: BigQuery ML logistic regression.
--
-- Label: booked_warm_escape_60d = the customer made a confirmed warm-escape booking in the 60 days
-- after the reference date. Training rows are every customer as the warehouse saw them on
-- Sep 1, 2025 (features computed strictly before the reference date, label strictly after), which
-- is the same season one year before the Sep 1, 2026 snapshot the model scores.
--
-- Replace PROJECT_ID before running, or run with:  bq query --nouse_legacy_sql < sql/train_propensity.sql
-- after `sed -i 's/PROJECT_ID/my-project/g'`.  Record the elapsed time from the job details.

CREATE OR REPLACE MODEL `PROJECT_ID.cymbal_voyages.warm_escape_propensity`
TRANSFORM (
  IFNULL(days_since_last_booking, 9999) AS days_since_last_booking,  -- never-booked customers
  lifetime_bookings,
  loyalty_tier,
  home_market_climate,
  sessions_last_90d,
  warm_views_last_90d,
  IF(email_optin, 1, 0) AS email_optin,
  ltv_band,
  booked_warm_escape_60d
)
OPTIONS (
  model_type = 'LOGISTIC_REG',
  input_label_cols = ['booked_warm_escape_60d'],
  data_split_method = 'RANDOM',
  data_split_eval_fraction = 0.2,
  max_iterations = 20,
  enable_global_explain = TRUE
) AS
SELECT
  days_since_last_booking,
  lifetime_bookings,
  loyalty_tier,
  home_market_climate,
  sessions_last_90d,
  warm_views_last_90d,
  email_optin,
  ltv_band,
  booked_warm_escape_60d
FROM `PROJECT_ID.cymbal_voyages.propensity_training`;

-- Evaluation on the 20% random holdout BigQuery ML set aside. Expect roc_auc in the 0.75–0.80 range
-- (the reference logistic regression in generate_warehouse.py scores 0.78 on a random 20% holdout
-- by customer; see out/_manifest.json).
SELECT * FROM ML.EVALUATE(MODEL `PROJECT_ID.cymbal_voyages.warm_escape_propensity`);

-- Which features matter (global explanation).
SELECT * FROM ML.GLOBAL_EXPLAIN(MODEL `PROJECT_ID.cymbal_voyages.warm_escape_propensity`);

"""
Knobs for the Cymbal Voyages warehouse generator.

Everything that shapes the story lives here. Change a number, re-run `make`, and every table,
the plan, the training set and the schemas regenerate consistently. Nothing else in the package
holds a tunable constant.
"""
from __future__ import annotations

import datetime as dt

# --- Determinism -----------------------------------------------------------------------------
SEED = 20260916  # master seed; every module derives its own stream from this via SeedSequence

# --- Calendar (fixed; the story is a snapshot and must read the same way for a year) ---------
WINDOW_START = dt.date(2025, 7, 1)
WINDOW_END = dt.date(2026, 9, 15)          # inclusive
BURN_IN_START = dt.date(2021, 7, 1)         # simulated but never written: lets loyalty status reach steady state
SNAPSHOT_DATE = dt.date(2026, 9, 1)         # customer_features and segment queries are "as of" this date
ANOMALY_START = dt.date(2026, 7, 24)        # retargeting budget rotated to Fall City Breaks
INCIDENT_DATE = dt.date(2026, 8, 9)         # 4-hour site incident (red herring #1)
INCIDENT_HOURS = (14, 18)                   # UTC, [start, end); 10:00–14:00 US Eastern
PRICE_CHANGE_DATE = dt.date(2026, 8, 1)     # two packages re-priced (red herring #2)

# --- Row counts --------------------------------------------------------------------------------
N_CUSTOMERS = 50_000
N_ANON_SESSIONS = 280_000     # sessions with no customer_id (never convert: you must sign in to book)
KNOWN_SESSION_TARGET = 470_000  # expected known sessions; the activity model is scaled to hit this
N_CREATIVE_VARIANTS = 200
# Training set for the propensity model: every customer as the warehouse saw them on the reference
# date, labeled by whether they booked a warm escape in the following LABEL_WINDOW_DAYS. The model is
# used on SNAPSHOT_DATE (Sep 1, 2026) to build a fall audience and the feature list carries no
# season signal, so the reference date is the same date one year earlier. A second, earlier date can
# be added here (rows per date) to grow the table; each date contributes an honest forward label.
TRAINING_REF_DATES = {dt.date(2025, 9, 1): 50_000}
TRAINING_HOLDOUT_SHARE = 0.20  # random holdout by customer for the reported AUC
LABEL_WINDOW_DAYS = 60

# --- Story knobs -------------------------------------------------------------------------------
# Multiplier applied to the booking probability of the target cohort (lapsed Compass members in
# cold-weather markets browsing warm escapes) for sessions dated on/after ANOMALY_START.
# 0.42 takes their tracked conversion from ~6% to ~2.5%.
ANOMALY_FACTOR = 0.36
# How much the always-on retargeting historically lifted that cohort's warm-escape conversion.
RETARGETING_LIFT = 1.08
# Share of bookings completed inside a tracked web session (the rest complete in the app or by
# phone within two days of a browse session and carry no session_id).
TRACKED_SHARE = 0.40
# Cohort paid-social share of sessions before / after the budget rotation.
COHORT_PAID_SOCIAL_SHARE = (0.24, 0.03)
# Cohort browsing multiplier in the anomaly window ("intent flat to slightly up").
COHORT_INTENT_DRIFT = 0.87
# Price red herring: multiplier on the two re-priced packages' booking odds after PRICE_CHANGE_DATE.
PRICE_HERRING_PACKAGES = ("PKG-0032", "PKG-0057")
PRICE_HERRING_INCREASE = 0.12
PRICE_HERRING_DEMAND = 0.78
# Plan noise: plan = baseline * N(1, PLAN_JITTER) so on-plan cells read as +/- a few percent.
PLAN_JITTER = 0.025
CANCEL_RATE = 0.08

# --- Markets -----------------------------------------------------------------------------------
# (name, climate, relative population weight)
MARKETS = [
    ("Chicago", "cold", 3.0), ("Boston", "cold", 2.0), ("Minneapolis", "cold", 1.5),
    ("Detroit", "cold", 1.5), ("Denver", "cold", 1.6), ("Toronto", "cold", 2.4),
    ("Cleveland", "cold", 1.0), ("Milwaukee", "cold", 0.8),
    ("Miami", "warm", 1.6), ("Phoenix", "warm", 1.4), ("Houston", "warm", 1.6),
    ("Los Angeles", "warm", 2.4), ("San Diego", "warm", 1.0),
    ("New York", "mild", 4.0), ("Philadelphia", "mild", 1.4), ("Washington DC", "mild", 1.6),
    ("Atlanta", "mild", 1.5), ("Dallas", "mild", 1.5), ("Seattle", "mild", 1.4),
    ("Portland", "mild", 0.8), ("San Francisco", "mild", 1.6), ("Nashville", "mild", 0.8),
    ("Charlotte", "mild", 0.8), ("Vancouver", "mild", 1.0), ("Raleigh", "mild", 0.6),
]
CLIMATE_SHARE = {"cold": 0.53, "mild": 0.29, "warm": 0.18}

# --- Loyalty -----------------------------------------------------------------------------------
TIER_SHARE = {"none": 0.30, "blue": 0.38, "silver": 0.20, "gold": 0.12}
EMAIL_OPTIN = {"member": 0.85, "nonmember": 0.55}
SMS_OPTIN = {"member": 0.35, "nonmember": 0.15}

# --- Seasonality (index 0 = January) --------------------------------------------------------------
# Browsing intensity by home-market climate.
SESSION_SEASON = {
    "cold": [1.35, 1.10, 0.90, 0.70, 0.60, 0.70, 0.90, 1.60, 1.55, 1.30, 1.10, 1.00],
    "mild": [1.80, 1.50, 1.40, 1.25, 1.20, 1.20, 1.35, 1.90, 1.90, 1.65, 1.50, 1.50],
    "warm": [1.40, 1.35, 1.40, 1.40, 1.40, 1.45, 1.45, 1.40, 1.35, 1.35, 1.35, 1.40],
}
# What people look at, by category and month (relative interest).
CATEGORY_SEASON = {
    "warm_escape": [1.40, 1.10, 0.70, 0.50, 0.40, 0.45, 0.80, 1.60, 1.70, 1.50, 1.30, 1.20],
    "city_break":  [0.80, 0.90, 1.20, 1.30, 1.20, 1.00, 0.90, 1.00, 1.30, 1.30, 0.90, 0.80],
    "ski":         [1.30, 1.10, 0.70, 0.30, 0.20, 0.20, 0.30, 0.60, 1.00, 1.40, 1.50, 1.40],
    "adventure":   [0.90, 1.10, 1.30, 1.30, 1.20, 1.00, 0.90, 0.80, 0.80, 0.80, 0.80, 0.80],
    "cruise":      [1.60, 1.50, 1.30, 0.90, 0.80, 0.70, 0.70, 0.80, 0.90, 1.00, 1.10, 1.30],
}
# Interest in each category by climate (before seasonality).
CATEGORY_AFFINITY = {
    "cold": {"warm_escape": 1.00, "city_break": 0.45, "ski": 0.35, "adventure": 0.30, "cruise": 0.35},
    "mild": {"warm_escape": 2.00, "city_break": 0.55, "ski": 0.25, "adventure": 0.35, "cruise": 0.35},
    "warm": {"warm_escape": 1.20, "city_break": 0.60, "ski": 0.30, "adventure": 0.40, "cruise": 0.40},
}
# Per-session booking odds by category (before status/tier/season/latent multipliers).
BOOK_BASE = {"warm_escape": 0.135, "city_break": 0.170, "ski": 0.180, "adventure": 0.135, "cruise": 0.145}
BOOK_SEASON = {  # booking (not browsing) seasonality by category
    "warm_escape": [1.15, 1.00, 0.80, 0.70, 0.65, 0.70, 0.85, 1.20, 1.25, 1.20, 1.15, 1.10],
    "city_break":  [0.90, 0.95, 1.10, 1.15, 1.10, 1.00, 0.95, 1.00, 1.15, 1.10, 0.90, 0.85],
    "ski":         [1.10, 1.00, 0.80, 0.60, 0.50, 0.50, 0.60, 0.80, 1.00, 1.20, 1.25, 1.15],
    "adventure":   [1.00, 1.05, 1.10, 1.10, 1.05, 1.00, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95],
    "cruise":      [1.25, 1.20, 1.10, 0.95, 0.90, 0.85, 0.85, 0.90, 0.95, 1.00, 1.05, 1.15],
}
# Month-of-year weights for customers' most recent booking before the window opens (index 0 = January).
PRIOR_BOOKING_SEASON = [1.4, 1.0, 0.8, 0.6, 0.5, 0.5, 0.6, 1.6, 1.6, 1.4, 1.1, 1.0]
# Intent: each warm-escape view in the previous three months raises warm-escape booking odds by this
# fraction (capped at INTENT_CAP views). This is what makes warm_views_last_90d predictive.
INTENT_BOOST = 0.30
INTENT_CAP = 6
ACTIVITY_SIGMA = 1.2      # spread of per-customer browsing intensity (lognormal sigma)
BOOK_LATENT_SIGMA = 0.15  # spread of the unobserved booking trait (lognormal sigma)
# Warm-escape booking odds multiplier for customers outside the target cohort, by climate. Sets the
# cohort's share of cold-market warm bookings (and so the depth of the cold-market miss) and the
# cold markets' share of the category (and so the overall miss).
WARM_BOOK_MULT_NONCOHORT = {"cold": 1.45, "mild": 1.75, "warm": 1.85}
STATUS_SESSION_MULT = {"active": 0.35, "lapsed": 1.00, "never": 0.45}
STATUS_BOOK_MULT = {"active": 0.85, "lapsed": 0.70, "never": 0.45}
TIER_SESSION_MULT = {"none": 0.80, "blue": 1.00, "silver": 1.15, "gold": 1.30}
TIER_BOOK_MULT = {"none": 0.80, "blue": 1.00, "silver": 1.10, "gold": 1.20}
# Extra browsing lift for the cohort by month (index 0 = January): lapsed cold-market members are the
# warm-escape season's core shoppers, so their browsing swells from late summer.
COHORT_SEASON_LIFT = [1.3, 1.0, 1.0, 1.0, 1.0, 3.8, 5.5, 3.8, 3.4, 2.2, 1.5, 1.1]

# --- Channels --------------------------------------------------------------------------------------
CHANNELS = ["paid_search", "paid_social", "organic", "email", "direct", "affiliate"]
KNOWN_CHANNEL_MIX = {"paid_search": 0.14, "paid_social": 0.11, "organic": 0.24, "email": 0.19, "direct": 0.27, "affiliate": 0.05}
ANON_CHANNEL_MIX = {"paid_search": 0.26, "paid_social": 0.16, "organic": 0.34, "email": 0.04, "direct": 0.12, "affiliate": 0.08}
DEVICE_MIX = {"mobile": 0.58, "desktop": 0.36, "tablet": 0.06}
UNTRACKED_BOOKING_CHANNEL_MIX = {"direct": 0.45, "email": 0.25, "organic": 0.15, "paid_search": 0.08, "paid_social": 0.05, "affiliate": 0.02}
# Diurnal profile for session timestamps (UTC hour weights, 0..23).
HOUR_WEIGHTS = [1.2, 0.8, 0.5, 0.3, 0.2, 0.2, 0.3, 0.5, 0.8, 1.1, 1.4, 1.7, 2.0, 2.1, 2.2, 2.1, 2.0, 1.9, 1.8, 1.9, 2.1, 2.3, 2.2, 1.7]
TRAVELERS_MIX = {1: 0.28, 2: 0.56, 3: 0.08, 4: 0.08}
LEAD_DAYS = {"warm_escape": (120, 45), "city_break": (45, 25), "ski": (90, 40), "adventure": (120, 50), "cruise": (150, 60)}

# --- Paid media economics (per channel) ----------------------------------------------------------------
CPC = {"paid_search": 1.60, "paid_social": 2.10, "affiliate": 0.60}
CTR = {"paid_search": 0.040, "paid_social": 0.011, "affiliate": 0.020}
ALWAYS_ON_CVR = {"CMP-001": 0.006, "CMP-002": 0.010, "CMP-010": 0.0025}
RETARGETING_KEEPALIVE_USD = 150.0   # what CMP-002 spends per day after the rotation
RETARGETING_SEASON = [1.10, 0.90, 0.90, 0.60, 0.60, 0.60, 1.00, 1.30, 1.30, 1.30, 1.30, 1.10]
CONTRIBUTION_MARGIN = 0.22
PAID_ATTRIBUTION_SHARE = 0.75   # share of a campaign's attributed bookings that come through its paid channel (rest: email)

# --- Decisioning policy defaults ---------------------------------------------------------------------
# Rules are evaluated in ascending priority; the first enabled rule whose condition(s) hold wins.
# A rule has one required condition (feature/operator/threshold) and one optional second
# condition (feature_2/operator_2/threshold_2) that is ANDed with the first. Thresholds are
# strings so one column can hold 60, 0.30 or 'gold'.
POLICY_RULES = [
    # rule_id, priority, feature, operator, threshold, feature_2, operator_2, threshold_2, action, reason_template, enabled
    ("R01", 10, "days_since_last_booking", "<=", "60", None, None, None, "suppress",
     "Booked {days_since_last_booking} days ago; too soon to market to again.", True),
    ("R02", 20, "loyalty_tier", "==", "gold", "propensity_score", ">=", "0.60", "route_to_loyalty_team",
     "Gold member with propensity {propensity_score:.2f}; personal outreach from the loyalty team.", True),
    ("R03", 30, "propensity_score", ">=", "0.30", "email_contactable", "==", "true", "send_offer",
     "Propensity {propensity_score:.2f} clears the offer threshold and the customer accepts email.", True),
    ("R04", 40, "propensity_score", ">=", "0.30", "sms_contactable", "==", "true", "send_offer",
     "Propensity {propensity_score:.2f} clears the offer threshold and the customer accepts SMS.", True),
    ("R05", 50, "propensity_score", ">=", "0.30", None, None, None, "hold_for_retargeting",
     "Propensity {propensity_score:.2f} clears the offer threshold but the customer is not contactable; reach through paid retargeting.", True),
    ("R06", 60, "warm_views_last_90d", ">=", "3", None, None, None, "hold_for_retargeting",
     "Browsed warm escapes {warm_views_last_90d} times in 90 days; keep in the retargeting pool.", True),
    ("R07", 70, "loyalty_status", "==", "never", None, None, None, "suppress",
     "Never booked; excluded from win-back offers (rule disabled by default).", False),
    ("R08", 99, "propensity_score", ">=", "0", None, None, None, "hold_for_retargeting",
     "Default: no other rule matched; hold in the retargeting pool.", True),
]

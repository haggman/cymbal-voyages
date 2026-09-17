"""Customers with latent traits and a pre-window booking history (needed for loyalty status)."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from . import config as C


def build_customers(rng: np.random.Generator) -> pd.DataFrame:
    n = C.N_CUSTOMERS
    climates = [m[1] for m in C.MARKETS]
    # market weights: population weight scaled so each climate hits its share
    w = np.array([m[2] for m in C.MARKETS], dtype=float)
    for cl, share in C.CLIMATE_SHARE.items():
        mask = np.array([c == cl for c in climates])
        w[mask] = w[mask] / w[mask].sum() * share
    market_idx = rng.choice(len(C.MARKETS), size=n, p=w / w.sum())
    market = np.array([C.MARKETS[i][0] for i in market_idx])
    climate = np.array([C.MARKETS[i][1] for i in market_idx])

    tiers = np.array(list(C.TIER_SHARE))
    tier = rng.choice(tiers, size=n, p=list(C.TIER_SHARE.values()))
    member = tier != "none"

    # signup: 10% inside the window, the rest 2018–Jun 2025 with more weight on recent years
    days_before = rng.gamma(shape=2.0, scale=800, size=n).astype(int) + 45
    signup = np.array([C.WINDOW_START - dt.timedelta(days=int(d)) for d in days_before], dtype="object")
    in_window = rng.random(n) < 0.10
    win_days = (C.WINDOW_END - C.WINDOW_START).days
    for i in np.where(in_window)[0]:
        signup[i] = C.WINDOW_START + dt.timedelta(days=int(rng.integers(0, win_days - 14)))
    signup = np.array([min(s, dt.date(2026, 8, 31)) for s in signup], dtype="object")
    signup = np.array([max(s, dt.date(2018, 1, 1)) for s in signup], dtype="object")

    # pre-window lifetime bookings, by tier; nobody who signed up inside the window has any
    pre = np.zeros(n, dtype=int)
    for t, (p_zero, lam, floor) in {"none": (0.50, 0.8, 1), "blue": (0.25, 1.0, 1),
                                    "silver": (0.0, 1.5, 4), "gold": (0.0, 3.0, 8)}.items():
        m = tier == t
        k = m.sum()
        has = rng.random(k) >= p_zero
        pre[m] = np.where(has, floor + rng.poisson(lam, size=k), 0)
    pre[in_window] = 0
    # tenure cap: no more than ~one booking per 4 months of tenure
    tenure_months = np.maximum(1, days_before // 30)
    pre = np.minimum(pre, np.maximum(1, tenure_months // 4)) * (pre > 0)
    # silver and gold are earned by booking; anyone at those tiers with no history is really blue
    tier = np.where(np.isin(tier, ["silver", "gold"]) & (pre == 0), "blue", tier)
    member = tier != "none"

    # last pre-window booking: mixture of recent (active) and older (lapsed) so ~55% of cold-market
    # members who ever booked are lapsed when the window opens
    activity = rng.lognormal(0.0, C.ACTIVITY_SIGMA, size=n)
    p_recent = np.clip(0.17 * activity ** 0.6, 0.04, 0.80)  # heavy browsers are rarely lapsed
    # bookings cluster in the warm-escape season (Aug–Jan), so lapse anniversaries do too
    season_w = np.array(C.PRIOR_BOOKING_SEASON, dtype=float)  # index 0 = January
    def seasonal_ago(size: int, years_back: int) -> np.ndarray:
        month = rng.choice(12, size=size, p=season_w / season_w.sum())  # 0..11
        day = rng.integers(1, 28, size=size)
        out = np.empty(size, dtype=int)
        for i in range(size):
            y = C.WINDOW_START.year
            d = dt.date(y, month[i] + 1, int(day[i]))
            if d >= C.WINDOW_START - dt.timedelta(days=20):
                d = d.replace(year=y - 1)
            out[i] = (C.WINDOW_START - d).days + 365 * years_back
        return out
    r = rng.random(n)
    ago = np.where(r < p_recent, seasonal_ago(n, 0),
                   np.where(rng.random(n) < 0.7, seasonal_ago(n, 1), seasonal_ago(n, 2)))
    ago = np.minimum(ago, days_before - 10)
    last_pre = np.array([C.WINDOW_START - dt.timedelta(days=int(a)) if b > 0 else None
                         for a, b in zip(ago, pre)], dtype="object")
    first_ago = np.minimum(days_before - 5, ago + rng.integers(0, 900, size=n) * (pre > 1))
    first_pre = np.array([C.WINDOW_START - dt.timedelta(days=int(a)) if b > 0 else None
                          for a, b in zip(first_ago, pre)], dtype="object")

    avg_rev = rng.normal(1900, 350, size=n).clip(600, 4500)
    ltv_pre = np.round(pre * avg_rev * rng.uniform(0.85, 1.15, size=n), 2)

    email = np.where(member, rng.random(n) < C.EMAIL_OPTIN["member"], rng.random(n) < C.EMAIL_OPTIN["nonmember"])
    sms = np.where(member, rng.random(n) < C.SMS_OPTIN["member"], rng.random(n) < C.SMS_OPTIN["nonmember"])

    df = pd.DataFrame({
        "customer_id": [f"C{i:06d}" for i in range(1, n + 1)],
        "signup_date": signup,
        "home_market": market,
        "home_market_climate": climate,
        "loyalty_tier": tier,
        "email_optin": email,
        "sms_optin": sms,
        # latent traits (never exported)
        "_activity": activity,
        "_book_latent": rng.lognormal(0.0, C.BOOK_LATENT_SIGMA, size=n),
        "_pre_bookings": pre,
        "_last_pre_booking": last_pre,
        "_first_pre_booking": first_pre,
        "_ltv_pre": ltv_pre,
    })
    # per-customer category interest: climate affinity with individual noise
    for cat in C.CATEGORY_SEASON:
        base = np.array([C.CATEGORY_AFFINITY[c][cat] for c in climate])
        df[f"_aff_{cat}"] = base * rng.lognormal(0.0, 0.5, size=n)
    return df

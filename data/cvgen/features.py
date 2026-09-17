"""Plan, customer_features (as of SNAPSHOT_DATE), the propensity training set, and a local reference model."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from . import config as C
from .activity import EPOCH, CATS

LTV_BANDS = [(0, "none"), (1, "low"), (1500, "mid"), (5000, "high"), (12000, "vip")]  # lower bound, band


def ltv_band(ltv: np.ndarray) -> np.ndarray:
    out = np.full(len(ltv), "none", dtype=object)
    for lo, name in LTV_BANDS:
        out[ltv >= lo] = name
    return out


def build_plan(baseline: pd.DataFrame, bookings: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    months = sorted(baseline["plan_month"].unique())
    markets = [m[0] for m in C.MARKETS]
    grid = pd.MultiIndex.from_product([months, CATS, markets], names=["plan_month", "category", "market"]).to_frame(index=False)
    counts = baseline.groupby(["plan_month", "category", "market"]).size().rename("base").reset_index()
    plan = grid.merge(counts, how="left").fillna({"base": 0})
    # September is a 15-day snapshot; the plan is for the whole month
    sep = plan["plan_month"] == dt.date(2026, 9, 1)
    plan.loc[sep, "base"] = plan.loc[sep, "base"] * 30 / 15
    conf = bookings[bookings["status"] == "confirmed"]
    avg_rev = conf.groupby("category")["revenue_usd"].mean()
    plan["planned_bookings"] = np.maximum(0, np.round(plan["base"] * rng.normal(1.0, C.PLAN_JITTER, size=len(plan)))).astype(int)
    plan["planned_revenue_usd"] = np.round(plan["planned_bookings"] * plan["category"].map(avg_rev) * rng.normal(1.0, 0.02, size=len(plan)), 2)
    return plan[["plan_month", "category", "market", "planned_bookings", "planned_revenue_usd"]]


def _window_counts(sess: pd.DataFrame, start: dt.date, end_excl: dt.date) -> pd.DataFrame:
    lo, hi = (start - EPOCH).days, (end_excl - EPOCH).days
    s = sess[(sess["session_date_ord"] >= lo) & (sess["session_date_ord"] < hi) & sess["customer_id"].notna()]
    g = s.groupby("customer_id").agg(sessions=("session_date_ord", "size"), warm_views=("viewed_warm_escape", "sum"),
                                     last_session_ord=("session_date_ord", "max"))
    return g


def build_customer_features(cust: pd.DataFrame, sess: pd.DataFrame, bookings: pd.DataFrame,
                            status_hist: pd.DataFrame) -> pd.DataFrame:
    snap = C.SNAPSHOT_DATE
    st = status_hist[status_hist["status_month"] == snap.replace(day=1)].set_index("customer_id")
    conf = bookings[bookings["status"] == "confirmed"]
    before = conf[conf["booking_date"] < snap]
    ltv_window = before.groupby("customer_id")["revenue_usd"].sum()
    ltv = cust.set_index("customer_id")["_ltv_pre"].add(ltv_window, fill_value=0.0)
    last_booking = before.groupby("customer_id")["booking_date"].max()
    active_res = conf[conf["travel_start_date"] >= snap].groupby("customer_id").size()
    w = _window_counts(sess, snap - dt.timedelta(days=90), snap)
    all_sess = sess[sess["customer_id"].notna()].groupby("customer_id")["session_date_ord"].max()

    df = cust[["customer_id", "loyalty_tier", "home_market_climate", "email_optin", "sms_optin"]].copy()
    df = df.set_index("customer_id")
    df["loyalty_status"] = st["loyalty_status"]
    dsl = st["days_since_last_booking"]
    df["days_since_last_booking"] = dsl.astype("Int64")
    df["last_booking_date"] = [ (snap - dt.timedelta(days=int(d))) if pd.notna(d) else None for d in dsl.reindex(df.index)]
    df["lifetime_bookings"] = st["lifetime_bookings_to_date"].astype(int)
    df["lifetime_value_usd"] = np.round(ltv.reindex(df.index).fillna(0.0), 2)
    df["ltv_band"] = ltv_band(df["lifetime_value_usd"].to_numpy())
    df["booked_last_60d"] = (dsl.reindex(df.index).fillna(99999) <= 60)
    df["has_active_reservation"] = active_res.reindex(df.index).fillna(0).astype(int) > 0
    df["sessions_last_90d"] = w["sessions"].reindex(df.index).fillna(0).astype(int)
    df["warm_views_last_90d"] = w["warm_views"].reindex(df.index).fillna(0).astype(int)
    last_sess = all_sess.reindex(df.index)
    days_since_sess = (snap - EPOCH).days - last_sess
    eng = 0.6 * (1 - np.exp(-0.35 * df["sessions_last_90d"])) + 0.4 * np.exp(-days_since_sess.fillna(9999) / 45.0)
    df["recent_engagement_score"] = np.round(eng.clip(0, 1), 3)
    df["email_contactable"] = df.pop("email_optin")
    df["sms_contactable"] = df.pop("sms_optin")
    df["as_of_date"] = snap
    return df.reset_index()


def build_training_set(cust: pd.DataFrame, sess: pd.DataFrame, bookings: pd.DataFrame,
                       status_hist: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    conf = bookings[bookings["status"] == "confirmed"]
    warm = conf[conf["category"] == "warm_escape"]
    base = cust.set_index("customer_id")
    parts = []
    for ref, n_rows in C.TRAINING_REF_DATES.items():
        ids = rng.choice(cust["customer_id"].to_numpy(), size=n_rows, replace=False)
        st = status_hist[status_hist["status_month"] == ref.replace(day=1)].set_index("customer_id").reindex(ids)
        w = _window_counts(sess, ref - dt.timedelta(days=90), ref).reindex(ids)
        ltv_w = conf[conf["booking_date"] < ref].groupby("customer_id")["revenue_usd"].sum().reindex(ids).fillna(0.0)
        ltv = base.loc[ids, "_ltv_pre"].to_numpy() + ltv_w.to_numpy()
        lab_end = ref + dt.timedelta(days=C.LABEL_WINDOW_DAYS)
        booked = warm[(warm["booking_date"] >= ref) & (warm["booking_date"] < lab_end)]["customer_id"].unique()
        parts.append(pd.DataFrame({
            "reference_date": ref, "customer_id": ids,
            "days_since_last_booking": st["days_since_last_booking"].to_numpy(),
            "lifetime_bookings": st["lifetime_bookings_to_date"].to_numpy().astype(int),
            "loyalty_tier": base.loc[ids, "loyalty_tier"].to_numpy(),
            "home_market_climate": base.loc[ids, "home_market_climate"].to_numpy(),
            "sessions_last_90d": w["sessions"].fillna(0).to_numpy().astype(int),
            "warm_views_last_90d": w["warm_views"].fillna(0).to_numpy().astype(int),
            "email_optin": base.loc[ids, "email_optin"].to_numpy(),
            "ltv_band": ltv_band(ltv),
            "booked_warm_escape_60d": np.isin(ids, booked).astype(int),
        }))
    df = pd.concat(parts, ignore_index=True)
    df["days_since_last_booking"] = df["days_since_last_booking"].astype("Int64")
    return df


FEATURES_NUM = ["days_since_last_booking", "lifetime_bookings", "sessions_last_90d", "warm_views_last_90d", "email_optin"]
FEATURES_CAT = ["loyalty_tier", "home_market_climate", "ltv_band"]


def _design(df: pd.DataFrame) -> pd.DataFrame:
    X = pd.DataFrame(index=df.index)
    X["days_since_last_booking"] = df["days_since_last_booking"].astype(float).fillna(9999.0)
    X["lifetime_bookings"] = df["lifetime_bookings"].astype(float)
    X["sessions_last_90d"] = df["sessions_last_90d"].astype(float)
    X["warm_views_last_90d"] = df["warm_views_last_90d"].astype(float)
    X["email_optin"] = df["email_optin"].astype(float)
    for col, levels in (("loyalty_tier", ["none", "blue", "silver", "gold"]),
                        ("home_market_climate", ["cold", "mild", "warm"]),
                        ("ltv_band", ["none", "low", "mid", "high", "vip"])):
        for lv in levels[1:]:
            X[f"{col}_{lv}"] = (df[col] == lv).astype(float)
    return X


def fit_reference_model(train: pd.DataFrame):
    """A local logistic regression on the shipped training set: gives the parquet a propensity_score
    before BigQuery ML runs, and an AUC estimate the BQML model should land near."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score, log_loss
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    y = train["booked_warm_escape_60d"].to_numpy()
    X = _design(train)
    # random holdout by customer (so the same person is never on both sides)
    cid = train["customer_id"].str.slice(1).astype(int).to_numpy()
    holdout = ((cid * 2654435761) % 1000) < int(C.TRAINING_HOLDOUT_SHARE * 1000)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0))
    model.fit(X[~holdout], y[~holdout])
    p = model.predict_proba(X[holdout])[:, 1]
    metrics = {"holdout_auc": round(float(roc_auc_score(y[holdout], p)), 4),
               "holdout_log_loss": round(float(log_loss(y[holdout], p)), 4),
               "positive_rate": round(float(y.mean()), 4), "rows": int(len(train)),
               "holdout": f"random {int(C.TRAINING_HOLDOUT_SHARE*100)}% of customers"}
    model.fit(X, y)  # refit on everything for scoring
    return model, metrics


def score(model, features: pd.DataFrame) -> np.ndarray:
    df = features.rename(columns={"email_contactable": "email_optin"})
    return np.round(model.predict_proba(_design(df))[:, 1], 4)

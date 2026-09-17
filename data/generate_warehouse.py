#!/usr/bin/env python3
"""
Generate the Cymbal Voyages warehouse (mkt016 "From Question to Campaign").

    python3 generate_warehouse.py            # writes out/<table>/part-*.parquet, schemas/*.json, out/_manifest.json

Deterministic: everything derives from cvgen.config.SEED. Knobs (row counts, anomaly depth, calendar)
live in cvgen/config.py. Runs in about a minute on a laptop.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from cvgen import config as C
from cvgen import activity, ads, catalog, customers, features, schemas, writer

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
SCHEMA_DIR = ROOT / "schemas"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main() -> int:
    t0 = time.time()
    ss = np.random.SeedSequence(C.SEED)
    r_cust, r_cat, r_act, r_anon, r_ads, r_creative, r_plan, r_train = [np.random.default_rng(s) for s in ss.spawn(8)]
    OUT.mkdir(exist_ok=True)
    manifest = {"seed": C.SEED, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "window": [C.WINDOW_START.isoformat(), C.WINDOW_END.isoformat()], "snapshot_date": C.SNAPSHOT_DATE.isoformat(),
                "anomaly_start": C.ANOMALY_START.isoformat(), "anomaly_factor": C.ANOMALY_FACTOR, "tables": {}}

    log("customers")
    cust = customers.build_customers(r_cust)
    log("catalog")
    dest = catalog.load_destinations()
    pkg = catalog.build_packages(dest, r_cat)

    log("simulating sessions and bookings (with burn-in)")
    known, bookings, baseline, status_hist, final_state, incident_lost_known = activity.simulate(cust, dest, pkg, r_act)
    log(f"  known sessions {len(known):,}  bookings {len(bookings):,}")
    anon = activity.anonymous_sessions(known, dest, r_anon)
    sessions, bookings = activity.finalize_sessions_and_bookings(known, anon, bookings)
    log(f"  total sessions {len(sessions):,}  (anonymous {len(anon):,})")

    # customers: loyalty fields as of the end of the window
    last = final_state.set_index("customer_id")
    cust_out = cust[["customer_id", "signup_date", "home_market", "home_market_climate", "loyalty_tier", "email_optin", "sms_optin"]].copy()
    lb = last["last_booking_ord"].reindex(cust_out["customer_id"]).to_numpy()
    cust_out["last_booking_date"] = [dt.date.fromordinal(int(o) + activity.EPOCH.toordinal()) if o >= 0 else None for o in lb]
    cust_out["lifetime_bookings"] = last["lifetime_bookings"].reindex(cust_out["customer_id"]).to_numpy()
    cust_out["lifetime_value_usd"] = last["lifetime_value_usd"].reindex(cust_out["customer_id"]).to_numpy()
    end_ord = (C.WINDOW_END - activity.EPOCH).days
    days = np.where(lb >= 0, end_ord - lb, -1)
    cust_out["loyalty_status"] = np.where(cust_out["lifetime_bookings"] == 0, "never", np.where(days >= 365, "lapsed", "active"))

    log("plan")
    plan = features.build_plan(baseline, bookings, r_plan)

    log("ads, campaigns, creative")
    camps, _segments = ads.load_campaigns()
    ad_perf = ads.build_ad_performance(camps, r_ads)
    avg_rev = float(bookings.loc[bookings["status"] == "confirmed", "revenue_usd"].mean())
    camp_hist = ads.build_campaign_history(camps, ad_perf, avg_rev)
    creative = ads.build_creative_variants(camps, r_creative)

    log("customer features and training set")
    feats = features.build_customer_features(cust, known, bookings, status_hist)
    train = features.build_training_set(cust, known, bookings, status_hist, r_train)
    model, metrics = features.fit_reference_model(train)
    feats["propensity_score"] = features.score(model, feats)
    log(f"  reference model: {metrics}")

    policy = pd.DataFrame(C.POLICY_RULES, columns=["rule_id", "priority", "feature", "operator", "threshold", "feature_2",
                                                   "operator_2", "threshold_2", "action", "reason_template", "enabled"])
    activations = pd.DataFrame({"receipt_id": pd.Series(dtype="object"), "segment_description": pd.Series(dtype="object"),
                                "audience_size": pd.Series(dtype="int64"), "channel": pd.Series(dtype="object"),
                                "submitted_at": pd.Series(dtype="datetime64[us]"), "status": pd.Series(dtype="object")})

    status_out = status_hist.copy()
    status_out["days_since_last_booking"] = status_out["days_since_last_booking"].astype("Int64")

    log("writing parquet")
    tables = {
        "customers": cust_out, "destinations": dest, "packages": pkg, "web_sessions": sessions, "bookings": bookings,
        "ad_performance": ad_perf, "plan": plan, "campaign_history": camp_hist, "creative_variants": creative,
        "customer_month_status": status_out, "customer_features": feats, "propensity_training": train,
        "decisioning_policy": policy, "activations": activations,
    }
    for name, df in tables.items():
        paths = writer.write_table(df, name, OUT)
        size = sum(p.stat().st_size for p in paths)
        manifest["tables"][name] = {"rows": int(len(df)), "parts": len(paths), "bytes": int(size)}
        log(f"  {name:<24} {len(df):>9,} rows  {size/1e6:6.1f} MB  {len(paths)} part(s)")
    schemas.write_schemas(SCHEMA_DIR)
    manifest["reference_model"] = metrics
    manifest["incident_sessions_removed"] = int(incident_lost_known) + int(manifest.get("incident_anon", 0))
    manifest["elapsed_seconds"] = round(time.time() - t0, 1)
    (OUT / "_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    log(f"done in {manifest['elapsed_seconds']}s; total {sum(t['bytes'] for t in manifest['tables'].values())/1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

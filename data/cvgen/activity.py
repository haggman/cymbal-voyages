"""
Month-by-month simulation of known-customer web sessions and the bookings they lead to.

The story lives here. Each month, every customer's loyalty status is read from their booking
history, that status (plus climate, tier, season and two latent traits) sets how much they browse
and how likely a warm-escape session is to become a booking, and the target cohort — lapsed
Compass members in cold-weather markets browsing warm escapes — gets its conversion multiplied
by ANOMALY_FACTOR for sessions on/after ANOMALY_START. The same uniform draw is compared against
the pre-anomaly probability to count "baseline" bookings, which become the plan.
"""
from __future__ import annotations

import calendar
import datetime as dt

import numpy as np
import pandas as pd

from . import config as C

CATS = list(C.CATEGORY_SEASON)
EPOCH = dt.date(1970, 1, 1)


def months_in_window(start: dt.date | None = None) -> list[tuple[dt.date, int]]:
    out = []
    start = start or C.WINDOW_START
    d = start.replace(day=1)
    while d <= C.WINDOW_END:
        last = dt.date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])
        first = max(d, start)
        end = min(last, C.WINDOW_END)
        out.append((first, (end - first).days + 1))
        d = (last + dt.timedelta(days=1))
    return out


def _to_ord(dates) -> np.ndarray:
    return np.array([(x - EPOCH).days if x is not None else -1 for x in dates], dtype=np.int64)


def _status(last_ord: np.ndarray, lifetime: np.ndarray, ms_ord: int) -> tuple[np.ndarray, np.ndarray]:
    days = np.where(last_ord >= 0, ms_ord - last_ord, -1)
    status = np.where(lifetime == 0, "never", np.where(days >= 365, "lapsed", "active")).astype(object)
    return status, days


def _weighted_pick(rng, pool_ids: np.ndarray, pool_w: np.ndarray, size: int) -> np.ndarray:
    return rng.choice(pool_ids, size=size, p=pool_w / pool_w.sum())


def simulate(cust: pd.DataFrame, dest: pd.DataFrame, pkg: pd.DataFrame, rng: np.random.Generator):
    n = len(cust)
    climate = cust["home_market_climate"].to_numpy()
    market = cust["home_market"].to_numpy()
    tier = cust["loyalty_tier"].to_numpy()
    member = tier != "none"
    activity = cust["_activity"].to_numpy()
    book_latent = cust["_book_latent"].to_numpy()
    aff = np.stack([cust[f"_aff_{c}"].to_numpy() for c in CATS], axis=1)  # n x 5

    signup_ord = _to_ord(cust["signup_date"])
    last_ord = _to_ord(cust["_last_pre_booking"])
    lifetime = cust["_pre_bookings"].to_numpy().copy()
    ltv = cust["_ltv_pre"].to_numpy().copy()

    # catalog pools
    dest_by_cat = {c: dest.index[dest["category"] == c].to_numpy() for c in CATS}
    dest_w = rng.lognormal(0.0, 0.5, size=len(dest))
    dest_ids = dest["destination_id"].to_numpy()
    dest_cat = dest["category"].to_numpy()
    pkg_by_dest = {d: pkg.index[pkg["destination_id"] == d].to_numpy() for d in dest_ids}
    pkg_w = pkg["popularity"].to_numpy()
    pkg_ids = pkg["package_id"].to_numpy()
    pkg_price = pkg["base_price_usd"].to_numpy()
    pkg_prev = pkg["previous_base_price_usd"].to_numpy()
    pkg_dest = pkg["destination_id"].to_numpy()
    herring = np.isin(pkg_ids, C.PRICE_HERRING_PACKAGES)
    change_ord = (C.PRICE_CHANGE_DATE - EPOCH).days
    anomaly_ord = (C.ANOMALY_START - EPOCH).days
    inc_ord = (C.INCIDENT_DATE - EPOCH).days
    end_ord = (C.WINDOW_END - EPOCH).days

    season_cat = np.array([C.CATEGORY_SEASON[c] for c in CATS])  # 5 x 12
    book_base = np.array([C.BOOK_BASE[c] for c in CATS])
    book_season = np.array([C.BOOK_SEASON[c] for c in CATS])
    sess_season = {k: np.array(v) for k, v in C.SESSION_SEASON.items()}
    hour_p = np.array(C.HOUR_WEIGHTS) / sum(C.HOUR_WEIGHTS)
    chan_names = np.array(list(C.KNOWN_CHANNEL_MIX))
    chan_p = np.array(list(C.KNOWN_CHANNEL_MIX.values()))
    untracked_names = np.array(list(C.UNTRACKED_BOOKING_CHANNEL_MIX))
    untracked_p = np.array(list(C.UNTRACKED_BOOKING_CHANNEL_MIX.values()))
    dev_names = np.array(list(C.DEVICE_MIX)); dev_p = np.array(list(C.DEVICE_MIX.values()))
    trav_vals = np.array(list(C.TRAVELERS_MIX)); trav_p = np.array(list(C.TRAVELERS_MIX.values()))

    months = months_in_window()
    burn_in = months_in_window(C.BURN_IN_START)[: len(months_in_window(C.BURN_IN_START)) - len(months)]

    # --- scale browsing so the expected known-session count hits KNOWN_SESSION_TARGET ------------
    def raw_lambda(status, ms):
        mi = ms.month - 1
        lam = activity * np.array([sess_season[c][mi] for c in climate]) \
            * np.vectorize(C.STATUS_SESSION_MULT.get)(status) * np.vectorize(C.TIER_SESSION_MULT.get)(tier)
        cohort = (status == "lapsed") & member & (climate == "cold")
        lam = lam * np.where(cohort, C.COHORT_SEASON_LIFT[mi], 1.0)
        return lam, cohort
    st0, _ = _status(last_ord, lifetime, (C.WINDOW_START - EPOCH).days)
    expected = sum(raw_lambda(st0, ms)[0].sum() * nd / 30.4 for ms, nd in months)
    base_rate = C.KNOWN_SESSION_TARGET / expected

    status_rows, sess_parts, book_parts, base_parts = [], [], [], []
    sess_key = 0
    incident_lost = 0
    warm_hist = [np.zeros(n, dtype=np.int64) for _ in range(3)]  # warm-view sessions, last three months
    for ms, nd in burn_in + months:
        record = ms >= C.WINDOW_START  # burn-in months shape the state but are never written out
        ms_ord = (ms - EPOCH).days
        mi = ms.month - 1
        status, days_since = _status(last_ord, lifetime, ms_ord)
        if record:
          status_rows.append(pd.DataFrame({
              "status_month": ms.replace(day=1), "customer_id": cust["customer_id"].to_numpy(),
              "loyalty_tier": tier, "loyalty_status": status,
              "days_since_last_booking": np.where(days_since >= 0, days_since, np.nan),
              "lifetime_bookings_to_date": lifetime.copy(),
          }))
        lam, cohort = raw_lambda(status, ms)
        lam = lam * base_rate * nd / 30.4
        if ms >= dt.date(2026, 7, 1):
            lam = lam * np.where(cohort, C.COHORT_INTENT_DRIFT, 1.0)
        lam = np.where(signup_ord > ms_ord + nd - 1, 0.0, lam)  # not a customer yet
        n_sess = rng.poisson(lam)
        ci = np.repeat(np.arange(n), n_sess)
        S = len(ci)
        if S == 0:
            continue
        day_ord = np.maximum(ms_ord + rng.integers(0, nd, size=S), signup_ord[ci])
        hour = rng.choice(24, size=S, p=hour_p)
        secs = day_ord * 86400 + hour * 3600 + rng.integers(0, 3600, size=S)
        # red herring #1: sessions inside the incident window never happened
        hole = (day_ord == inc_ord) & (hour >= C.INCIDENT_HOURS[0]) & (hour < C.INCIDENT_HOURS[1])

        # category per session
        P = aff[ci] * season_cat[:, mi][None, :]
        P = P / P.sum(axis=1, keepdims=True)
        cum = np.cumsum(P, axis=1)
        u = rng.random(S)[:, None]
        cat_idx = (u > cum).sum(axis=1).clip(0, 4)
        cat = np.array(CATS, dtype=object)[cat_idx]

        # destinations viewed: 1-4 from the primary category, sometimes one from another category
        k = rng.choice([1, 2, 3, 4], size=S, p=[0.40, 0.30, 0.20, 0.10])
        extra = rng.random(S) < 0.20
        views = []
        viewed_warm = np.zeros(S, dtype=bool)
        picks_by_cat = {}
        for c in CATS:
            m = cat == c
            cnt = int(m.sum())
            if cnt:
                pool = dest_by_cat[c]
                picks_by_cat[c] = (np.where(m)[0], rng.choice(pool, size=(cnt, 4), p=dest_w[pool] / dest_w[pool].sum()))
        primary_pick = np.zeros((S, 4), dtype=np.int64)
        for c, (rows, picks) in picks_by_cat.items():
            primary_pick[rows] = picks
        extra_pick = rng.choice(len(dest), size=S, p=dest_w / dest_w.sum())
        for i in range(S):
            ids = list(dict.fromkeys(primary_pick[i, :k[i]].tolist()))
            if extra[i] and extra_pick[i] not in ids:
                ids.append(int(extra_pick[i]))
            views.append([dest_ids[j] for j in ids])
            viewed_warm[i] = any(dest_cat[j] == "warm_escape" for j in ids)

        # channel: cohort sessions lean on paid social until the budget rotation
        channel = rng.choice(chan_names, size=S, p=chan_p)
        coh_s = cohort[ci]
        pre, post = C.COHORT_PAID_SOCIAL_SHARE
        ps_share = np.where(day_ord < anomaly_ord, pre, post)
        r = rng.random(S)
        force_ps = coh_s & (r < ps_share)
        force_other = coh_s & ~force_ps & (channel == "paid_social")
        channel = np.where(force_ps, "paid_social", channel)
        other = rng.choice(np.array(["direct", "organic", "email"]), size=S, p=[0.45, 0.35, 0.20])
        channel = np.where(force_other, other, channel).astype(object)

        device = rng.choice(dev_names, size=S, p=dev_p)
        landing = np.where(rng.random(S) < 0.72, cat, "home").astype(object)

        # booking odds
        st_s = status[ci]
        p = book_base[cat_idx] * book_season[cat_idx, mi] \
            * np.vectorize(C.STATUS_BOOK_MULT.get)(st_s) * np.vectorize(C.TIER_BOOK_MULT.get)(tier[ci]) \
            * book_latent[ci]
        recent_warm = np.minimum(warm_hist[0] + warm_hist[1] + warm_hist[2], C.INTENT_CAP)
        is_warm = cat == "warm_escape"
        p = p * np.where(is_warm, 1.0 + C.INTENT_BOOST * recent_warm[ci], 1.0)
        coh_warm = coh_s & is_warm
        p = p * np.where(coh_warm, C.RETARGETING_LIFT, 1.0)
        noncoh_warm = ~coh_s & (cat == "warm_escape")
        p = p * np.where(noncoh_warm, np.vectorize(C.WARM_BOOK_MULT_NONCOHORT.get)(climate[ci]), 1.0)
        p_base = np.clip(p, 0.0, 0.6)
        warm_hist = [warm_hist[1], warm_hist[2], np.bincount(ci[viewed_warm & ~hole], minlength=n)]
        p_act = p_base * np.where(coh_warm & (day_ord >= anomaly_ord), C.ANOMALY_FACTOR, 1.0)
        u = rng.random(S)
        intent_base = u < p_base
        intent_act = (u < p_act) & ~hole
        tracked = rng.random(S) < C.TRACKED_SHARE
        cancel = rng.random(S) < C.CANCEL_RATE
        converted = intent_act & tracked
        added = converted | (rng.random(S) < 0.09)
        pages = 1 + rng.poisson(2.6, size=S) + converted * 3

        # searched travel month
        lead_mu = np.array([C.LEAD_DAYS[c][0] for c in cat]); lead_sd = np.array([C.LEAD_DAYS[c][1] for c in cat])
        lead = np.clip(rng.normal(lead_mu, lead_sd), 14, 400).astype(int)
        stm_ord = day_ord + lead
        stm = [dt.date.fromordinal(int(o) + EPOCH.toordinal()).replace(day=1) if rng.random() < 0.7 else None
               for o in stm_ord]

        keys = np.arange(sess_key, sess_key + S)
        sess_key += S
        if record:
          sess_parts.append(pd.DataFrame({
              "_key": keys, "_ts": secs, "session_date_ord": day_ord,
              "customer_id": cust["customer_id"].to_numpy()[ci], "channel": channel, "device": device,
              "landing_category": landing, "destinations_viewed": views, "primary_category_viewed": cat,
              "viewed_warm_escape": viewed_warm, "pages_viewed": pages, "searched_travel_month": stm,
              "added_to_cart": added, "converted": converted,
          }).loc[~hole])
          incident_lost += int(hole.sum())

        # baseline bookings -> plan basis (confirmed only)
        bm = intent_base & ~cancel
        if record:
            base_parts.append(pd.DataFrame({"plan_month": ms.replace(day=1), "category": cat[bm],
                                            "market": market[ci[bm]]}))

        # actual bookings
        bi = np.where(intent_act)[0]
        if len(bi) == 0:
            continue
        b_cat = cat[bi]
        b_dest = np.empty(len(bi), dtype=object)
        for c in CATS:
            m = b_cat == c
            if m.any():
                pool = dest_by_cat[c]
                b_dest[m] = rng.choice(pool, size=int(m.sum()), p=dest_w[pool] / dest_w[pool].sum())
        b_pkg = np.array([rng.choice(pkg_by_dest[dest_ids[d]], p=pkg_w[pkg_by_dest[dest_ids[d]]] / pkg_w[pkg_by_dest[dest_ids[d]]].sum())
                          for d in b_dest])
        b_tracked = tracked[bi]
        b_date = day_ord[bi] + np.where(b_tracked, 0, rng.integers(0, 3, size=len(bi)))
        b_date = np.minimum(b_date, end_ord)
        # red herring #2: the two re-priced packages lose some demand after the change
        keep = ~(herring[b_pkg] & (b_date >= change_ord) & (rng.random(len(bi)) > C.PRICE_HERRING_DEMAND))
        bi, b_cat, b_pkg, b_tracked, b_date = bi[keep], b_cat[keep], b_pkg[keep], b_tracked[keep], b_date[keep]
        nb = len(bi)
        price = np.where(herring[b_pkg] & (b_date < change_ord), np.nan_to_num(pkg_prev[b_pkg].astype(float)), pkg_price[b_pkg])
        travelers = rng.choice(trav_vals, size=nb, p=trav_p)
        revenue = np.round(price * travelers * rng.uniform(0.92, 1.0, size=nb), 2)
        b_channel = np.where(b_tracked, channel[bi], rng.choice(untracked_names, size=nb, p=untracked_p)).astype(object)
        lead_mu = np.array([C.LEAD_DAYS[c][0] for c in b_cat]); lead_sd = np.array([C.LEAD_DAYS[c][1] for c in b_cat])
        travel = b_date + np.clip(rng.normal(lead_mu, lead_sd), 14, 400).astype(int)
        b_cancel = cancel[bi]
        if record:
          book_parts.append(pd.DataFrame({
              "customer_id": cust["customer_id"].to_numpy()[ci[bi]], "package_id": pkg_ids[b_pkg],
              "booking_date_ord": b_date, "travel_start_ord": travel, "channel": b_channel,
              "travelers": travelers, "revenue_usd": revenue,
              "status": np.where(b_cancel, "cancelled", "confirmed").astype(object),
              "_session_key": np.where(b_tracked, keys[bi], -1),
              "category": b_cat, "market": market[ci[bi]],
          }))
        # update state with confirmed bookings
        ok = ~b_cancel
        cidx = ci[bi][ok]
        np.maximum.at(last_ord, cidx, b_date[ok])
        np.add.at(lifetime, cidx, 1)
        np.add.at(ltv, cidx, revenue[ok])

    sessions = pd.concat(sess_parts, ignore_index=True)
    bookings = pd.concat(book_parts, ignore_index=True)
    baseline = pd.concat(base_parts, ignore_index=True)
    status_hist = pd.concat(status_rows, ignore_index=True)
    final_state = pd.DataFrame({"customer_id": cust["customer_id"], "last_booking_ord": last_ord,
                                "lifetime_bookings": lifetime, "lifetime_value_usd": np.round(ltv, 2)})
    return sessions, bookings, baseline, status_hist, final_state, incident_lost


def anonymous_sessions(known: pd.DataFrame, dest: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Sessions with no customer_id. They follow the site's daily traffic shape and never convert."""
    N = C.N_ANON_SESSIONS
    day_counts = known.groupby("session_date_ord").size().astype(float)
    # the known sessions already have the incident hole cut out; restore that day's weight so the
    # anonymous sessions lose it only once (the hole is applied below)
    inc = (C.INCIDENT_DATE - EPOCH).days
    day_counts.loc[inc] = (day_counts.loc[inc - 1] + day_counts.loc[inc + 1]) / 2
    days = day_counts.index.to_numpy(); w = day_counts.to_numpy().astype(float)
    day_ord = rng.choice(days, size=N, p=w / w.sum())
    hour = rng.choice(24, size=N, p=np.array(C.HOUR_WEIGHTS) / sum(C.HOUR_WEIGHTS))
    secs = day_ord * 86400 + hour * 3600 + rng.integers(0, 3600, size=N)
    month_idx = np.array([dt.date.fromordinal(int(o) + EPOCH.toordinal()).month - 1 for o in day_ord])
    season = np.array([C.CATEGORY_SEASON[c] for c in CATS])  # 5x12
    aff = np.array([0.55, 0.60, 0.30, 0.40, 0.35])
    P = (aff[:, None] * season)[:, month_idx].T
    P = P / P.sum(axis=1, keepdims=True)
    cat_idx = (rng.random(N)[:, None] > np.cumsum(P, axis=1)).sum(axis=1).clip(0, 4)
    cat = np.array(CATS, dtype=object)[cat_idx]
    dest_ids = dest["destination_id"].to_numpy(); dest_cat = dest["category"].to_numpy()
    dest_w = rng.lognormal(0.0, 0.5, size=len(dest))
    k = rng.choice([1, 2, 3], size=N, p=[0.55, 0.30, 0.15])
    views, viewed_warm = [], np.zeros(N, dtype=bool)
    picks = np.zeros((N, 3), dtype=np.int64)
    for c in CATS:
        m = cat == c
        pool = dest.index[dest["category"] == c].to_numpy()
        picks[m] = rng.choice(pool, size=(int(m.sum()), 3), p=dest_w[pool] / dest_w[pool].sum())
    for i in range(N):
        ids = list(dict.fromkeys(picks[i, :k[i]].tolist()))
        views.append([dest_ids[j] for j in ids])
        viewed_warm[i] = any(dest_cat[j] == "warm_escape" for j in ids)
    lead_mu = np.array([C.LEAD_DAYS[c][0] for c in cat]); lead_sd = np.array([C.LEAD_DAYS[c][1] for c in cat])
    stm_ord = day_ord + np.clip(rng.normal(lead_mu, lead_sd), 14, 400).astype(int)
    stm = [dt.date.fromordinal(int(o) + EPOCH.toordinal()).replace(day=1) if r < 0.45 else None
           for o, r in zip(stm_ord, rng.random(N))]
    inc_ord = (C.INCIDENT_DATE - EPOCH).days
    hole = (day_ord == inc_ord) & (hour >= C.INCIDENT_HOURS[0]) & (hour < C.INCIDENT_HOURS[1])
    return pd.DataFrame({
        "_key": -1, "_ts": secs, "session_date_ord": day_ord, "customer_id": None,
        "channel": rng.choice(np.array(list(C.ANON_CHANNEL_MIX)), size=N, p=list(C.ANON_CHANNEL_MIX.values())),
        "device": rng.choice(np.array(list(C.DEVICE_MIX)), size=N, p=list(C.DEVICE_MIX.values())),
        "landing_category": np.where(rng.random(N) < 0.6, cat, "home").astype(object),
        "destinations_viewed": views, "primary_category_viewed": cat, "viewed_warm_escape": viewed_warm,
        "pages_viewed": 1 + rng.poisson(1.8, size=N), "searched_travel_month": stm,
        "added_to_cart": rng.random(N) < 0.04, "converted": False,
    }).loc[~hole].reset_index(drop=True)


def finalize_sessions_and_bookings(known: pd.DataFrame, anon: pd.DataFrame, bookings: pd.DataFrame):
    """Sort, assign public ids, attach booking session ids."""
    sess = pd.concat([known, anon], ignore_index=True)
    sess = sess.sort_values(["_ts", "_key"], kind="mergesort").reset_index(drop=True)
    sess["session_id"] = [f"S{i:08d}" for i in range(1, len(sess) + 1)]
    key_to_id = dict(zip(sess.loc[sess["_key"] >= 0, "_key"], sess.loc[sess["_key"] >= 0, "session_id"]))
    sess["session_ts"] = pd.to_datetime(sess["_ts"], unit="s")
    sess["session_date"] = [dt.date.fromordinal(int(o) + EPOCH.toordinal()) for o in sess["session_date_ord"]]

    bk = bookings.sort_values(["booking_date_ord", "customer_id", "package_id"], kind="mergesort").reset_index(drop=True)
    bk["booking_id"] = [f"B{i:07d}" for i in range(1, len(bk) + 1)]
    bk["session_id"] = [key_to_id.get(k) if k >= 0 else None for k in bk["_session_key"]]
    bk["booking_date"] = [dt.date.fromordinal(int(o) + EPOCH.toordinal()) for o in bk["booking_date_ord"]]
    bk["travel_start_date"] = [dt.date.fromordinal(int(o) + EPOCH.toordinal()) for o in bk["travel_start_ord"]]
    return sess, bk

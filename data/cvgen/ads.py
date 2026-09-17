"""Campaign roster (content/campaigns.json), daily paid-media performance, and creative variants."""
from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pandas as pd

from . import config as C
from .catalog import CONTENT_DIR

IMAGERY = ["beach_couple", "family_pool", "resort_aerial", "city_skyline", "adventure"]
OFFERS = ["percent_off", "bonus_points", "free_night", "urgency", "no_offer"]
CTAS = ["book_now", "see_deals", "plan_your_escape", "claim_offer"]


def load_campaigns() -> tuple[list[dict], dict]:
    raw = json.loads((CONTENT_DIR / "campaigns.json").read_text(encoding="utf-8"))
    for c in raw["campaigns"]:
        c["start_date"] = dt.date.fromisoformat(c["start_date"])
        c["end_date"] = dt.date.fromisoformat(c["end_date"])
    return raw["campaigns"], raw["segments"]


def _markets(scope: str) -> list[tuple[str, str, float]]:
    if scope == "all":
        return C.MARKETS
    if scope == "cold":
        return [m for m in C.MARKETS if m[1] == "cold"]
    if scope == "cold_mild":
        return [m for m in C.MARKETS if m[1] in ("cold", "mild")]
    raise ValueError(scope)


def _retargeting_baseline(d: dt.date, camp: dict) -> float:
    return camp["daily_spend_usd"] * C.RETARGETING_SEASON[d.month - 1]


def build_ad_performance(campaigns: list[dict], rng: np.random.Generator) -> pd.DataFrame:
    by_id = {c["campaign_id"]: c for c in campaigns}
    retarget = by_id["CMP-002"]
    days = [C.WINDOW_START + dt.timedelta(days=i) for i in range((C.WINDOW_END - C.WINDOW_START).days + 1)]
    rows = []
    for camp in campaigns:
        if not camp["paid_channel"]:
            continue
        mk = _markets(camp["markets"])
        w = np.array([m[2] for m in mk]); w = w / w.sum()
        ch = camp["paid_channel"]
        for d in days:
            if d < camp["start_date"] or d > camp["end_date"]:
                continue
            if camp["campaign_id"] == "CMP-002":
                total = _retargeting_baseline(d, camp) if d < C.ANOMALY_START else C.RETARGETING_KEEPALIVE_USD
            elif camp["campaign_id"] == "CMP-012":
                total = _retargeting_baseline(d, retarget) - C.RETARGETING_KEEPALIVE_USD
            elif camp["seasonal"] == "warm":
                total = camp["daily_spend_usd"] * C.RETARGETING_SEASON[d.month - 1]
            else:
                total = camp["daily_spend_usd"]
            for (name, _, _), share in zip(mk, w):
                spend = total * share * rng.normal(1.0, 0.03)
                clicks = int(rng.poisson(spend / C.CPC[ch]))
                impressions = int(round(clicks / C.CTR[ch] * rng.lognormal(0.0, 0.10)))
                rows.append((d, ch, camp["campaign_id"], camp["name"], camp["target_segment"], name,
                             impressions, clicks, round(float(spend), 2)))
    df = pd.DataFrame(rows, columns=["spend_date", "channel", "campaign_id", "campaign_name", "target_segment",
                                     "market", "impressions", "clicks", "spend_usd"])
    # attributed conversions: fixed CVR for always-on programs; seasonal campaigns are scaled so their
    # paid conversions agree with the bookings_attributed the retrospectives quote
    conv = np.zeros(len(df), dtype=int)
    for cid, g in df.groupby("campaign_id"):
        camp = by_id[cid]
        if camp["bookings_attributed"] is None:
            cvr = C.ALWAYS_ON_CVR[cid]
        else:
            cvr = camp["bookings_attributed"] * C.PAID_ATTRIBUTION_SHARE / max(1, g["clicks"].sum())
        conv[g.index] = rng.binomial(g["clicks"].to_numpy(), min(cvr, 0.5))
    df["attributed_conversions"] = conv
    return df.sort_values(["spend_date", "campaign_id", "market"]).reset_index(drop=True)


def build_campaign_history(campaigns: list[dict], ads: pd.DataFrame, avg_revenue_usd: float) -> pd.DataFrame:
    rows = []
    for c in campaigns:
        g = ads[ads["campaign_id"] == c["campaign_id"]]
        spend = float(g["spend_usd"].sum())
        if c["bookings_attributed"] is None:
            booked = int(round(g["attributed_conversions"].sum() / C.PAID_ATTRIBUTION_SHARE))
            roi = round((booked * avg_revenue_usd * C.CONTRIBUTION_MARGIN - spend) / spend, 1) if spend else None
        else:
            booked, roi = c["bookings_attributed"], c["roi"]
        rows.append({
            "campaign_id": c["campaign_id"], "name": c["name"], "objective": c["objective"],
            "target_segment": c["target_segment"], "start_date": c["start_date"], "end_date": c["end_date"],
            "channels": c["channels"], "budget_usd": float(c["budget_usd"]), "spend_to_date_usd": round(spend, 2),
            "bookings_attributed": booked, "roi": roi, "retrospective": c["retrospective"],
        })
    return pd.DataFrame(rows)


# Conversion multipliers by segment family. The lapsed-member story is the planted signal; the
# other families keep the table from reading as if one recipe worked for everyone.
_MULT = {
    "lapsed": {
        "offer": {"bonus_points": 1.75, "free_night": 1.25, "no_offer": 0.95, "percent_off": 0.62, "urgency": 0.52},
        "imagery": {"beach_couple": 1.45, "resort_aerial": 1.10, "family_pool": 0.85, "adventure": 0.70, "city_skyline": 0.60},
        "cta": {"plan_your_escape": 1.35, "book_now": 1.00, "see_deals": 0.90, "claim_offer": 0.80},
    },
    "broad": {
        "offer": {"percent_off": 1.20, "urgency": 1.05, "free_night": 1.05, "bonus_points": 0.95, "no_offer": 0.75},
        "imagery": {"family_pool": 1.15, "beach_couple": 1.10, "resort_aerial": 1.00, "city_skyline": 0.90, "adventure": 0.90},
        "cta": {"book_now": 1.10, "see_deals": 1.05, "claim_offer": 1.00, "plan_your_escape": 0.90},
    },
    "urban": {
        "offer": {"free_night": 1.20, "percent_off": 1.05, "no_offer": 1.00, "urgency": 0.95, "bonus_points": 0.85},
        "imagery": {"city_skyline": 1.50, "adventure": 0.85, "beach_couple": 0.75, "resort_aerial": 0.70, "family_pool": 0.65},
        "cta": {"see_deals": 1.10, "book_now": 1.05, "plan_your_escape": 0.95, "claim_offer": 0.90},
    },
    "active_outdoors": {
        "offer": {"no_offer": 1.10, "free_night": 1.05, "percent_off": 1.00, "bonus_points": 1.00, "urgency": 0.85},
        "imagery": {"adventure": 1.55, "resort_aerial": 0.95, "city_skyline": 0.75, "beach_couple": 0.70, "family_pool": 0.65},
        "cta": {"book_now": 1.05, "plan_your_escape": 1.05, "see_deals": 0.95, "claim_offer": 0.90},
    },
    "active_member": {
        "offer": {"bonus_points": 1.50, "free_night": 1.15, "no_offer": 1.00, "percent_off": 0.80, "urgency": 0.75},
        "imagery": {"beach_couple": 1.20, "resort_aerial": 1.10, "family_pool": 1.00, "adventure": 0.85, "city_skyline": 0.80},
        "cta": {"plan_your_escape": 1.15, "book_now": 1.05, "see_deals": 0.95, "claim_offer": 0.90},
    },
}
_FAMILY = {"lapsed_compass_cold": "lapsed", "lapsed_compass": "lapsed", "all_customers": "broad", "prospects": "broad",
           "urban_explorers": "urban", "ski_enthusiasts": "active_outdoors", "adventure_seekers": "active_outdoors",
           "cruise_interest": "broad", "active_compass": "active_member"}
_VARIANTS_PER_CAMPAIGN = {"CMP-001": 4, "CMP-002": 48, "CMP-003": 32, "CMP-004": 16, "CMP-005": 12, "CMP-006": 24,
                          "CMP-007": 10, "CMP-008": 14, "CMP-009": 6, "CMP-010": 2, "CMP-011": 12, "CMP-012": 20}


def build_creative_variants(campaigns: list[dict], rng: np.random.Generator) -> pd.DataFrame:
    assert sum(_VARIANTS_PER_CAMPAIGN.values()) == C.N_CREATIVE_VARIANTS
    rows = []
    vid = 0
    for camp in campaigns:
        n = _VARIANTS_PER_CAMPAIGN[camp["campaign_id"]]
        for i in range(n):
            vid += 1
            seg = camp["target_segment"]
            # Winter Sun ran a cold-market cut; its variants are tagged with the narrower segment
            if camp["campaign_id"] == "CMP-003" and i < 20:
                seg = "lapsed_compass_cold"
            fam = _MULT[_FAMILY[seg]]
            offer = rng.choice(OFFERS) if camp["campaign_id"] != "CMP-006" else rng.choice(["percent_off", "urgency", "percent_off"])
            imagery = rng.choice(IMAGERY)
            cta = rng.choice(CTAS)
            base_cvr = {"lapsed": 0.026, "broad": 0.014, "urban": 0.016, "active_outdoors": 0.017, "active_member": 0.030}[_FAMILY[seg]]
            cvr = base_cvr * fam["offer"][offer] * fam["imagery"][imagery] * fam["cta"][cta] * rng.lognormal(0.0, 0.18)
            impressions = int(rng.lognormal(np.log(420_000), 0.7))
            ctr = rng.uniform(0.006, 0.018)
            clicks = int(rng.binomial(impressions, ctr))
            conversions = int(rng.binomial(clicks, min(cvr, 0.5)))
            rows.append({
                "variant_id": f"CRV-{vid:04d}", "campaign_id": camp["campaign_id"], "target_segment": seg,
                "hero_imagery_style": imagery, "offer_framing": offer, "cta_construction": cta,
                "impressions": impressions, "clicks": clicks, "conversions": conversions,
                "conversion_rate": round(conversions / clicks, 5) if clicks else 0.0,
            })
    return pd.DataFrame(rows)

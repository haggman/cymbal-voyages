"""Destinations (hand-written content in content/destinations.json) and generated packages."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

# (name suffix, nights, price multiplier vs the 7-night reference, template family)
PACKAGE_TYPES = {
    "warm_escape": [("Long Weekend", 3, 0.55, "short"), ("Classic Week", 7, 1.00, "classic"),
                    ("Family Escape", 7, 0.95, "family"), ("Romantic Retreat", 5, 0.90, "couples"),
                    ("Grand Escape", 10, 1.35, "grand")],
    "city_break":  [("Long Weekend", 3, 0.60, "short"), ("City Explorer", 4, 0.80, "classic"),
                    ("Food and Culture Week", 6, 1.05, "grand"), ("Couples Getaway", 4, 0.85, "couples"),
                    ("Extended Stay", 8, 1.30, "family")],
    "ski":         [("Powder Weekend", 3, 0.60, "short"), ("Ski Week", 7, 1.00, "classic"),
                    ("Family Ski Week", 7, 1.05, "family"), ("First Tracks", 5, 0.85, "couples"),
                    ("Two-Resort Tour", 9, 1.40, "grand")],
    "adventure":   [("Highlights", 5, 0.80, "short"), ("Classic Expedition", 8, 1.00, "classic"),
                    ("Active Week", 7, 1.00, "couples"), ("Family Adventure", 7, 0.95, "family"),
                    ("Grand Expedition", 12, 1.50, "grand")],
    "cruise":      [("4-Night Sampler", 4, 0.60, "short"), ("7-Night Sailing", 7, 1.00, "classic"),
                    ("Family Sailing", 7, 1.00, "family"), ("Balcony Upgrade Week", 7, 1.30, "couples"),
                    ("10-Night Grand Voyage", 10, 1.45, "grand")],
}
REFERENCE_PRICE = {"budget": 560, "mid": 900, "premium": 1400, "luxury": 2500}  # per person, 7 nights, flights included

OPENERS = {
    "short": [
        "Three or four nights is enough to reset when the trip is built around {name}. This package keeps the logistics light: flights, {nights} nights in a well-located room, and airport transfers, so the time on the ground is yours.",
        "A short break to {name}, planned so that none of it is spent waiting. Flights, {nights} nights and transfers are arranged; you land, drop the bags and start with {h1}.",
        "For a long weekend away, {name} rewards a compact plan. We include flights, {nights} nights and transfers, and we suggest an itinerary that fits {h1} and {h2} without rushing either.",
    ],
    "classic": [
        "Our most popular way to see {name}: {nights} nights, flights and transfers included, with a daily rhythm that leaves room for {h1} and an afternoon of doing nothing in particular.",
        "The {nights}-night classic for {name}. Flights and transfers are included, the hotel is one we have vetted ourselves, and the pace is {vibe1} by design.",
        "{nights} nights in {name} with the essentials handled. Flights, transfers and a central hotel are included, and our destination notes cover {h1}, {h2} and how to get to each without a rental car.",
    ],
    "family": [
        "Built for families who want {name} to be easy. {nights} nights in connecting or family rooms, flights, transfers and a kids-stay-free arrangement where the hotel offers one.",
        "A family week in {name} with the friction removed: {nights} nights in family-sized rooms, flights and transfers included, and a day-by-day plan that alternates {h1} with pool time.",
        "Traveling with kids or three generations? This {nights}-night stay in {name} includes flights, transfers and rooms that actually fit everyone, plus a shortlist of activities by age.",
    ],
    "couples": [
        "{nights} nights in {name} for two. Flights, transfers and an adults-oriented hotel are included, along with one dinner reservation we make on your behalf.",
        "A quieter take on {name}: {nights} nights, flights and transfers included, with a hotel chosen for its calm and a plan built around {h1} and long evenings.",
        "For couples, {name} at an unhurried pace. This {nights}-night package includes flights, transfers and a room upgrade where available, and it leaves most days open.",
    ],
    "grand": [
        "The long version of {name}: {nights} nights, flights and transfers included, with two bases so you see more than one side of the place.",
        "When {name} deserves more than a week. {nights} nights, flights and transfers, and an itinerary that covers {h1}, {h2} and {h3} with proper rest days in between.",
        "Our fullest {name} itinerary. {nights} nights with flights and transfers included, hotel changes handled for you, and enough time for {h1} to become a habit rather than an item on a list.",
    ],
}
MIDDLES = [
    "Days can revolve around {m1} and {m2}; our concierge notes rank the options by how much of the day they take.",
    "Expect {vibe1}, {vibe2} days. {m1_cap} is the obvious draw, and {m2} is the one repeat visitors tell us they wish they had done sooner.",
    "The itinerary suggests {m1} early in the stay and saves {m2} for the last full day, when you know the place well enough to enjoy it.",
    "{m2_cap} is included as an optional excursion, bookable before departure or once you arrive.",
    "Two things we recommend not skipping: {m1} and {m2}. Everything else is negotiable.",
    "The {vibe1} character of {region} comes through in the details: {m1}, {m2}, and the walk back afterward.",
]
CLOSERS = [
    "Prices are per person, based on double occupancy, with taxes and fees included unless stated. Cymbal Compass members earn points on the full package value.",
    "Good for {good_for}. Prices are per person, double occupancy, taxes and fees included; availability is limited in peak weeks.",
    "Best between {best_months}. Per-person pricing assumes double occupancy and includes taxes and fees; Compass points post within 14 days of completed travel.",
    "Suits {good_for}. Prices per person, double occupancy, taxes and fees included. Free cancellation applies until 14 days before departure on most departures.",
    "Departures run {best_months}. Prices are per person, based on two sharing, taxes and fees included; single travelers can request a supplement quote.",
]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def _month_span(months: list[int]) -> str:
    ms = sorted(months)
    if not ms:
        return "year-round"
    # find a contiguous run allowing wraparound
    return f"{MONTH_NAMES[ms[0]-1]} and {MONTH_NAMES[ms[-1]-1]}" if len(ms) > 1 else MONTH_NAMES[ms[0]-1]


def load_destinations() -> pd.DataFrame:
    raw = json.loads((CONTENT_DIR / "destinations.json").read_text(encoding="utf-8"))
    rows = []
    for d in raw:
        rows.append({
            "destination_id": d["destination_id"], "name": d["name"], "country": d["country"],
            "region": d["region"], "category": d["category"], "description": d["description"],
            "price_band": d["price_band"], "best_months": [int(m) for m in d["best_months"]],
            "highlights": list(d["highlights"]), "vibe": list(d["vibe"]), "good_for": list(d["good_for"]),
        })
    df = pd.DataFrame(rows)
    assert len(df) == 60 and df["destination_id"].is_unique
    return df


def _describe(rng: np.random.Generator, dest: dict, ptype: tuple) -> str:
    suffix, nights, _, family = ptype
    h = list(dest["highlights"])
    rng.shuffle(h)
    v = list(dest["vibe"])
    ctx = {
        "name": dest["name"], "nights": nights, "region": dest["region"],
        "h1": h[0], "h2": h[1], "h3": h[2], "m1": h[3], "m2": h[4],
        "m1_cap": h[3][0].upper() + h[3][1:], "m2_cap": h[4][0].upper() + h[4][1:],
        "vibe1": v[0], "vibe2": v[1], "good_for": " and ".join(dest["good_for"][:2]),
        "best_months": _month_span(dest["best_months"]),
    }
    parts = [rng.choice(OPENERS[family]), rng.choice(MIDDLES), rng.choice(CLOSERS)]
    text = " ".join(p.format(**ctx) for p in parts)
    n = len(text.split())
    if n < 60:  # add a second middle sentence
        extra = rng.choice([m for m in MIDDLES if m != parts[1]])
        text = " ".join([parts[0].format(**ctx), parts[1].format(**ctx), extra.format(**ctx), parts[2].format(**ctx)])
    return text


def build_packages(dest: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    pid = 0
    for _, d in dest.iterrows():
        dd = d.to_dict()
        for ptype in PACKAGE_TYPES[d["category"]]:
            pid += 1
            suffix, nights, mult, _ = ptype
            ref = REFERENCE_PRICE[d["price_band"]]
            price = ref * mult * (nights / 7) ** 0.35 * rng.uniform(0.94, 1.06)
            price = float(np.round(price / 10) * 10 - 1)  # $1,499-style
            eff = C.WINDOW_START - dt.timedelta(days=int(rng.integers(120, 540)))
            rows.append({
                "package_id": f"PKG-{pid:04d}", "destination_id": d["destination_id"],
                "name": f"{d['name']} {suffix}", "nights": nights,
                "description": _describe(rng, dd, ptype), "base_price_usd": price,
                "previous_base_price_usd": None, "price_effective_date": eff,
                "popularity": float(rng.lognormal(0, 0.45)),
            })
    df = pd.DataFrame(rows)
    # Red herring #2: two warm-escape packages re-priced on PRICE_CHANGE_DATE.
    for pk in C.PRICE_HERRING_PACKAGES:
        i = df.index[df["package_id"] == pk][0]
        old = df.at[i, "base_price_usd"]
        df.at[i, "previous_base_price_usd"] = old
        df.at[i, "base_price_usd"] = float(np.round(old * (1 + C.PRICE_HERRING_INCREASE) / 10) * 10 - 1)
        df.at[i, "price_effective_date"] = C.PRICE_CHANGE_DATE
    assert len(df) == 300
    return df

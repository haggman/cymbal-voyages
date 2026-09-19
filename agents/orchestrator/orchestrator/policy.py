"""Cymbal Voyages decisioning policy engine.

Deterministic on purpose: the model never decides who gets what. It calls these
functions, which read `decisioning_policy` and `customer_features` fresh on every
call, apply the enabled rules in priority order (first match wins), and return an
action and a reason for each customer. Anything a person might type into the
policy table (tier names in any case, "0.3" / ".30" / "30%", "TRUE" / "yes",
"=" / "==" / "≥") is normalized before it is compared.
"""
from __future__ import annotations

import math
import re
import string
from collections import Counter, OrderedDict
from dataclasses import dataclass
from typing import Any, Iterable

# customer_features columns a rule may test, and how to read them.
NUMERIC = {
    "propensity_score", "days_since_last_booking", "lifetime_bookings",
    "lifetime_value_usd", "sessions_last_90d", "warm_views_last_90d",
    "recent_engagement_score",
}
UNIT_INTERVAL = {"propensity_score", "recent_engagement_score"}  # 0–1 scores
BOOLEAN = {"booked_last_60d", "has_active_reservation", "email_contactable", "sms_contactable"}
TEXT = {"loyalty_tier", "loyalty_status", "home_market_climate", "ltv_band", "customer_id"}
FEATURES = NUMERIC | BOOLEAN | TEXT

ACTIONS = ("send_offer", "route_to_loyalty_team", "hold_for_retargeting", "suppress")

_OPS = {
    "==": "==", "=": "==", "eq": "==", "is": "==", "equals": "==",
    "!=": "!=", "<>": "!=", "≠": "!=", "ne": "!=", "is not": "!=", "not": "!=",
    ">=": ">=", "≥": ">=", "=>": ">=", "ge": ">=", "gte": ">=", "at least": ">=",
    ">": ">", "gt": ">", "above": ">", "more than": ">",
    "<=": "<=", "≤": "<=", "=<": "<=", "le": "<=", "lte": "<=", "at most": "<=",
    "<": "<", "lt": "<", "below": "<", "less than": "<",
}
_TRUE = {"true", "t", "yes", "y", "1", "on"}
_FALSE = {"false", "f", "no", "n", "0", "off"}
_ACTION_ALIASES = {
    "send offer": "send_offer", "offer": "send_offer", "send": "send_offer",
    "route to loyalty team": "route_to_loyalty_team", "loyalty team": "route_to_loyalty_team",
    "route_to_loyalty": "route_to_loyalty_team",
    "hold for retargeting": "hold_for_retargeting", "hold": "hold_for_retargeting",
    "retarget": "hold_for_retargeting", "retargeting": "hold_for_retargeting",
    "suppress": "suppress", "suppression": "suppress", "exclude": "suppress",
}


def _norm_name(value: Any) -> str:
    return re.sub(r"[\s\-]+", "_", str(value or "").strip().lower())


def norm_feature(value: Any) -> str:
    return _norm_name(value)


def norm_operator(value: Any) -> str | None:
    key = re.sub(r"\s+", " ", str(value or "").strip().lower())
    return _OPS.get(key)


def norm_action(value: Any) -> str | None:
    key = str(value or "").strip().lower()
    if _norm_name(key) in ACTIONS:
        return _norm_name(key)
    return _ACTION_ALIASES.get(re.sub(r"[_\-]+", " ", key))


def norm_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    s = str(value).strip().lower()
    if s in _TRUE:
        return True
    if s in _FALSE:
        return False
    return None


def norm_number(value: Any, feature: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        n = float(value)
    else:
        s = str(value).strip().lower().replace(",", "").replace("$", "")
        pct = s.endswith("%")
        s = s.rstrip("%").strip()
        s = re.sub(r"\s*(days?|d)$", "", s)
        try:
            n = float(s)
        except ValueError:
            return None
        if pct:
            n /= 100.0
    if feature in UNIT_INTERVAL and 1.0 < n <= 100.0:
        n /= 100.0  # "30" for a 0–1 score means 30%
    return n


def norm_text(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip().strip("'\"").lower()
    return s or None


@dataclass
class Condition:
    feature: str
    op: str
    threshold: Any
    raw: str

    def test(self, row: dict) -> bool:
        v = row.get(self.feature)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return False
        if self.feature in NUMERIC:
            v = float(v)
        elif self.feature in BOOLEAN:
            v = norm_bool(v)
            if v is None:
                return False
        else:
            v = norm_text(v)
        t = self.threshold
        try:
            if self.op == "==":
                return v == t
            if self.op == "!=":
                return v != t
            if self.op == ">=":
                return v >= t
            if self.op == ">":
                return v > t
            if self.op == "<=":
                return v <= t
            if self.op == "<":
                return v < t
        except TypeError:
            return False
        return False


def _condition(feature: Any, op: Any, threshold: Any) -> tuple[Condition | None, str | None]:
    f = norm_feature(feature)
    if not f:
        return None, None
    if f not in FEATURES:
        return None, f"unknown feature '{feature}'"
    o = norm_operator(op)
    if o is None:
        return None, f"unknown operator '{op}' for {f}"
    if f in NUMERIC:
        t = norm_number(threshold, f)
    elif f in BOOLEAN:
        t = norm_bool(threshold)
    else:
        t = norm_text(threshold)
    if t is None:
        return None, f"cannot read threshold '{threshold}' for {f}"
    if f in BOOLEAN and o not in ("==", "!="):
        return None, f"operator '{op}' makes no sense for yes/no feature {f}"
    return Condition(f, o, t, f"{f} {o} {threshold}"), None


@dataclass
class Rule:
    rule_id: str
    priority: float
    conditions: list[Condition]
    action: str
    reason_template: str

    def describe(self) -> str:
        return " AND ".join(c.raw for c in self.conditions)


def parse_policy(rows: Iterable[dict]) -> tuple[list[Rule], list[str]]:
    """Turn raw decisioning_policy rows into rules. Returns (rules, warnings)."""
    rules, warnings = [], []
    for r in rows:
        rid = str(r.get("rule_id") or "?").strip()
        enabled = norm_bool(r.get("enabled"))
        if enabled is False:
            continue  # NULL counts as enabled, so a rule a student adds without the column still runs
        action = norm_action(r.get("action"))
        if action is None:
            warnings.append(f"{rid}: skipped, unknown action '{r.get('action')}'")
            continue
        conds, bad = [], False
        for f, o, t in ((r.get("feature"), r.get("operator"), r.get("threshold")),
                        (r.get("feature_2"), r.get("operator_2"), r.get("threshold_2"))):
            if f is None or (isinstance(f, float) and math.isnan(f)) or not str(f).strip():
                continue
            c, err = _condition(f, o, t)
            if err:
                warnings.append(f"{rid}: skipped, {err}")
                bad = True
                break
            conds.append(c)
        if bad or not conds:
            if not bad:
                warnings.append(f"{rid}: skipped, no condition")
            continue
        try:
            prio = float(r.get("priority"))
        except (TypeError, ValueError):
            prio = float("inf")
        rules.append(Rule(rid, prio, conds, action, str(r.get("reason_template") or "")))
    rules.sort(key=lambda x: (x.priority, x.rule_id))
    return rules, warnings


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def render_reason(template: str, row: dict) -> str:
    values = _SafeDict()
    for k, v in row.items():
        if isinstance(v, float) and math.isnan(v):
            v = None
        values[k] = v
    try:
        return string.Formatter().vformat(template, (), values)
    except (ValueError, TypeError, KeyError, IndexError):
        # fall back to plain substitution when a format spec doesn't fit the value
        return re.sub(r"\{(\w+)(?::[^}]*)?\}", lambda m: str(values.get(m.group(1), m.group(0))), template)


NO_MATCH = ("hold_for_retargeting", "none", "No rule matched; held in the retargeting pool by default.")


def decide(row: dict, rules: list[Rule]) -> tuple[str, str, str]:
    """Return (action, rule_id, reason) for one customer: first matching rule wins."""
    for rule in rules:
        if all(c.test(row) for c in rule.conditions):
            return rule.action, rule.rule_id, render_reason(rule.reason_template, row)
    return NO_MATCH


def summarize(rows: list[dict], rules: list[Rule], sample_per_action: int = 3) -> dict:
    by_action, by_rule = Counter(), Counter()
    samples: dict[str, list] = OrderedDict((a, []) for a in ACTIONS)
    for row in rows:
        action, rid, reason = decide(row, rules)
        by_action[action] += 1
        by_rule[(rid, action)] += 1
        if len(samples.setdefault(action, [])) < sample_per_action:
            samples[action].append({"customer_id": row.get("customer_id"), "rule": rid, "reason": reason})
    total = len(rows)
    return {
        "customers": total,
        "by_action": [
            {"action": a, "customers": n, "share_pct": round(100 * n / total, 1) if total else 0.0}
            for a, n in sorted(by_action.items(), key=lambda kv: -kv[1])
        ],
        "by_rule": [
            {"rule": rid, "action": a, "customers": n}
            for (rid, a), n in sorted(by_rule.items(), key=lambda kv: -kv[1])
        ],
        "examples": {a: s for a, s in samples.items() if s},
    }

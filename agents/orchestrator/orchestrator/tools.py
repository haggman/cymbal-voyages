"""The orchestrator's tools. Each call re-reads the policy table, so an edit in
BigQuery shows up on the very next run."""
from __future__ import annotations

from . import data, policy


def _load_policy():
    rules, warnings = policy.parse_policy(data.policy_rows())
    return rules, warnings


def show_policy() -> dict:
    """Show the decisioning rules exactly as they are applied right now.

    Use this when someone asks what the policy is, why a rule did or did not fire,
    or after someone says they changed the policy table.

    Returns:
        dict: the enabled rules in the order they are checked (first match wins),
        plus any rows that were skipped and why.
    """
    rules, warnings = _load_policy()
    return {
        "rules_in_order": [
            {"rule": r.rule_id, "priority": r.priority, "when": r.describe(), "action": r.action}
            for r in rules
        ],
        "skipped_rows": warnings,
        "note": "Rules are checked top to bottom and the first one that matches decides. "
                "Customers no rule matches are held for retargeting.",
    }


def decide_for_segment(
    climate: str,
    member_status: str,
    lapsed_months_min: int = 0,
    lapsed_months_max: int = 0,
    email_only: bool = False,
    exclude_booked_last_60d: bool = False,
) -> dict:
    """Decide the next best action for every customer in an audience.

    The audience is always Cymbal Compass loyalty members who looked at a
    warm-escape destination in the last 90 days, narrowed by the arguments below.
    Use the same values the audience was sized with.

    Args:
        climate: Home-market climate: cold, mild, warm, or any.
        member_status: lapsed (no booking in 12+ months), active, never, or any
            (all Compass members).
        lapsed_months_min: Only customers whose last booking was at least this many
            months ago. 0 means no minimum. "Lapsed 24+ months" is 24.
        lapsed_months_max: Only customers whose last booking was less than this many
            months ago. 0 means no maximum. "Lapsed 12 to 24 months" is min 12, max 24.
        email_only: True to keep only customers we can email.
        exclude_booked_last_60d: True to drop anyone who booked in the last 60 days.

    Returns:
        dict: how many customers get each action, which rule decided them, and a
        few example customers per action with the reason in plain English.
    """
    p = data.segment_params(climate, member_status, lapsed_months_min, lapsed_months_max,
                            email_only, exclude_booked_last_60d)
    rules, warnings = _load_policy()
    result = policy.summarize(data.segment_rows(p), rules)
    result["audience"] = p
    if warnings:
        result["policy_rows_skipped"] = warnings
    return result


def decide_for_customers(customer_ids: list[str]) -> dict:
    """Decide the next best action for specific customers, one by one.

    Args:
        customer_ids: Customer ids such as C000123 (up to 200). "c123" or "123"
            also work.

    Returns:
        dict: for each customer, the action, the rule that decided it, and the
        reason; plus any ids that were not found.
    """
    ids = []
    for raw in customer_ids or []:
        cid = data.norm_customer_id(raw)
        if cid and cid not in ids:
            ids.append(cid)
    ids = ids[: data.MAX_IDS]
    rules, warnings = _load_policy()
    rows = {r["customer_id"]: r for r in data.customer_rows(ids)} if ids else {}
    decisions = []
    for cid in ids:
        row = rows.get(cid)
        if row is None:
            continue
        action, rid, reason = policy.decide(row, rules)
        decisions.append({
            "customer_id": cid, "action": action, "rule": rid, "reason": reason,
            "loyalty_tier": row.get("loyalty_tier"),
            "propensity_score": round(float(row["propensity_score"]), 3) if row.get("propensity_score") is not None else None,
        })
    out = {"decisions": decisions, "not_found": [c for c in ids if c not in rows]}
    if warnings:
        out["policy_rows_skipped"] = warnings
    return out

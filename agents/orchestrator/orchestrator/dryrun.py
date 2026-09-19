"""Command-line check of the policy engine against BigQuery (no model involved).

  BQ_PROJECT=my-project python -m orchestrator.dryrun           # base, E and F audiences
  BQ_PROJECT=my-project python -m orchestrator.dryrun --ids C000123 C000456
"""
import argparse
import json

from . import tools

AUDIENCES = {
    "base (variant A)": dict(climate="cold", member_status="lapsed"),
    "variant E (all cold-market Compass browsers)": dict(climate="cold", member_status="any"),
    "variant F (E minus booked in last 60 days)": dict(climate="cold", member_status="any", exclude_booked_last_60d=True),
}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*")
    a = ap.parse_args()
    if a.ids:
        print(json.dumps(tools.decide_for_customers(a.ids), indent=2, default=str))
    else:
        print(json.dumps(tools.show_policy(), indent=2, default=str))
        for name, kw in AUDIENCES.items():
            r = tools.decide_for_segment(**kw)
            print(f"\n== {name}: {r['customers']} customers")
            for x in r["by_rule"]:
                print(f"   {x['action']:<24} {x['rule']:<5} {x['customers']:>6}")

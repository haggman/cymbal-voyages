"""Offline check of the policy engine against the Parquet files in data/out (DuckDB).

  pip install duckdb pandas pyarrow
  python tests/local_check.py
"""
import importlib.util
import pathlib
import sys

import duckdb

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parents[2] / "data" / "out"
spec = importlib.util.spec_from_file_location("policy", HERE.parent / "orchestrator" / "policy.py")
policy = importlib.util.module_from_spec(spec)
sys.modules["policy"] = policy
spec.loader.exec_module(policy)

con = duckdb.connect()
for t in ("customer_features", "decisioning_policy"):
    con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{OUT / t}/*.parquet')")


def rows(sql):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


BASE = "home_market_climate='cold' AND loyalty_tier!='none' AND warm_views_last_90d>=1"
AUD = {
    "A": f"{BASE} AND loyalty_status='lapsed'",
    "E": BASE,
    "F": f"{BASE} AND NOT booked_last_60d",
}
policy_rows = rows("SELECT * FROM decisioning_policy ORDER BY priority")
rules, warn = policy.parse_policy(policy_rows)
assert not warn, warn

fails = 0
def check(label, got, want):
    global fails
    ok = got == want
    fails += not ok
    print(("PASS " if ok else "FAIL ") + label, got if ok else f"got {got}, want {want}")

for k, where in AUD.items():
    s = policy.summarize(rows(f"SELECT * FROM customer_features WHERE {where}"), rules)
    print(f"\n{k}: {s['customers']}", [(x['rule'], x['action'], x['customers']) for x in s['by_rule']])
    if k == "A":
        got = {x['rule']: x['customers'] for x in s['by_rule']}
        check("dry run A", got, {"R08": 2801, "R06": 703, "R03": 269, "R05": 31, "R04": 20, "R02": 14})
        print("   example:", s["examples"]["send_offer"][0])
    if k == "E":
        sup = {x['rule']: x['customers'] for x in s['by_rule']}.get("R01", 0)
        check("suppress fires on E", sup > 0, True); print("   R01 on E:", sup)
    if k == "F":
        sup = {x['rule']: x['customers'] for x in s['by_rule']}.get("R01", 0)
        print("   R01 on F:", sup, "(F already removes everyone who booked in 60 days)")

# normalization: the ways a person might type the same policy
messy = [dict(r) for r in policy_rows]
for r in messy:
    if r["rule_id"] == "R02":
        r["threshold"], r["operator_2"], r["threshold_2"] = " Gold ", "≥", "60%"
    if r["rule_id"] == "R03":
        r["operator"], r["threshold"], r["threshold_2"], r["action"] = "=>", ".3", "TRUE", "Send Offer"
    if r["rule_id"] == "R04":
        r["threshold"], r["threshold_2"] = "30", "yes"
    if r["rule_id"] == "R01":
        r["threshold"], r["operator"] = "60 days", "=<"
rules2, warn2 = policy.parse_policy(messy)
s2 = policy.summarize(rows(f"SELECT * FROM customer_features WHERE {AUD['A']}"), rules2)
check("messy policy gives same A result",
      {x['rule']: x['customers'] for x in s2['by_rule']},
      {"R08": 2801, "R06": 703, "R03": 269, "R05": 31, "R04": 20, "R02": 14})
check("messy policy warnings", warn2, [])

# the natural student edit: offer threshold 0.30 -> 0.15
edit = [dict(r) for r in policy_rows]
for r in edit:
    if r["rule_id"] in ("R03", "R04", "R05"):
        r["threshold"] = "0.15"
s3 = policy.summarize(rows(f"SELECT * FROM customer_features WHERE {AUD['A']}"), policy.parse_policy(edit)[0])
print("\nthreshold 0.15 on A:", [(x['action'], x['customers'], x['share_pct']) for x in s3['by_action']])
sys.exit(1 if fails else 0)

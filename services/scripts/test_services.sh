#!/usr/bin/env bash
# End-to-end check of the deployed lab services against the reference numbers in
# data/docs/anomaly-walkthrough.md. Run in Cloud Shell from the repo root, in the lab project:
#
#   bash services/scripts/test_services.sh 2>&1 | tee services-test.log
set -uo pipefail
PROJECT="${PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
TOOLBOX_SVC="${TOOLBOX_SVC:-audience-tools}"
ORCH_SVC="${ORCH_SVC:-orchestrator}"
TB=$(gcloud run services describe "$TOOLBOX_SVC" --project "$PROJECT" --region "$REGION" --format='value(status.url)')
OR=$(gcloud run services describe "$ORCH_SVC" --project "$PROJECT" --region "$REGION" --format='value(status.url)')
TOKEN=$(gcloud auth print-identity-token)

tool() {  # tool <name> <json-params>
  curl -s -X POST "$TB/api/tool/$1/invoke" -H "Authorization: Bearer $TOKEN" \
       -H "Content-Type: application/json" -d "$2"
}
show() { python3 -c '
import json,sys
raw=sys.stdin.read()
try:
    r=json.loads(raw); res=r.get("result",r)
    res=json.loads(res) if isinstance(res,str) else res
    for row in (res if isinstance(res,list) else [res]): print("   ", json.dumps(row, default=str))
except Exception: print("    RAW:", raw[:1500])'; }

echo "== MCP endpoint lists the tools"
curl -s -X POST "$TB/mcp" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | python3 -c 'import sys,re,json; t=sys.stdin.read(); m=re.search(r"\{.*\}", t, re.S); d=json.loads(m.group(0)) if m else {}; [print("   ", x["name"], x.get("annotations")) for x in d.get("result",{}).get("tools",[])] or print("    RAW:", t[:800])'

seg() { tool resolve_segment "$1" | show; }
echo; echo "== resolve_segment, walkthrough variants A-F (want 3838/0.156, 3271, 2242/0.188, 1596/0.112, 8152/0.189, 6049/0.154)"
echo " A base";            seg '{"segment_description":"lapsed Compass members in cold markets who browsed warm destinations","climate":"cold","member_status":"lapsed"}'
echo " B email only";      seg '{"segment_description":"only the ones we can email","climate":"cold","member_status":"lapsed","email_only":true}'
echo " C lapsed 12-24";    seg '{"segment_description":"lapsed 12 to 24 months","climate":"cold","member_status":"lapsed","lapsed_months_min":12,"lapsed_months_max":24}'
echo " D lapsed 24+";      seg '{"segment_description":"lapsed more than two years","climate":"cold","member_status":"lapsed","lapsed_months_min":24}'
echo " E all members";     seg '{"segment_description":"widen to all Compass members in cold markets who browsed warm","climate":"cold","member_status":"any"}'
echo " F E minus recent";  seg '{"segment_description":"drop anyone who booked in the last 60 days","climate":"cold","member_status":"any","exclude_booked_last_60d":true}'
echo; echo "== resolve_segment, meaning match"
echo " Hawaii";            seg '{"segment_description":"lapsed cold-market members who looked at Hawaii","climate":"cold","member_status":"lapsed","destination_hint":"Hawaii"}'
echo " warm in March";     seg '{"segment_description":"lapsed members who want somewhere warm in March","climate":"cold","member_status":"lapsed","destination_hint":"somewhere warm","travel_month":3}'

echo; echo "== activate_segment: first send, then a reworded retry (want the same receipt, one row)"
SEG_ID=$(tool resolve_segment '{"segment_description":"base","climate":"cold","member_status":"lapsed"}' \
  | python3 -c 'import json,sys; r=json.load(sys.stdin)["result"]; r=json.loads(r) if isinstance(r,str) else r; print(r[0]["segment_id"])')
echo "   segment_id: $SEG_ID"
ACT1=$(python3 -c 'import json,sys; print(json.dumps({"segment_id":sys.argv[1],"segment_description":"lapsed Compass members in cold markets who browsed warm destinations","audience_size":3838,"channel":"email"}))' "$SEG_ID")
ACT2=$(python3 -c 'import json,sys; print(json.dumps({"segment_id":sys.argv[1],"segment_description":"cold-market lapsed loyalty members browsing sun trips","audience_size":3838,"channel":"email"}))' "$SEG_ID")
echo " first";  tool activate_segment "$ACT1" | show
echo " retry";  tool activate_segment "$ACT2" | show
bq query --project_id "$PROJECT" --nouse_legacy_sql --format=pretty \
  "SELECT receipt_id, channel, audience_size, segment_description, submitted_at FROM cymbal_voyages.activations ORDER BY submitted_at"

echo; echo "== variant_performance lapsed_compass_cold (want bonus_points 4.76, beach_couple 3.49, plan_your_escape 3.95)"
tool variant_performance '{"segment":"lapsed_compass_cold"}' | show

echo; echo "== orchestrator: deterministic policy dry run (want A: R08 2801, R06 703, R03 269, R05 31, R04 20, R02 14)"
python3 -m venv "${TMPDIR:-/tmp}/orch-venv" >/dev/null 2>&1 && . "${TMPDIR:-/tmp}/orch-venv/bin/activate" \
  && pip install -q google-cloud-bigquery==3.45.2 >/dev/null 2>&1 \
  && (cd agents/orchestrator && BQ_PROJECT="$PROJECT" BQ_ACCESS_TOKEN="$(gcloud auth print-access-token)" python -m orchestrator.dryrun)
deactivate 2>/dev/null || true

echo; echo "== orchestrator: served agent card"
curl -s "$OR/a2a/orchestrator/.well-known/agent-card.json" -H "Authorization: Bearer $TOKEN" | head -c 1200; echo

a2a() {  # a2a <text>
  for method in message/send SendMessage; do
    body=$(python3 -c 'import json,sys,uuid; print(json.dumps({"jsonrpc":"2.0","id":"1","method":sys.argv[1],"params":{"message":{"role":"user","messageId":str(uuid.uuid4()),"parts":[{"kind":"text","text":sys.argv[2]}]}}}))' "$method" "$1")
    out=$(curl -s -m 120 -X POST "$OR/a2a/orchestrator" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$body")
    if ! grep -Eq '"Method not found"|"code": ?-32601' <<<"$out"; then
      python3 -c '
import json,sys
d=json.loads(sys.argv[1]); texts=[]
def walk(x):
    if isinstance(x,dict):
        if "text" in x and isinstance(x["text"],str): texts.append(x["text"])
        for v in x.values(): walk(v)
    elif isinstance(x,list):
        for v in x: walk(v)
walk(d.get("result",d)); print("   ["+sys.argv[2]+"] " + (texts[-1] if texts else json.dumps(d)[:1500]))' "$out" "$method"
      return
    fi
  done
  echo "    no A2A method accepted: $out" | head -c 800
}
echo; echo "== orchestrator over A2A (the model reports the tool's numbers)"
a2a "Run the lapsed Compass members in cold markets who browsed warm destinations through the policy. How many get each action?"
a2a "Now widen it to all Compass members in cold markets who browsed warm destinations. Does anyone get suppressed?"
a2a "What should we do with customer c71, and why?"

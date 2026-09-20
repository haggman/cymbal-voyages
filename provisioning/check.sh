#!/usr/bin/env bash
# Start Lab check for mkt016. Run in Cloud Shell in the lab project, any directory:
#
#   bash check.sh                 # status of everything Start Lab provisions + timing
#   bash check.sh --reimport      # re-fire the brand-corpus import (if it never started or failed)
#
# Read-only except --reimport. Exit 0 only when everything is READY.
set -uo pipefail
P="${PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
R="${REGION:-us-central1}"
DS=cymbal_voyages
CORPUS=cymbal-voyages-brand-corpus
CORPUS_URIS='["gs://class-demo/cymbal-voyages/v1/brand_corpus/*.pdf"]'
PN=$(gcloud projects describe "$P" --format='value(projectNumber)')
GE="https://discoveryengine.googleapis.com/v1alpha/projects/$P/locations/global"
STORE="$GE/collections/default_collection/dataStores/$CORPUS"
TOK=$(gcloud auth print-access-token)
api() { curl -s -H "Authorization: Bearer $TOK" -H "X-Goog-User-Project: $P" -H "Content-Type: application/json" "$@"; }
ok=1; T=()   # T: completion timestamps for the timing summary
say() { printf '%-28s %s\n' "$1" "$2"; }
bad() { say "$1" "✗ $2"; ok=0; }

if [[ "${1:-}" == "--reimport" ]]; then
  api -X POST "$STORE/branches/default_branch/documents:import" \
    -d "{\"gcsSource\":{\"inputUris\":$CORPUS_URIS,\"dataSchema\":\"content\"},\"reconciliationMode\":\"INCREMENTAL\"}"
  echo; exit 0
fi

echo "mkt016 Start Lab check — project $P ($PN)"; echo

# 1. Identity provider (Settings → Authentication → global)
idp=$(api "$GE/aclConfig" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("idpConfig",{}).get("idpType","NOT SET"))' 2>/dev/null)
[[ "$idp" == "GSUITE" ]] && say "Identity provider" "✓ Google Identity (GSUITE)" || bad "Identity provider" "$idp"

# 2. Brand corpus: store, import operation, document count, and which apps it is attached to
store=$(api "$STORE")
if grep -q '"name"' <<<"$store"; then
  created=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("createTime",""))' <<<"$store")
  say "Corpus data store" "✓ exists (created $created)"
  ops=$(api "$STORE/branches/default_branch/operations")
  read -r odone osucc ofail oend ostart < <(python3 - "$ops" <<'PY'
import json,sys
ops=[o for o in json.loads(sys.argv[1]).get("operations",[]) if "importDocuments" in o.get("name","") or "ImportDocuments" in json.dumps(o.get("metadata",{}))]
if not ops: print("none 0 0 - -"); sys.exit()
o=sorted(ops,key=lambda o:o.get("metadata",{}).get("createTime",""))[-1]; m=o.get("metadata",{})
print(("done" if o.get("done") else "running"), m.get("successCount",0), m.get("failureCount",0), m.get("updateTime","-") if o.get("done") else "-", m.get("createTime","-"))
PY
)
  case "$odone" in
    done) if [[ "$ofail" == "0" && "$osucc" -ge 12 ]]; then say "Corpus import" "✓ done: $osucc documents, 0 failures (${ostart:11:8} → ${oend:11:8})"; T+=("$oend"); else bad "Corpus import" "done with $osucc ok / $ofail failed"; fi ;;
    running) bad "Corpus import" "running since ${ostart:11:8} ($osucc so far) — not ready yet" ;;
    *) bad "Corpus import" "no import operation found — run: bash check.sh --reimport" ;;
  esac
  attached=$(api "$GE/collections/default_collection/engines" | python3 -c "
import json,sys
e=json.load(sys.stdin).get('engines',[])
print(', '.join(x.get('displayName',x['name'].split('/')[-1]) for x in e if '$CORPUS' in x.get('dataStoreIds',[])) or 'none')")
  napps=$(api "$GE/collections/default_collection/engines" | python3 -c 'import json,sys; print(len(json.load(sys.stdin).get("engines",[])))')
  say "Corpus attached to apps" "$attached   ($napps app(s) in project; Task 1 needs 'none')"
else
  bad "Corpus data store" "missing"
fi

# 3. BigQuery warehouse job, tables, model, the numbers the lab quotes
job=$(bq ls -j -a -n 50 --format=json --project_id="$P" 2>/dev/null | python3 -c '
import json,sys
j=[x for x in json.load(sys.stdin) if x["jobReference"]["jobId"].startswith("cv_warehouse_")]
if not j: print("none"); sys.exit()
x=sorted(j,key=lambda x:int(x["statistics"].get("creationTime",0)))[-1]; s=x["statistics"]
import datetime as d
f=lambda ms: d.datetime.fromtimestamp(int(ms)/1000,d.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ms else "-"
err=x["status"].get("errorResult",{}).get("message","")
print(x["jobReference"]["jobId"], x["status"]["state"], f(s.get("startTime")), f(s.get("endTime")), (err or "ok").replace(" ","_")[:200])')
read -r jid jstate jstart jend jerr <<<"$job"
if [[ "$jid" == "none" ]]; then bad "Warehouse job" "not found"
elif [[ "$jstate" != "DONE" ]]; then bad "Warehouse job" "$jid $jstate (started $jstart)"
elif [[ "$jerr" != "ok" ]]; then bad "Warehouse job" "$jid FAILED: ${jerr//_/ }"
else say "Warehouse job" "✓ $jid done ($jstart → $jend)"; T+=("$jend"); fi

# INFORMATION_SCHEMA.TABLES lists tables only; __TABLES__ alone also counts the
# BQML model (measured Sep 19: "16 tables" = 15 + warm_escape_propensity).
tables=$(bq query --project_id="$P" --nouse_legacy_sql --format=csv \
  "SELECT t.table_name, r.row_count FROM \`$P.$DS.INFORMATION_SCHEMA.TABLES\` t JOIN \`$P.$DS.__TABLES__\` r ON r.table_id = t.table_name ORDER BY 1" 2>/dev/null | tail -n +2 | tr '\n' ' ')
# Compare against the frozen table list, and NAME any extra: every table in the
# dataset shows up in Task 1's data-agent table picker.
expected=$(gcloud storage cat gs://class-demo/cymbal-voyages/v1/schemas/_tables.json 2>/dev/null | python3 -c 'import json,sys; print(" ".join(sorted(json.load(sys.stdin))))')
actual=$(tr ' ' '\n' <<<"$tables" | cut -d, -f1 | grep -v '^$' | sort | tr '\n' ' ')
extra=$(comm -13 <(tr ' ' '\n' <<<"$expected" | sort) <(tr ' ' '\n' <<<"$actual" | sort) | grep -v '^$' | tr '\n' ' ')
missing=$(comm -23 <(tr ' ' '\n' <<<"$expected" | sort) <(tr ' ' '\n' <<<"$actual" | sort) | grep -v '^$' | tr '\n' ' ')
ntab=$(wc -w <<<"$actual")
if [[ -z "$extra$missing" ]]; then say "Tables" "✓ $ntab, exactly the frozen list"
else bad "Tables" "$ntab — extra: ${extra:-none} · missing: ${missing:-none}"; fi
empty=$(tr ' ' '\n' <<<"$tables" | awk -F, '$2==0 && $1!="activations"{print $1}' | tr '\n' ' ')
[[ -z "$empty" ]] || bad "Empty tables" "$empty"
aud=$(bq query --project_id="$P" --nouse_legacy_sql --format=csv "
  SELECT COUNT(*), ROUND(AVG(propensity_score),3), ROUND(100*COUNTIF(propensity_score>=0.30)/COUNT(*),1)
  FROM \`$P.$DS.customer_features\`
  WHERE home_market_climate='cold' AND loyalty_tier!='none' AND loyalty_status='lapsed' AND warm_views_last_90d>=1" 2>/dev/null | tail -1)
# Reference scores as shipped (no re-scoring at Start Lab, decision 2026-09-19).
[[ "$aud" == 3838,0.156,8.7 ]] && say "Audience (as the lab quotes)" "✓ $aud" || bad "Audience (as the lab quotes)" "${aud:-no result} (expect 3838,0.156,8.7; 0.162/10.3 means something re-scored)"
bq show --model "$P:$DS.warm_escape_propensity" >/dev/null 2>&1 && say "Propensity model" "✓" || bad "Propensity model" "missing"
desc=$(bq show --format=json "$P:$DS.ad_performance" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get("description",""))')
grep -q "Jul 24" <<<"$desc" && bad "ad_performance description" "still names Jul 24 (stale schemas)" || say "ad_performance description" "✓ no Jul 24 leak"

# 4. Cloud Run services
for s in audience-tools orchestrator; do
  info=$(gcloud run services describe "$s" --project "$P" --region "$R" --format=json 2>/dev/null)
  if [[ -z "$info" ]]; then bad "Cloud Run $s" "missing"; continue; fi
  read -r url ready rtime minsc < <(python3 -c '
import json,sys; d=json.load(sys.stdin); c={x["type"]:x for x in d["status"].get("conditions",[])}
r=c.get("Ready",{}); a=d["spec"]["template"]["metadata"].get("annotations",{})
print(d["status"].get("url","-"), r.get("status"), r.get("lastTransitionTime","-"), a.get("autoscaling.knative.dev/minScale","0"))' <<<"$info")
  inv=$(gcloud run services get-iam-policy "$s" --project "$P" --region "$R" --format=json 2>/dev/null)
  grep -q "service-$PN@gcp-sa-discoveryengine" <<<"$inv" && ginv=1 || ginv=0
  grep -q '"allUsers"' <<<"$inv" && pub=1 || pub=0
  if [[ "$ready" == "True" && "$minsc" == "1" && $ginv == 1 && $pub == 0 ]]; then say "Cloud Run $s" "✓ $url (min 1, GE invoker, private)"; T+=("$rtime")
  else bad "Cloud Run $s" "ready=$ready min=$minsc ge_invoker=$ginv public=$pub"; fi
done
[[ "$(gcloud run services describe orchestrator --project "$P" --region "$R" --format='value(status.url)' 2>/dev/null)" == "https://orchestrator-$PN.$R.run.app" ]] \
  || say "" "(orchestrator status.url differs from the deterministic URL; the card uses https://orchestrator-$PN.$R.run.app, which Cloud Run also serves)"

# 5. Card
card=$(gcloud storage cat "gs://$P-lab/orchestrator-card.json" 2>/dev/null)
grep -q "https://orchestrator-$PN.$R.run.app/a2a/orchestrator" <<<"$card" && ! grep -q -e supportedInterfaces -e preferredTransport <<<"$card" \
  && say "Trimmed agent card" "✓ gs://$P-lab/orchestrator-card.json" || bad "Trimmed agent card" "missing or wrong URL"

# Timing: first resource created → last thing ready.
echo
python3 - "${created:-}" "${T[@]}" <<'PY'
import sys,datetime as d
p=lambda s: d.datetime.strptime(s[:19],"%Y-%m-%dT%H:%M:%S") if s and s!="-" and len(s)>=19 else None
vals=[p(x) for x in sys.argv[1:]]
start=vals[0]; rest=[v for v in vals[1:] if v]
if start and rest:
    end=max(rest); print(f"Timing: corpus store created {start:%H:%M:%S}Z → last item ready {end:%H:%M:%S}Z = {(end-start).total_seconds()/60:.1f} min after the corpus store (add ~1 min for apply start)")
PY
echo; (( ok )) && { echo "READY"; exit 0; } || { echo "NOT READY"; exit 1; }

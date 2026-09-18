#!/usr/bin/env bash
# Load every Cymbal Voyages table from Cloud Storage into BigQuery dataset cymbal_voyages.
# Idempotent: every load uses --replace, the dataset is created only if missing, and column
# descriptions are (re)applied from schemas/*.json after each load.
#
#   PROJECT_ID=my-project ./sql/load.sh
#   PROJECT_ID=my-project BUCKET=class-demo PREFIX=cymbal-voyages/v1 LOCATION=US ./sql/load.sh
#
# Expects the layout docs/staging.md produces:
#   gs://$BUCKET/$PREFIX/out/<table>/*.parquet     (data)
#   gs://$BUCKET/$PREFIX/schemas/<table>.json      (optional; local schemas/ is used when present)
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
BUCKET="${BUCKET:-class-demo}"
PREFIX="${PREFIX:-cymbal-voyages/v1}"
DATASET="${DATASET:-cymbal_voyages}"
LOCATION="${LOCATION:-US}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMAS="$HERE/../schemas"

if [[ -z "$PROJECT_ID" ]]; then echo "Set PROJECT_ID" >&2; exit 1; fi
if [[ ! -d "$SCHEMAS" ]]; then
  SCHEMAS="$(mktemp -d)"
  gcloud storage cp "gs://$BUCKET/$PREFIX/schemas/*.json" "$SCHEMAS/" >/dev/null
fi
command -v jq >/dev/null || { echo "jq is required (apt-get install jq / brew install jq)" >&2; exit 1; }

echo "Project $PROJECT_ID · dataset $DATASET · source gs://$BUCKET/$PREFIX/out"
if ! bq --project_id="$PROJECT_ID" show --dataset "$DATASET" >/dev/null 2>&1; then
  bq --project_id="$PROJECT_ID" mk --location="$LOCATION" --dataset \
     --description "Cymbal Voyages marketing warehouse (mkt016 From Question to Campaign)" "$DATASET"
fi

TABLES=$(jq -r 'keys[]' "$SCHEMAS/_tables.json")
for t in $TABLES; do
  uri="gs://$BUCKET/$PREFIX/out/$t/*.parquet"
  desc=$(jq -r --arg t "$t" '.[$t].description' "$SCHEMAS/_tables.json")
  part=$(jq -r --arg t "$t" '.[$t].partition // empty' "$SCHEMAS/_tables.json")
  ptype=$(jq -r --arg t "$t" '.[$t].partition_type // "DAY"' "$SCHEMAS/_tables.json")
  cluster=$(jq -r --arg t "$t" '(.[$t].cluster // []) | join(",")' "$SCHEMAS/_tables.json")

  if ! gcloud storage ls "$uri" >/dev/null 2>&1; then
    if [[ "$t" == "catalog_embeddings" ]]; then
      echo "· $t: not staged yet (run embeddings/build_embeddings.py, then re-run); skipping"
      continue
    fi
    echo "· $t: nothing at $uri" >&2; exit 1
  fi

  args=(--project_id="$PROJECT_ID" load --replace --source_format=PARQUET --parquet_enable_list_inference=true)
  [[ -n "$part" ]] && args+=(--time_partitioning_field="$part" --time_partitioning_type="$ptype")
  [[ -n "$cluster" ]] && args+=(--clustering_fields="$cluster")

  # An empty Parquet file (activations) still carries its schema, but bq load treats it as an
  # error, so that table is created from the schema file instead.
  if [[ "$t" == "activations" ]]; then
    bq --project_id="$PROJECT_ID" rm -f -t "$DATASET.$t" >/dev/null 2>&1 || true
    bq --project_id="$PROJECT_ID" mk --table --description "$desc" "$DATASET.$t" "$SCHEMAS/$t.json" >/dev/null
    echo "· $t: created empty from schema"
    continue
  fi

  echo "· $t: loading"
  bq "${args[@]}" "$DATASET.$t" "$uri" >/dev/null
  # apply column descriptions (modes in the JSON are relaxed so this never fails on a mode change)
  jq '[.[] | if .mode == "REQUIRED" then .mode = "NULLABLE" else . end]' "$SCHEMAS/$t.json" > "/tmp/cv_schema_$t.json"
  bq --project_id="$PROJECT_ID" update --schema "/tmp/cv_schema_$t.json" --description "$desc" "$DATASET.$t"
  rows=$(bq --project_id="$PROJECT_ID" query --nouse_legacy_sql --format=csv "SELECT COUNT(*) FROM \`$PROJECT_ID.$DATASET.$t\`" | tail -1)
  echo "    $rows rows"
done
echo "done"

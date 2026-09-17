# Staging the data to Cloud Storage and BigQuery

Everything below is parameterized on `PROJECT_ID`, `BUCKET` and `PREFIX`. The lab's Terraform / startup script reads from `gs://$BUCKET/$PREFIX/`, so `v1` in the prefix is the data version: regenerate into `v2` rather than overwriting once labs are pointed at `v1`.

```bash
export PROJECT_ID=<your-project>       # only needed for the BigQuery and embedding steps
export BUCKET=class-demo
export PREFIX=cymbal-voyages/v1
```

## 1. Generate (or regenerate) locally

```bash
cd cymbal-voyages/data
make            # out/, schemas/, docs/ — about 30 seconds
make pdfs       # brand_corpus/pdf/*.pdf (needs pandoc + wkhtmltopdf)
```

## 2. Embeddings (needs Vertex AI in PROJECT_ID)

```bash
pip install -r embeddings/requirements.txt
PROJECT_ID=$PROJECT_ID python3 embeddings/build_embeddings.py
# writes out/catalog_embeddings/part-000.parquet (360 rows × 3,072 dims, about 9 MB)
```

## 3. Copy to Cloud Storage

`rsync` makes this idempotent; `--delete-unmatched-destination-objects` on `out/` clears any stale part files from an earlier generation.

```bash
gcloud storage rsync --recursive --delete-unmatched-destination-objects out       gs://$BUCKET/$PREFIX/out
gcloud storage rsync --recursive                                        schemas   gs://$BUCKET/$PREFIX/schemas
gcloud storage rsync --recursive                                        brand_corpus/pdf gs://$BUCKET/$PREFIX/brand_corpus
gcloud storage cp docs/data-dictionary.md docs/anomaly-walkthrough.md   gs://$BUCKET/$PREFIX/docs/
gcloud storage ls -r gs://$BUCKET/$PREFIX/ | head -50
```

Resulting layout:

```
gs://class-demo/cymbal-voyages/v1/
  out/<table>/part-NNN.parquet      one folder per table (15 folders incl. catalog_embeddings)
  out/_manifest.json                seed, row counts, reference-model metrics
  schemas/<table>.json              BigQuery schemas with column descriptions
  schemas/_tables.json              table descriptions, partition and clustering
  brand_corpus/*.pdf                12 PDFs for the Gemini Enterprise data store
  docs/                             data dictionary and anomaly walkthrough
```

Make the objects readable by the lab projects the way the other `class-demo` lab folders are (the bucket is yours; the lab's provisioning script will `bq load` from it with the student project's service account, so it needs `storage.objects.get` on the prefix).

## 4. Load into BigQuery (what the lab's startup script will do)

```bash
PROJECT_ID=$PROJECT_ID BUCKET=$BUCKET PREFIX=$PREFIX ./sql/load.sh
```

`load.sh` creates dataset `cymbal_voyages` if needed, loads every table with `--replace` (partitioned and clustered per `schemas/_tables.json`), re-applies the column descriptions from the schema files, creates the empty `activations` table from its schema, and skips `catalog_embeddings` with a note if it has not been staged yet. Needs `bq`, `gcloud` and `jq`.

## 5. Model

```bash
sed "s/PROJECT_ID/$PROJECT_ID/g" sql/train_propensity.sql   | bq query --nouse_legacy_sql
sed "s/PROJECT_ID/$PROJECT_ID/g" sql/predict_propensity.sql | bq query --nouse_legacy_sql
```

Note the elapsed time of the `CREATE MODEL` job (Job details in the console, or `bq show -j <job_id>`) and record it in `docs/data-dictionary.md` under *Propensity model*.

## 6. Gemini Enterprise data store

Point a Cloud Storage data store at `gs://$BUCKET/$PREFIX/brand_corpus/` (unstructured documents, PDF). The Markdown sources in `brand_corpus/*.md` are the ones to edit; re-run `make pdfs` and step 3 after any change.

## Verifying a load

```bash
bq query --nouse_legacy_sql "SELECT table_id, row_count FROM \`$PROJECT_ID.cymbal_voyages.__TABLES__\` ORDER BY table_id"
```

Expected row counts are in `out/_manifest.json`. Then run any query from `docs/anomaly-walkthrough.md`; the numbers must match the document exactly.

# Cymbal Voyages data foundation (mkt016 · From Question to Campaign)

Seeded, deterministic synthetic warehouse for the Gemini Enterprise marketing lab: 50,000 customers, 570,000 web sessions, 49,000 bookings, daily ad spend, a plan, a campaign history with creative results, a customer-feature table with a warm-escape propensity score, a decisioning policy, and a 12-document brand corpus. The story it encodes (August 2026 warm-escape bookings 18% under plan because the retargeting budget for lapsed Compass members in cold-weather markets was rotated to Fall City Breaks on July 24, 2026) is documented with exact numbers in `docs/anomaly-walkthrough.md`.

```
make            # nothing → out/ (Parquet), schemas/ (BigQuery JSON), docs/ (dictionary + walkthrough), ~30 s
make pdfs       # brand_corpus/pdf/*.pdf (pandoc + wkhtmltopdf)
make embeddings # out/catalog_embeddings/ via Vertex AI gemini-embedding-001 (needs PROJECT_ID)
make stage      # gcloud storage rsync to gs://class-demo/cymbal-voyages/v1/   (see docs/staging.md)
make load       # bq load into $PROJECT_ID:cymbal_voyages                        (sql/load.sh)
```

| Path | What |
| --- | --- |
| `generate_warehouse.py`, `cvgen/` | The generator. `cvgen/config.py` holds every knob (seed, row counts, calendar, anomaly depth); `activity.py` is the month-by-month customer simulation; `schemas.py` is the single source of column descriptions. |
| `content/` | Hand-written inputs: 60 destination descriptions (`destinations.json`), the campaign roster with the numbers the briefs quote (`campaigns.json`). |
| `out/<table>/part-*.parquet`, `out/_manifest.json` | Generated data (one folder per table; total about 22 MB) and a manifest with row counts and the reference model's metrics. |
| `schemas/*.json`, `schemas/_tables.json` | BigQuery schemas with marketer-facing column descriptions; table descriptions, partitioning and clustering. |
| `sql/load.sh` | Idempotent `bq load` of every table with partitioning, clustering and descriptions. |
| `sql/train_propensity.sql`, `sql/predict_propensity.sql` | BigQuery ML `LOGISTIC_REG` and the scoring statement that fills `customer_features.propensity_score`. |
| `sql/walkthrough_queries.py`, `sql/verify_local.py`, `sql/build_walkthrough.py`, `sql/build_dictionary.py` | The SQL trail (BigQuery dialect), a DuckDB runner that executes it against `out/` with no cloud access, and the two doc renderers. |
| `embeddings/build_embeddings.py` | Embeds destination and package text (gemini-embedding-001, 3,072 dims) into `out/catalog_embeddings/`. |
| `brand_corpus/*.md`, `brand_corpus/build_pdfs.sh` | The agency onboarding packet (Markdown is the source of truth) and its PDF renderer. |
| `docs/data-dictionary.md` | Every table and column, the data-agent instructions, glossary and verified queries, model and embedding details. |
| `docs/anomaly-walkthrough.md` | The query trail from "August missed" to the finding, with the numbers each query returns, plus the red herrings and the audience, creative and policy queries. |
| `docs/staging.md` | The `gcloud storage` and `bq` commands to stage and load. |

Regenerating with the same seed reproduces every file byte for byte (`out/_manifest.json` records the seed and a generation timestamp; everything else is identical). Change a knob and the plan, the training set, the docs and the walkthrough numbers all follow.

Python 3.11+, `pip install -r requirements.txt` (pandas, pyarrow, numpy, scikit-learn, duckdb). No Google Cloud access is needed until `make embeddings` / `make stage` / `make load`.

# mkt016 provisioning (Start Lab)

Everything that has to exist in a student's project when they click **Start Lab** for *From Question to Campaign*. Students never touch this; it's here for the curious (plan decision D7).

- `terraform/` is the tree the Qwiklabs startup-script runner applies. The copy Qwiklabs actually runs is mirrored into `gcp-ce-content/labs/mkt016-from-question-to-campaign/terraform/` by `sync.sh`.
- `terraform/files/` is **generated** by `sync.sh` from the canonical repo files (`services/toolbox/tools.yaml`, `agents/orchestrator/orchestrator/agent.card.template.json`, `data/sql/train_propensity.sql`). Never edit it by hand. After changing any source, run `bash provisioning/sync.sh`. `bash provisioning/sync.sh --check` fails if anything is out of step.
- `check.sh` runs in Cloud Shell in the lab project. It reports everything below plus the timing, and exits 0 only when all of it is ready.

## What runs, in order

The runner's whole command line is `terraform apply -var gcp_project_id=… -var gcp_zone=… -var gcp_region=… -auto-approve`. `username` arrives through `custom_properties` in `qwiklabs.yaml`. Terraform runs everything in parallel except where there's a dependency, so the order below is the critical path.

| # | What | How | Time |
| :-- | :-- | :-- | :-- |
| 1 | **Brand corpus** data store *Cymbal Voyages Brand Corpus*: Layout Parser, location `global`, unattached to any app | `google_discovery_engine_data_store`, then the one REST call `documents:import` over `gs://class-demo/cymbal-voyages/v1/brand_corpus/*.pdf` via the `http` data source. It starts in the first wave, behind only the Discovery Engine API enable and a 30 s settle. | import ~10 min (S8); keeps running after apply |
| 2 | Identity provider = **Google Identity** at `global` | `google_discovery_engine_acl_config`, `idp_type = GSUITE` | seconds |
| 3 | APIs, Discovery Engine service identity, student roles (dataAgentCreator, dataAgentUser, discoveryengine.admin), two runtime service accounts and their roles | native | < 1 min |
| 4 | BigQuery: dataset `cymbal_voyages` (US), 15 tables with schemas, descriptions, partitioning and clustering read **at plan time** from `gs://class-demo/cymbal-voyages/v1/schemas/` | `google_bigquery_table` ×15 | seconds |
| 5 | One BigQuery **script job**: `LOAD DATA INTO` ×14 (activations stays empty), then `train_propensity.sql`. **No re-scoring**: `customer_features` keeps its shipped scores, which every number in the lab was verified on (decision Sep 19) | `google_bigquery_job` | 2 min measured; keeps running after apply |
| 6 | Cloud Run `audience-tools` (Toolbox 1.12.0, `tools.yaml` from secret `audience-tools-config`) and `orchestrator` (1.0.0, `GOOGLE_CLOUD_LOCATION=global`, `AGENT_URL` = its own deterministic URL). Both min instances 1, private, `run.invoker` for the Discovery Engine agent | `google_cloud_run_v2_service`, after a 30 s IAM settle | ~1–2 min |
| 7 | Trimmed agent card → `gs://<project>-lab/orchestrator-card.json` (also a Terraform output) | `google_storage_bucket_object` | seconds |

**Two things finish after the apply returns, by design:** the BigQuery script job (the provider's `google_bigquery_job` only waits for the job to *exist*) and the corpus import (a long-running operation). Nothing in the tree needs either to finish. "Everything ready" in the timing log means both are done. `check.sh` reports them.

## What it does not do (student steps)

Gemini Enterprise app and feature toggles (Task 0), the BigQuery data agent (Task 1), the Audience Tools custom MCP data store (Task 3), attaching the brand corpus to the app (Task 4), and registering the orchestrator by card (Task 6).

Why the corpus starts unattached: an app's "connectors" are its engine's `dataStoreIds`, and the Discovery Engine API has no separate per-app "disabled" flag. At Start Lab there's no app, so there's nothing to disable. The store simply isn't connected until Task 4, so Task 1's bare assistant can't read the Fall City Breaks brief. `check.sh` prints which apps the corpus is attached to, so you can confirm Task 0's app creation doesn't attach it automatically.

## Access it needs

- **The Terraform runner's identity** reads `gs://class-demo/cymbal-voyages/v1/schemas/*` at plan time and `…/out/*` in the load job.
- **The lab project's Discovery Engine service agent** (`service-PN@gcp-sa-discoveryengine.iam.gserviceaccount.com`) reads `…/brand_corpus/*.pdf`. The spike proved it can.

Both principals differ per project, so the prefix needs `allAuthenticatedUsers` (or `allUsers`) → Storage Object Viewer, the same as the other lab folders.

## When it fails

| Symptom | Where | Fix |
| :-- | :-- | :-- |
| Apply fails at **plan** reading `_tables.json` | the runner can't read `class-demo` | Grant object read on the prefix (see above) |
| `Brand corpus import did not start (HTTP 403) … storage.buckets.create` | the Discovery Engine agent's storage grant hadn't propagated (the import creates a staging bucket in the project) | Raise `time_sleep.ge_agent_settle`; re-running apply retries the import |
| `Brand corpus import did not start (HTTP …)`, any other error | the `http` data source | Read the body. 403 means the runner lacks `discoveryengine` rights, or the API isn't settled yet (raise the 30 s sleep). Retry by hand: `bash check.sh --reimport` |
| `acl_config` error | identity provider can't be set before Gemini Enterprise is activated | Delete that block; Task 0 sets Google Identity by hand |
| `audience-tools` fails with `Error code 7 … internal error` (or a secret permission error) | IAM propagation to the secret (measured Sep 19 at 30 s) | Raise `time_sleep.iam_settle` (now 60 s, plus a grant on the secret itself) |
| `check.sh`: warehouse job FAILED | the SQL (error text shown) | Re-run it: the job's SQL is in BigQuery → Job history, and it's safe to re-run (TRUNCATE + LOAD) |
| `check.sh`: audience not 3838 / 0.156 / 8.7 | the data isn't v1, or something re-scored `customer_features` (0.162 / 10.3 is the re-scored state) | Check the job SQL; Start Lab must not run `predict_propensity.sql` |
| `check.sh`: ad_performance still names Jul 24 | stale schemas in the bucket | Re-stage `schemas/` from the repo (SC1 fix d7c1734) |
| Corpus attached to an app during Task 1 | Task 0's app creation auto-attached it | Make it a Task 0 step: remove it from the app's connected data stores |

## Timing

See `TIMING.md`. Target is under 10 min to everything ready; 15 is the ceiling.

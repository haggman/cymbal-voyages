# Cymbal Voyages lab services (mkt016): contracts and deploy facts

This file is the hand-off from the services build (SC2) to provisioning (SC3) and to the lab writers. It assumes you have never seen the conversations that produced it.

The lab runs two services on Cloud Run, both pre-built as container images and deployed at Start Lab:

| Service | What it is | Gemini Enterprise connects to it as | Used in |
| :-- | :-- | :-- | :-- |
| **Audience Tools** | MCP Toolbox for Databases, configured by `services/toolbox/tools.yaml`, with three tools over the `cymbal_voyages` BigQuery dataset | a **custom MCP server data store** (admin console → Connected data stores → Create → Custom MCP server) | Task 3 (resolve and activate), Task 5 (variant performance, attached to Brand Studio) |
| **Orchestrator** | an ADK agent served over A2A, in `agents/orchestrator/` | a **custom agent via A2A** (admin console → Agents → + Add agent → Custom agent via A2A → paste the card) | Task 6 |

There is no analyst service (Task 1 uses the BigQuery data agent the students build) and no image service (Brand Studio, a Gemini Enterprise chat agent, generates images itself).

---

## Part 1. The tools, in a marketer's words

These are the contracts the lab asks students to read. The Builder reads them in `tools.yaml`; the Marketer meets `activate_segment`'s contract on the **Review: Activate Segment** card. The Gemini Enterprise Actions tab shows only the names (**Resolve Segment**, **Activate Segment**, **Variant Performance**), not these details.

### Resolve Segment (`resolve_segment`): read-only, runs without asking

**What it does.** Sizes an audience and tells you how good it is. Every audience starts as Cymbal Compass loyalty members who looked at a warm-escape destination in the last 90 days (June 3 to August 31, 2026). Your description narrows it.

**What you say to it.** Describe the audience in plain English, and refine it out loud. Gemini turns your words into the tool's choices:

| You say | The tool hears |
| :-- | :-- |
| "lapsed Compass members in cold markets who browsed warm destinations" | climate = cold, member status = lapsed (no booking in 12+ months) |
| "only the ones we can email" | email only = yes |
| "lapsed 12 to 24 months" | last booking at least 12 and under 24 months ago |
| "lapsed more than two years" | last booking 24+ months ago |
| "widen to all Compass members in cold markets who browsed warm" | member status = any |
| "drop anyone who booked in the last 60 days" | remove recent bookers = yes |
| "who looked at Hawaii" / "somewhere quiet with snorkeling" | the five catalog destinations closest in meaning; only customers who viewed one of them count |
| (no place or kind of trip named) | destination hint = none (a required field; Gemini fills it) |
| "somewhere warm in March" | the meaning match, limited to destinations at their best in March |

**What comes back** (one row):

| Field | Meaning |
| :-- | :-- |
| `segment_id` | a readable name for exactly what was counted, e.g. `cold markets | lapsed members | any time since last booking | any contact | recent bookers kept | viewed any warm escape` |
| `segment_description` | your words, unchanged |
| `customers` | how many customers are in the audience |
| `avg_propensity` | average likelihood to book a warm escape in the next 60 days (0 to 1) |
| `pct_propensity_ge_030`, `strong_propensity_customers` | the share and number with a strong likelihood (0.30 or higher) |
| `email_contactable` | how many we can email |
| `destinations_matched` | which destinations the meaning match chose, or "any warm-escape destination" |
| `data_as_of` | 2026-09-01, the date the customer features were computed |

**What it never does.** It never changes data, never contacts anyone, and never returns individual customers. That is why it carries `readOnlyHint` and Gemini Enterprise runs it without a confirmation prompt.

**Reference answers** (reference propensity scores, as shipped; after BigQuery ML re-scoring, averages move slightly: the base becomes 0.162 and 10.3%):

| Variant (Task 3 refinement) | customers | avg propensity | ≥ 0.30 | email-contactable |
| :-- | --: | --: | --: | --: |
| A. base: lapsed, cold, browsed warm | 3,838 | 0.156 | 8.7% | 3,271 |
| B. A, email only | 3,271 | 0.156 | 8.6% | 3,271 |
| C. A, lapsed 12–24 months | 2,242 | 0.188 | 13.5% | 1,908 |
| D. A, lapsed 24+ months | 1,596 | 0.112 | 2.0% | 1,363 |
| E. all Compass members, cold, browsed warm | 8,152 | 0.189 | 14.9% | 6,952 |
| F. E, minus anyone who booked in the last 60 days | 6,049 | 0.154 | 9.1% | 5,137 |

### Activate Segment (`activate_segment`): asks before it acts

**What it does.** Sends an audience to a channel and returns the activation receipt. In this lab the "channel" is a stand-in: it writes one receipt row to `cymbal_voyages.activations` and nothing else. The contract is the lesson; in production the same four fields would go to an ad platform, a CDP or an email service.

**What you say to it.** "Activate that audience to email." Gemini fills the four fields from the last Resolve Segment result and shows the **Review: Activate Segment** card, where you can check and edit them before you click **Send**:

| Field on the card | Meaning |
| :-- | :-- |
| Segment Id | copied from Resolve Segment; it names what was counted |
| Segment Description | the audience in plain English, printed on the receipt |
| Audience Size | the count Resolve Segment reported |
| Channel | email, paid_social or paid_search |

**What comes back.** The receipt: `receipt_id` (e.g. `act-3f1c…`), `segment_description`, `audience_size`, `channel`, `submitted_at`, `status` (`accepted`), and a `note` saying whether this was a new activation or a repeat.

**What it never does.** It never sends the same audience to the same channel twice. The receipt ID is built from the segment ID and the channel, not from the wording, so a retry, even one described in different words, returns the original receipt with the note "already activated … nothing was sent twice", and the table keeps one row. It deliberately does **not** carry `readOnlyHint`, so Gemini Enterprise always asks first: that confirmation is a teaching moment.

### Variant Performance (`variant_performance`): read-only, runs without asking

**What it does.** Shows which creative actually converted for a segment in past campaigns, so new creative starts from evidence. Its description tells an agent to call it **before generating or suggesting any creative**.

**What you say to it.** "What has worked for lapsed Compass members in cold markets?" Segments: `lapsed_compass_cold`, `lapsed_compass`, `active_compass`, `all_customers`, `prospects`, `urban_explorers`, `ski_enthusiasts`, `cruise_interest`, `adventure_seekers`.

**What comes back.** One row per option, for each of three creative choices (offer framing, hero image style, call to action): `rank`, `option`, `variants`, `clicks`, `bookings`, `booking_rate_pct` (bookings per click, click-weighted), best first. For `lapsed_compass_cold`:

| Choice | Best | Worst |
| :-- | :-- | :-- |
| offer framing | bonus_points 4.76% | percent_off 1.49%, urgency 1.49% |
| hero image style | beach_couple 3.49% | adventure 1.97% (city_skyline 1.98%) |
| call to action | plan_your_escape 3.95% | claim_offer 2.10% |

For `all_customers`, percent_off wins (1.63%): the learning is segment-specific.

**What it never does.** It never changes data and never generates creative itself.

### The Orchestrator (A2A agent)

**What it does.** Decides the next best action for every customer in an audience: **send_offer**, **route_to_loyalty_team**, **hold_for_retargeting** or **suppress**. It reads the `decisioning_policy` table fresh on every call and applies the enabled rules in priority order; the first rule that matches decides; anyone no rule matches is held for retargeting. The model never picks an action itself; it calls the policy engine and explains the result.

**What you say to it.** "Run the lapsed Compass members in cold markets who browsed warm destinations through the policy." / "Now widen it to all Compass members in cold markets." / "What should we do with C000071, and why?" / "What rules are you applying?" / (after the Builder edits the table) "Run it again."

**What comes back.** How many customers get each action, which rule decided them, and example customers with the reason from the rule's `reason_template` ("Propensity 0.56 clears the offer threshold and the customer accepts email."). For named customers: the action, rule and reason per customer.

**What it never does.** It never overrides the policy, never contacts customers, and never writes to any table. It does not depend on how a person types the policy table: tier names in any case (`Gold`, ` gold `), thresholds as `0.3`, `.30`, `30%` or `30` (for 0–1 scores), yes/no values as `true`, `TRUE`, `yes`, operators as `>=`, `≥`, `=>`, `=`, and actions as `send offer` or `send_offer` all read the same. A row it cannot read is skipped and reported, never guessed at. A row with `enabled` left empty counts as enabled.

**Reference answers** (default policy, reference scores):

| Audience | send_offer | route_to_loyalty_team | hold_for_retargeting | suppress |
| :-- | --: | --: | --: | --: |
| Base (variant A), 3,838 | 289 (R03 269, R04 20) | 14 (R02) | 3,535 (R08 2,801, R06 703, R05 31) | 0 |
| Variant E, 8,152 | 466 (R03 434, R04 32) | 38 (R02) | 5,545 (R08 4,686, R06 813, R05 46) | **2,103 (R01)** |
| Variant F, 6,049 | 466 | 38 | 5,545 | 0 |
| Base, offer threshold lowered 0.30 → 0.15 (R03, R04, R05) | 1,082 (28%) | 14 | 2,742 | 0 |

Suppress (R01, "booked in the last 60 days") fires on **variant E**, which includes recent bookers. Variant F removes exactly those customers, so suppress cannot fire there.

---

## Part 2. Deploy facts for provisioning

### Images (public Artifact Registry, pull without a grant)

Published Sep 19 in the long-lived project **`class-demo-labs`** (public read): Toolbox **1.12.0**, orchestrator **1.0.0**.

| Service | Image | Notes |
| :-- | :-- | :-- |
| Audience Tools | `us-central1-docker.pkg.dev/class-demo-labs/cymbal-voyages/toolbox:1.12.0` | a mirror of Google's `us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox` at that pinned version, never `:latest` |
| Orchestrator | `us-central1-docker.pkg.dev/class-demo-labs/cymbal-voyages/orchestrator:1.0.0` | built from `agents/orchestrator/` (Python 3.12, google-adk 2.9.2, a2a-sdk 1.1.4, google-cloud-bigquery 3.45.2) |

Rebuild and republish with `bash services/scripts/build_images.sh` (it publishes to the current gcloud project, or `IMAGE_PROJECT=...`).

**Where the images live.** `us-central1-docker.pkg.dev/class-demo-labs/cymbal-voyages`, public read (`allUsers` → Artifact Registry Reader), so every lab project pulls without a grant. `deploy_services.sh` defaults to it and reads the newest Toolbox and orchestrator tags from it. To publish a new version, run `build_images.sh` in Cloud Shell in `class-demo-labs` (it sets up the APIs, the Cloud Build service account's roles and the repo on first run). The Sep 19 test build also left copies in the spike project; ignore them. **Verified Sep 19:** `deploy_services.sh` run with defaults in the spike Qwiklabs project pulled both images from `class-demo-labs` across projects, and `test_services.sh` passed, so a student lab project can use them with no grant.

### Reference deployment

`services/scripts/deploy_services.sh` is the executable version of everything below; Terraform should reproduce it. Region `us-central1`. Prerequisite: the `cymbal_voyages` dataset is loaded (and scored).

**APIs:** `run`, `secretmanager`, `bigquery`, `aiplatform`, `discoveryengine`. Create the Discovery Engine service identity (`gcloud beta services identity create --service=discoveryengine.googleapis.com`) so the invoker grant below has a member to bind.

**Audience Tools**

| Setting | Value |
| :-- | :-- |
| Cloud Run service | `audience-tools` |
| Image | `us-central1-docker.pkg.dev/class-demo-labs/cymbal-voyages/toolbox:1.12.0` |
| Runtime service account | `audience-tools-sa@PROJECT.iam.gserviceaccount.com` |
| Its project roles | `roles/bigquery.jobUser`, `roles/bigquery.dataViewer`, `roles/bigquery.dataEditor` (the receipt row), `roles/secretmanager.secretAccessor`, **`roles/aiplatform.user`** (the meaning match embeds the destination hint with `gemini-embedding-001` on Vertex AI) |
| Secret | `audience-tools-config`, created from `services/toolbox/tools.yaml` **unchanged** (the file reads the project from the environment) |
| Secret mount | `--set-secrets /secrets/tools.yaml=audience-tools-config:latest` |
| Args | `--tools-file=/secrets/tools.yaml,--address=0.0.0.0,--port=8080` |
| Env vars | `GOOGLE_CLOUD_PROJECT=<lab project id>` (required: BigQuery jobs and embeddings run there) |
| Scaling | `--min-instances=1` |
| Auth | `--no-allow-unauthenticated` |
| Invoker | `roles/run.invoker` on the service for `service-PROJECT_NUMBER@gcp-sa-discoveryengine.iam.gserviceaccount.com` |
| What the student pastes | the service URL + `/mcp`, authentication **None** (Cloud Run IAM does the work; Gemini Enterprise sends a Google-signed ID token as its service agent) |

**Orchestrator**

| Setting | Value |
| :-- | :-- |
| Cloud Run service | `orchestrator` |
| Image | `us-central1-docker.pkg.dev/class-demo-labs/cymbal-voyages/orchestrator:1.0.0` |
| Runtime service account | `orchestrator-sa@PROJECT.iam.gserviceaccount.com` |
| Its project roles | `roles/bigquery.jobUser`, `roles/bigquery.dataViewer`, `roles/aiplatform.user` |
| Env vars | `GOOGLE_CLOUD_PROJECT=<project>`, **`GOOGLE_CLOUD_LOCATION=global`** (Gemini 3.x returns 404 in us-central1; also pinned in code), `GOOGLE_GENAI_USE_VERTEXAI=TRUE`, `BQ_PROJECT=<project>`, `BQ_DATASET=cymbal_voyages`, `ORCHESTRATOR_MODEL=gemini-3.5-flash`, `AGENT_URL=https://orchestrator-PROJECT_NUMBER.us-central1.run.app` |
| Scaling / memory | `--min-instances=1`, `--memory 1Gi` |
| Auth | `--no-allow-unauthenticated` |
| Invoker | `roles/run.invoker` for the Discovery Engine service agent (as above) |

`AGENT_URL` is the service's own URL. Cloud Run URLs are deterministic (`https://SERVICE-PROJECT_NUMBER.REGION.run.app`), so provisioning can set it on the first deploy. At start-up the container writes it into the card it serves.

### The agent card

- **Served at:** `https://orchestrator-PROJECT_NUMBER.us-central1.run.app/a2a/orchestrator/.well-known/agent-card.json`. The A2A library rewrites the served card in its newer format (it moves the URL into `supportedInterfaces`), which Gemini Enterprise's *Custom agent via A2A* dialog rejects. **Do not ask students to copy the served card.**
- **What students paste:** the trimmed card, `agents/orchestrator/orchestrator/agent.card.template.json` with `__AGENT_URL__` replaced by the service URL. It has no `supportedInterfaces` and no `preferredTransport`. `deploy_services.sh` writes it to `orchestrator-card.json`. Provisioning should write the same file somewhere the lab can show it (for example a Cloud Storage object in the lab project, or a lab output), or the lab can build it with one `sed` in Cloud Shell.

```json
{
  "name": "Cymbal Voyages Orchestrator",
  "description": "Decides the next best action for each customer in an audience (send an offer, route to the loyalty team, hold for retargeting, or suppress) by applying Cymbal Voyages' decisioning policy table, and explains every decision in plain English.",
  "url": "https://orchestrator-PROJECT_NUMBER.us-central1.run.app/a2a/orchestrator",
  "version": "1.0.0",
  "protocolVersion": "0.3.0",
  "capabilities": {"streaming": true},
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"],
  "skills": ["… three skills: decide_for_segment, decide_for_customers, show_policy; see the template file …"]
}
```

### Toolbox 1.12 behaviours the design depends on

- Tools are served **only over MCP** (`POST /mcp`, JSON-RPC `tools/list` and `tools/call`). The older `/api/tool/...` REST endpoints return `410 Gone` ("disabled by default"). Gemini Enterprise uses MCP, so nothing in the lab is affected.
- A parameter that uses `valueFromParam` + `embeddedBy` is copied from its source **before** defaults apply, so the source can't be optional. That's why `destination_hint` is required (Gemini sends `none` when no place was named).
- `bigquery-sql` runs a multi-statement script (`DECLARE` … `MERGE` … `SELECT`) and returns the final `SELECT`'s rows. `activate_segment` relies on this.
- `annotations:` in `tools.yaml` reach the MCP `tools/list` response as written (`readOnlyHint`, `destructiveHint`, `idempotentHint`).
- `${GOOGLE_CLOUD_PROJECT}` in `tools.yaml` is substituted from the service's environment, so one file works in every lab project.

### Verifying a deployment

`bash services/scripts/test_services.sh` (Cloud Shell, repo root, lab project) calls every tool over MCP (`tools/call` on `/mcp`; Toolbox 1.x disables its old `/api` REST endpoints), checks the receipt retry, runs the orchestrator's policy engine against BigQuery, fetches the served card, and asks the orchestrator three questions over A2A. The numbers must match the reference answers above.

### Files

```
services/toolbox/tools.yaml          the three tools (the file the lab shows the Builder)
services/toolbox/spike/tools.yaml    the Sep 18 spike version, kept for the record
services/scripts/build_images.sh     publish both images (image project)
services/scripts/deploy_services.sh  reference deployment into a lab project
services/scripts/test_services.sh    end-to-end check against the reference answers
agents/orchestrator/                 ADK agent: orchestrator/{agent,tools,policy,data,dryrun}.py,
                                     agent.card.template.json, Dockerfile, entrypoint.sh, requirements.txt
agents/orchestrator/tests/local_check.py   offline check of the policy engine against data/out (DuckDB)
```

---

## Part 3. Test run (Sep 19, spike project `qwiklabs-gcp-04-df5f1f023984`, reference propensity scores)

`test_services.sh` against the deployed services. Every number matches `data/docs/anomaly-walkthrough.md`.

| Check | Result |
| :-- | :-- |
| MCP `tools/list` | 3 tools; resolve_segment and variant_performance `readOnlyHint: true`; activate_segment `readOnlyHint: false, idempotentHint: true` |
| A base | 3,838 · 0.156 · 8.7% (334) · 3,271 email |
| B email only | 3,271 · 0.156 · 8.6% |
| C lapsed 12–24 months | 2,242 · 0.188 · 13.5% · 1,908 email |
| D lapsed 24+ months | 1,596 · 0.112 · 2.0% |
| E all Compass members | 8,152 · 0.189 · 14.9% · 6,952 email |
| F E minus booked in 60 days | 6,049 · 0.154 · 9.1% · 5,137 email |
| "Hawaii" (lapsed, cold) | 2,005 · 0.191; matched Maui, Oahu, Kauai, Hawaiian Islands Cruise **and Key West** (the catalog has only four Hawaii items, so the fifth-closest is filled from elsewhere; the answer lists the matches, so the marketer can see it) |
| "somewhere warm" + March (lapsed, cold) | 2,326 · 0.187; matched Key West, Los Cabos, Maui, Montego Bay, Tulum and the Riviera Maya |
| activate, then reworded retry | first: `act-0eb274a679ac`, "New activation recorded."; retry with a different description: **same receipt**, original timestamp, "already activated … nothing was sent twice"; one row for that receipt |
| variant_performance lapsed_compass_cold | bonus_points 4.76 · beach_couple 3.49 · plan_your_escape 3.95 (all three tables match exactly) |
| orchestrator dry run, base | R08 2,801 · R06 703 · R03 269 · R05 31 · R04 20 · R02 14 |
| orchestrator, variant E | suppress (R01) **2,103** of 8,152 |
| orchestrator, variant F | suppress 0 (F already removes recent bookers) |
| orchestrator over A2A | reported the same counts in prose (3,535 / 289 / 14; then 2,103 suppressed); "c71" normalized to C000071 → send_offer, R03, propensity 0.56 |
| served card | A2A-1.x format with `supportedInterfaces`, as expected; students paste the trimmed card |

The `activations` table in the spike project holds leftover rows from Phase 1 and earlier test runs; a fresh lab starts empty.

## Part 4. Decisions made in the build that the plan left open

1. **Toolbox is mirrored, not referenced.** The lab pulls `toolbox:1.12.0` from our public repo, not Google's registry, so a Google-side change can't break Start Lab.
2. **`resolve_segment` takes structured choices plus the marketer's words.** Gemini maps phrasing to `climate`, `member_status`, `lapsed_months_min/max`, `email_only`, `exclude_booked_last_60d`, `destination_hint` and `travel_month`; the description carries the phrase-to-choice table. The marketer's words are echoed back unchanged.
3. **Meaning match: top 5 destinations by cosine distance** on `catalog_embeddings`. The hint is embedded inside Toolbox (Vertex AI `gemini-embedding-001`, 3,072 dims), so provisioning needs **no BigQuery connection or remote model**, only `roles/aiplatform.user` on the Toolbox service account. The 90-day viewing window matches `warm_views_last_90d` (Jun 3 – Aug 31, 2026).
4. **A readable `segment_id` is the activation key.** The receipt is `act-` + MD5(segment_id | channel). This puts a fifth field, **Segment Id**, on the Review card (Channel, Audience Size, Segment Description, Segment Id). Task 3's text should name it.
5. **`activate_segment` returns a `note`** saying whether the activation is new or a repeat, so the retry beat reads clearly in the chat.
6. **Channels limited to email, paid_social and paid_search** (`allowedValues`).
7. **The orchestrator's model never decides.** Python applies the policy; the model picks the tool and explains. Rows it can't read are skipped and reported; `enabled` left empty counts as enabled; `priority` ties break on `rule_id`.
8. **Orchestrator segments use the same filters as `resolve_segment`** (no destination match), so "run the Task 3 audience through the policy" gives matching counts.
9. **Suppress is shown on variant E, not F.** F removes exactly the customers R01 would suppress. The plan's Task 6 wording ("the variant that includes recent bookers") already means E.
10. **Lowering the offer threshold to 0.15 sends offers to 1,082 of 3,838 (28%)**, not "about a third". Task 6 should quote 28%.
11. **Separate service accounts** (`audience-tools-sa`, `orchestrator-sa`) with least privilege; the orchestrator cannot write to BigQuery.
12. **Orchestrator model `gemini-3.5-flash`** (as in the spike), overridable by `ORCHESTRATOR_MODEL`.
13. **Card URL filled at start-up from `AGENT_URL`**, which provisioning can compute before deploying because Cloud Run URLs are deterministic.

# mkt016 — From Question to Campaign: Build Plan

**Lab:** `mkt016-from-question-to-campaign` (folder, yaml title, and H1 must match)
**Story:** Cymbal Voyages, agentic marketing with Gemini Enterprise
**Contract:** SOW signed 8/27/2026 ($50k): the 3-hour lab per the outline, a video walkthrough (recorded after the event), deployment to explore.qwiklabs.com with Google's help, one year of maintenance
**Outline (contract reference):** Google Doc `1QpDrDXjh7FL3VLIxvCN7EApEyrFZlZRRq68r6veONTI` — speculative and malleable; we retrofit it at the end as the record of what was built
**Event:** ~Sep 30, 2026. Content done by Fri Sep 25, Mon Sep 28 at the latest. Qwiklabs publishing lead time is negligible.
**Repos:** lab markdown in `gcp-ce-content/labs/mkt016-from-question-to-campaign/` (branch `mkt016`); everything else in `DevWork/cymbal-voyages` → `github.com/haggman/cymbal-voyages`
**Data staging:** `gs://class-demo/cymbal-voyages/v1/` (frozen once labs point at it; regenerate into `v2`)
**Planning docs:** this file plus `mkt016-handoff-*.md` in the project's `claude/` folder; spike record in `cymbal-voyages/docs/spike-findings.md` and `docs/sc2-phase1-handback.md`

Last updated: 2026-09-19 (planning conversation, day 4)

**Status (Sep 19, evening):** SC1 data foundation delivered, staged, and fixed (§6a). Spike S1–S8 finished Sep 18 (§4); the six decisions are made (§4a). **SC2 Phase 2 done and tested Sep 19:** both services built, images public in `class-demo-labs`, every number matches the walkthrough (§7a). SC3 (provisioning) can open now. SC4 (Tasks 0–2) is writing. Two things still untested inside Gemini Enterprise go on the Sep 21 walk (§10, R10).

---

## 1. Decisions locked on day 1 (D6 and D8 corrected Sep 19)

| # | Decision | Why |
| :-- | :-- | :-- |
| D1 | Lab 3 is ignored entirely. Task 7 wraps the loop and stops; no tee-up. | Google gave no answer on §9.1. |
| D2 | We synthesize the warehouse and write the brand corpus ourselves. | No Google data. Public travel datasets have none of the ad-spend, CRM, loyalty, or creative-outcome dimensions, and a planted anomaly is easier to build than to retrofit. |
| D3 | The anomaly is **August 2026** warm-escapes bookings, 18% under plan. Monday's readout explains August; Friday's campaign is the **fall recovery campaign** for the October–November booking window (winter warm-escape travel). Fixed dates in the data. | The outline mixed March and July; a reviewer wanted fall. Early-bird winter-sun bookings open in late summer, so an August miss is credible, and the lab must read the same way for a year. |
| D4 | Pairs share **one lab project** (one partner starts the lab, both sign in with its credentials). Sharing a keyboard is the pair's choice; the legs are sequential either way. A solo student walks both roles. | Halves provisioning, matches Google's "same project" comment, and the platform makes it trivial. |
| D5 | Time block is 180–210 min: intro 5–15 min, one 15-min break, the rest is lab. Plan tasks for **~165 min** with the §11 cut list as a safety net, not the plan. | Patrick's call on the intro. |
| D6 | Brand Studio produces a **campaign brief** using the **brief template shipped in the brand corpus**, which has **ten** fixed headings: Objective, Audience, Insight, Channels, Offer, Budget and modeled reach, KPIs, Creative direction, Legal review notes, Retrospective (left as "to be added after the campaign"). The Creative direction section is what Task 5 generates against. | Resolves Tarun's two useful comments (campaign vs. creative brief; give them a template). Heading count corrected from the file, Sep 19. |
| D7 | Anything that doesn't teach a featured product is provisioned at Start Lab. The Terraform and scripts ship in a `provisioning/` subfolder of the repo for the curious. | Patrick's rule; matches project philosophy. |
| D8 | Product names as of Sep 2026, as the UI shows them: Gemini Enterprise has two employee-made agent types, **Chat agent** and **Workflow**, behind two separate admin toggles (*Enable chat agents*, *Enable workflow*); the docs' "Workflow Builder (formerly Agent Designer)" covers the second. **Brand Studio is a Chat agent.** Custom agents (A2A, Agent Runtime) are registered only in the **admin console** (Agents → + Add agent), never in the web app. **Nano Banana 2 = Gemini 3.1 Flash Image** (GA in Gemini Enterprise June 2). **Gemini Enterprise Agent Platform / Agent Runtime** (code identifiers unchanged: ReasoningEngine, `google_vertex_ai_reasoning_engine`, `google-cloud-aiplatform`). Gemini 3.x models are served from the **`global`** location only. Prose uses current names; code uses the identifiers; the lab says why once. | Spike S1, S6, S7 (Sep 18). |
| D9 | Video walkthrough is recorded after the event. Not part of this build window. | Patrick. |
| D10 | Every implementation choice defaults to a pattern already proven in a lab project. After the spike, every path in §5 is proven in a Qwiklabs project. | Seven working days. |

## 2. What changed from the outline, and why (as verified by the spike)

The outline was written for a two-month build and guessed at three mechanisms. The docs pointed one way; the spike settled all three in a real lab project:

**Agent Designer cannot register OpenAPI tools, and the Actions list shows no schemas.** Task 3's tools are **MCP Toolbox for Databases** on Cloud Run, connected as a **custom MCP data store**. Both tools are plain `bigquery-sql` in one `tools.yaml`; no custom server. The read-only tool runs without a prompt; the write tool shows a **Review: Activate Segment** card with labelled, editable parameters, which is where the tool contract becomes visible to the Marketer. The Builder sees the contract in `tools.yaml`. No org-policy override was needed; the only prerequisite is an identity provider on the Gemini Enterprise instance (§7).

**The assistant over a BigQuery data store is retrieval, not analysis.** Tasks 1–2 use a **BigQuery data agent** (Conversational Analytics) built in BigQuery → Agents, published twice (skip the Agent Registry offer; take *Integrate via A2A → Copy JSON*), and registered in the admin console as a *Custom agent via A2A*. Publishing creates the OAuth client itself; each user clicks *Authorize* once. No consent screen, no client ID, no ADK analyst fallback.

**Skills are assistant-only.** *"Using agents and skills together is not supported yet."* An agent conversation can't be left mid-chat. Task 2's readout is a copy → Skills → *executive-readout* → **New chat** (the trigger is pre-filled) → paste hand-off, which teaches exactly that: Skills live in the assistant, agents are separate surfaces.

**And one the docs didn't warn about:** a **Workflow** agent errors on image generation; a **Chat agent** generates images itself, takes follow-ups, and can attach both the brand corpus and the Toolbox MCP data store as tools. Brand Studio is therefore a Chat agent, and Tasks 4–5 need no image tool.

Everything else in the outline stands: the story, the seven tasks, the alternating Builder/Marketer legs, the pre-built propensity model and embeddings, the ADK orchestrator, the per-customer decisioning policy, and the governance aside (A2A-by-card agents bypass Agent Gateway; the *Add agent* dialog now also offers *Agents from Agent Registry*, which is the governed route, so the aside can point at it).

## 3. Research findings (Sep 16), with spike corrections (Sep 18)

- Workflow Builder / Agent Designer: in the product these are **Chat agent** and **Workflow**, two toggles, two types. Workflows run from a trigger with input fields, gather missing inputs by chat, and (undocumented) accept follow-ups; they error on image generation. Chat agents are conversational, generate images, and take data stores and MCP data stores as tools; **Google Search is on by default and the corpus is off** in the tools picker.
- Custom MCP server data stores: StreamableHTTP only. Auth **None** for Cloud Run (Gemini Enterprise sends a Google-signed ID token; grant `roles/run.invoker` to `service-PROJECT_NUMBER@gcp-sa-discoveryengine.iam.gserviceaccount.com`). Actions appear after *reload custom actions*, disabled by default; the Actions tab shows Name / Type / Status only. `readOnlyHint` skips the confirmation; a write tool gets a Review card. **No org-policy override and no FQDN allow-listing were needed in a Qwiklabs project** (the docs' warning did not apply). Prerequisite: Settings → Authentication → identity provider = **Google Identity**, or the create wizard blocks.
- A2A agent registration: admin console → Agents → + Add agent → *Custom agent via A2A* → paste card. The dialog offers five routes: Agent Runtime, Dialogflow, A2A, Marketplace, Agent Registry. Gemini Enterprise **rejects** ADK's generated card until `supportedInterfaces` and `preferredTransport` are removed; the trimmed card is checked into the repo.
- ADK deploys: `adk deploy cloud_run --a2a` serves **no card without an `agent.json`** in the agent folder; card path `/a2a/<agent>/.well-known/agent-card.json`. Cloud Run from source 2 min 25 s; Agent Runtime 2 min 42 s. Every ADK agent needs `GOOGLE_CLOUD_LOCATION=global` (env var on Cloud Run; `os.environ[...]` before ADK imports on Agent Runtime) or Gemini 3.x 404s in `us-central1`.
- BigQuery data agents: BigQuery → **Agents** → + New agent → Add source (the table picker scrolls without looking like it; list the tables and say how many). **No auto-save, no leave warning.** Verified queries are entered under a field labelled **Question**, so titles are written as questions. Publish twice. Answers can be downloaded as PDF. Charts not observed inside Gemini Enterprise (R3 still open).
- Skills: GA, on in a fresh lab project with no allowlist (R5 closed). *Create skill with Gemini* fills a form whose Name / Description / Instructions fields are directly editable, so students paste three fields from the repo's `skills/executive-readout/SKILL.md`; the skill's page has a **New chat** button that pre-fills the trigger.
- Image generation: assistant and Chat agent both generate; Workflow errors. Model name to record on the Sep 21 walk.
- Cloud Storage data store: Layout Parser, pointed **directly** at `gs://class-demo/cymbal-voyages/v1/brand_corpus/` (no copy, no permission issue), 12 PDFs, **~10 min** to indexed.

## 4. Spike results (Sep 18, project `qwiklabs-gcp-04-df5f1f023984`)

| ID | Result | Locks |
| :-- | :-- | :-- |
| S1 | Pass | Task 0 with exact toggle names; identity-provider step; admin-only agent registration |
| S2 | Pass | Tasks 1–2 via data agent → A2A. Q2 closed. Data leak fixed (commit d7c1734); one more data fix pending (§6a) |
| S3 | Partial | Skills work, not alongside an agent. Task 2 uses the copy → New chat hand-off |
| S4 | Pass | Task 3 via Toolbox as a custom MCP data store. Q1 closed: no org-policy override |
| S5 | Pass | Orchestrator works on Cloud Run (2:25) and Agent Runtime (2:42). R1 closed |
| S6 | Pass | A grounded agent writes on-voice briefs, cites the right retrospective, takes follow-ups; the generic banned-phrase rule fails until tightened |
| S7 | Pass | Chat agent generates images; Workflow errors. R2 resolved: Brand Studio is a Chat agent |
| S8 | Pass (tight) | Corpus import ~10 min; fire it first at Start Lab |

Full record: `cymbal-voyages/docs/spike-findings.md`; summary: `docs/sc2-phase1-handback.md`.

## 4a. The six decisions (Sep 19)

1. **Task 2 readout: the Skill, with the hand-off.** It is the only place Skills appear in the lab, the outline's product map promised them, and the hand-off teaches something true (Skills live in the assistant; an agent chat is its own surface). Students paste the three fields from `skills/executive-readout/SKILL.md`; nobody edits Gemini-generated Markdown. The readout format also goes into the data agent's instructions as a one-line fallback ("when asked for an executive readout, write three paragraphs…"), so the beat survives if the Skill UI moves.
2. **Task 1 typing load: paste blocks, and fewer of them.** Students paste the instructions paragraph, **three** glossary terms (warm escapes, booking, lapsed member) and **two** verified queries (bookings vs. plan; cohort conversion on warm-escape sessions, year over year), all as copy blocks in the lab. Dropped from the student set: *retargeting* (it names CMP-002 and gives the answer away), *cold-weather markets*, *Compass tier*, *propensity score*, *plan* (all covered by column descriptions or the instructions). The third verified query (daily paid spend by campaign) is added by the Builder **in Task 2**, when the Marketer's "when did retargeting fall?" gets a monthly answer; that is the fallback route used as a beat. The data agent stays student-created (creating it by API at Start Lab is untested and would remove the point of Task 1).
3. **Task 3 contract beat: both.** The Builder reads `tools.yaml` (shown in the lab, and it's the file mounted into the service) and names the two tools and their parameters before enabling them; the lab says plainly that the Actions tab shows names only. The Marketer meets the same contract on the **Review: Activate Segment** card, parameters humanized and editable. Same contract, two audiences, which is the lesson.
4. **Orchestrator host: Cloud Run.** One pattern for every lab service (prebuilt image, `--min-instances=1`, invoker grant, registration by pasting a card, the same move as Task 1), and it gave the correct decision in the test. Agent Runtime becomes an **optional post-event task** ("deploy the same orchestrator to Agent Runtime and register it; under three minutes") so the product still appears, and Task 6's prose carries a one-line aside.
5. **Task 1 bare-assistant risk: create the corpus data store at Start Lab, keep its connector disabled until Task 4.** The import must start at Start Lab (10 min), but the assistant must not be able to read `05-brief-fall-city-breaks-2026` during Task 1. SC3 finds the API or CLI to leave the connector disabled (the console does it per app); if it isn't scriptable, Task 0's Builder disables it. Task 4's "attach the brand corpus" then becomes a real Builder step. On the Sep 21 walk, ask the Task 1 question with the connector disabled and again with it enabled, so we know what the failure looks like.
6. **Both new beats adopted.** Task 1 gets three answers, not two: the bare assistant (generic), the data agent before instructions (**sure but partly wrong**: it blames the Aug 1 price increase, a 3% red herring), and the data agent with definitions (decomposes before naming a cause). Task 4's banned-phrase rule **fails on the first run** ("guaranteed lowest price" sails through with a note that it "will require legal review"), the Builder tightens the rule, and the re-run is clean. Both are stronger than the outline's version of the same beats.

## 5. Task structure (~165 min lab time; every path spike-verified)

Legs alternate Builder (🔧) and Marketer (📣). The **admin console** is the Builder's surface; the **web app** is the Marketer's.

**Task 0 — Both seats working (10 min).** Both partners sign in to the shared project. 🔧 Activate Gemini Enterprise (trial license); Configurations → Feature management → *Enable chat agents*, *Enable workflow*, *Enable skills* (plus model selector, canvas, Gemini 3.8 Flash); Save and expect the "may take some time" toast. Settings → Authentication → identity provider → **Google Identity** (unless provisioning set it). Confirm the brand-corpus connector is present and disabled. 📣 Open the web app; see Agents and Skills. Two front doors, one product.

**Task 1 — The question nobody can answer (22 min).**
📣 4 min: ask the bare assistant why August warm-escapes bookings missed plan. Confident, generic, wrong. Write it down.
🔧 14 min: BigQuery → Agents → + New agent → **Cymbal Voyages Analyst** → Add source → tick the **9 tables** in the picker's order (ad_performance, bookings, campaign_history, customer_month_status, customers, destinations, packages, plan, web_sessions) → **Save**. Ask the same question in the preview once, before any instructions: sure, and partly wrong (it names the price increase). Then paste the instructions, three glossary terms and two verified queries (titles as questions) → Save → Publish → skip Agent Registry → Publish again → *Integrate via A2A* → Copy JSON → admin console → Agents → + Add agent → *Custom agent via A2A* → paste. *Teaching beat: the tables took two minutes; the definitions took ten, and they are what changed the answer.*
📣 4 min: same question to the Analyst in the web app; **Authorize** once. Three answers side by side.

**Task 2 — Root cause and the Monday readout (22 min).**
📣 8 min: follow the thread. Which markets? Cold, all eight, −33.5%. Traffic or conversion? The cohort verified query: lapsed Compass, cold market, 6.74% → 2.43% on warm-escape browsing, every other cohort flat. Size the red herrings (incident ≈ 65 bookings, re-pricing ≈ 18). When did retargeting fall? The agent, working from monthly totals, says August 1.
🔧 6 min: paste the daily paid-spend verified query; the Marketer re-asks and gets **July 24** (the $150/day keep-alive). Then Skills → *Create skill with Gemini* → paste Name, Description, Instructions from the lab → Save.
📣 8 min: ask the Analyst for the findings summary (the prompt is in the lab) → copy → Skills → *executive-readout* → **New chat** → paste → send. Three paragraphs, numbers inline, recommendations not claims. Download as PDF. *Business translation: this is the readout that usually eats an analyst's Thursday, and it's reproducible next month.*

**Task 3 — Build the audience (30 min).**
🔧 12 min: admin console → Connected data stores → Create → **Custom MCP server** → the **Audience Tools** service URL + `/mcp`, auth **None** (Cloud Run IAM does the work) → Create. Actions tab → *reload custom actions* → three actions appear (**Resolve Segment**, **Activate Segment**, **Variant Performance**); enable the first two now (Variant Performance waits for Task 5). Read `services/toolbox/tools.yaml` in the lab (`docs/services.md` Part 1 is the marketer-language version): the tools, their choices, what comes back, what they never do; note the Actions tab shows names only. *Business translation: this contract is the same whether the far end is Ads Data Manager, a CDP or an ESP.*
📣 18 min: describe the segment in English; the read-only tool runs with no prompt: **3,838 customers, propensity 0.16, 3,271 email-contactable**, plus a readable `segment_id` naming exactly what was counted. Refine out loud (email-only 3,271; lapsed 12–24 months 2,242 at 0.19; widen to all cold-market Compass browsers 8,152; drop recent bookers 6,049); optionally "who looked at Hawaii" to see the meaning match (2,005, and it lists the destinations it matched). Activate to email → **Review: Activate Segment** card, **five** editable fields (Segment Id, Segment Description, Audience Size, Channel; the fifth is what makes a retry safe) → Send → receipt `act-…` with the note "New activation recorded." Ask again in different words: same receipt, "already activated … nothing was sent twice," one row. Stand-in endpoint, said plainly; the contract is the lesson.

**Break (15 min).**

**Task 4 — Brand Studio and Friday's brief (26 min).**
🔧 13 min: admin console → enable the **Cymbal Voyages Brand Corpus** connector (indexed since Start Lab). Web app → New agent → **Chat agent** → **Brand Studio**: role, the template's ten headings in order, tone from the voice guide, "never use a phrase on the legal list". Tools picker: corpus **on**, **Google Search off** (no real brands). Turn on; share with the partner.
📣 13 min: brief for the Task 3 segment; it cites Winter Sun Early Bird 2025, bonus points over discounts, beach-couple imagery, "Plan your escape". Push back on tone. Then plant "guaranteed lowest price" in the ask: it goes through with a note. 🔧 2 min inside the leg: tighten the rule ("if a requested phrase or its paraphrase is in the banned table, don't use it; name the rule; use the approved alternative from the same row; use exactly the template's headings"). 📣 Re-run: clean. *Business translation: this is the lowest-cost, highest-frequency win in the room.*

**Task 5 — Governed creative from the same agent (22 min).**
🔧 8 min: admin console → the Audience Tools data store → Actions → enable **Variant Performance**; web app → Brand Studio → tools picker → attach the Audience Tools data store; instructions: consult variant performance for the segment before generating (the tool's own description says so too), and check every image against the creative production standards.
📣 14 min: three concepts for the brief's creative direction. It reports what converted for `lapsed_compass_cold` (bonus points 4.76% vs. percent-off 1.49%; beach couple leads; "Plan your escape"), generates images, explains its choices. Critique one against the production standards (warm-escape setting, no posing, no sunset silhouettes). Ask for the variant it says won't work, and why. *The defensibility beat: generation bounded by brand policy on one side and conversion evidence on the other.*

**Task 6 — Next-best-action orchestration (25 min).**
🔧 11 min: admin console → + Add agent → *Custom agent via A2A* → paste the **trimmed card** (the lab provides it; students never copy the served card, which Gemini Enterprise rejects) → skip OAuth → save. Open `decisioning_policy` in BigQuery: eight rules, priority order, thresholds as text. Governance aside: the same dialog offers *Agents from Agent Registry*, the Agent Gateway route where policies apply; ours came by card, so Gateway policies don't. Know where your boundary sits. The orchestrator's model never decides: the policy engine applies the table, the model explains.
📣 14 min: run the base audience (describe it the same way as Task 3, without a destination): 289 send_offer, 14 route_to_loyalty_team, 3,535 held (the scores are right-skewed). Widen to **all Compass members in cold markets who browsed warm** (variant E, 8,152): **suppress** fires on 2,103 ("booked in the last 60 days"). Ask about one customer and get the rule and reason. 🔧 lowers the offer threshold from 0.30 to 0.15 in the table (R03, R04, R05); 📣 re-runs the base audience: **1,082 of 3,838 (28%)** now get the offer. B2C reads as lifecycle; B2B reads as MQL→SQL routing.

**Task 7 — Wrap (7 min).** The loop: a question nobody could answer → an explanation → an audience → a brief → creative → a per-customer decision, all traceable to the company's own data, none of it from a blank page. Business translation table by team. No Lab 3 tee-up.

**Optional (post-event):** deploy the orchestrator to Agent Runtime and register it (under three minutes); B2B seam (intent-weighted account list → lead routing); instructor-driven Veo moment; re-run the loop next month with the September data.

Cut order if the room runs slow: Task 5 marketer leg to one concept; Task 6 becomes instructor-driven with hands-on moved to optional; Task 2 thread compressed to the cohort query and the daily-spend query.

## 6. Data design (summary; the full spec is in the data-engineering handoff)

BigQuery dataset `cymbal_voyages`, fixed calendar Jul 2025–Sep 2026, ~50k customers, ~60 destinations, ~300 packages, ~570k web sessions, ~49k bookings, daily ad performance by channel × campaign × market, 12 past campaigns, ~200 creative variants with outcomes, a monthly plan table, per-customer decisioning features, a `decisioning_policy` rules table, and an empty `activations` receipts table. A BQML logistic-regression propensity model (booking in next 60 days) and precomputed embeddings over destination and package descriptions.

The planted chain: warm-escapes bookings in August 2026 are 18% under plan while every other category and every warm-climate market is on plan. Web sessions from lapsed Compass members in cold-weather markets browsing warm destinations are flat to up, but their conversion fell from 6.74% to 2.43%. The paid-social retargeting campaign that closed that cohort had its budget rotated to a fall city-breaks campaign on July 24 (visible only at daily grain in `ad_performance`). Two red herrings: a 4-hour site incident on Aug 9 and a price increase on two packages on Aug 1. Prior-year August was on plan.

Brand corpus (12 PDFs): brand voice guide, campaign brief template (ten headings), three past briefs with retrospectives, competitive one-pager, legal claims list, Compass program summary, audience-segments glossary, channel playbook, seasonal calendar, creative production standards.

## 6a. What SC1 delivered (Sep 18), and what the lab text must absorb

Everything is under `DevWork/cymbal-voyages/data/`. Read `docs/data-dictionary.md` and `docs/anomaly-walkthrough.md` before writing any task; the lab quotes their numbers verbatim.

**Deviations from the spec, accepted:** bookings ~49k, sessions ~570k; only signed-in sessions convert and 40% of bookings complete in a tracked session; a 16th table `customer_month_status` gives loyalty status as of each month; `propensity_training` is every customer as of Sep 1, 2025 with a 60-day warm-escape label; `plan` carries the seasonal shape. Load: 15 tables in ~5 min with `bash sql/load.sh`. Model: BQML `LOGISTIC_REG`, trains in 56 s, roc_auc 0.786. Embeddings: `gemini-embedding-001`, 3,072 dims, 360 rows.

**The numbers the story turns on:** August 2026 warm escapes 3,175 vs. plan 3,876 (−18.1%, gap 701); cold markets −33.5% across all eight, mild −1.7%, warm −2.8%; August 2025 +1.0%; July 2026 −6.5% (first dated clue). Cohort conversion on warm-escape browsing: lapsed Compass, cold market 6.74% → 2.43% on 5,546 → 6,050 sessions; every other cohort flat. Cohort paid-social sessions 1,277 → 156. CMP-002 drops to a $150/day keep-alive on Jul 24 (last full day Jul 23); CMP-012 gets the money; total paid spend rises with the season. Red herrings: Aug 9 incident ≈ 65 bookings (9% of the gap), Aug 1 re-pricing ≈ 18 bookings (3%).

**Audience:** "lapsed Compass members in cold markets who viewed a warm destination in the last 90 days" = 3,838 customers, avg propensity 0.156, 8.7% ≥ 0.30, 3,271 email-contactable (85%). After `predict_propensity.sql`: 0.162 / 10.3%. **Decided Sep 19 (SC3): provisioning does not re-score**, so the lab quotes the shipped reference scores: 0.156 ("0.16") / 8.7%. Measured with re-scoring on, the policy counts moved (336 / 15 / 3,487 instead of 289 / 14 / 3,535), so re-scoring was dropped rather than rewriting Tasks 3 and 6. "Did not book" is implied by lapsed. Variants A–F drive Task 3's refinement.

**Creative learning for `lapsed_compass_cold`:** bonus_points 4.76% vs. percent_off 1.49% and urgency 1.49%; beach_couple 3.49% leads; "Plan your escape" 3.95% beats "Claim offer" 2.10%. For `all_customers` percent_off wins. Matches the Winter Sun Early Bird 2025 retrospective.

**Policy dry run (confirmed by the built orchestrator, Sep 19):** base audience 289 send_offer (R03 269, R04 20), 14 route_to_loyalty_team, 3,535 held, 0 suppressed. The offer threshold lowered to 0.15 sends offers to **1,082 of 3,838 (28%)**. The "suppressed because they booked last week" beat needs **variant E** (all cold-market Compass browsers, 8,152), where R01 suppresses 2,103; variant F has already removed those customers, so suppress cannot fire there.

**Data fixes applied:** the `propensity_training` description (Sep 18, planning); the `ad_performance` table description and the CMP-002 retrospective no longer name the Jul 24 rotation (SC1, commit d7c1734), so the unaided agent no longer gets the answer from text.

**Data fixes still owed (Patrick runs `docs/sc1-fix-prompt-2.md` in the data conversation, then re-stages `schemas/` and `docs/`):** the dictionary's cohort verified query must filter on `viewed_warm_escape` and compare August 2026 with August 2025 (it currently yields 3.86% → 3.50%, not 6.74% → 2.43%); add the daily paid-spend-by-campaign verified query; add an instruction to size the red herrings; reword verified-query titles as questions; drop or neutralize the *retargeting* glossary entry that names CMP-002. Confirm `_tables.json` in `gs://…/v1/schemas/` carries the d7c1734 description (the spike project needed a hand `bq update`).

## 7. Provisioning design (Start Lab, target ≤15 min; every item spike-verified)

Qwiklabs startup-script Terraform as in mkt013–015, native resources first. Order matters because of the corpus import:

1. **First thing:** create the **Cymbal Voyages Brand Corpus** Cloud Storage data store, Layout Parser, pointed directly at `gs://class-demo/cymbal-voyages/v1/brand_corpus/`, and fire the import (~10 min). Leave the app connector **disabled** if that is scriptable (decision 5); otherwise Task 0 disables it.
2. APIs (BigQuery, Gemini Data Analytics, Gemini for Google Cloud, Discovery Engine, Cloud Run, Secret Manager, Artifact Registry, Vertex AI; *Knowledge Catalog was not needed*). Service identities. `roles/run.invoker` on every Cloud Run service for `service-PN@gcp-sa-discoveryengine.iam.gserviceaccount.com`.
3. Identity provider = **Google Identity** on the Gemini Enterprise instance, if scriptable (needed before any custom MCP data store can be created).
4. BigQuery: dataset `cymbal_voyages`; load all 16 tables from `gs://…/v1/out/` with the schemas from `gs://…/v1/schemas/` (`google_bigquery_job` load jobs, or `bash sql/load.sh` from a **fresh checkout at a pinned commit** with no stale local `schemas/`); then `train_propensity.sql` (56 s). **No `predict_propensity.sql`** (decided Sep 19: the shipped scores are the ones every lab number was verified on; see §6a).
5. Cloud Run, both services from the public images in `class-demo-labs`, exactly as `services/scripts/deploy_services.sh` does it (§7a): **`audience-tools`** (Toolbox 1.12.0 mirror, `tools.yaml` from the `audience-tools-config` secret, service account with `bigquery.jobUser`, `bigquery.dataViewer`, `bigquery.dataEditor`, `secretmanager.secretAccessor`, **`aiplatform.user`**) and **`orchestrator`** (1.0.0, `GOOGLE_CLOUD_LOCATION=global`, `AGENT_URL` set to its own deterministic URL). Both `--min-instances=1`, no unauthenticated access, `roles/run.invoker` for the Discovery Engine service agent. The trimmed agent card is written where the lab can show it.
6. Gemini Enterprise app activation, feature toggles, and the data-agent build stay student steps (Task 0 and Task 1); nothing a student creates triggers a fresh import.

Measured pieces: BigQuery load ~5 min, model 1 min, Cloud Run deploys seconds from an image, corpus import ~10 min. Everything runs in parallel behind the import.

## 7a. What SC2 delivered (Sep 19)

`docs/services.md` in the repo is the handoff: Part 1 the tool contracts in marketer language (the lab quotes it), Part 2 the deploy facts (SC3 reproduces `services/scripts/deploy_services.sh` in Terraform), Part 3 the test run (every number matches the walkthrough), Part 4 thirteen build decisions. Images, public-read, pulled cross-project with no grant: `us-central1-docker.pkg.dev/class-demo-labs/cymbal-voyages/toolbox:1.12.0` and `.../orchestrator:1.0.0`. No builds at Start Lab.

**Absorbed into §5:** the Review card has five fields (Segment Id is the activation key, so a reworded retry returns the same receipt); the offer threshold at 0.15 sends 1,082 of 3,838 (28%); suppress fires on variant E (2,103 of 8,152), not F; the Actions tab lists three actions; `resolve_segment` returns a readable `segment_id` and, for a place or vibe, the five closest catalog destinations ("Hawaii" matches four Hawaii items plus Key West as the fifth-closest, which the answer shows). Task 6's audiences are described the same way as Task 3's, without a destination hint, so the orchestrator's counts match.

**For the lab writers:** `tools.yaml` reads the project from its environment, so the file shown to the Builder is the exact file mounted in the service. Channels are limited to email, paid_social, paid_search. The orchestrator normalizes anything a student types into the policy table (case, `30%`, `≥`, `yes`) and skips rows it can't read with a report, so Task 6's edit can't break it. The served agent card is in the newer A2A format that Gemini Enterprise rejects; students paste the trimmed card the lab provides.

## 8. Sub-conversations and venues

| # | Conversation | Venue | Status |
| :-- | :-- | :-- | :-- |
| SC1 | Data engineering | Standalone | Done Sep 18; one fix prompt pending (`docs/sc1-fix-prompt-2.md`) |
| SC2 | Spike companion → services | Standalone | **Done Sep 19** (§7a) |
| SC3 | Provisioning: Terraform + startup script, qwiklabs.yaml, timing | Standalone | Handoff updated Sep 19 with the deploy facts; **open now** |
| SC4 | Task writing: Tasks 0–2 | In project | Opened Sep 19 |
| SC5 | Task writing: Task 3 | In project | Tue |
| SC6 | Task writing: Tasks 4–5 | In project | Wed |
| SC7 | Task writing: Tasks 6–7, Overview, Summary, Optional | In project | Wed |
| SC8 | Run-through checklist artifact for the full lab | In project | Thu |

## 9. Schedule

| Day | Patrick | Claude |
| :-- | :-- | :-- |
| Sat 19 | Data fixes done; SC2 Phase 2 done; SC4 opened | Plan and SC3 handoff updated |
| Sun 20 / Mon 21 | Open SC3. End-to-end walk in the spike project: R10 (Audience Tools data store, orchestrator by trimmed card), both Task 1 corpus states, Brand Studio + Variant Performance, banned-phrase re-run, image model name | SC3 build; provisioning timing |
| Tue 22 | Test tasks as they land | SC4, SC5 |
| Wed 23 | Test tasks as they land | SC6, SC7 |
| Thu 24 | Full run-through from Start Lab; R4 recheck list | Assemble en.md, yaml, diagram; SC8 |
| Fri 25 | Fixes; submit to Qwiklabs | Retrofit outline |
| Mon 28 | Buffer; second run-through inside Qwiklabs | — |

## 10. Open questions and risks

**Closed by the spike:** Q1 (no org-policy override needed; prerequisite is the identity provider), Q2 (publishing creates the OAuth client; users Authorize once), R1 (Agent Runtime 2:42; hosting is a free choice, Cloud Run chosen), R2 (Chat agent generates images; Workflow doesn't), R5 (Skills on in a fresh lab project).

**Still open:**
- **R3:** charts inside Gemini Enterprise from the data agent: not observed. The readout is prose by design; not load-bearing.
- **R6 (new):** the corpus connector must be **disabled** at Start Lab or Task 1's bare assistant may read the Fall City Breaks brief. SC3 finds the API; Sep 21 walk tests both states.
- **R7 (new):** the Chat agent must actually call `variant_performance` before generating in Task 5 (instruction-driven ordering, not enforced). Sep 21 walk confirms; if flaky, the tool description carries the ordering ("call this before generating any creative").
- **R8 (new):** the unaided data agent's answer is non-deterministic; the lab describes its shape ("names a cause, usually the price increase") and never quotes it verbatim.
- **R10 (new, Sep 21 walk):** two things the services build could not test inside Gemini Enterprise: creating the Audience Tools custom MCP data store on the new `audience-tools` URL (three actions, the five-field Review card, the reworded retry), and registering the orchestrator by the trimmed card and running the Task 6 questions through the assistant. Also confirm `destination_hint` behaves when no place is named (Gemini should send `none`, not invent one).
- **R9 (new):** corpus import ~10 min is inside the budget only because it starts first. If Start Lab measures over 15 min, drop the Layout Parser for the eight PDFs without tables and keep it for the four with tables.
- **R4 (Sep 24 recheck list):** the Skill + agent restriction; the Actions tab layout; where Google Search's default sits in the Chat agent's tools picker; the banned-phrase re-run with the tightened rule; `variant_performance` called before generation; workflow follow-up behaviour (only if a Workflow is used anywhere, which it currently isn't); the A2A card fields Gemini Enterprise rejects.

## 11. Nano Banana prompt for the architecture diagram

*A clean, wide 16:9 architecture diagram in a flat Google Cloud style, white background, thin grey connectors, product icons as simple rounded squares with short labels, no photographic elements. Three horizontal bands. Top band, labeled "Marketer (Gemini Enterprise web app)": a chat window with four agents listed on its left, "Cymbal Voyages Analyst," "Brand Studio," "Orchestrator," and "Skills: executive-readout." Middle band, labeled "Builder (admin console and BigQuery)": four boxes in a row, "BigQuery data agent" (a table icon), "Custom MCP data store: Audience Tools" (a plug icon), "Chat agent: Brand Studio" (a document icon), "A2A agent card" (a card icon), each connected upward to its agent in the top band by one arrow. Bottom band, labeled "Provisioned at Start Lab": "BigQuery: cymbal_voyages warehouse, propensity model, catalog embeddings, decisioning policy," "Cloud Storage: brand corpus (12 PDFs)," "Cloud Run: MCP Toolbox (resolve_segment, activate_segment, variant_performance)," and "Cloud Run: ADK orchestrator," with thin arrows from each up to the middle-band box that uses it. Along the very top, a thin timeline of seven chevrons reading "Ask," "Explain," "Audience," "Brief," "Creative," "Decide," "Wrap." Title in the upper left: "From Question to Campaign: Cymbal Voyages." Legible at 1600 pixels wide.*

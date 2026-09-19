# mkt016 spike results: hand-back from the spike companion (SC2) to planning

*Paste everything below the line into the planning conversation. The full record, with UI names, quotes and numbers, is `docs/spike-findings.md` in the cymbal-voyages repo.*

---

The S1–S8 spike is finished (Sep 18, Qwiklabs project `qwiklabs-gcp-04-df5f1f023984`). Seven items pass and one is partial. Here is what it locks, what contradicts the plan, and what you need to decide.

## Scorecard

| ID | Result | What it locks |
| :-- | :-- | :-- |
| S1 | Pass | Task 0 as written, with exact toggle names, plus an identity-provider step |
| S2 | Pass | Tasks 1–2: BigQuery data agent → A2A card → Gemini Enterprise. No ADK analyst fallback. Q2 closed |
| S3 | Partial | Skills work but cannot be used alongside an agent. The Task 2 readout needs a copy/paste hand-off |
| S4 | Pass | Task 3: MCP Toolbox for Databases on Cloud Run as a custom MCP data store. No FastMCP server. **Q1 closed: no org-policy override needed** |
| S5 | Pass | Task 6: the ADK orchestrator works on both Cloud Run (2m25s) and Agent Runtime (2m42s). **R1 closed** |
| S6 | Pass | Tasks 4–5: an agent grounded on the brand corpus writes on-voice briefs and takes follow-ups |
| S7 | Pass | A **Chat agent** generates images; a **Workflow** agent errors. Brand Studio is a Chat agent. **R2 resolved** |
| S8 | Pass (tight) | Brand corpus import is about 10 min (12 PDFs, Layout Parser, direct from `class-demo`) |

## What each task now looks like

**Task 0.**
- Admin: Configurations → Feature management → *Enable chat agents*, *Enable workflow*, *Enable skills* (plus model selector, canvas, Gemini 3.8 Flash). Save; there's a short propagation delay.
- **New:** Settings → Authentication → identity provider → **Google Identity**. Without it the custom MCP data store can't be created. SC3 should set it at Start Lab if it's scriptable; otherwise it's a Builder step.
- Workflows and chat agents are separate toggles and separate agent types (web app: New agent → **Chat agent** | **Workflow**).
- Custom agents (A2A, Agent Runtime) are registered **only in the admin console** (Agents → + Add agent), never in the web app.

**Task 1.**
- Build the agent: BigQuery → Agents → New agent → Add source → tick **9 tables**, listed in the picker's order: ad_performance, bookings, campaign_history, customer_month_status, customers, destinations, packages, plan, web_sessions. The list scrolls without looking like it does, so the lab must list the tables and say how many there are.
- **There is no auto-save and no warning on leaving.** Tell students to Save before testing.
- Publish twice. The first publish offers Agent Registry, which needs an Agent Gateway, so skip it. The second offers **Integrate via A2A → Copy JSON**. Then admin → Custom agent via A2A → paste.
- Publishing creates the OAuth client itself. Each user clicks **Authorize** once on first use.
- The verified-query field is labelled **Question**, so verified-query titles should be written as questions.

**Task 1 data fix (done).** Before the fix, the unaided agent named the whole cause, CMP-002 → CMP-012 on Jul 24, from a table description and a campaign retrospective. SC1 removed both (commit d7c1734). The unaided agent now confidently blames the **Aug 1 price increase** (the red herring, worth about 3% of the gap). **Suggested new Task 1 beat:** without the definitions it sounds sure and is partly wrong; with them, it breaks the numbers down before naming a cause.

**Task 2.**
- The executive readout works as an assistant Skill (`skills/executive-readout/SKILL.md`; students paste Name, Description and Instructions).
- Adding a Skill inside an agent chat gives: *"Using agents and skills together is not supported yet."* An agent conversation can't be left mid-chat.
- The flow is: copy the Analyst's summary → Skills → executive-readout → **New chat** (pre-fills `/executive-readout`) → paste → send.
- The Skill output is clean. Any wrong numbers come from the agent's summary.
- **Open for SC1** (`docs/sc1-fix-prompt-2.md`, not yet run): the dictionary's cohort verified query yields 3.86% → 3.50% instead of the story's **6.74% → 2.43%**. It lacks `viewed_warm_escape` and compares month to month rather than year over year. The agent also dates the retargeting cut to Aug 1, when it was Jul 24, because it works from monthly totals. The prompt adds a daily-spend verified query and an instruction to size the red herrings.

**Task 3.**
- Toolbox `tools.yaml` holds `resolve_segment` (read-only, runs with no prompt, returns **3,838 / 0.156 / 3,271 email**, exactly the walkthrough) and `activate_segment`.
- `activate_segment` shows a **"Review: Activate Segment"** card with editable Channel, Audience Size and Segment Description fields, then writes a receipt. A retry says "already activated" and returns the same receipt, with one row in the table.
- The Actions tab shows only Name, Type and Status, with the names shown as "Resolve Segment" and "Activate Segment". **It doesn't show parameters or descriptions.**
- Actions appear only after **reload custom actions**, and are disabled by default.

**Tasks 4–5.**
- Brand Studio is a **Chat agent**, grounded on **Cymbal Voyages Brand Corpus**, with the Toolbox data store attachable as a tool. It generates images itself, so there's no image tool.
- **In the tools picker, Google Search is on by default and the corpus is off.** The Builder must turn the corpus on and Google Search off (no real brands).
- First run: grounding was excellent. It cited CMP-003 Winter Sun Early Bird, bonus points over discounts, beach couple imagery and "Plan your escape".
- **But it kept a planted "Guaranteed lowest price" line** (row 1 of the legal list's banned table) and only said it needed legal review. It also skipped the template's Budget and modeled reach and KPIs headings.
- **Suggested Task 4 beat:** the first run lets it through; the Builder adds an explicit rule ("if a phrase or its paraphrase is in the banned table, don't use it; name the rule; use the approved alternative from the same row; use exactly the template's headings"); the re-run is clean.
- A hero image from the assistant was close to the production standards but not on brief (a temperate coast, a posed walk). That's a good "check it against the standards" critique for Task 5.

**Task 6.**
- Both hosts work.
- **Gotchas:**
  - every agent needs `GOOGLE_CLOUD_LOCATION=global`, or Gemini 3.x returns a 404 in us-central1;
  - `adk deploy cloud_run --a2a` serves no card without an `agent.json`;
  - Gemini Enterprise rejects the card until `supportedInterfaces` and `preferredTransport` are removed.

## Contradictions with the plan

1. **D8 / §5 "Build Brand Studio in Workflow Builder":** it should be a **Chat agent**. Workflows error on image generation, are documented as single-turn (follow-ups worked in practice, but that's undocumented), and gather their inputs by chat. The one argument for a Workflow is enforced step order (the performance lookup before generation), which is worth a one-line aside.
2. **§5 Task 2, "a Skill … produces the executive readout" from the data agent:** only possible with the copy/paste hand-off above.
3. **§5 Task 3, "read the two tools' schemas" in the actions list:** that UI shows no schemas. The **Review: Activate Segment** card is where the contract becomes visible, with labelled, editable parameters, and it's a strong Marketer moment. For the Builder, show `tools.yaml` (or `docs/services.md`).
4. **D6, "brief template with nine fixed headings":** the template has **ten** (Objective, Audience, Insight, Channels, Offer, Budget and modeled reach, KPIs, Creative direction, Legal review notes, Retrospective).
5. **§7 "Brand corpus copied to a project bucket":** not needed. The import reads `gs://class-demo/cymbal-voyages/v1/brand_corpus/` directly.
6. **§3, the custom MCP data store's org-policy fear:** didn't happen. The real prerequisite is the identity provider.

## Decisions for you

1. **Task 2 readout route:** the Skill with copy/paste (recommended; it teaches that Skills live in the assistant), or the readout format in the data agent's instructions (one step), or the verified-query fallback.
2. **Task 1 typing load:** the glossary and verified queries were slow to type. How many do students type, and what's pre-loaded? (Can the data agent be created by API at Start Lab? Not tested.)
3. **Task 3 contract beat:** move it to the Review card, `tools.yaml`, or both.
4. **Orchestrator host:** the companion leans **Cloud Run**, for one pattern for every service (prebuilt image, `--min-instances=1`, paste-the-card registration like Task 1) and because it gave the correct decision in the test. Agent Runtime also works.
5. **Task 1 bare-assistant risk:** `05-brief-fall-city-breaks-2026.md` says outright that CMP-012 was funded from CMP-002. If the corpus data store is connected at Start Lab and the assistant searches it by default, Task 1's "confident, generic, wrong" beat could come back half-right. Either connect the corpus in Task 4, or test the Task 1 question with it connected.
6. **Adopt the two new beats?** Task 1's "sure but partly wrong" and Task 4's "the rule fails, then is tightened".

## For provisioning (SC3)

- Run `bash sql/load.sh`, never `./`. Run it from a fresh checkout at a pinned commit, or with no local `schemas/` folder: the script prefers a local `schemas/` over the bucket's, and a stale clone applied old descriptions.
- Set the identity provider (Google Identity) if it's scriptable.
- Start the brand corpus data store import **first** (Layout Parser, direct from `class-demo`, about 10 min), in parallel with the BigQuery load (about 5 min) and the service deploys.
- Every Cloud Run service uses **`--min-instances=1`** (Patrick's rule) and grants `roles/run.invoker` to `service-PN@gcp-sa-discoveryengine.iam.gserviceaccount.com`.
- Toolbox: Google's image, **pinned** (not `:latest`), `tools.yaml` from Secret Manager, and a service account with bigquery.jobUser, bigquery.dataViewer, **bigquery.dataEditor** (for the receipt) and secretmanager.secretAccessor.
- ADK services: `GOOGLE_CLOUD_LOCATION=global`, plus the trimmed agent card from the repo.
- After the reload, re-run `sql/predict_propensity.sql` if the lab quotes post-scoring numbers (0.162 rather than 0.16).

## Recheck on the Sep 24 run-through (R4)

- Workflow follow-up behaviour, if used anywhere.
- The Skill + agent restriction.
- The Actions tab layout.
- Where the Google Search default sits in the Chat agent's tools picker.
- The Brand Studio banned-phrase re-run with the tightened rule.
- `variant_performance` actually called by the Chat agent before it generates.

## Next from SC2 (Phase 2)

Building the services on the spike's working base:

- `services/toolbox/tools.yaml`: the real `resolve_segment` with walkthrough variants A–F and the semantic destination match; `activate_segment` with a receipt key that survives rewording; and `variant_performance`.
- `agents/orchestrator/`, reading `decisioning_policy`, on Cloud Run unless you choose otherwise.
- Images in a public Artifact Registry repo.
- `docs/services.md`.

No analyst agent and no image tool are needed.

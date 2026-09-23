# mkt016 — From Question to Campaign: Build Plan

**Lab:** `mkt016-from-question-to-campaign` (folder, yaml title, and H1 must match)
**Story:** Cymbal Voyages, agentic marketing with Gemini Enterprise
**Contract:** SOW signed 8/27/2026 ($50k): the 3-hour lab per the outline, a video walkthrough (recorded after the event), deployment to explore.qwiklabs.com with Google's help, one year of maintenance
**Outline (contract reference):** Google Doc `1QpDrDXjh7FL3VLIxvCN7EApEyrFZlZRRq68r6veONTI` — speculative and malleable; we retrofit it at the end as the record of what was built
**Event:** ~Sep 30, 2026. Content done by Fri Sep 25, Mon Sep 28 at the latest. Qwiklabs publishing lead time is negligible.
**Repos:** lab markdown in `gcp-ce-content/labs/mkt016-from-question-to-campaign/` (branch `mkt016`); everything else in `DevWork/cymbal-voyages` → `github.com/haggman/cymbal-voyages`
**Data staging:** `gs://class-demo/cymbal-voyages/v1/` (frozen once labs point at it; regenerate into `v2`)
**Planning docs:** this file plus `mkt016-handoff-*.md` in the project's `claude/` folder; spike record in `cymbal-voyages/docs/spike-findings.md` and `docs/sc2-phase1-handback.md`

Last updated: 2026-09-22, evening (planning conversation absorbed SC6's handback, `claude/mkt016-sc6-handback.md`: Tasks 4–5 as written, two lab users against D4, §5d, §8, §9, R4/R7/R13, image model)

**Status (Sep 22, evening):** SC1 data foundation delivered, staged, and fixed (§6a). Spike S1–S8 finished Sep 18 (§4); the six decisions are made (§4a). SC2 Phase 2 done and tested Sep 19 (§7a). SC3 (provisioning) running; two timed Start Labs at ≈7.5 min (§7). **SC4 (Tasks 0–2), SC5 (Task 3), and SC6 (Tasks 4–5) done Sep 21–22**, each walked in a fresh Start Lab project with zero verify markers left (§5a–§5d; Task 5.4 still being finished on the walk). `en.md` now runs Overview through Task 5, ≈150 min as written. **SC7 (Tasks 6–7, Lab Summary, Optional) opens next** with `claude/mkt016-handoff-tasks-6-7.md`. **New since SC6:** the lab provisions **two lab users** (both Owner on the one project) so agents can be shared for real; that has to be validated on the Thursday run-through (R13). The orchestrator half of R10 waits for Task 6. Google has not yet answered the deck-review email (60-minute lab blocks; CMO room); nothing in the build changes until they do (§5, timing note).

---

## 1. Decisions locked on day 1 (D6 and D8 corrected Sep 19)

| # | Decision | Why |
| :-- | :-- | :-- |
| D1 | Lab 3 is ignored entirely. Task 7 wraps the loop and stops; no tee-up. | Google gave no answer on §9.1. |
| D2 | We synthesize the warehouse and write the brand corpus ourselves. | No Google data. Public travel datasets have none of the ad-spend, CRM, loyalty, or creative-outcome dimensions, and a planted anomaly is easier to build than to retrofit. |
| D3 | The anomaly is **August 2026** warm-escapes bookings, 18% under plan. Monday's readout explains August; Friday's campaign is the **fall recovery campaign** for the October–November booking window (winter warm-escape travel). Fixed dates in the data. | The outline mixed March and July; a reviewer wanted fall. Early-bird winter-sun bookings open in late summer, so an August miss is credible, and the lab must read the same way for a year. |
| D4 | Pairs share **one lab project**. **Amended Sep 22 (SC6):** the lab provisions **two lab users**, `user_0` and `user_1`, both Owner on the project, surfaced as Username 1 / Password 1 and Username 2 / Password 2, because Gemini Enterprise agents are per user and Task 4 shares Brand Studio for real. The lab text says the two accounts are interchangeable; the Terraform's three explicit grants still land on `user_0` only (R13). Sharing a keyboard is still the pair's choice; the legs are sequential either way. A solo student walks both roles on one account. | Halves provisioning, matches Google's "same project" comment, and sharing an agent teaches something true. |
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
- Image generation: assistant and Chat agent both generate; Workflow errors. **Sep 22:** no image tool is selected anywhere; Gemini Enterprise switches into image generation on request, using **Nano Banana** (the UI's name for it). Asked for "concepts," a Chat agent writes shot descriptions; the picture is a separate ask.
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
2. **Task 1 typing load: paste blocks, and fewer of them.** Students paste the instructions paragraph, **three** glossary terms (warm escapes, booking, lapsed member) and **two** verified queries (bookings vs. plan; cohort conversion on warm-escape sessions, year over year), all as copy blocks in the lab. Dropped from the student set: *retargeting* (it names CMP-002 and gives the answer away), *cold-weather markets*, *Compass tier*, *propensity score*, *plan* (all covered by column descriptions or the instructions). ~~The third verified query (daily paid spend by campaign) is added by the Builder in Task 2~~ **Superseded Sep 21 (§5a):** the Task 1 instructions get the Analyst to July 24 on its own, so the daily-spend query is no longer a student step; it stays in the dictionary as optional. The data agent stays student-created (creating it by API at Start Lab is untested and would remove the point of Task 1).
3. **Task 3 contract beat: both.** The Builder reads `tools.yaml` (shown in the lab, and it's the file mounted into the service) and names the two tools and their parameters before enabling them; the lab says plainly that the Actions tab shows names only. The Marketer meets the same contract on the **Review: Activate Segment** card, parameters humanized and editable. Same contract, two audiences, which is the lesson.
4. **Orchestrator host: Cloud Run.** One pattern for every lab service (prebuilt image, `--min-instances=1`, invoker grant, registration by pasting a card, the same move as Task 1), and it gave the correct decision in the test. Agent Runtime becomes an **optional post-event task** ("deploy the same orchestrator to Agent Runtime and register it; under three minutes") so the product still appears, and Task 6's prose carries a one-line aside.
5. **Task 1 bare-assistant risk: create the corpus data store at Start Lab, keep it away from the app until Task 4.** ~~SC3 finds the API or CLI to leave the connector disabled; if it isn't scriptable, Task 0's Builder disables it.~~ **Settled Sep 21 (R6 closed):** a data store created by provisioning is simply **unattached** (Connected apps: N/A) and stays that way after the student creates the app, so there is nothing to disable. Task 4's Builder **adds** the existing store to the app, which is the real step we wanted anyway.
6. **Both new beats adopted.** Task 1 gets three answers, not two: the bare assistant (generic), the data agent before instructions (**sure but partly wrong**: it blames the Aug 1 price increase, a 3% red herring), and the data agent with definitions (decomposes before naming a cause). Task 4's banned-phrase rule **fails on the first run** ("guaranteed lowest price" sails through with a note that it "will require legal review"), the Builder tightens the rule, and the re-run is clean. Both are stronger than the outline's version of the same beats.

## 5. Task structure (~182 min lab time as written; the 165 target is in the timing note below)

Legs alternate Builder (🔧) and Marketer (📣). The **admin console** is the Builder's surface; the **web app** is the Marketer's. Tasks 0–5 are written and walked (§5b–§5d); their entries here are summaries of `en.md`. Tasks 6–7 are still the plan. **The lab text never mentions the break**; the facilitator calls it (Patrick, Sep 22).

**Task 0 — Get both seats working (~15 min, written; rewritten after the Sep 21 walk, see §5a).** Both partners sign in. 🔧 The trial and Google Identity are already done by provisioning, so the Builder creates the `cymbal-voyages` app; Feature management toggles; then the **Assistant** tab: *Default web search state* **Off** and a short Cymbal Voyages system instruction. Meet the brand corpus (Data stores → Documents tab, green checks, RAG explained). 📣 Open the web app (*Go to Gemini Enterprise*); see Agents and Skills.

**Task 1 — Ask the question nobody can answer (~30 min, written; seven sub-tasks 1.1–1.7, roles rebalanced).**
📣 1.1 ask the bare assistant why August warm-escapes bookings missed plan: confident, generic, wrong; write it down. 🔧 1.2 BigQuery → Agents → + New agent → **Cymbal Voyages Analyst** → Add source → the **9 tables** in the picker's order → **Save**. 📣 1.3 ask the same question in the preview before any instructions: sure, and partly wrong (it names a cause, usually the price increase). 📣 1.4 paste the instructions and three glossary terms (business knowledge is the Marketer's). 🔧 1.5 paste the two verified queries (SQL is the Builder's), with the one "trust the table, check the prose" callout. 🔧 1.6 Save → Publish → skip Agent Registry → Publish again → *Integrate via A2A* → Copy JSON → admin console → + Add agent → *Custom agent via A2A* → paste. 📣 1.7 same question to the Analyst in the web app; **Authorize** once. Three answers side by side. *Teaching beat: the tables took two minutes; the definitions took ten, and they are what changed the answer.*

**Task 2 — Find the root cause and write the Monday readout (~21 min, written).**
📣 2.1 (10) follow the thread: which markets (cold, all eight, −33.5%); traffic or conversion (the cohort verified query: lapsed Compass, cold market, 6.74% → 2.43% on warm-escape browsing, every other cohort flat); size the red herrings; when did retargeting fall: **July 24**, because the Task 1 instructions tell the Analyst to date a change at daily grain (one-line fallback prompt if an Analyst says August 1). 🔧 2.2 (4) Skills → *Create skill with Gemini* → paste Name, Description, Instructions → Save. 📣 2.3 (7) ask the Analyst for the findings summary → copy → Skills → *executive-readout* → **New chat** → paste → send. Three paragraphs, numbers inline, recommendations not claims. Download as PDF. *Business translation: this is the readout that usually eats an analyst's Thursday, and it's reproducible next month.*

**Task 3 — Build the audience (≈34 min, written; see §5c).** Opens with a shared 3-minute concept section, **Understanding the Audience Tools** (MCP, MCP Toolbox for Databases, how we built the three tools, repo links, diagram `img/audience-tools.png`), then a Marketer ➜ Builder banner.
🔧 3.1–3.3 (12): Connected data stores → **+ New data store** → **Add MCP server** → **No authentication**, the templated MCP URL → Create. **Data / Actions (New)** → **Reload custom actions** → Activate Segment, Resolve Segment, Variant Performance → **Enable actions** on the first two (Variant Performance waits for Task 5, same page). Read the contract: Activate Segment from `tools.yaml` in full (the segment-ID+channel hash is the lesson), the other two without their SQL, and a field-by-field map of what the Builder and the Marketer each see.
📣 3.4–3.5 (16): describe the segment in English; Resolve Segment runs with no prompt: **3,838 customers, propensity 0.16, 3,271 email-contactable**, plus a readable `segment_id`. Refine (email-only 3,271; lapsed 12–24 months 2,242 at 0.19; widen 8,152; drop recent bookers 6,049; optional Hawaii 2,005). Activate the **base 3,838 to email** (aside: 567 can't be emailed; Task 6 decides per customer) → **Review: Activate Segment** card, **four** fields in order (Segment Description, Audience Size, Channel, Segment ID) → receipt **`act-0eb274a679ac`** (a hash of segment ID + channel, identical in every project). Reword and retry: "already been successfully activated," same receipt, original description. Gemini's closing "draft email copy" offer is teed up as "hold that thought; it's Task 4."
🔧 3.6 (3): the one receipt row in `cymbal_voyages.activations`. Business translation closes the task ("an ad platform's audience manager, a CDP, or an email service provider"). Task 3 ends on the Builder.

*(Facilitator-called break lands here; not in the lab text.)*

**Task 4 — Brand Studio and Friday's brief (26 min, written; see §5d).** Opens on the Builder, picking up Task 3's "hold that thought"; **no switch banner**.
🔧 4.1–4.2 (12): app → **Connected data stores** → **+ Add existing data stores** → tick **Cymbal Voyages Brand Corpus** → **Connect**. Back to the web app (Apps → cymbal-voyages → **Go to Gemini Enterprise**) → **New agent** → **Build manually** → Name / Description / Instructions form → **Brand Studio** with the generic instruction block (role, ground in the corpus, the template's headings in order, voice guide, cite retrospectives by identifier, "never use a phrase on the legal claims list") → tools: corpus **on**, **Google Search off** (on by default in every new agent; the app-level default does not reach it) → **Create** → **Chat with agent** → **Agents** → **Your agents** → ⋮ → **Share** → the partner's lab username.
📣 4.3–4.4 (9): the brief prompt carries Task 3's numbers (3,838; 0.156; 334 / 8.7%; 3,271; `act-0eb274a679ac`; July 24), since Brand Studio has only the corpus. Check the ten headings (drift can show up on the first run). Push back on tone. Plant "guaranteed lowest price": it goes through with a legal-review note. 🔧 4.5 (2): **Agents** → card → ⋮ → **Edit** → flow editor → **Brand Studio** node → **Details** → replace the instructions with the tightened block (ten headings "and no others", Retrospective placeholder, S6's legal rule plus "even if the user asks for it" and "name the rule in Legal review notes") → **Update**. 📣 4.6 (3): **new chat**, combined prompt, clean brief. Business translation closes the task.

**Task 5 — Governed creative from the same agent (24 min, written; see §5d).** Opens with a Marketer ➜ Builder banner after a two-minute opener.
🔧 5.1–5.2 (8): Actions page → tick **Variant Performance** → **Enable actions** (points back to 3.3). Edit Brand Studio → **Connectors** → **+** → **Audience Tools** (all three actions show) → two added instructions: consult variant performance for the segment before generating creative; check every image against the creative production standards → **Update**.
📣 5.3–5.5 (16): new chat; **two pastes in order** (the brief copied from the 4.6 chat via **Recent**, then the three-concepts prompt). Brand Studio opens with the whole Variant Performance table (*Creative Variant Performance Baseline*: 4.76 / 1.49 / 3.49 / 3.95 / 2.10, numbers that exist only in the warehouse, so the table is the proof the tool ran); concepts are shot descriptions. Then ask for **one** hero image for concept 1 (Nano Banana, no tool selection; the other two optional). Critique it against the Beach couple row and the imagery rules; revise. 5.5: `Run Variant Performance for the all_customers segment…`, named explicitly, and percent-off flips to the winner (1.63%); a loosely worded question gets answered from memory instead, and the lab says why. Business translation closes the task. Task 5 ends on the Marketer.

**Task 6 — Next-best-action orchestration (25 min; handoff `claude/mkt016-handoff-tasks-6-7.md`).** Opens with a Marketer ➜ Builder banner after its opener; a short shared concept section (the orchestrator, the policy table, "the model never decides") is fine, three minutes at most.
🔧 11 min: admin console → + Add agent → *Custom agent via A2A* → paste the **trimmed card** (the lab provides it; students never copy the served card, which Gemini Enterprise rejects) → skip OAuth → save. Open `decisioning_policy` in BigQuery: eight rules, priority order, thresholds as text. Governance aside: the same dialog offers *Agents from Agent Registry*, the Agent Gateway route where policies apply; ours came by card, so Gateway policies don't. Know where your boundary sits. The orchestrator's model never decides: the policy engine applies the table, the model explains.
📣 14 min: run the base audience (describe it the same way as Task 3, without a destination): 289 send_offer, 14 route_to_loyalty_team, 3,535 held (the scores are right-skewed). Widen to **all Compass members in cold markets who browsed warm** (variant E, 8,152): **suppress** fires on 2,103 ("booked in the last 60 days"). Ask about one customer and get the rule and reason. 🔧 lowers the offer threshold from 0.30 to 0.15 in the table (R03, R04, R05); 📣 re-runs the base audience: **1,082 of 3,838 (28%)** now get the offer. B2C reads as lifecycle; B2B reads as MQL→SQL routing.

**Task 7 — Wrap (7 min).** The loop: a question nobody could answer → an explanation → an audience → a brief → creative → a per-customer decision, all traceable to the company's own data, none of it from a blank page. Business translation table by team. No Lab 3 tee-up.

**Optional (post-event):** deploy the orchestrator to Agent Runtime and register it (under three minutes); B2B seam (intent-weighted account list → lead routing); instructor-driven Veo moment; re-run the loop next month with the September data.

**Timing note (Sep 22, evening).** Written: 15 + 30 + 21 + 34 + 26 + 24 = 150. Planned: 25 + 7 = 32. Running total **≈182 min** of lab against the 165 target; with a 5–15 min intro and the 15-min break that is 202–212 min, at or just over the top of D5's 180–210 block. Thursday's run-through gives the real Task 4–5 minutes; until then Tasks 6 and 7 are written to 25 and 7 as hard ceilings, and the cut list below gets rehearsed, not just listed. If Google confirms the deck's 60-minute lab blocks or a CMO-only room, the lab text still doesn't change: the cut list becomes an instructor note, and a Google SE takes the Builder seat at each table.

Cut order if the room runs slow: Task 0.4's Documents-tab visit; Task 2.1 prompts 1 and 4; Task 3.4.6 (Hawaii); the Variant Performance YAML excerpt in 3.2.6 (then reword 5.2.3's "Its own description, which you read in `tools.yaml`"); Task 5 to one concept (change "three" to "one" in the 5.3 prompt and skip 5.4); Task 6 becomes instructor-driven with hands-on moved to optional.

## 5a. Notes for the Task 3–7 writers from the Sep 21 walk (Tasks 0–2, fresh Start Lab)

- **Switch banners.** Every change of role between sub-tasks gets a visible banner, not just the 🔧/📣 in the heading. Exact markup, with blank lines around it:
  `---` / `**🔄 Switch: 🔧 Builder ➜ 📣 Marketer**` / `---`. Tasks 0–2 have seven. **Task 2 ends on the Marketer and Task 3 opens with the Builder, so Task 3 starts with a Marketer ➜ Builder banner** right after its opener.
- **Oxford comma** in every list of three or more (now in `lab-style-guide.md` §1 and §13).
- **App-level settings now in Task 0.3:** *Default web search state* is **Off**, and the app has a system instruction naming Cymbal Voyages, warm escapes, Compass, and "say what data would answer it instead of guessing." Brand Studio's own instructions and tools picker are separate; Task 4 still turns Google Search off in the agent's picker (R4: check whether the app default already does it).
- **Provisioning did more than planned:** the Gemini Enterprise trial was already active and Google Identity already set at `global`. No student step for either. The corpus shows **Connected apps: N/A** after the app is created, so R6 is closed: nothing to disable, and Task 4 *adds* the store to the app.
- **Deep Research** does not appear in the Agents list in a Start Lab project; the only Google-made agent shown is **Gemini Notebooks**. Docs still list Deep Research (not deprecated; unavailable in the Frontline edition), so it's likely the trial's edition. Don't reference Deep Research anywhere in the lab.
- The Overview now has a **"What Start Lab built for you"** section pointing at `github.com/haggman/cymbal-voyages` → `provisioning/terraform` (public). Later tasks can say "provisioned at Start Lab" without re-explaining.
- The web-app link on the app's **Overview** page is **Go to Gemini Enterprise** (upper right).
- **✅ accomplished lists need a blank line between items.** Qwiklabs joins consecutive lines into one paragraph, so the style guide's template (no blank lines) renders as one run-on line. Fixed in Tasks 0–2 and in `lab-style-guide.md` §4.
- **Balance the roles.** The walk found Task 1 was almost all Builder. It's now rebalanced: the Marketer runs the tables-only question in the agent preview and writes the instructions and glossary (business knowledge); the Builder does the tables, the verified queries (SQL), and publishing. When a task has both roles touching the same console object, hand off with **Save, then leave the editor**; the BigQuery agent editor overwrites without warning if a stale tab saves. Aim for roughly even Builder and Marketer minutes per task.
- **Numbers in agent prose can slip even when the tables are right** (a Task 1 test run put the total gap at 660 while its table showed 663 from cold markets alone; it's 701). Describe what to look for, not exact text, and keep one "trust the table, check the prose" callout per lab (it's in Task 1.5).
- Task 1 is now seven sub-tasks (1.1–1.7), ~30 min against the plan's 22.
- **Decision 4a.2's third verified query is dropped (Sep 21 walk).** With the Task 1 instructions ("to date a change in spend or traffic, look at daily figures"), the Analyst answered **July 24** on its own; the "August 1, then fix it" beat never happened. Task 2 is now three sub-tasks: 📣 2.1 follow the thread (the date step now calls back to that instruction sentence, with a one-line fallback prompt if an Analyst says August 1), 🔧 2.2 create the Skill, 📣 2.3 readout. Task 2 ≈ 21 min. The daily-spend query stays in `data-dictionary.md` but is no longer a student step.
- **Reference answers are shapes, not numbers,** except where a verified query computes them. Red-herring estimates in particular vary by method (one run: outage 25–35 bookings, price 18; our reference: ~65 and ~18). (Planning note for Tasks 3 and 6: the Toolbox tools and the orchestrator return deterministic counts, so those tasks quote exact numbers and describe only the assistant's wording as a shape.)

## 5b. SC4 handback (Sep 21): Tasks 0–2 done, and what's owed elsewhere

**State:** `en.md` has the Overview (incl. "What Start Lab built for you"), Tasks 0–2, and `<!-- Task 3 continues here -->`. Walked end to end in a fresh Start Lab project; 0 `[[verify]]` markers left. New architecture diagram at `instructions/img/architecture.png` (+ `.svg` source), text sized for the Qwiklabs pane; the §11 Nano Banana prompt is now optional.

**Measured/estimated timing:** Task 0 ≈ 15 min, Task 1 ≈ 30, Task 2 ≈ 21 → ~66 min against the plan's 54. The overrun buys the RAG/new-hire framing in Task 0 and the Builder/Marketer rebalance in Task 1. Candidate trims if the full lab runs long: Task 0.4's Documents-tab visit, and Task 2.1 prompts 1 and 4.

**Owed by others:**
- **SC1 / data dictionary:** add the Analyst readout fallback sentence to the dictionary's instructions paragraph (it's in `en.md` Task 1.4 but not in `data-dictionary.md` / `build_dictionary.py`): *"When asked for an executive readout, write three short paragraphs of plain prose (what happened, why it happened, what we recommend) with the numbers written into the sentences."* Mark the daily-spend verified query as optional (no longer a student step). If Patrick wants Oxford commas inside paste blocks, change the sources first.
- **SC3 / provisioning:** confirm what activates the Gemini Enterprise trial (nothing in the tree does it explicitly; the lab now says the setup scripts did, with a fallback). Send the Task 4 menu path for adding the existing corpus data store to the app.
- **Patrick:** set `qwiklabs.yaml` duration back to 180 before submission; commit after **File → Revert File** in VS Code whenever Claude has edited `en.md`.
- **SC8 (run-through checklist):** the Tasks 0–2 checklist artifact exists but is stale after the walk; rebuild from the final `en.md` for the full lab.

## 5c. SC5 handback (Sep 22): Task 3 done, and what later tasks inherit

Full record: `claude/mkt016-sc5-handback.md`. Walked in `qwiklabs-gcp-04-0bb3cdf9d22f`; 0 verify markers; new diagram `instructions/img/audience-tools.png` (+ `.svg`). Builder ≈15 min, Marketer ≈16, plus the 3-minute shared concept section.

**What Tasks 4–7 inherit:**
- **The Review card has four fields**, not five: Segment Description\*, Audience Size\*, Channel, Segment ID (the last two greyed but passed through). The plan's "five" was a miscount.
- **Task 3 ends on the Builder; Task 4 opens on the Builder** after the break, so Task 4 has no switch banner at the top.
- **Task 5 enables Variant Performance on the same Actions page** Task 3.2/3.3 already walked (admin console → app → Connected data stores → Audience Tools → **Data / Actions (New)** → tick → **Enable actions**), so Task 5 can point back rather than re-teach the path.
- **Gemini's "draft email copy" offer** at the end of Task 3 is teed up as "hold that thought; it's Task 4." Task 4's opener should pick that line up.
- **Web app defaults after the connector exists:** Connectors shows **Audience Tools on, Google Search off** in a new chat. Brand Studio's tools picker is still its own thing (R4).
- **Business translation lands once, at the end of each task** (Task 3 set the pattern). "Ads Data Manager" isn't named anywhere; use "an ad platform's audience manager, a CDP, or an email service provider."
- **Receipt `act-0eb274a679ac`** is the same in every project (MD5 of segment ID + channel); Task 6 can refer to it.
- A concept section read by both roles before the first banner is now an accepted shape (Task 3's "Understanding the Audience Tools"). Task 6 will want the same for the orchestrator and the policy table; keep it to three minutes.

**Owed by others:** Patrick commits `en.md` and the two image files (VS Code **File → Revert File** first). Nothing owed to SC1 or SC3 from this one.

## 5d. SC6 handback (Sep 22): Tasks 4–5 done, and what Tasks 6–7 inherit

Full record: `claude/mkt016-sc6-handback.md`. Walked in a Start Lab project Sep 22 (5.4 still in progress on the walk); 0 verify markers; Task 4 🔧 14 / 📣 12, Task 5 🔧 8 / 📣 16. `qwiklabs.yaml` now provisions two lab users (D4, R13).

**What Tasks 6–7 inherit:**
- **Task 5 ends on the Marketer; Task 6 opens with a Marketer ➜ Builder banner** after its opener.
- **No break references anywhere in the lab.** Task 3's "Coming up" was already edited to drop "Take your break."
- **Task 5's "Coming up" promises** "connect a next-best-action orchestrator that decides, customer by customer, and says why" and mentions "those 3,838." Task 6's opener picks that up.
- **Established UI Task 6 can point back to** rather than re-teach: editing an agent (**Agents** → card → ⋮ → **Edit** → flow editor → node → **Details**), the **Update** button and its "running conversations may change" warning, the **Recent** chat list, **Copy response**, and the admin console's **Agents → + Add agent → Custom agent via A2A** path (Task 1.6 did it for the Analyst; Task 6 does it again with a pasted card).
- **Two lab users.** Anything Task 6 creates in the admin console (the registered orchestrator) is app-level and visible to both; anything created in the web app is per user and needs a share. Task 6 registers in the admin console, so nothing to share.
- **Facts come from tools or the prompt, never from memory.** The 5.5 lesson: an instruction that orders a tool before *generating* doesn't fire for an opinion; name the segment when you want the tool. Task 6's orchestrator is called through the assistant, so the audience description in the prompt has to match Task 3's wording, without a destination, or the counts won't.
- **Images:** one, on request, Nano Banana; irrelevant to Task 6, but Task 7's wrap can name it.
- The two-instruction-blocks pattern (generic → tightened, select-all-and-replace paste) is available if Task 6's policy edit wants a similar shape; the policy edit is a BigQuery table change, though, so a DML copy block is the natural form.

**Owed by others:** Patrick finishes 5.4 on the walk, commits `en.md` and `qwiklabs.yaml` (VS Code **File → Revert File** first), and runs the two-account validation on Thursday (R13). SC3 adds the `username_1` custom property and a `for_each` grant only if R13 fails. SC1 (v2 only): align the template's "nine headings plus an appended Retrospective" wording with D6's ten. SC8: the checklist includes the two-account validation steps.

## 6. Data design (summary; the full spec is in the data-engineering handoff)

BigQuery dataset `cymbal_voyages`, fixed calendar Jul 2025–Sep 2026, ~50k customers, ~60 destinations, ~300 packages, ~570k web sessions, ~49k bookings, daily ad performance by channel × campaign × market, 12 past campaigns, ~200 creative variants with outcomes, a monthly plan table, per-customer decisioning features, a `decisioning_policy` rules table, and an empty `activations` receipts table. A BQML logistic-regression propensity model (booking in next 60 days) and precomputed embeddings over destination and package descriptions.

The planted chain: warm-escapes bookings in August 2026 are 18% under plan while every other category and every warm-climate market is on plan. Web sessions from lapsed Compass members in cold-weather markets browsing warm destinations are flat to up, but their conversion fell from 6.74% to 2.43%. The paid-social retargeting campaign that closed that cohort had its budget rotated to a fall city-breaks campaign on July 24 (visible only at daily grain in `ad_performance`). Two red herrings: a 4-hour site incident on Aug 9 and a price increase on two packages on Aug 1. Prior-year August was on plan.

Brand corpus (12 PDFs): brand voice guide, campaign brief template (ten headings), three past briefs with retrospectives, competitive one-pager, legal claims list, Compass program summary, audience-segments glossary, channel playbook, seasonal calendar, creative production standards.

## 6a. What SC1 delivered (Sep 18), and what the lab text must absorb

Everything is under `DevWork/cymbal-voyages/data/`. Read `docs/data-dictionary.md` and `docs/anomaly-walkthrough.md` before writing any task; the lab quotes their numbers verbatim.

**Deviations from the spec, accepted:** bookings ~49k, sessions ~570k; only signed-in sessions convert and 40% of bookings complete in a tracked session; a 16th table `customer_month_status` gives loyalty status as of each month; `propensity_training` is every customer as of Sep 1, 2025 with a 60-day warm-escape label; `plan` carries the seasonal shape. Load: 15 tables in ~5 min with `bash sql/load.sh`. Model: BQML `LOGISTIC_REG`, trains in 56 s, roc_auc 0.786. Embeddings: `gemini-embedding-001`, 3,072 dims, 360 rows.

**The numbers the story turns on:** August 2026 warm escapes 3,175 vs. plan 3,876 (−18.1%, gap 701); cold markets −33.5% across all eight, mild −1.7%, warm −2.8%; August 2025 +1.0%; July 2026 −6.5% (first dated clue). Cohort conversion on warm-escape browsing: lapsed Compass, cold market 6.74% → 2.43% on 5,546 → 6,050 sessions; every other cohort flat. Cohort paid-social sessions 1,277 → 156. CMP-002 drops to a $150/day keep-alive on Jul 24 (last full day Jul 23); CMP-012 gets the money; total paid spend rises with the season. Red herrings: Aug 9 incident ≈ 65 bookings (9% of the gap), Aug 1 re-pricing ≈ 18 bookings (3%).

**Audience:** "lapsed Compass members in cold markets who viewed a warm destination in the last 90 days" = 3,838 customers, avg propensity 0.156, 8.7% ≥ 0.30, 3,271 email-contactable (85%). After `predict_propensity.sql`: 0.162 / 10.3%. The lab quotes whichever state provisioning leaves the data in (§7 says: re-run scoring, quote 0.16). "Did not book" is implied by lapsed. Variants A–F drive Task 3's refinement.

**Creative learning for `lapsed_compass_cold`:** bonus_points 4.76% vs. percent_off 1.49% and urgency 1.49%; beach_couple 3.49% leads; "Plan your escape" 3.95% beats "Claim offer" 2.10%. For `all_customers` percent_off wins. Matches the Winter Sun Early Bird 2025 retrospective.

**Policy dry run (confirmed by the built orchestrator, Sep 19):** base audience 289 send_offer (R03 269, R04 20), 14 route_to_loyalty_team, 3,535 held, 0 suppressed. The offer threshold lowered to 0.15 sends offers to **1,082 of 3,838 (28%)**. The "suppressed because they booked last week" beat needs **variant E** (all cold-market Compass browsers, 8,152), where R01 suppresses 2,103; variant F has already removed those customers, so suppress cannot fire there.

**Data fixes applied:** the `propensity_training` description (Sep 18, planning); the `ad_performance` table description and the CMP-002 retrospective no longer name the Jul 24 rotation (SC1, commit d7c1734), so the unaided agent no longer gets the answer from text; the sc1-fix-prompt-2 set (cohort verified query, question-form titles, retargeting glossary entry) applied and re-staged by Patrick, Sep 19.

**Data fixes still owed (§5b):** the readout fallback sentence in the dictionary's instructions paragraph; mark the daily-spend verified query optional.

## 7. Provisioning design (Start Lab, target ≤15 min; every item spike-verified)

Qwiklabs startup-script Terraform as in mkt013–015, native resources first. Order matters because of the corpus import:

1. **First thing:** create the **Cymbal Voyages Brand Corpus** Cloud Storage data store, Layout Parser, pointed directly at `gs://class-demo/cymbal-voyages/v1/brand_corpus/`, and fire the import (~10 min). ~~Leave the app connector disabled if that is scriptable.~~ **Sep 21:** nothing to do; the store is created unattached and stays that way when the student creates the app (R6 closed).
2. APIs (BigQuery, Gemini Data Analytics, Gemini for Google Cloud, Discovery Engine, Cloud Run, Secret Manager, Artifact Registry, Vertex AI; *Knowledge Catalog was not needed*). Service identities. `roles/run.invoker` on every Cloud Run service for `service-PN@gcp-sa-discoveryengine.iam.gserviceaccount.com`.
3. Identity provider = **Google Identity** on the Gemini Enterprise instance. **Sep 21:** already set at `global` in the first Start Lab project, and the trial was already active; SC3 is confirming which resource does it (§5b) so the lab's Task 0 wording stays honest.
4. BigQuery: dataset `cymbal_voyages`; load all 16 tables from `gs://…/v1/out/` with the schemas from `gs://…/v1/schemas/` (`google_bigquery_job` load jobs, or `bash sql/load.sh` from a **fresh checkout at a pinned commit** with no stale local `schemas/`); then `train_propensity.sql` (56 s). **Re-scoring (`predict_propensity.sql`) was dropped by SC3 on Sep 19:** it moved the policy counts, so the lab quotes the staged scores (avg propensity 0.156 → "0.16"; the 289 / 14 / 3,535 and 1,082 counts are for this state).
5. Cloud Run, both services from the public images in `class-demo-labs`, exactly as `services/scripts/deploy_services.sh` does it (§7a): **`audience-tools`** (Toolbox 1.12.0 mirror, `tools.yaml` from the `audience-tools-config` secret, service account with `bigquery.jobUser`, `bigquery.dataViewer`, `bigquery.dataEditor`, `secretmanager.secretAccessor`, **`aiplatform.user`**) and **`orchestrator`** (1.0.0, `GOOGLE_CLOUD_LOCATION=global`, `AGENT_URL` set to its own deterministic URL). Both `--min-instances=1`, no unauthenticated access, `roles/run.invoker` for the Discovery Engine service agent. The trimmed agent card is written where the lab can show it.
6. The Gemini Enterprise **app**, its feature toggles, and the data-agent build stay student steps (Task 0 and Task 1); nothing a student creates triggers a fresh import.

**Measured by SC3 (`provisioning/TIMING.md`, runs 1–2, Sep 19–20):** apply ≈2.6 min in one pass, warehouse job ≈2 min, corpus import ≈6 min, **everything ready ≈7.5 min** from apply start; slowest piece is the import; no flakes. Two first-apply failures were fixed before the timed runs (Discovery Engine agent needs a storage grant plus a 60 s settle before the import; the Toolbox secret needs a secret-level grant plus a 60 s settle). The orchestrator image is now `1.0.1`. Tree: `provisioning/terraform` (mirrored into the lab folder's `terraform/` for the runner), `README.md`, `check.sh` (polls the import and prints READY), `sync.sh`.

**Lab users (Sep 22):** `qwiklabs.yaml` provisions `user_0` and `user_1`, both `roles/owner` on `project_0`, shown as Username 1 / Password 1 and Username 2 / Password 2. `custom_properties` still passes only `user_0.local_username`, so `main.tf`'s explicit grants (`geminidataanalytics.dataAgentCreator`, `geminidataanalytics.dataAgentUser`, `discoveryengine.admin`) land on `user_0`; `user_1` relies on Owner. If R13 finds `user_1` short, the fix is a `username_1` custom property, a matching variable, and a `for_each` over both on `google_project_iam_member.student`; the alternative is pinning User 1 as the Builder in Task 0.1.

**Templated values the lab text uses (from `qwiklabs.yaml` → `terraform/outputs.tf`; rename both together):** `{{{project_0.startup_script.audience_tools_mcp_url | "AUDIENCE_TOOLS_MCP_URL"}}}` (already ends in `/mcp`; Task 3) and `{{{project_0.startup_script.orchestrator_card_object | "ORCHESTRATOR_CARD"}}}` (a `gs://` object path; Task 6 decides whether to show the card inline as well).

## 7a. What SC2 delivered (Sep 19)

`docs/services.md` in the repo is the handoff: Part 1 the tool contracts in marketer language (the lab quotes it), Part 2 the deploy facts (SC3 reproduces `services/scripts/deploy_services.sh` in Terraform), Part 3 the test run (every number matches the walkthrough), Part 4 thirteen build decisions. Images, public-read, pulled cross-project with no grant: `us-central1-docker.pkg.dev/class-demo-labs/cymbal-voyages/toolbox:1.12.0` and `.../orchestrator:1.0.0`. No builds at Start Lab.

**Absorbed into §5:** the Review card has four fields (corrected Sep 22; Segment ID is the activation key, so a reworded retry returns the same receipt); the offer threshold at 0.15 sends 1,082 of 3,838 (28%); suppress fires on variant E (2,103 of 8,152), not F; the Actions tab lists three actions; `resolve_segment` returns a readable `segment_id` and, for a place or vibe, the five closest catalog destinations ("Hawaii" matches four Hawaii items plus Key West as the fifth-closest, which the answer shows). Task 6's audiences are described the same way as Task 3's, without a destination hint, so the orchestrator's counts match.

**For the lab writers:** `tools.yaml` reads the project from its environment, so the file shown to the Builder is the exact file mounted in the service. Channels are limited to email, paid_social, paid_search. The orchestrator normalizes anything a student types into the policy table (case, `30%`, `≥`, `yes`) and skips rows it can't read with a report, so Task 6's edit can't break it. The served agent card is in the newer A2A format that Gemini Enterprise rejects; students paste the trimmed card the lab provides.

## 8. Sub-conversations and venues

| # | Conversation | Venue | Status |
| :-- | :-- | :-- | :-- |
| SC1 | Data engineering | Standalone | Done Sep 18; two small items owed (§5b) |
| SC2 | Spike companion → services | Standalone | **Done Sep 19** (§7a) |
| SC3 | Provisioning: Terraform + startup script, qwiklabs.yaml, timing | Standalone | Running; tree, yaml, README, and two timed runs done (≈7.5 min ready, §7); third timed run and the two §5b answers owed |
| SC4 | Task writing: Tasks 0–2 | In project | **Done Sep 21**: written, walked in a real Start Lab project, all verify markers closed (§5a, §5b) |
| SC5 | Task writing: Task 3 | In project | **Done Sep 22**: written, walked in a fresh Start Lab project, all verify markers closed (§5c, `claude/mkt016-sc5-handback.md`) |
| SC6 | Task writing: Tasks 4–5 | In project | **Done Sep 22**: written, walked (5.4 finishing), all verify markers closed; two lab users added (§5d, `claude/mkt016-sc6-handback.md`) |
| SC7 | Task writing: Tasks 6–7, Lab Summary, Optional | In project | Handoff written Sep 22 (`claude/mkt016-handoff-tasks-6-7.md`); **open next** |
| SC8 | Run-through checklist artifact for the full lab | In project | Thu, from the final `en.md` |

## 9. Schedule

| Day | Patrick | Claude |
| :-- | :-- | :-- |
| Sat 19 | Data fixes done; SC2 Phase 2 done; SC4 opened | Plan and SC3 handoff updated |
| Sun 20 / Mon 21 | SC3 opened; first Start Lab worked. Tasks 0–2 walked in it (done). Deck-review email to Google | SC4 done; plan absorbed; SC5 handoff |
| Tue 22 | Tasks 3, 4, and 5 walked (done, 5.4 finishing); R10's Task 3 half closed; two lab users added | SC5 and SC6 done, plan absorbed, SC7 handoff |
| Wed 23 | Test Tasks 6–7 as they land; R10's orchestrator half | SC7 |
| Thu 24 | Full run-through from Start Lab, **twice, swapping seats** (R13); R4 recheck list | Assemble en.md, yaml; SC8 |
| Fri 25 | Fixes; submit to Qwiklabs | Retrofit outline |
| Mon 28 | Buffer; second run-through inside Qwiklabs | — |

## 10. Open questions and risks

**Closed by the spike:** Q1 (no org-policy override needed; prerequisite is the identity provider), Q2 (publishing creates the OAuth client; users Authorize once), R1 (Agent Runtime 2:42; hosting is a free choice, Cloud Run chosen), R2 (Chat agent generates images; Workflow doesn't), R5 (Skills on in a fresh lab project).

**Still open:**
- **R3:** charts inside Gemini Enterprise from the data agent: not observed. The readout is prose by design; not load-bearing.
- ~~R6~~ **Closed Sep 21:** the corpus is created unattached (Connected apps: N/A) and stays that way after the student creates the app.
- ~~R7~~ **Closed for the walk, Sep 22:** Brand Studio called Variant Performance first and opened its answer with the whole table; the numbers exist only in the warehouse, so the table is the proof. Caveat kept in the lab (5.5): a loosely worded question gets answered from memory, so the prompt names the segment. Fallback prompt stays in 5.3.
- **R13 (new, Sep 22): two lab users.** `user_1` has Owner but not the three explicit grants. Thursday's run-through runs the lab twice, swapping seats, and proves: User 2 can do every Builder step (app, Feature management and Assistant settings, data agent create and publish, A2A registration, MCP data store, enable actions) and every Marketer step (web app, **Authorize** once per user, Audience Tools, opening a shared agent); sharing works both ways (4.2.9); and the Task 2 Skill created by one user is visible to the other (if Skills are per user, Task 2.3 needs a share step or a role swap). Fix if it fails: §7's `username_1` grant, or pin User 1 as Builder.
- **R8:** the unaided data agent's answer is non-deterministic; the lab describes its shape ("names a cause, usually the price increase") and never quotes it verbatim. Extended by the walk to every agent answer that isn't a verified-query or tool result (§5a).
- **R10, Task 3 half closed Sep 22:** the Audience Tools data store on the provisioned `audience-tools` URL, the three actions, the four-field Review card, `destination_hint` staying `none` when no place is named, and the reworded retry returning the original receipt `act-0eb274a679ac` are all confirmed in a Start Lab project. **Still open (Wed 23, as Task 6 lands):** registering the orchestrator by the trimmed card and running the Task 6 questions through the assistant.
- **R9:** corpus import ~10 min is inside the budget only because it starts first. If Start Lab measures over 15 min, drop the Layout Parser for the eight PDFs without tables and keep it for the four with tables.
- **R11 (new, Sep 21):** the lab runs ~176 min as written against a 165 target (§5 timing note). Inside the block, but the cut list has to be real and rehearsed on Thursday, not theoretical.
- **R12 (new, Sep 21):** Google's deck shows 60-minute lab blocks and a "50 CMOs" room. Email sent; if either is confirmed, the lab text is unchanged and the delivery plan changes (cut list as an instructor note; Google SE in the Builder seat per table).
- **R4 (Sep 24 recheck list), partly closed Sep 22:** ~~where Google Search's default sits~~ (on in every new agent's picker; the app-level default does not reach it; the lab turns it off in 4.2.6); ~~`variant_performance` called before generation~~ (R7). **Still to recheck:** the Skill + agent restriction; the Actions tab layout; whether the first-run banned phrase goes through in a Chat agent the way it did in the Workflow (S6) and the re-run with the tightened rule is clean; the A2A card fields Gemini Enterprise rejects (Task 6 will settle it); workflow follow-up behaviour only if a Workflow is used anywhere, which it isn't.

## 11. Nano Banana prompt for the architecture diagram (optional since Sep 21; a diagram exists at `instructions/img/architecture.png`)

*A clean, wide 16:9 architecture diagram in a flat Google Cloud style, white background, thin grey connectors, product icons as simple rounded squares with short labels, no photographic elements. Three horizontal bands. Top band, labeled "Marketer (Gemini Enterprise web app)": a chat window with four agents listed on its left, "Cymbal Voyages Analyst," "Brand Studio," "Orchestrator," and "Skills: executive-readout." Middle band, labeled "Builder (admin console and BigQuery)": four boxes in a row, "BigQuery data agent" (a table icon), "Custom MCP data store: Audience Tools" (a plug icon), "Chat agent: Brand Studio" (a document icon), "A2A agent card" (a card icon), each connected upward to its agent in the top band by one arrow. Bottom band, labeled "Provisioned at Start Lab": "BigQuery: cymbal_voyages warehouse, propensity model, catalog embeddings, decisioning policy," "Cloud Storage: brand corpus (12 PDFs)," "Cloud Run: MCP Toolbox (resolve_segment, activate_segment, variant_performance)," and "Cloud Run: ADK orchestrator," with thin arrows from each up to the middle-band box that uses it. Along the very top, a thin timeline of seven chevrons reading "Ask," "Explain," "Audience," "Brief," "Creative," "Decide," "Wrap." Title in the upper left: "From Question to Campaign: Cymbal Voyages." Legible at 1600 pixels wide.*

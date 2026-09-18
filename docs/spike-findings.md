# mkt016 Spike Findings

Running record of the S1–S8 verification spike for **mkt016 — From Question to Campaign**. Plan reference: `mkt016-plan.md` §4 (spike), §5 (task paths), §7 (provisioning), §10 (open questions).

Started: 2026-09-18
Project(s) used: `qwiklabs-gcp-04-df5f1f023984` (a real Qwiklabs lab project, so the lab-project results below are the real ones)

Status key: **PASS** (plan path works as written) · **PARTIAL** (works with a change the lab must absorb) · **FAIL** (fallback path engaged) · _pending_

## Summary: what the spike locks

| ID | Status | Locks |
| :-- | :-- | :-- |
| S1 | **PASS** | Task 0 as written; the admin Add-agent dialog offers both A2A and Agent Runtime, so S5 and Task 6 have both registration routes |
| S2 | **PASS** (with lab-text changes and one data fix) | Tasks 1–2 primary path: BigQuery data agent → A2A card → Gemini Enterprise. Q2 closed for the end-user side. Agent Registry route is out (needs an Agent Gateway). |
| S3 | _pending_ | Task 2 Builder leg (Skill vs. verified query + glossary) |
| S4 | _pending_ | Task 3 primary path (custom MCP data store); Q1 |
| S5 | _pending_ | Task 3 fallback; Task 6 hosting (Cloud Run vs. Agent Runtime); R1 |
| S6 | _pending_ | Tasks 4–5 (Workflow Builder agent) |
| S7 | _pending_ | Task 5 creative path; R2 |
| S8 | _pending_ | Start Lab budget (corpus import time) |

## Contradictions to take back to planning

1. **S1 — D8 / Task 0 wording.** Workflows and agents are two separate toggles and two separate object types in the app (**Enable chat agents** and **Enable workflow**), not one renamed feature. Task 0 should name the exact toggles (list under S1). Agents built both ways show up in the agents table as *Employee-made*.
2. **S1 — who registers custom agents.** Custom agents (A2A, Agent Runtime) are registered only from the **admin console** (Gemini Enterprise → Agents → **+ Add agent**). The end-user app has no way to do it. Every "register by card" step (Tasks 1, 3 fallback, 6) is an admin-console step for the Builder, not something done in the web app.
3. **S1 — SC3 provisioning note.** `data/sql/load.sh` was committed without its execute bit (git mode 100644), so it failed to run until `chmod +x`. Fixed in the repo (mode 100755, staged, not yet committed). The copy in GCS will not keep the bit either, so provisioning should call `bash load.sh` rather than `./load.sh`.
4. **S2 — the data gives the answer away (SC1 fix needed).** With **no** instructions, glossary or verified queries, the data agent's first answer was the full root cause: −701 (−18.1%), cold markets −663 (−33.5%), *"because the marketing budget for the Warm Escapes Retargeting campaign (CMP-002…) was reallocated on July 24, 2026, to fund … Fall City Breaks 2026 (CMP-012)."* The source is the `ad_performance` **table description** that `load.sh` applies. It says the allocation changed on Jul 24. That collapses Task 2's "follow the thread", and it weakens Task 1's "the definitions are what matter" beat, because the agent does brilliantly without them. **Suggested fix (SC1):** in `data/cvgen/schemas.py`, `data/schemas/_tables.json` and `data/docs/data-dictionary.md`, find `Total paid spend is steady across the summer of 2026, but its allocation between campaigns changed on Jul 24, 2026.` and delete that sentence, leaving `Daily paid-media results by campaign and market, Jul 1, 2025 – Sep 15, 2026. Only paid channels (paid_search, paid_social, affiliate) appear here; email and organic have no media spend.` Then re-stage and re-run the unaided question. A second leak of the same kind: the CMP-002 `retrospective` in `data/content/campaigns.json` ends `Budget was rotated to Fall City Breaks in late July 2026 to fund the launch.` Delete it too. The full fix prompt for SC1 is in `docs/sc1-fix-prompt.md`. Also consider whether the `retargeting` glossary entry, which names CMP-002 and `lapsed_compass_cold`, gives too much away once the Builder types it in Task 1.
5. **S2 — Task 1 Builder leg timing.** Patrick found typing the glossary terms and the verified query "time-consuming". The 14-minute Builder leg as drafted (8 glossary terms, 3 verified queries in `data-dictionary.md`) is at risk. The lab should give copy-paste blocks and probably a shorter set (e.g. 3–4 terms, 1 verified query). This is a planning call.
6. **S2 → planning: can the bare assistant in Task 1 see the answer?** `brand_corpus/05-brief-fall-city-breaks-2026.md` says outright that CMP-012 was funded by rotating CMP-002's budget from July 24. That is fine for Brand Studio. But §7 creates the corpus data store at Start Lab, so if the assistant grounds on connected data stores by default, Task 1's "confident, generic, wrong" beat could come back half-right. Check in S6/S8 whether the assistant cites the corpus before the Builder attaches it.
7. **S2 — Knowledge Catalog API.** The checklist's "Knowledge Catalog" API was not in the API list. Everything worked without it, so it is not a requirement for this path. It may be listed under its older service name (`dataplex.googleapis.com`). Check before SC3 puts it in the API list.

---

## S1 — Fresh project, Gemini Enterprise activation, toggles

**Status: PASS** (2026-09-18)

- Data load: `sql/load.sh` + model started first, as the checklist says. It needed `chmod +x` first (see Contradiction 3), then ran. _Load time: not recorded._
- Gemini Enterprise trial license activated; app created as **test-app** (display name "Test App").
- **Configurations → Feature management**, toggles turned on exactly as the UI names them: **Enable chat agents**, **Enable workflow**, **Enable model selector**, **Enable canvas**, **Enable skills**, **Enable Gemini 3.8 Flash**. Saving shows the toast *"Feature controls updated successfully. It [may take some time] for the changes to take effect"*. Task 0 needs to tell students to expect that short propagation delay.
- The preview (end-user app) shows **Agents** with a new-agent button, and **Skills**. There is no path in the end-user app for adding a custom (A2A or Agent Runtime) agent.
- Admin left nav (the "Apps → test-app" breadcrumb): Overview, Connected data stores, **Actions**, Prompt chips, Configurations, **Agents**, **Skills**, Security, Integration. Links further down: Gemini Notebook, CodeAssist, Manage subscriptions.
- Agents page filters: **All / Google-made / Our agents**, plus **+ Add agent**. The agents table has Display name, Agent ID and Agent type columns; Core Assistant, My Agent and My Workflow (both *Employee-made*) and Deep Research (*Google-made (Deep Research)*) are listed. There is also an info banner: observability and user-content logging are off by default, with a **Configure agent logging** button.
- **+ Add agent → "Choose an agent type"** offers five cards: **Custom agent via Agent Runtime**, **Custom agent via Dialogflow**, **Custom agent via A2A** ("Custom Agents deployed anywhere that speak A2A protocol"), **Agents via Marketplace**, **Agents from Agent Registry** ("Agents in a registry within the Agent Gateway configured for this Gemini Enterprise instance").

**Locks:** Task 0 as written (with the toggle names). Both registration routes the plan needs exist in a lab project: A2A by card (the Task 1 data agent, the Task 3 fallback, the Task 6 orchestrator) and Agent Runtime (the S5 comparison). *Agents from Agent Registry* is new relative to §3. It is the Agent Gateway route, which could make the Task 6 governance aside concrete ("this is where a governed agent would come from; ours came by card"). Not load-bearing.

**Still open:** Skills was on in a fresh lab project with no allowlist step, so R5 is closed.

## S2 — BigQuery data agent → Gemini Enterprise via A2A + OAuth

**Status: PASS** (2026-09-18). The primary path works end to end in a Qwiklabs project. See Contradictions 4–6 for what the lab and data must absorb.

**APIs.** BigQuery, Gemini Data Analytics and Gemini for Google Cloud enabled. "Knowledge Catalog" was not found by that name; not needed.

**UI path and names.** BigQuery → left nav **Agents** (URL `/bigquery/agents_hub`) → the hub reads *"Chat with your data · Built with Gemini"*, with tabs **Agents / Knowledge sources** and side links **New chat · Agent catalog · Monitoring (Preview)**. **+ New agent** opens the **Editor**: *Agent name* (required), *Agent description*, **Knowledge sources → Add source** → a **Select sources** dialog (tabs All / Recent, a *Search BigQuery resources* box, a *Show starred only* toggle, then a project → `cymbal_voyages` → table tree with checkboxes).

**Lab-writing notes from the build:**
- **The table list scrolls, and the fact is hidden.** The picker shows about 8 tables and then what looks like empty space, so it looks as if tables are missing. The step must list the tables to tick in the picker's own (alphabetical) order and say how many there are. Patrick selected **9**, confirmed as, in picker order: `ad_performance`, `bookings`, `campaign_history`, `customer_month_status`, `customers`, `destinations`, `packages`, `plan`, `web_sessions`.
- **No auto-save and no leave warning.** Clicking away from the editor discards the agent silently. Tell students to click **Save** as soon as the sources, instructions and glossary are in, before testing.
- **Glossary terms and verified queries are slow to enter by hand** (Contradiction 5).
- **Verified query UI:** the top field is labelled **Question** and the SQL below it is the answer. Our verified-query titles are phrased as labels ("Bookings versus plan by month and category"). Reword them as questions, e.g. "How did bookings compare with plan by month and category?", "How did conversion change by customer cohort and month?", "How did paid spend move by campaign each week?"
- **Answers can be downloaded as PDF** (download button on each answer). This could be useful as the Task 2 readout artifact.

**Answers (same question: "Why did warm escapes bookings miss plan in August?")**
1. *Unaided* (tables only; column/table descriptions present from `load.sh`): the whole story in one answer, including the CMP-002 → CMP-012 rotation on Jul 24. Its summary table (cold 1,981 plan / 1,318 actual / −663 / −33.5%; mild −23 / −1.7%; warm −15 / −2.8%) matches the anomaly walkthrough exactly. **Too good; see Contradiction 4.**
2. *With instructions, glossary and verified query* (BigQuery Studio): cold markets −33.5% (1,318 vs. 1,981), a split by active vs. lapsed Compass members from `customer_month_status`, cold revenue $2.83M vs. $4.29M planned (−34.2%). It does **not** jump to the campaign cause. The instruction "break it down … before speculating" makes it decompose rather than conclude. That is the behavior Task 2 wants.
3. *Inside Gemini Enterprise via A2A:* trace shows *Analyzing context → Matched a verified query → Context retrieved → Running a query ×2*. It answered by market (Chicago −153 / −34.9%, Toronto −119, Boston −103 … all eight cold markets −28% to −35%; mild and warm within about ±8%). The per-market gaps sum to −701, and the cold markets to −663: consistent with the walkthrough. Output was a table plus bullet findings. _Charts: not observed (R3 still open)._

**Publishing.** You publish **twice**. The first publish offers registration with **Agent Registry**. The second offers **Integrate via A2A** with **Copy JSON** (the agent card). Agent Registry needs an Agent Gateway configured first, so it is not viable for the lab. The A2A JSON path was used: Gemini Enterprise admin → Agents → + Add agent → **Custom agent via A2A** → paste.

**First use in Gemini Enterprise.** The first question produced a prompt that the agent needs extra permissions, with an **Authorize** button → a "Sign in with Google" page → signed in as the student → the query ran. One authorization per user, as §3 predicted.

**Timings:** _not recorded._ Builder effort was dominated by entering the glossary and the verified query.

**Locks:** Tasks 1–2 primary path (no ADK analyst fallback needed). Q2: end-user OAuth works in a lab project. **Confirmed:** publishing handled the OAuth client and consent screen. Patrick created nothing by hand, so there is no OAuth step for SC3 or the students. R3 is still open.

## S3 — Assistant Skill wrapping the readout

_pending_

## S4 — Custom MCP data store (Toolbox / FastMCP on Cloud Run)

_pending_

## S5 — ADK agent via A2A: Cloud Run, then Agent Runtime

_pending_

## S6 — Workflow Builder agent on a GCS data store

_pending_

## S7 — Image generation

_pending_

## S8 — GCS data store import time

_pending_

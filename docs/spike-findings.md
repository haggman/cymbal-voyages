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
| S3 | **PARTIAL** | Skills work, but can't be used with an agent ("Using agents and skills together is not supported yet"). The readout needs a manual copy → new chat → `/executive-readout` hand-off. Task 2's Builder-leg route (Skill with hand-off, the verified-query fallback, or the readout format in the data agent's instructions) is a planning call. |
| S4 | _pending_ | Task 3 primary path (custom MCP data store); Q1 |
| S5 | _pending_ | Task 3 fallback; Task 6 hosting (Cloud Run vs. Agent Runtime); R1 |
| S6 | _pending_ | Tasks 4–5 (Workflow Builder agent) |
| S7 | _pending_ | Task 5 creative path; R2 |
| S8 | _pending_ | Start Lab budget (corpus import time) |

## Contradictions to take back to planning

1. **S1 — D8 / Task 0 wording.** Workflows and agents are two separate toggles and two separate object types in the app (**Enable chat agents** and **Enable workflow**), not one renamed feature. Task 0 should name the exact toggles (list under S1). Agents built both ways show up in the agents table as *Employee-made*.
2. **S1 — who registers custom agents.** Custom agents (A2A, Agent Runtime) are registered only from the **admin console** (Gemini Enterprise → Agents → **+ Add agent**). The end-user app has no way to do it. Every "register by card" step (Tasks 1, 3 fallback, 6) is an admin-console step for the Builder, not something done in the web app.
3. **S1 — SC3 provisioning note.** `data/sql/load.sh` was committed without its execute bit (git mode 100644), so it failed to run until `chmod +x`. Fixed in the repo (mode 100755, staged, not yet committed). The copy in GCS will not keep the bit either, so provisioning should call `bash load.sh` rather than `./load.sh`.
4. **S2 — the data gives the answer away (SC1 fix needed).** With **no** instructions, glossary or verified queries, the data agent's first answer was the full root cause: −701 (−18.1%), cold markets −663 (−33.5%), *"because the marketing budget for the Warm Escapes Retargeting campaign (CMP-002…) was reallocated on July 24, 2026, to fund … Fall City Breaks 2026 (CMP-012)."* The source is the `ad_performance` **table description** that `load.sh` applies. It says the allocation changed on Jul 24. That collapses Task 2's "follow the thread", and it weakens Task 1's "the definitions are what matter" beat, because the agent does brilliantly without them. **Suggested fix (SC1):** in `data/cvgen/schemas.py`, `data/schemas/_tables.json` and `data/docs/data-dictionary.md`, find `Total paid spend is steady across the summer of 2026, but its allocation between campaigns changed on Jul 24, 2026.` and delete that sentence, leaving `Daily paid-media results by campaign and market, Jul 1, 2025 – Sep 15, 2026. Only paid channels (paid_search, paid_social, affiliate) appear here; email and organic have no media spend.` Then re-stage and re-run the unaided question. A second leak of the same kind: the CMP-002 `retrospective` in `data/content/campaigns.json` ends `Budget was rotated to Fall City Breaks in late July 2026 to fund the launch.` Delete it too. The full fix prompt for SC1 is in `docs/sc1-fix-prompt.md`. **Resolved Sep 18:** SC1 applied the fix (commit `d7c1734`). It was reloaded into the spike project, and the `ad_performance` description was set by hand with `bq update` because the Cloud Shell clone was stale (see note 8). The re-test is under S2, "Re-test after the data fix". Also consider whether the `retargeting` glossary entry, which names CMP-002 and `lapsed_compass_cold`, gives too much away once the Builder types it in Task 1.
5. **S2 — Task 1 Builder leg timing.** Patrick found typing the glossary terms and the verified query "time-consuming". The 14-minute Builder leg as drafted (8 glossary terms, 3 verified queries in `data-dictionary.md`) is at risk. The lab should give copy-paste blocks and probably a shorter set (e.g. 3–4 terms, 1 verified query). This is a planning call.
6. **S2 → planning: can the bare assistant in Task 1 see the answer?** `brand_corpus/05-brief-fall-city-breaks-2026.md` says outright that CMP-012 was funded by rotating CMP-002's budget from July 24. That is fine for Brand Studio. But §7 creates the corpus data store at Start Lab, so if the assistant grounds on connected data stores by default, Task 1's "confident, generic, wrong" beat could come back half-right. Check in S6/S8 whether the assistant cites the corpus before the Builder attaches it.
7. **S2 — Knowledge Catalog API.** The checklist's "Knowledge Catalog" API was not in the API list. Everything worked without it, so it is not a requirement for this path. It may be listed under its older service name (`dataplex.googleapis.com`). Check before SC3 puts it in the API list.
8. **S2 → SC3: `load.sh` prefers a local `schemas/` folder over the bucket's.** The first reload after the fix still applied the old description, because it ran from a Cloud Shell clone taken before the fix, and `load.sh` uses `../schemas` when that folder exists. Provisioning must run `load.sh` from a fresh checkout at a pinned commit, or from a copy with no local `schemas/` so it pulls from `gs://…/v1/schemas/`. Otherwise bucket and descriptions can silently disagree.
9. **S2 → planning: a new Task 1 beat is available.** After the fix, the unaided agent confidently blames the **Aug 1 price increase** (a red herring worth about 18 bookings, 3% of the gap) alongside the cold-market miss and low retargeting spend. The instructed agent decomposes instead of asserting a cause. "Without the definitions it sounds sure and is partly wrong" is a stronger Task 1 contrast than "without the definitions it's vague".
10. **S3 — a Skill can't hand off to (or run alongside) the data agent.** Attaching `/executive-readout` in the Analyst agent's chat gives the toast *"Using agents and skills together is not supported yet. Please use one at a time."* The working route: ask the agent for a findings summary → the response's copy button → new chat → `/executive-readout based on the following:` + paste. That is three extra steps in the 6-minute Marketer leg, and it teaches that Skills live in the assistant, not in agents. Alternatives: (a) the §5 fallback (verified query + glossary term on the data agent); (b) put the readout format in the data agent's own instructions, so "give me the executive readout" works in one step. Planning call.
11. **S3 → SC1: the dictionary's cohort verified query does not reproduce the story's pivot number.** Asked for the cohort's conversion change, the agent reported lapsed Compass cold-market conversion *"fell from 3.86% to 3.50%"*. The walkthrough's pivot is **6.74% → 2.43%**. That figure is on **warm-escape browsing sessions** (`WHERE s.viewed_warm_escape`), August 2025 vs. August 2026. The verified query *"Conversion rate by customer cohort and month"* in `data/docs/data-dictionary.md` has no `viewed_warm_escape` filter, so it measures all sessions month by month. **Fix:** replace it with the walkthrough's query (anomaly-walkthrough.md, the cohort table under "lapsed Compass member, cold market | 5,546 | 6.74"), or add `WHERE s.viewed_warm_escape`. Add to the instructions or glossary: *"cohort conversion means conversion on sessions that viewed a warm escape, compared with the same month last year."* Other upstream errors also flowed into the readout: the incident at "15 to 25 bookings" (walkthrough ≈65), the CMP-002 baseline at "$12.4k to $14.9k per week" (walkthrough ≈$20.9k; $12.4k is the transition week), weekly conversions "63 → 1–4" (walkthrough ≈100 → 3–9), and revenue −$1.59M / −18.9% (walkthrough −$1.62M / −19.3%).
12. **S3 — a skill generated from a one-line request is generic and invents facts.** "Create skill with Gemini" turned the one-line request into a long incident-post-mortem skill (engineering examples, "SLA impact"). The readout it produced opened with a preamble ("Good call synthesizing this…"), used an emoji heading, bold and rules, and stated a remediation as done: *"engineering has deployed patches to prevent session data loss"*. That is not in the data. If the Skill route stays, ship a Cymbal-specific instruction block (or a SKILL.md for **Upload skill**) that says: output only the three paragraphs, with no preamble, headings, emoji or bold; use only numbers present in the input; paragraph 3 gives *recommendations*, never claims that actions were taken.

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

**Re-test after the data fix (Sep 18, new agent, same 9 tables, no instructions, same question):** the leak is closed. The agent no longer names CMP-002 → CMP-012, a budget rotation, or July 24 as the cause. Its answer:
- Headline: *"…primarily due to severe underperformance in key cold-weather feeder markets (e.g., Chicago, Toronto, and Boston, each trailing plan by 30% to 35%), driven by price increases on core packages (Aruba Classic Week and Maui Classic Week took effect August 1, 2026) alongside a sharp pullback in dedicated warm-escape retargeting ad spend."*
- Per-market table identical to the earlier runs (Chicago 439/286/−153 … Milwaukee 106/71/−35).
- Drivers it lists: (1) the cold-market deficits (correct); (2) **the Aug 1 price increases**: Aruba Classic Week $1,449 → $1,619, Maui Classic Week $1,319 → $1,479, *"dampening early-booking conversion"* (the planted red herring, stated as a cause); (3) *"Paid media spend was heavily directed toward Fall City Breaks and generic Brand Search, while dedicated Warm Escapes Retargeting received only ~$4.6k in media spend during August"*. That matches the $150/day keep-alive × 31 days, so it is found from the spend data, not from text.
- **What Task 2 still has to do:** rule out the price increase (≈18 bookings, 3% of the gap), rule out the Aug 9 incident, establish **when** retargeting fell and from what level (Jul 24; $3,000/day before), and connect it to the mechanism: lapsed Compass members in cold markets still browsing but converting at 2.43% instead of 6.74%. The unaided agent did none of that. The thread is intact.
- Caveat: answers are non-deterministic. Another run may weight the drivers differently, so the lab text should not quote the unaided answer verbatim.

**Timings:** _not recorded._ Builder effort was dominated by entering the glossary and the verified query.

**Locks:** Tasks 1–2 primary path (no ADK analyst fallback needed). Q2: end-user OAuth works in a lab project. **Confirmed:** publishing handled the OAuth client and consent screen. Patrick created nothing by hand, so there is no OAuth step for SC3 or the students. R3 is still open.

## S3 — Assistant Skill wrapping the readout

**Status: PARTIAL** (2026-09-18). A Skill can be created and invoked in the assistant. It cannot be combined with an agent, so the plan's "hand off to the registered data agent" does not work (Contradiction 10).

**UI path and names.** Web app → **Skills**. Empty state: *"Add your first skill — Create with Gemini, explore the marketplace, or upload your own to get started"*, with three buttons: **Create skill with Gemini**, **Browse skills**, **Upload skill**. *Create skill with Gemini* opens a split view: a chat box on the left, and on the right a form with **Name\*** (64 chars), **Description\*** (1,024), *Created by: You*, **Trigger** (auto-filled as `/` + the slugged name), **Instructions** (500,000), **Cancel / Save**.

**What was done.** Typed into the left-hand chat: *"Name: Executive readout. Instructions: a three-paragraph narrative (what happened, why, what we'll do), numbers inline, no charts, no bullets, one sentence on the business impact."* Gemini filled the form: name `executive-readout`, trigger `/executive-readout`, a 345-character description ("Synthesizes complex operational updates, project milestones, or incident reports into a concise, professional, three-paragraph narrative executive…"), and long instructions (Overview, When to Use, Expected Input/Output, Required Tools/Data, a four-step workflow including a self-check). The Instructions field **renders the Markdown**. There is no raw or source view, and copying out of it drops the formatting. The lab should hand students text to paste or a file to upload, never ask them to edit the generated Markdown.

**Invocation.**
- In the Analyst agent's chat, adding the skill chip gives the toast *"Using agents and skills together is not supported yet. Please use one at a time."*
- Workaround that worked: in the agent, prompt *"Summarize what we found about why warm escapes missed plan in August 2026: the size of the miss versus plan, where it was concentrated by market climate, which customer cohort's conversion changed and by how much, what happened to the Warm Escapes Retargeting campaign and when, and what the site incident and the price change contributed. Include the numbers."* → copy the response → **new chat** → `/executive-readout based on the following:` + paste.

**Output.** Three narrative paragraphs with numbers inline, a bolded business-impact sentence and no bullets, so the format is honoured. But: a chatty preamble and sign-off, an emoji heading, horizontal rules, one invented action, and the upstream numeric errors (Contradictions 11–12). Right: 701 / 3,175 / 3,876 / −18.1%; cold −663 / −33.5%; mild −1.7%, warm −2.8%; CMP-002 collapse "starting in late July". Wrong or unverified: see Contradiction 11. The Aug 1 price change is described as a compounding cause, not ruled out (about 3% of the gap).

**Timings:** _not recorded._

**Locks:** Skills are assistant-only (confirms §2 and §3). Task 2's Builder leg as written ("a Skill … [that] produces the executive readout" from the data agent's findings) needs either the copy/paste hand-off or a different route; see Contradiction 10. **Confirmed:** it must be a new chat. Choosing an agent opens a dedicated agent conversation, and there is no way to leave or deactivate the agent mid-conversation. The hand-off is always copy → new chat → paste.

**Draft Cymbal-specific skill:** `skills/executive-readout/SKILL.md` (Sep 18). Its frontmatter `name` / `description` and its body map onto the form's Name, Description and Instructions fields, so students can paste three fields instead of uploading a file. **Re-test with the Cymbal skill (Sep 18):** Patrick edited the existing skill in place and pasted the new text. Editing works; no upload is needed. The prompt was *"Please give me the /executive-readout for the following:"* + the Analyst agent's summary (copy button). The copy **flattens tables**: the climate table arrived as one run-together line (`climatebookingsplanned_bookings…`), and the skill still read it correctly. Output: three clean paragraphs, no preamble, headings, emoji or bold; recommendations written as proposals ("We recommend that marketing…", "product and pricing teams should review…"); no invented actions; every number traceable to the input. Two small misses, both fixed in the SKILL.md since: a `---` separator plus a spurious *"Missing from the findings: The specific business impact of the recommendations"* (the impact sentence is now defined as the impact of the miss itself), and no separator line allowed. **The remaining errors are all upstream in the agent's summary:** it dated the CMP-002 collapse **August 1** (monthly totals $69,944 → $4,650; true date Jul 24), used the 3.86% → 3.50% cohort figure, left the incident unquantified, and kept the price change as a contributing cause. The skill faithfully passed these on. Fix prompt for SC1: `docs/sc1-fix-prompt-2.md`.

**Form and edit paths (confirmed Sep 18):** the right-hand form in *Create skill with Gemini* is directly editable, so students can ignore the Gemini chat and paste Name, Description and Instructions. An existing skill opens at **Skills → *skill name*** as a detail page: title, `/trigger`, description, *Created by*, the instructions in a panel with a **rendered / source (`<>`) toggle**. The create/edit form (with the Gemini chat on the left) has no such toggle, so raw Markdown can be seen only on the detail page, and a **New chat** button. The **⋮** menu has **Edit / Disable / Delete**; *Edit* reopens the three-field form. In the Skills list the skill appears under **Enabled** as a folder containing `SKILL.md`. That confirms the SKILL.md packaging, so **Upload skill** is a possible alternative, though no file upload is needed. **Confirmed:** the skill page's **New chat** button opens a new chat with the skill's trigger already entered as the first thing in the message box. So the Task 2 hand-off is: copy the Analyst's summary → Skills → executive-readout → **New chat** → paste → send. Patrick has updated the skill in the spike project to the current `SKILL.md`.

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

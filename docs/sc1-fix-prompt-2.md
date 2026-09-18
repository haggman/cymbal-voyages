# SC1 follow-up 2: make the verified queries reproduce the walkthrough

*Paste everything below the line into the data-engineering conversation (SC1).*

---

Thanks for the description fix: the unaided data agent no longer names the cause, and it now blames the Aug 1 price change with confidence, which is a useful beat for Task 1. The spike (items S2 and S3, Sep 18) found a second problem, this time in the **verified queries and instructions** in `docs/data-dictionary.md`. The lab has the Builder type these into the BigQuery data agent. With them in place, the agent's findings summary got the story's key numbers wrong, and those errors flowed straight into the executive readout.

## What the configured agent reported, versus the walkthrough

| Finding | Agent said | `anomaly-walkthrough.md` says | Why |
| :-- | :-- | :-- | :-- |
| Target-cohort conversion | lapsed Compass, cold: 3.86% (Jul 2026) → 3.50% (Aug 2026) | **6.74% → 2.43%**, Aug 2025 vs. Aug 2026, warm-escape browsing sessions | The dictionary's verified query "Conversion rate by customer cohort and month" has no `WHERE s.viewed_warm_escape` and compares month to month, not year over year |
| When retargeting collapsed | "on **August 1**", $69,944 in July → $4,650 in August, "$2,200+/day" | **Jul 24**, from about $3,000/day (about $20.9k a week) to the $150 keep-alive | The agent aggregated spend by month, and a monthly total hides the date. The weekly verified query exists but wasn't used, and there is no daily one |
| Site incident | "isolated temporary loss", not quantified (in another run, "15 to 25 bookings") | **≈65 bookings** (9% of the gap) | No verified query or instruction for it |
| Price change | "contributing to conversion resistance", not quantified | **≈18 bookings** (3% of the gap) | No verified query or instruction for it |

Everything else matched exactly: 701 / −18.1%, $1,620,380 / −19.3%, cold −663 / −33.5% / −$1,467,293 / −34.2%, mild −1.7%, warm −2.8%.

## What I need

1. **Replace the cohort verified query** in the dictionary with the walkthrough's "Conversion of warm-escape browsing sessions by customer cohort, August 2025 versus August 2026" (Step 5), so it filters on `viewed_warm_escape` and compares the same month last year. It must return 6.74 → 2.43 for the target cohort.
2. **Add a daily-grain spend query** based on the walkthrough's "Warm Escapes Retargeting, daily, the week of the change" (Step 6), and add one sentence to the **instructions**: *"To date a change in spend or traffic, look at daily figures; monthly totals hide the date."*
3. **Add to the instructions how to size a red herring**: *"When asked what an incident or a price change contributed, estimate it in bookings and as a share of the gap."* If the agent can't reliably get to ≈65 and ≈18 from the instruction alone, draft the two walkthrough queries (Step 4, "Red herring 1: daily sessions around the Aug 9 incident" and "Red herring 2 in context…") as candidate verified queries. Mark them **optional**, because typing time in the Task 1 Builder leg is already a problem, and planning will decide what ships.
4. **Reword every verified-query title as a question.** The data agent's UI labels that field **Question**. For example: "How did bookings compare with plan by month and category?", "How did warm-escape browsing conversion change by customer cohort, this August versus last?", "How did paid spend move by campaign each week?", "When exactly did Warm Escapes Retargeting spend change?"
5. **Glossary:** add or extend a term so that "conversion" for the cohort question means conversion on warm-escape browsing sessions, compared with the same month last year.
6. **Flag the verified-query count and length.** Tell me how many verified queries and glossary terms the full set now has, and the character count of each, so planning can decide which ones students type and which could be pre-loaded.

## Verify before handing back

Run each verified query in BigQuery against the reloaded `cymbal_voyages` data (spike project `qwiklabs-gcp-04-df5f1f023984` is fine) and confirm it returns the walkthrough's figure: 6.74 → 2.43; July 23 as the last full-spend day and Jul 24 as the first $150 day; ≈65; ≈18. Only the docs change, so there's no regeneration or re-staging of data, but re-copy `docs/data-dictionary.md` to `gs://class-demo/cymbal-voyages/v1/docs/`, commit and push.

## Hand back

The new verified-query and glossary text exactly as students would paste it, the per-query result check, and the counts from item 6.

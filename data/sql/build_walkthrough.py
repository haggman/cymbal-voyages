"""Render docs/anomaly-walkthrough.md from the query results (called by verify_local.py --write)."""
from __future__ import annotations

import datetime as dt

from verify_local import md_table  # noqa: F401  (import cycle is fine at call time)


def _row(res, key, **match):
    title, sql, cols, rows = res[key]
    for r in rows:
        d = dict(zip(cols, r))
        if all(d.get(k) == v for k, v in match.items()):
            return d
    raise KeyError((key, match))


def _block(res, key, note: str = "") -> str:
    title, sql, cols, rows = res[key]
    out = [f"### {title}", "", "```sql", sql, "```", "", md_table(cols, rows), ""]
    if note:
        out += [note, ""]
    return "\n".join(out)


def render(res: dict) -> str:
    warm = _row(res, "q01_aug_vs_plan_by_category", category="warm_escape")
    cold = _row(res, "q03_aug_warm_by_climate", climate="cold")
    mild = _row(res, "q03_aug_warm_by_climate", climate="mild")
    warmc = _row(res, "q03_aug_warm_by_climate", climate="warm")
    aug25 = _row(res, "q02_warm_escapes_by_month", month=dt.date(2025, 8, 1))
    jul26 = _row(res, "q02_warm_escapes_by_month", month=dt.date(2026, 7, 1))
    coh = _row(res, "q09_cohort_conversion", cohort="lapsed Compass member, cold market")
    other = _row(res, "q09_cohort_conversion", cohort="lapsed Compass member, other market")
    active = _row(res, "q09_cohort_conversion", cohort="active Compass member")
    inc = {r[0]: (r[1], r[2]) for r in res["q05_incident_daily_sessions"][3]}
    aug9 = inc[dt.date(2026, 8, 9)]
    neighbors = [inc[d] for d in inc if d != dt.date(2026, 8, 9)]
    avg_sess = sum(n[0] for n in neighbors) / len(neighbors)
    avg_conv = sum(n[1] for n in neighbors) / len(neighbors)
    lost_sess = int(round(avg_sess - aug9[0]))
    lost_conv = int(round(avg_conv - aug9[1]))
    lost_bookings = int(round(lost_conv / 0.4))
    price = {r[0]: dict(zip(res["q08_price_change_context"][2], r)) for r in res["q08_price_change_context"][3]}
    rep = price["re-priced Aug 1"]
    ps25 = _row(res, "q11_cohort_channel_mix", channel="paid_social")
    seg = dict(zip(res["q16_segment_base"][2], res["q16_segment_base"][3][0]))
    fcb = _row(res, "q15_campaign_history_fcb", campaign_id="CMP-012")
    rt = _row(res, "q15_campaign_history_fcb", campaign_id="CMP-002")
    miss = warm["planned_bookings"] - warm["bookings"]
    cold_miss = cold["planned_bookings"] - cold["bookings"]
    offers = {r[0]: r[4] for r in res["q18_creative_offer"][3]}
    imagery = {r[0]: r[4] for r in res["q19_creative_imagery"][3]}
    ctas = {r[0]: r[4] for r in res["q20_creative_cta"][3]}

    P = []
    P.append(f"""# Anomaly walkthrough: why August 2026 missed plan

*Generated from the shipped data by `sql/verify_local.py --write`. Every number below is what the query returns against `out/` (DuckDB) and, once loaded, against `cymbal_voyages` in BigQuery. Regenerating the data with the same seed reproduces these numbers exactly.*

**The finding the trail converges on.** August 2026 warm-escape bookings came in {abs(warm['bookings_variance_pct']):.1f}% under plan ({warm['bookings']:,} confirmed bookings against a plan of {warm['planned_bookings']:,}, a gap of {miss:,}). Every other category landed within a few percent of plan. The whole miss sits in the cold-weather markets ({cold['variance_pct']:+.1f}%, {cold_miss:,} bookings short); mild ({mild['variance_pct']:+.1f}%) and warm ({warmc['variance_pct']:+.1f}%) markets were on plan. Inside the cold markets, the miss belongs to one cohort: lapsed Cymbal Compass members who browsed warm destinations. Their browsing held up ({coh['aug_2025_sessions']:,} warm-escape sessions in August 2025, {coh['aug_2026_sessions']:,} in August 2026) but their conversion fell from {coh['aug_2025_conv_pct']:.1f}% to {coh['aug_2026_conv_pct']:.1f}%, while every other cohort converted the same as last year. The always-on paid-social program that reached that cohort, Warm Escapes Retargeting (CMP-002), had its budget rotated to Fall City Breaks 2026 (CMP-012) on **July 24, 2026**; total paid spend never dropped, which is why a naive spend check says nothing changed. August 2025 was on plan ({aug25['variance_pct']:+.1f}%), so seasonality is ruled out. Two red herrings, a 4-hour site incident on Aug 9 and a price increase on two packages on Aug 1, each explain a rounding error's worth of the gap.

The queries are in BigQuery SQL against dataset `cymbal_voyages`. Column names and values are the ones the data agent sees in `schemas/*.json`.

## Step 1: confirm the miss and rule out the other categories
""")
    P.append(_block(res, "q01_aug_vs_plan_by_category",
                    f"Warm escapes are the only category materially off plan. The other four are within about ±5% on bookings, which is inside the plan's normal noise. Revenue tells the same story as bookings, so this is a volume problem, not a price-mix problem."))
    P.append("## Step 2: rule out seasonality\n")
    P.append(_block(res, "q02_warm_escapes_by_month",
                    f"Every month from July 2025 through June 2026 is within about ±3% of plan, including August 2025 at {aug25['variance_pct']:+.1f}%. The plan already carries the seasonal shape (August and September are the biggest warm-escape months because cold-weather customers book winter trips from late summer). Note July 2026 at {jul26['variance_pct']:+.1f}%: the miss starts in the last week of July, which is the first dated clue."))
    P.append("## Step 3: find where the miss lives\n")
    P.append(_block(res, "q03_aug_warm_by_climate",
                    f"The cold-weather markets carry the entire gap: {cold['bookings']:,} bookings against a plan of {cold['planned_bookings']:,} ({cold['variance_pct']:+.1f}%). Mild and warm markets are on plan."))
    P.append(_block(res, "q04_aug_warm_by_market",
                    "All eight cold markets are down by roughly the same proportion and no mild or warm market is down more than plan noise, so this is not one city's problem (a local competitor, a weather event) but something that touched all cold-weather customers at once."))
    P.append("## Step 4: check the two obvious explanations (the red herrings)\n\n### Red herring 1: the August 9 site incident\n")
    P.append(_block(res, "q05_incident_daily_sessions"))
    P.append(_block(res, "q06_incident_hourly",
                    f"Sessions on Aug 9 were {aug9[0]:,} against roughly {avg_sess:,.0f} on the surrounding days: about {lost_sess:,} sessions lost during the four hours (14:00–18:00 UTC, 10am–2pm Eastern) when the site was down. Converted sessions were {aug9[1]} against roughly {avg_conv:.0f}, so the incident cost about {lost_conv} tracked bookings, or roughly {lost_bookings} bookings in total once app and phone bookings are counted (about 40% of bookings complete in a tracked web session). That is a real loss, and it is about {100 * lost_bookings / miss:.0f}% of a {miss:,}-booking gap."))
    P.append("### Red herring 2: the August 1 price increase\n")
    P.append(_block(res, "q07_price_change_packages"))
    P.append(_block(res, "q08_price_change_context",
                    f"Two packages (Aruba Classic Week and Maui Classic Week) went up about 12% on Aug 1. Their August bookings were {rep['aug_bookings']} against {rep['aug_2025_bookings']} the August before, a drop that is real but tiny: {rep['aug_bookings']} bookings is {100 * rep['aug_bookings'] / warm['bookings']:.1f}% of the category, and the {rep['aug_2025_bookings'] - rep['aug_bookings']}-booking year-over-year decline is about {100 * (rep['aug_2025_bookings'] - rep['aug_bookings']) / miss:.0f}% of the gap. Part of that decline is the cohort effect below anyway, since both packages sell heavily to cold-weather members."))
    P.append("## Step 5: follow the thread into customer behavior\n")
    P.append(_block(res, "q09_cohort_conversion",
                    f"This is the pivot of the analysis. Warm-escape browsing sessions are split by who was browsing, using each customer's loyalty status as it stood at the start of that month (`customer_month_status`). Lapsed Compass members in cold markets browsed as much as last year ({coh['aug_2025_sessions']:,} sessions then, {coh['aug_2026_sessions']:,} now) and converted at {coh['aug_2025_conv_pct']:.2f}% then versus {coh['aug_2026_conv_pct']:.2f}% now. Active members ({active['aug_2025_conv_pct']:.1f}% → {active['aug_2026_conv_pct']:.1f}%) and lapsed members in other markets ({other['aug_2025_conv_pct']:.1f}% → {other['aug_2026_conv_pct']:.1f}%) did not move. Anonymous sessions never convert because booking requires signing in."))
    P.append(_block(res, "q10_cohort_monthly",
                    f"Month by month, the cohort's conversion runs 6–8% through the 2025 booking season, eases to 4–5% in the off-season (as it did in July 2025), and then, instead of climbing back into the 6–8% range when the season opens, drops to {coh['aug_2026_conv_pct']:.1f}% in August 2026 and stays down in September. The paid-social share of the cohort's sessions collapses at the same moment, from about 24% to about 3%, with the first partial-month dip in July."))
    P.append(_block(res, "q11_cohort_channel_mix",
                    f"The cohort's paid-social sessions fell from {ps25['aug_2025_sessions']:,} to {ps25['aug_2026_sessions']:,}, while direct, organic and email sessions all rose. Intent was still there; the paid reminder that used to close it was not."))
    P.append("## Step 6: follow the thread into ad spend\n")
    P.append(_block(res, "q12_total_paid_spend_weekly",
                    "The naive check. Total paid spend did not fall in late July; it rose with the season into August (the retargeting budget carried a seasonal uplift, and Fall City Breaks inherited it), and paid social specifically rose. Anyone who stops here concludes spend is not the problem."))
    P.append(_block(res, "q13_spend_by_campaign_weekly",
                    "By campaign, the story is plain: Warm Escapes Retargeting (CMP-002), the always-on program aimed at `lapsed_compass_cold`, drops to a token keep-alive in the week of July 20, and Fall City Breaks 2026 (CMP-012) starts the same week with the same money. Attributed conversions for CMP-002 go from roughly 100 a week to single digits."))
    P.append(_block(res, "q14_retargeting_daily",
                    f"Daily grain pins the date: July 23 is the last full day, July 24 is the first day at the $150 keep-alive."))
    P.append(_block(res, "q15_campaign_history_fcb",
                    f"`campaign_history` confirms it in words: CMP-012 is \"funded by rotating the always-on paid-social budget rather than new money\" and has delivered {fcb['bookings_attributed']} bookings at an ROI of {fcb['roi']} through mid-September; CMP-002's retrospective notes the budget was rotated in late July 2026. The brand corpus brief for Fall City Breaks says the same in its budget section."))
    P.append(f"""## What the trail adds up to

1. Warm escapes missed plan by {abs(warm['bookings_variance_pct']):.1f}% in August 2026; nothing else did, and August 2025 was on plan.
2. The gap is entirely in cold-weather markets, spread across all eight of them.
3. Neither the Aug 9 incident (about {lost_bookings} bookings) nor the Aug 1 price change (about {rep['aug_2025_bookings'] - rep['aug_bookings']} bookings) is more than a few percent of the {miss:,}-booking gap.
4. Lapsed Compass members in cold markets browsed warm escapes as much as last year but converted at {coh['aug_2026_conv_pct']:.1f}% instead of {coh['aug_2025_conv_pct']:.1f}%; every other cohort converted normally.
5. Their paid-social sessions fell by roughly 90% because Warm Escapes Retargeting was defunded on July 24, 2026 to launch Fall City Breaks; total spend stayed flat so the change is invisible at the top line.

## Later tasks: sizing the audience, learning from creative, dry-running the policy

### The audience in one query
""")
    P.append(_block(res, "q16_segment_base",
                    f"\"Lapsed Compass members in cold markets who viewed a warm destination in the last 90 days and did not book\" resolves to **{seg['customers']:,} customers** from `customer_features` alone (as of Sep 1, 2026; the 90-day window is Jun 3 – Aug 31). A lapsed customer by definition has not booked in 12 months, so \"did not book\" is implied by `loyalty_status = 'lapsed'`. Average propensity is {seg['avg_propensity']:.2f} and {seg['pct_propensity_ge_030']:.1f}% score 0.30 or higher; {seg['pct_email_contactable']:.0f}% are email-contactable."))
    P.append(_block(res, "q17_segment_variants",
                    "Each edit to the segment definition moves both the size and the propensity profile, which is what the lab's audience task needs to show: restricting to email-contactable trims the size and leaves propensity alone; splitting by how long ago they lapsed separates a higher-propensity recently-lapsed group (12–24 months) from a colder long-lapsed group (24+ months); widening to all Compass members in cold markets who browsed warm roughly doubles the audience and raises average propensity because it pulls in active members; dropping recent bookers from that wider set takes it back down."))
    P.append("### Which creative converted this segment\n")
    P.append(_block(res, "q18_creative_offer"))
    P.append(_block(res, "q19_creative_imagery"))
    P.append(_block(res, "q20_creative_cta",
                    f"For `lapsed_compass_cold`, bonus points ({offers['bonus_points']:.2f}%) beat percent-off ({offers['percent_off']:.2f}%) and urgency ({offers['urgency']:.2f}%) by a wide margin; beach-couple imagery ({imagery['beach_couple']:.2f}%) leads and city skyline trails; \"Plan your escape\" ({ctas['plan_your_escape']:.2f}%) is the best call to action and \"Claim offer\" the worst. Loyalty members respond to recognition, not discounts, which is also what the Winter Sun Early Bird 2025 retrospective in the brand corpus says."))
    P.append(_block(res, "q21_creative_contrast",
                    "The same table gives a different answer for the broad `all_customers` segment, where percent-off does fine. The learning is segment-specific, which is the point."))
    P.append("### Decisioning dry run\n")
    P.append(_block(res, "q22_policy_dry_run",
                    "With the default `decisioning_policy` (suppress if booked in the last 60 days; route gold members with propensity ≥ 0.60 to the loyalty team; send an offer at propensity ≥ 0.30 when contactable; otherwise hold for retargeting), most of the base audience is held for retargeting because the score distribution is right-skewed (median about 0.12). Lowering the offer threshold to 0.15 sends offers to roughly a third of the audience; that edit is the natural thing for students to try."))
    return "\n".join(P)

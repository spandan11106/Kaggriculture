"""Turn a pull_replays summary.json into a committable loss analysis.

Answers: how often does v19 lose, to whom (by strength), and WHERE the game is
lost — opening/build vs endgame — via the per-day money gap and a crossover day.
Also compares final farm composition (our meta vs opponents' in losses).

Usage:
  python scripts/loss_report.py 55245235 > analysis/loss_report_55245235.md
"""
import json, statistics, sys

SUB = sys.argv[1] if len(sys.argv) > 1 else "55245235"
SUMMARY = f"replays/live_{SUB}/summary.json"
US_SCORE_DEFAULT = 2563.2  # v19 current public score; used to tier opponents

recs = [r for r in json.load(open(SUMMARY)) if "error" not in r]
us_score = US_SCORE_DEFAULT


def gap_by_day(r, days):
    out = []
    for d in days:
        u, o = r["money_us"], r["money_opp"]
        if d < len(u) and u[d] is not None and o[d] is not None:
            out.append(u[d] - o[d])
        else:
            out.append(None)
    return out


def last_lead_day(r):
    """Highest day index where we were still >= opponent (>=0), else -1 (never led)."""
    u, o = r["money_us"], r["money_opp"]
    lead = -1
    for d in range(min(len(u), len(o))):
        if u[d] is not None and o[d] is not None and u[d] >= o[d]:
            lead = d
    return lead


def p(*a):
    print(*a)


n = len(recs)
wins = [r for r in recs if r["result"] == "WIN"]
losses = [r for r in recs if r["result"] == "LOSS"]
ties = [r for r in recs if r["result"] == "TIE"]
errs = [r for r in recs if r["us_status"] != "DONE" or r["opp_status"] != "DONE"]
margins = [r["margin"] for r in recs]

p(f"# v19 loss analysis — submission {SUB}\n")
p(f"_{n} public episodes; v19 public score {us_score}._\n")
p(f"- **Record:** {len(wins)}W – {len(losses)}L – {len(ties)}T "
  f"(winrate **{len(wins)/n:.0%}**)")
p(f"- **Mean margin:** {statistics.mean(margins):+,.0f} "
  f"(median {statistics.median(margins):+,.0f}, "
  f"range {min(margins):+,.0f}..{max(margins):+,.0f})")
p(f"- **Non-DONE episodes:** {len(errs)}"
  + ("" if not errs else " — " + ", ".join(str(r["ep"]) for r in errs)))

# tier by opponent strength relative to us
def tier(r):
    s = r["opp_score"]
    if s is None:
        return "unknown"
    return "stronger" if s > us_score else "weaker/equal"


p("\n## Record vs opponent strength\n")
p("| Opponent tier | games | W | L | T | winrate | mean margin |")
p("|---|--:|--:|--:|--:|--:|--:|")
for t in ("stronger", "weaker/equal", "unknown"):
    g = [r for r in recs if tier(r) == t]
    if not g:
        continue
    w = sum(x["result"] == "WIN" for x in g)
    l = sum(x["result"] == "LOSS" for x in g)
    ti = sum(x["result"] == "TIE" for x in g)
    mm = statistics.mean(x["margin"] for x in g)
    p(f"| {t} | {len(g)} | {w} | {l} | {ti} | {w/len(g):.0%} | {mm:+,.0f} |")

# all losses, sorted by opponent strength
p("\n## Losses (sorted by opponent strength)\n")
p("| ep | opponent | opp rank | opp score | margin | last-lead day |")
p("|---|---|--:|--:|--:|--:|")
for r in sorted(losses, key=lambda r: -(r["opp_score"] or 0)):
    ll = last_lead_day(r)
    ll_s = "never" if ll < 0 else f"d{ll+1}"
    p(f"| {r['ep']} | {r['opp'][:22]} | {r['opp_rank']} | "
      f"{r['opp_score'] if r['opp_score'] else '?'} | {r['margin']:+,} | {ll_s} |")

# where is the game lost? mean money gap by day, losses vs stronger opponents
days = [4, 9, 14, 19, 24, 29]
strong_losses = [r for r in losses if (r["opp_score"] or 0) > us_score]
pool = strong_losses if strong_losses else losses
p(f"\n## Where the game is lost — mean money gap (us − opp) by day\n")
p(f"_across {len(pool)} loss{'es' if len(pool)!=1 else ''} "
  f"vs {'stronger' if strong_losses else 'all'} opponents_\n")
p("| | day 5 | day 10 | day 15 | day 20 | day 25 | day 30 (final) |")
p("|---|--:|--:|--:|--:|--:|--:|")
cols = [[] for _ in days]
for r in pool:
    for i, v in enumerate(gap_by_day(r, days)):
        if v is not None:
            cols[i].append(v)
means = [statistics.mean(c) if c else None for c in cols]
p("| **mean gap** | " + " | ".join(f"{m:+,.0f}" if m is not None else "–" for m in means) + " |")
lead_share = []
for i in range(len(days)):
    if cols[i]:
        lead_share.append(sum(1 for v in cols[i] if v >= 0) / len(cols[i]))
    else:
        lead_share.append(None)
p("| **% of these games we lead** | " +
  " | ".join(f"{s:.0%}" if s is not None else "–" for s in lead_share) + " |")

nl = sum(1 for r in pool if last_lead_day(r) < 0)
led_then_lost = sum(1 for r in pool if last_lead_day(r) >= len(r["money_us"]) - 6)
p(f"\n- **Led at some point then lost late (last-lead in final ~5 days):** "
  f"{led_then_lost}/{len(pool)} → points leak in the **endgame / final sell-off**.")
p(f"- **Behind essentially wire-to-wire (never led):** {nl}/{len(pool)} → "
  f"a **build/opening** deficit, not market execution.")

# composition comparison in losses
p("\n## Final farm composition — us vs opponents (in losses)\n")
keys = set()
for r in pool:
    keys |= set(r["comp_us"]) | set(r["comp_opp"])
order = ["COW", "SHEEP", "GOOSE", "STRAWBERRY", "MELON", "TOMATO", "CARROT", "WHEAT",
         "PASTURE", "COOP", "WEED"]
order += sorted(k for k in keys if k not in order)
p("| tile | us (mean) | opp (mean) | Δ (opp−us) |")
p("|---|--:|--:|--:|")
for k in order:
    if k not in keys:
        continue
    us_m = statistics.mean(r["comp_us"].get(k, 0) for r in pool)
    op_m = statistics.mean(r["comp_opp"].get(k, 0) for r in pool)
    if us_m == 0 and op_m == 0:
        continue
    p(f"| {k} | {us_m:.1f} | {op_m:.1f} | {op_m-us_m:+.1f} |")

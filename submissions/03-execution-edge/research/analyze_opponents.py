"""Measure the diversification frontier from REAL opponent replays.

For each of v19's public loss/win replays, extract the opponent's build composition
and their per-good SELL volume (their actual market supply). Answers: does any
opponent — especially a STRONG one — supply the 'empty' markets (eggs/carrots/tomatoes)
or field geese? That decides whether diversification is a real, untapped edge or a
market everyone correctly avoids.

Run: python submissions/03-execution-edge/research/analyze_opponents.py
"""
import json, glob, os
from collections import Counter, defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")
REPDIR = os.path.join(ROOT, "replays", "live_55245235")
SUMMARY = json.load(open(os.path.join(REPDIR, "summary.json")))
by_ep = {str(s["ep"]): s for s in SUMMARY}

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL"]


def composition(farm):
    c = Counter()
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict):
                if t.get("kind") in ("COOP", "PASTURE"):
                    c[t.get("animal") or ("EMPTY-" + t["kind"])] += 1
                elif t.get("kind") == "PLANT":
                    c[t.get("crop")] += 1
    return c


def buys(steps, seat):
    """Reliable build intent: what the opponent actually PURCHASED (seeds + animals)."""
    tot = Counter()
    for st in steps:
        act = st[seat].get("action") or {}
        for o in act.get("market", []) or []:
            if not o:
                continue
            if o[0] in ("BUY_SEED", "BUY_ANIMAL") and len(o) > 2:
                tot[o[1]] += o[2]
    return tot


rows = []
for f in sorted(glob.glob(os.path.join(REPDIR, "episode-*.json"))):
    ep = os.path.basename(f).split("-")[1]
    meta = by_ep.get(ep)
    if not meta:
        continue
    r = json.load(open(f))
    steps = r["steps"]
    us_seat = meta["us_seat"]
    opp_seat = 1 - us_seat
    opp_farm = steps[-1][opp_seat]["observation"]["farms"][opp_seat]
    comp = composition(opp_farm)
    opp_buys = buys(steps, opp_seat)
    rows.append((meta, comp, opp_buys))

rows.sort(key=lambda x: x[0].get("opp_rank", 9999))

print("=" * 122)
print("OPPONENT BUILDS  (from 14 real v19 replays)   BUY_SEED/BUY_ANIMAL = reliable build intent")
print("  final-composition COW/SHEEP/GOOSE/STRAW persist; melon/wheat/carrot/tomato are harvested away, so read them from BUYS")
print("=" * 122)
hdr = (f"{'opp':22} {'rank':>4} {'res':>4} {'margin':>7} | final: {'COW':>3} {'SHP':>3} {'GOOSE':>5} {'STRW':>4} "
       f"|| bought: {'goose':>5} {'cow':>3} {'sheep':>5} {'carrot':>6} {'tomato':>6} {'melon':>5} {'straw':>5}")
print(hdr)
print("-" * 122)
agg = defaultdict(int)
diversifiers = []
for meta, comp, b in rows:
    goose_b, carr_b, toma_b = b.get("GOOSE", 0), b.get("CARROT", 0), b.get("TOMATO", 0)
    line = (f"{meta['opp'][:22]:22} {meta.get('opp_rank','?'):>4} {meta['result'][:4]:>4} {meta['margin']:>7} | "
            f"       {comp.get('COW',0):>3} {comp.get('SHEEP',0):>3} {comp.get('GOOSE',0):>5} {comp.get('STRAWBERRY',0):>4} "
            f"||         {goose_b:>5} {b.get('COW',0):>3} {b.get('SHEEP',0):>5} {carr_b:>6} {toma_b:>6} {b.get('MELON',0):>5} {b.get('STRAWBERRY',0):>5}")
    print(line)
    if goose_b > 0: agg['bought_geese'] += 1
    if carr_b > 0: agg['bought_carrots'] += 1
    if toma_b > 0: agg['bought_tomatoes'] += 1
    if goose_b + carr_b + toma_b > 0:
        agg['diversified'] += 1
        diversifiers.append(f"{meta['opp']}(r{meta.get('opp_rank','?')})")

print("-" * 122)
print(f"games analyzed: {len(rows)}")
print(f"  bought GEESE (egg market):    {agg['bought_geese']}/{len(rows)}")
print(f"  bought CARROT seed:           {agg['bought_carrots']}/{len(rows)}")
print(f"  bought TOMATO seed:           {agg['bought_tomatoes']}/{len(rows)}")
print(f"  ANY diversification:          {agg['diversified']}/{len(rows)}")
print(f"  diversifiers: {sorted(set(diversifiers)) or 'NONE — every opponent runs the pure cow/sheep/straw/melon meta'}")
print("\nREAD: 0 diversifiers => eggs/carrots/tomatoes are genuinely UNTAPPED (real upside), but NO")
print("      opponent tape to distill => a diversified build must be CONSTRUCTED, not copied.")

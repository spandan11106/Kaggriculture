"""
Ground-truth economic analysis of Kaggriculture, replicating the EXACT formulas
from env_ref/kaggriculture.py (engine as of 2026-08-03).

Everything here is derived directly from the engine source so numbers are faithful.
Run: python analysis/economics.py
"""
import math

# ---- constants copied verbatim from kaggriculture.py ----
CROPS = {
    "WHEAT":      {"seed": 10, "first_yield_day": 2, "max_yield_day": 4,  "interval": 0, "max_yield": 6, "ongoing": False, "base": 25},
    "CARROT":     {"seed": 20, "first_yield_day": 2, "max_yield_day": 3,  "interval": 0, "max_yield": 4, "ongoing": False, "base": 35},
    "TOMATO":     {"seed": 50, "first_yield_day": 8, "max_yield_day": 8,  "interval": 1, "max_yield": 4, "ongoing": True,  "base": 60},
    "STRAWBERRY": {"seed": 100,"first_yield_day": 10,"max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True,  "base": 120},
    "MELON":      {"seed": 80, "first_yield_day": 10,"max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False, "base": 250},
}
ANIMALS = {
    "GOOSE": {"cost": 300, "first_yield_day": 4, "interval": 1, "max_held": 4, "product": "EGG",  "base": 50},
    "COW":   {"cost": 400, "first_yield_day": 8, "interval": 2, "max_held": 6, "product": "MILK", "base": 160},
    "SHEEP": {"cost": 500, "first_yield_day": 6, "interval": 3, "max_held": 6, "product": "WOOL", "base": 200},
}
MARKET_I0 = 10000
PRICE_FLOOR = 1
MARKET_PARAMS = {
    "WHEAT":      {"base":  25, "T": 400, "below_func": "sqrt",   "below_target": 0.80, "above_func": "log",    "above_target": 0.20},
    "CARROT":     {"base":  35, "T": 450, "below_func": "log",    "below_target": 0.20, "above_func": "sqrt",   "above_target": 0.70},
    "TOMATO":     {"base":  60, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "sqrt",   "above_target": 0.60},
    "STRAWBERRY": {"base": 120, "T": 100, "below_func": "sqrt",   "below_target": 0.70, "above_func": "linear", "above_target": 1.60},
    "MELON":      {"base": 250, "T": 300, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.60},
    "EGG":        {"base":  50, "T": 332, "below_func": "linear", "below_target": 0.40, "above_func": "log",    "above_target": 0.20},
    "MILK":       {"base": 160, "T": 122, "below_func": "sqrt",   "below_target": 0.60, "above_func": "linear", "above_target": 1.60},
    "WOOL":       {"base": 200, "T": 105, "below_func": "log",    "below_target": 0.20, "above_func": "sq",     "above_target": 3.20},
    "FERTILIZER": {"base": 100, "T": 200, "below_func": "linear", "below_target": 0.40, "above_func": "linear", "above_target": 0.40},
}

def _shape(func, x):
    x = max(0.0, x)
    return {"linear": x, "sq": x*x, "sqrt": math.sqrt(x), "log": math.log(1+x), "log10": math.log10(1+x)}[func]

def price_at_inventory(item, inv):
    p = MARKET_PARAMS[item]; base=p["base"]; T=p["T"]
    if inv < MARKET_I0:
        amp = p["below_target"]*base/_shape(p["below_func"], T)
        price = base + amp*_shape(p["below_func"], MARKET_I0-inv)
    else:
        amp = p["above_target"]*base/_shape(p["above_func"], T)
        price = base - amp*_shape(p["above_func"], inv-MARKET_I0)
    return max(PRICE_FLOOR, int(round(price)))

def sell_curve(item, start_inv=MARKET_I0):
    """Revenue selling units one at a time from start_inv. Returns list of (units, cum_rev, marginal_price)."""
    inv = start_inv; cum = 0; out=[]
    for k in range(1, 6000):
        pr = price_at_inventory(item, inv)  # quoted at pre-sell inventory
        cum += pr
        out.append((k, cum, pr))
        if pr > PRICE_FLOOR:
            inv += 1
        # continue; at floor price stays 1 forever
        if pr == PRICE_FLOOR and k > 5:  # stop shortly after hitting floor for the summary
            # keep a little tail then break
            if all(o[2]==PRICE_FLOOR for o in out[-3:]):
                break
    return out

def milestones(item):
    c = sell_curve(item)
    def at(n):
        if n<=len(c):
            u,cum,pr = c[n-1]; return cum, pr, cum/n
        return None
    floor_k = next((u for (u,cum,pr) in c if pr==PRICE_FLOOR), None)
    return {
        "base": MARKET_PARAMS[item]["base"],
        "rev25": at(25), "rev50": at(50), "rev100": at(100),
        "units_to_floor": floor_k,
        "max_extractable": c[-1][1] if c else 0,
    }

def scarcity_price(item, units_drained):
    """Price after town drains `units_drained` below I0 (no player selling)."""
    return price_at_inventory(item, MARKET_I0 - units_drained)

# ---------- town demand over the season ----------
def town_demand_per_product():
    """Total units of each product the town removes over 720 turns (day 0..29)."""
    TPD=24; STEPS=720
    SHOPS = {
        "BAKERY":["EGG","WHEAT"], "PIZZA_SHOP":["MILK","TOMATO","WHEAT"],
        "BRUNCH_SPOT":["EGG","WHEAT","STRAWBERRY"], "YARN_STORE":["WOOL"],
        "ICE_CREAM_SHOP":["STRAWBERRY","MILK","WHEAT"], "PET_CAFE":["CARROT"],
        "SMOOTHIE_SHOP":["STRAWBERRY","MILK"], "FARMERS_MARKET":["WHEAT","CARROT","TOMATO","STRAWBERRY"],
    }
    TC = ["WHEAT","CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL"]
    # Expected total: shops unlock 1 every 3 days (day 3,6,..., up to 8 shops by day 24).
    # We compute EXPECTED demand assuming all 8 shops eventually unlock (their identity is random,
    # but by end all-but-two unlock on avg; here we give the full-unlock upper bound + town center).
    demand = {p:0 for p in TC+["WOOL","EGG","MILK"]}
    for p in list(MARKET_PARAMS): demand.setdefault(p,0)
    # town center: every 12 turns, mult by day schedule (1 until day10, 2 until day20, 4 after)
    for step in range(STEPS):
        day = step//TPD
        if step % 12 == 0:
            m = 4 if day>=20 else (2 if day>=10 else 1)
            for it in TC: demand[it]+=m
    # shops: each unlocked shop consumes every 4 turns; single-product shops 2x.
    # unlock schedule: at end of day d where (d+1)%3==0 -> day indices 2,5,8,11,14,17,20,23 (8 unlocks)
    unlock_days = [d for d in range(30) if (d+1)%3==0][:8]
    # assume shops unlock in a fixed set (all 8) at those days (order random; demand sum identical if all unlock)
    shop_names = list(SHOPS)
    for i,ud in enumerate(unlock_days):
        if i>=len(shop_names): break
        shop = shop_names[i]  # placeholder ordering; total across all-8 is order-independent
    # compute assuming a shop active from unlock day to end
    for i,ud in enumerate(unlock_days):
        if i>=len(shop_names): break
        shop=shop_names[i]; prods=SHOPS[shop]; mult = 2 if len(prods)==1 else 1
        active_steps = [s for s in range(STEPS) if s//TPD > ud and s%4==0]
        for it in prods: demand[it]+= mult*len(active_steps)
    return demand

if __name__ == "__main__":
    print("="*84)
    print("MARKET ABSORPTION — selling from equilibrium (I0=10000). How fast price crashes.")
    print("="*84)
    print(f"{'item':11} {'base':>4} {'sell25':>16} {'sell50':>16} {'sell100':>17} {'toFloor':>8}")
    for it in ["WHEAT","CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER"]:
        m=milestones(it)
        def fmt(x):
            return f"${x[0]:>6.0f}@${x[1]:>3.0f}(a{x[2]:>3.0f})" if x else "        -       "
        print(f"{it:11} {m['base']:>4} {fmt(m['rev25']):>16} {fmt(m['rev50']):>16} {fmt(m['rev100']):>17} {str(m['units_to_floor']):>8}")
    print("  legend: sellN = $cumRevenue @ $marginalPrice (avg $/unit).  toFloor = units until price hits $1")

    print("\n"+"="*84)
    print("SCARCITY UPSIDE — price if town has drained N units below I0 (sell into scarcity)")
    print("="*84)
    print(f"{'item':11} {'base':>5} {'-25':>6} {'-50':>6} {'-100':>6} {'-200':>6}")
    for it in ["WHEAT","CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER"]:
        print(f"{it:11} {MARKET_PARAMS[it]['base']:>5} {scarcity_price(it,25):>6} {scarcity_price(it,50):>6} {scarcity_price(it,100):>6} {scarcity_price(it,200):>6}")

    print("\n"+"="*84)
    print("TOWN DEMAND over full season (720 turns) — total units removed (upper bound, all 8 shops)")
    print("="*84)
    d = town_demand_per_product()
    for it in ["WHEAT","CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL"]:
        print(f"  {it:11} {d.get(it,0):>5} units  (~sustains price near/above base for this much of YOUR supply)")

    print("\n"+"="*84)
    print("PER-TILE GROSS POTENTIAL (season=30d) at BASE price, ignoring crash. Rough turnover model.")
    print("="*84)
    # one-time crops: cycle length ~ max_yield_day+1 (harvest at max_yield_day, replant same day)
    def onetime_units(c):
        cd=CROPS[c]
        ws=(cd["max_yield_day"]+1)//2
        water_units = cd["max_yield_day"]-ws+1
        base_yield = min(cd["max_yield"], 1+water_units)          # no fertilizer
        fert_yield = min(cd["max_yield"], 1+2*water_units)        # fertilized in-window
        cycle = cd["max_yield_day"]+1
        cycles = 30//cycle
        return base_yield, fert_yield, cycle, cycles
    print(f"{'crop':11} {'seed':>4} {'base$':>5} {'yield/cyc':>9} {'fert/cyc':>8} {'cycleDays':>9} {'cyc/season':>10} {'units/season(base)':>18}")
    for c in ["WHEAT","CARROT","MELON"]:
        by,fy,cyc,cycles = onetime_units(c)
        print(f"{c:11} {CROPS[c]['seed']:>4} {CROPS[c]['base']:>5} {by:>9} {fy:>8} {cyc:>9} {cycles:>10} {by*cycles:>18}")
    # ongoing crops: 4 productions total then decay+replant
    def ongoing_units(c):
        cd=CROPS[c]
        # productions on interval, 4 total. life ~ first_yield_day + interval*(max_yield-1) + 1
        life = cd["first_yield_day"] + cd["interval"]*(cd["max_yield"]-1) + 2
        cycles = max(1, 30//life)
        base_total = cd["max_yield"]*cycles            # 1/production
        fert_total = cd["max_yield"]*2*cycles          # 2/production
        return base_total, fert_total, life, cycles
    for c in ["TOMATO","STRAWBERRY"]:
        bt,ft,life,cycles = ongoing_units(c)
        print(f"{c:11} {CROPS[c]['seed']:>4} {CROPS[c]['base']:>5} {'4/life':>9} {'8/life':>8} {life:>9} {cycles:>10} {bt:>18}")

    print("\n  ANIMALS (per tile, whole season, with DAILY CARE where useful):")
    print(f"  {'animal':7} {'cost':>4} {'prod':>5} {'base$':>5} {'~units/season':>13}  notes")
    # goose interval1: care banks +2/nonprod day but prod every day so care pays +2 each prod if fed+cared prior...
    # Simplify: report base (no care) and note care multiplier.
    for a in ["GOOSE","COW","SHEEP"]:
        ad=ANIMALS[a]
        start=ad["first_yield_day"]; iv=ad["interval"]
        prods = len([d for d in range(start,30,iv)])
        base_units = prods*1
        print(f"  {a:7} {ad['cost']:>4} {ad['product']:>5} {ad['base']:>5} {base_units:>13}  interval={iv}, +free 1 fertilizer/day, CARE boosts yield")

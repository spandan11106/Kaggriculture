"""Decode c27's embedded _TRACE and summarize the leader's field + market schedule.
This is the open-loop behavior the inventory-aware policy must match-or-beat."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analysis"))
import main_c27 as m
import economics as E

TRACE = m._TRACE
TPD = 24
print("tape steps:", len(TRACE))
print("sample step 0:", TRACE[0])
print("sample step 200:", TRACE[200])

def all_units(step_dict):
    out = []
    out.append(step_dict.get("farmer") or ["PASS"])
    out.extend(step_dict.get("hands") or [])
    return out

# ---- field actions aggregate ----
field_counts = {}
place_animal = {}
build = {"BUILD_COOP":0, "BUILD_PASTURE":0}
plant = {}
for s in TRACE:
    for a in all_units(s):
        if not isinstance(a, list) or not a: continue
        op = a[0]
        field_counts[op] = field_counts.get(op,0)+1
        if op == "PLANT" and len(a)>=2: plant[a[1]] = plant.get(a[1],0)+1
        if op == "PLACE" and len(a)>=2: place_animal[a[1]] = place_animal.get(a[1],0)+1
        if op in build: build[op]+=1

# ---- market aggregate ----
sell_units = {}; sell_steps = {}
buy_seed = {}; buy_animal = {}; buy_product = {}
hire_by_day = {}; land_steps = []
sell_by_day = {}   # item -> {day: units}
for i, s in enumerate(TRACE):
    day = i // TPD
    for o in s.get("market") or []:
        if not isinstance(o, list) or not o: continue
        op = o[0]
        if op == "SELL" and len(o)>=3:
            it = o[1]; q = int(o[2] or 0)
            sell_units[it] = sell_units.get(it,0)+q
            sell_steps.setdefault(it, []).append(i)
            sell_by_day.setdefault(it,{}).setdefault(day,0)
            sell_by_day[it][day]+=q
        elif op == "BUY_SEED" and len(o)>=3: buy_seed[o[1]] = buy_seed.get(o[1],0)+int(o[2] or 0)
        elif op == "BUY_ANIMAL" and len(o)>=3: buy_animal[o[1]] = buy_animal.get(o[1],0)+int(o[2] or 0)
        elif op == "BUY_PRODUCT" and len(o)>=3: buy_product[o[1]] = buy_product.get(o[1],0)+int(o[2] or 0)
        elif op == "HIRE": hire_by_day[day] = hire_by_day.get(day,0)+1
        elif op == "BUY_LAND": land_steps.append(i)

print("\n=== FIELD ACTION COUNTS (farmer+hands over 720 steps) ===")
for k,v in sorted(field_counts.items(), key=lambda kv:-kv[1]): print(f"  {k:20} {v}")
print("PLANT by crop:", plant)
print("PLACE animal:", place_animal, " builds:", build)

print("\n=== CAPITAL / LOGISTICS ===")
print("BUY_SEED:", buy_seed)
print("BUY_ANIMAL:", buy_animal)
print("BUY_PRODUCT:", buy_product)
print("BUY_LAND at steps:", land_steps, "(days", [s//TPD for s in land_steps], ")")
print("HIRE per day:", dict(sorted(hire_by_day.items())))
print("total hires:", sum(hire_by_day.values()))

print("\n=== MARKET SELL TOTALS vs profitable absorption ceiling ===")
print(f"{'item':11} {'tape_sells':>10} {'floor_at':>9} {'first25 avg$':>12} {'verdict'}")
for it in ["MELON","STRAWBERRY","MILK","WOOL","EGG","TOMATO","CARROT","WHEAT","FERTILIZER"]:
    tot = sell_units.get(it,0)
    mil = E.milestones(it)
    floor = mil["units_to_floor"]
    a25 = mil["rev25"][2] if mil["rev25"] else 0
    verdict = ""
    if floor and tot > floor: verdict = f"OVER-sells past floor by {tot-floor}"
    elif floor and tot > 0.7*floor: verdict = "near ceiling"
    print(f"{it:11} {tot:>10} {str(floor):>9} {a25:>12.0f}  {verdict}")

print("\n=== PREMIUM SELL TIMING (units sold per day) ===")
for it in ["MELON","STRAWBERRY","MILK","WOOL"]:
    d = sell_by_day.get(it,{})
    if not d: continue
    days = sorted(d)
    print(f"  {it:11} sold on days {days[0]}-{days[-1]}, per-day: " +
          " ".join(f"d{dd}:{d[dd]}" for dd in days))

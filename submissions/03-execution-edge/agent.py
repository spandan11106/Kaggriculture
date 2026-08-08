# Submission 3 — clean-room reactive scheduler (from scratch).
# v2: animals (cows/sheep/geese) + crops (melon/strawberry) with land expansion.
# Reactive/stateless: every decision derives from the live observation (cannot desync).
# One unit per task (greedy nearest; carriers preferred for placement).
import math

BOARD = 10
SHED = [(4, 4), (5, 4), (4, 5), (5, 5)]
SHED_SET = set(SHED)
STRUCT = {"COW": "PASTURE", "SHEEP": "PASTURE", "GOOSE": "COOP"}
ANIM_SELL = ("MILK", "WOOL", "EGG")
CROP_SELL = ("MELON", "STRAWBERRY")
SELLABLE = ANIM_SELL + CROP_SELL
N_HANDS = 7
WHEAT_RESERVE = 20
MONEY_FLOOR = 400
TARGET = {"GOOSE": 3, "COW": 6, "SHEEP": 5}
COST = {"COW": 400, "SHEEP": 500, "GOOSE": 300}
N_MELON = 16
N_STRAW = 28
CROP_SEED = {"MELON": 80, "STRAWBERRY": 100}

def _dist(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])
def _quad(x, y): return ("N" if y < 5 else "S") + ("W" if x < 5 else "E")

# Layout: animals on 14 NW tiles nearest shed; crops on remaining NW/NE/SW tiles.
_NW = [(x, y) for y in range(5) for x in range(5) if (x, y) not in SHED_SET]
_NW.sort(key=lambda p: (_dist(p, (4, 4)), p[1], p[0]))
ANIMAL_TILES = {}
for _i, _p in enumerate(_NW[:14]):
    ANIMAL_TILES[_p] = "GOOSE" if _i < 3 else "COW" if _i < 9 else "SHEEP"

_CROP_CELLS = [(x, y) for y in range(BOARD) for x in range(BOARD)
               if _quad(x, y) in ("NW", "NE", "SW") and (x, y) not in SHED_SET and (x, y) not in ANIMAL_TILES]
_CROP_CELLS.sort(key=lambda p: (_dist(p, (4, 4)), p[1], p[0]))
CROP_TILES = {}
for _i, _p in enumerate(_CROP_CELLS[:N_MELON + N_STRAW]):
    CROP_TILES[_p] = "MELON" if _i < N_MELON else "STRAWBERRY"

# quadrant a tile lives in -> we only act on it once unlocked
def _needs_quad(pos): return _quad(pos[0], pos[1])


def _toward(pos, target):
    x, y = pos; tx, ty = target
    if tx > x and x + 1 < BOARD: return "EAST"
    if tx < x and x - 1 >= 0:    return "WEST"
    if ty > y and y + 1 < BOARD: return "SOUTH"
    if ty < y and y - 1 >= 0:    return "NORTH"
    return "PASS"

def _nearest_shed(pos): return min(SHED, key=lambda s: _dist(pos, s))


def agent(obs, config=None):
    try:
        return _act(obs)
    except Exception:
        farm = (obs.get("farms") or [{}])[int(obs.get("player", 0) or 0)]
        return {"farmer": ["PASS"], "hands": [["PASS"]] * len(farm.get("hands", []) or []), "market": []}


def _act(obs):
    me = int(obs.get("player", 0) or 0)
    farm = obs["farms"][me]
    tiles = farm["tiles"]
    day = int(obs.get("day", 0) or 0)
    hour = int(obs.get("hour", 0) or 0)
    unlocked = set(farm.get("unlocked_quadrants") or ["NW"])
    priv = obs.get("private", {}) or {}
    shed = dict(priv.get("shed", {}) or {})
    seeds = dict(priv.get("seeds", {}) or {})
    invs = priv.get("inventories", [{}]) or [{}]
    positions = [tuple(farm["farmer"])] + [tuple(h) for h in (farm.get("hands") or [])]
    n = len(positions)

    def inv_of(i): return invs[i] if i < len(invs) else {}
    def tile(p): return tiles[p[1]][p[0]]

    placed = {"COW": 0, "SHEEP": 0, "GOOSE": 0}
    tasks = []      # (priority, kind, pos, arg)
    # animals
    for pos, atype in ANIMAL_TILES.items():
        t = tile(pos)
        if isinstance(t, dict) and t.get("animal"):
            placed[t["animal"]] = placed.get(t["animal"], 0) + 1
            if not t.get("fed_today"):                tasks.append((0, "FEED", pos, None))
            if int(t.get("yield_units", 0) or 0) > 0:  tasks.append((2, "HARVEST", pos, None))
            if not t.get("cared_today"):              tasks.append((5, "CARE", pos, None))
        elif isinstance(t, dict) and t.get("kind") == STRUCT[atype]:
            tasks.append((3, "PLACE", pos, atype))
        elif t is None:
            tasks.append((4, "BUILD", pos, atype))
    # crops
    planted_crop = {"MELON": 0, "STRAWBERRY": 0}
    for pos, crop in CROP_TILES.items():
        if _needs_quad(pos) not in unlocked:
            continue
        t = tile(pos)
        if isinstance(t, dict) and t.get("kind") == "PLANT":
            planted_crop[t.get("crop", crop)] = planted_crop.get(t.get("crop", crop), 0) + 1
            age = day - int(t.get("planted_day", day))
            if not t.get("watered_today"):            tasks.append((1, "WATER", pos, None))
            yld = int(t.get("yield_units", 0) or 0)
            ripe = yld > 0 and (age >= 12 if crop == "MELON" else age >= 10)
            if ripe:                                   tasks.append((2, "HARVEST", pos, None))
        elif isinstance(t, dict) and t.get("kind") == "WEED":
            tasks.append((6, "DIG", pos, None))
        elif t is None and seeds.get(crop, 0) > 0 and day <= (16 if crop == "MELON" else 18):
            tasks.append((4, "PLANT", pos, crop))

    shed_anim = {a: int(shed.get(a, 0) or 0) for a in ("COW", "SHEEP", "GOOSE")}
    carrying = [next((a for a in ("COW", "SHEEP", "GOOSE") if int(inv_of(i).get(a, 0) or 0) > 0), None)
                for i in range(n)]
    has_wheat = [int(inv_of(i).get("WHEAT", 0) or 0) > 0 for i in range(n)]

    tasks.sort(key=lambda t: t[0])
    assign = [None] * n
    used = set()
    place_budget = dict(shed_anim)
    seed_budget = {c: int(seeds.get(c, 0) or 0) for c in CROP_SEED}
    for pr, kind, pos, arg in tasks:
        cand = [i for i in range(n) if i not in used]
        if not cand:
            break
        if kind == "PLACE":
            carriers = [i for i in cand if carrying[i] == arg]
            if carriers:
                i = min(carriers, key=lambda i: _dist(positions[i], pos))
            elif place_budget.get(arg, 0) > 0:
                i = min(cand, key=lambda i: _dist(positions[i], pos)); place_budget[arg] -= 1
            else:
                continue
        elif kind == "PLANT":
            if seed_budget.get(arg, 0) <= 0:
                continue
            i = min(cand, key=lambda i: _dist(positions[i], pos)); seed_budget[arg] -= 1
        elif kind == "FEED":
            wheaters = [i for i in cand if has_wheat[i]]
            i = min(wheaters or cand, key=lambda i: _dist(positions[i], pos))
        else:
            i = min(cand, key=lambda i: _dist(positions[i], pos))
        used.add(i)
        assign[i] = (kind, pos, arg)

    actions = []
    for i in range(n):
        pos = positions[i]; job = assign[i]
        if job is None:
            actions.append(["PASS"] if pos in SHED_SET else [_toward(pos, _nearest_shed(pos))]); continue
        kind, tpos, arg = job
        if kind == "FEED":
            if has_wheat[i]:
                actions.append(["FEED"] if pos == tpos else [_toward(pos, tpos)])
            elif pos in SHED_SET and int(shed.get("WHEAT", 0) or 0) > 0:
                actions.append(["PICKUP", "WHEAT", min(6, int(shed.get("WHEAT", 0) or 0))])
            else:
                actions.append([_toward(pos, _nearest_shed(pos))])
        elif kind == "PLACE":
            if carrying[i] == arg:
                actions.append(["PLACE", arg] if pos == tpos else [_toward(pos, tpos)])
            elif pos in SHED_SET and shed_anim.get(arg, 0) > 0:
                actions.append(["PICKUP", arg, 1]); shed_anim[arg] -= 1
            else:
                actions.append([_toward(pos, _nearest_shed(pos))])
        elif kind == "PLANT":
            actions.append(["PLANT", arg] if pos == tpos else [_toward(pos, tpos)])
        elif kind == "WATER":
            actions.append(["WATER"] if pos == tpos else [_toward(pos, tpos)])
        elif kind == "HARVEST":
            actions.append(["HARVEST"] if pos == tpos else [_toward(pos, tpos)])
        elif kind == "CARE":
            actions.append(["CARE"] if pos == tpos else [_toward(pos, tpos)])
        elif kind == "DIG":
            actions.append(["DIG"] if pos == tpos else [_toward(pos, tpos)])
        elif kind == "BUILD":
            actions.append((["BUILD_COOP"] if arg == "GOOSE" else ["BUILD_PASTURE"]) if pos == tpos else [_toward(pos, tpos)])
        else:
            actions.append(["PASS"])

    for i in range(n):
        if assign[i] is None and sum(int(inv_of(i).get(s, 0) or 0) for s in SELLABLE) > 0:
            actions[i] = ["DROP"] if positions[i] in SHED_SET else [_toward(positions[i], _nearest_shed(positions[i]))]

    # ---------------- market ----------------
    market = []
    n_hands_target = N_HANDS if day >= 6 else 5      # ramp hands once income flows
    if hour == 0:
        market += [["HIRE"]] * min(n_hands_target, 10)
    money = float(farm.get("money", 0) or 0)
    carried_tot = {a: sum(1 for i in range(n) if carrying[i] == a) for a in COST}
    have = {a: placed[a] + shed_anim.get(a, 0) + carried_tot[a] for a in COST}
    need_seed = {c: max(0, tgt - planted_crop.get(c, 0) - int(seeds.get(c, 0) or 0))
                 for c, tgt in (("MELON", N_MELON), ("STRAWBERRY", N_STRAW))}
    committed_animals = sum(have.values())          # placed + shed + carried (all need feeding)

    # 1) SELL everything (raises cash + clears shed)
    for s in SELLABLE:
        q = int(shed.get(s, 0) or 0)
        if q > 0 and len(market) < 10:
            market.append(["SELL", s, q])

    # 2) WHEAT FEED RESERVE — top priority: starving animals escape. Scale reserve to herd size.
    shed_wheat = int(shed.get("WHEAT", 0) or 0)
    reserve = max(WHEAT_RESERVE, 3 * committed_animals)
    if committed_animals > 0 and shed_wheat < reserve and money > 200 and len(market) < 10:
        market.append(["BUY_PRODUCT", "WHEAT", min(reserve - shed_wheat, 14)])

    CUSHION = 500 + 25 * committed_animals          # feed cushion (keep wheat affordable)
    # 3) ANIMALS are the income engine — ramp the herd first (geese -> cows -> sheep), one/turn.
    #    A little melon seed alongside (cheap, plants free in NW, huge ROI) but animals lead.
    for a in ("GOOSE", "COW", "SHEEP"):
        if have[a] < TARGET[a] and money - COST[a] >= CUSHION and len(market) < 10:
            market.append(["BUY_ANIMAL", a, 1]); money -= COST[a]
            break
    # a couple melon seeds early (cheap, NW-plantable, pays off day ~12)
    mb = 0
    while need_seed["MELON"] > mb and money - 80 >= CUSHION and len(market) < 10 and day <= 14 and mb < 2:
        market.append(["BUY_SEED", "MELON", 1]); money -= 80; mb += 1

    # 4) Once the herd income flows (money comfortably high), expand into crops + land.
    if money > 1200:
        if "NE" not in unlocked and day >= 3 and len(market) < 10:
            market.append(["BUY_LAND"]); money -= 1000
        elif "NE" in unlocked and "SW" not in unlocked and day >= 8 and len(market) < 10:
            market.append(["BUY_LAND"]); money -= 2000
        for crop, cst in (("STRAWBERRY", 100), ("MELON", 80)):
            sb = 0
            while need_seed[crop] > sb and money - cst >= 1000 and len(market) < 10 and day <= 18 and sb < 4:
                market.append(["BUY_SEED", crop, 1]); money -= cst; sb += 1

    return {"farmer": actions[0], "hands": actions[1:], "market": market[:10]}

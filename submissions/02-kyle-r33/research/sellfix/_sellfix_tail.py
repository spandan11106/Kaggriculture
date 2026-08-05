# ============================================================================
# v19_sellfix wrapper  (appended after a byte-copy of agent/main.py)
# Late-market MILK/WOOL sell-filter (Lever A) + opportunistic animal-placement
# robustness (Lever B). Captures the effective `agent` as `_base_agent` and
# wraps it. The wrapper NEVER raises: on any error it returns the untouched base
# action (protects the "0 non-DONE episodes" safety invariant). Flags at the
# bottom are overridden by scripts/build_sellfix.py to bake sell-only/place-only.
# Spec: docs/superpowers/specs/2026-08-05-v19-sellfix-design.md
# ============================================================================
import math as _sf_math

ENABLE_SELLFIX = True
ENABLE_PLACEFIX = True
THETA = 0.75          # marginal-price floor as a fraction of base
SHED_HI = 85          # shed+inventory occupancy that forces a flush (no cap)
FLUSH_DAY = 28        # from this day on, liquidate everything (no cap)

# --- inlined ground-truth price curve (from analysis/economics.py) ----------
_SF_I0 = 10000
_SF_PARAMS = {
    "MILK": {"base": 160, "T": 122, "bf": "sqrt", "bt": 0.60, "af": "linear", "at": 1.60},
    "WOOL": {"base": 200, "T": 105, "bf": "log",  "bt": 0.20, "af": "sq",     "at": 3.20},
}


def _sf_shape(f, x):
    x = x if x > 0 else 0.0
    if f == "linear": return x
    if f == "sq":     return x * x
    if f == "sqrt":   return _sf_math.sqrt(x)
    if f == "log":    return _sf_math.log(1 + x)
    return x


def _sf_price(item, inv):
    p = _SF_PARAMS[item]; base = p["base"]; T = p["T"]
    if inv < _SF_I0:
        amp = p["bt"] * base / _sf_shape(p["bf"], T)
        price = base + amp * _sf_shape(p["bf"], _SF_I0 - inv)
    else:
        amp = p["at"] * base / _sf_shape(p["af"], T)
        price = base - amp * _sf_shape(p["af"], inv - _SF_I0)
    return max(1, int(round(price)))


def _sf_cap(item, inv):
    """Max units to sell now while every unit's marginal price stays >= THETA*base."""
    thr = THETA * _SF_PARAMS[item]["base"]
    k = 0
    while k < 400 and _sf_price(item, inv + k) >= thr:
        k += 1
    return k


def _sf_occupancy(obs):
    """Non-seed shed + carried inventory count (the 100-cap universe)."""
    priv = obs.get("private") or {}
    tot = sum(v for v in (priv.get("shed") or {}).values() if isinstance(v, (int, float)))
    for inv in (priv.get("inventories") or []):
        tot += sum(v for v in (inv or {}).values() if isinstance(v, (int, float)))
    return tot


def _apply_sellfix(obs, action):
    if int(obs.get("day", 0) or 0) >= FLUSH_DAY:
        return                                   # end-game: liquidate, no cap
    if _sf_occupancy(obs) >= SHED_HI:
        return                                   # shed pressure: flush, no cap
    inv = (obs.get("market") or {}).get("inventory") or {}
    out = []
    for o in (action.get("market") or []):
        if (isinstance(o, (list, tuple)) and len(o) >= 3 and o[0] == "SELL"
                and o[1] in ("MILK", "WOOL")):
            cap = _sf_cap(o[1], int(inv.get(o[1], _SF_I0)))
            if cap <= 0:
                continue                         # hold entirely (rest stays in shed)
            if cap < o[2]:
                out.append([o[0], o[1], cap])    # partial; remainder held
                continue
        out.append(o)
    action["market"] = out


# --- Lever B: opportunistic placement of a stuck (bought-but-unplaced) animal --
_SF_PLACE_ANIMALS = ("SHEEP", "COW", "GOOSE")


def _sf_stuck_animal(obs):
    shed = (obs.get("private") or {}).get("shed") or {}
    for a in _SF_PLACE_ANIMALS:
        if shed.get(a, 0) > 0:
            return a
    return None


def _sf_tile(farm, x, y):
    tiles = farm.get("tiles") or []
    row = tiles[y] if 0 <= y < len(tiles) else None
    return row[x] if row and 0 <= x < len(row) else "LOCKED"


def _apply_placefix(obs, action):
    animal = _sf_stuck_animal(obs)
    if not animal or int(obs.get("day", 0) or 0) >= FLUSH_DAY:
        return
    farms = obs.get("farms") or []
    player = obs.get("player", 0)
    if player >= len(farms):
        return
    farm = farms[player]
    want_struct = "COOP" if animal == "GOOSE" else "PASTURE"
    build_op = ["BUILD_COOP"] if animal == "GOOSE" else ["BUILD_PASTURE"]
    invs = (obs.get("private") or {}).get("inventories") or []

    def redirect(op, pos, unit_inv):
        # only ever touch an idle (PASS) unit — never steal a productive turn
        if not op or op[0] != "PASS":
            return op
        x, y = pos
        tile = _sf_tile(farm, x, y)
        holding = (unit_inv or {}).get(animal, 0) > 0
        if isinstance(tile, dict) and tile.get("kind") == want_struct and not tile.get("animal") and holding:
            return ["PLACE", animal, 1]
        if tile is None:
            return build_op                       # build the missing structure here
        return op

    farm_pos = farm.get("farmer", [0, 0])
    action["farmer"] = redirect(action.get("farmer"), farm_pos, invs[0] if invs else {})
    hpos = farm.get("hands") or []
    new_hands = []
    for i, hop in enumerate(action.get("hands") or []):
        pos = hpos[i] if i < len(hpos) else [0, 0]
        uinv = invs[i + 1] if i + 1 < len(invs) else {}
        new_hands.append(redirect(hop, pos, uinv))
    action["hands"] = new_hands


def _sf_copy_action(a):
    if not isinstance(a, dict):
        return a
    return {
        "farmer": list(a.get("farmer") or ["PASS"]),
        "hands": [list(h) for h in (a.get("hands") or [])],
        "market": [list(o) for o in (a.get("market") or [])],
    }


_base_agent = agent   # capture the effective v19 entry point (last real `def agent`)


def _sf_agent(obs):
    a = _base_agent(obs)
    if not (ENABLE_SELLFIX or ENABLE_PLACEFIX):
        return a
    try:
        b = _sf_copy_action(a)
        if ENABLE_SELLFIX:
            _apply_sellfix(obs, b)
        if ENABLE_PLACEFIX:
            _apply_placefix(obs, b)
        return b
    except Exception:
        return a          # never regress to a crash; return untouched base action


# CRITICAL: the Kaggle loader (kaggle_environments.agent.get_last_callable) picks
# the LAST callable *inserted into the module namespace* — not by name. Because
# `_base_agent = agent` above inserts a callable after the original `agent`, the
# wrapper must be the last NEWLY-defined callable. `_sf_agent` (defined just above)
# is that callable. Do NOT define or assign any callable below this line.
# (main.py uses the same trick: it ends with `_kaggle_submission_entrypoint`.)
agent = _sf_agent

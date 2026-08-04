"""Generate agent/controller_base.py from main_c27.py: the proven c27 tape/clone/terminal
logic PLUS a CONFIG-driven market layer (reactive sells, fertilizer-sell toggle, cow cap).

CONFIG defaults reproduce c27 exactly, so `controller_base.py` with default config must tie c27.
Variants are built by scripts/build_variant.py (swaps the CONFIG block).
"""
import os, re

ROOT = os.path.join(os.path.dirname(__file__), "..")
src = open(os.path.join(ROOT, "agent", "main_c27.py")).read()

# Keep everything up to (but not including) the original `def agent(`.
head, _sep, _tail = src.partition("\ndef agent(")
assert _sep, "could not find def agent( in main_c27.py"

EXT = r'''

# >>>CONFIG  (build_variant.py swaps this block; defaults == pure c27)
CONFIG = {
    "market_mode": "tape",       # "tape" | "reactive"
    "sell_fertilizer": True,      # tape mode: keep FERTILIZER sells
    "max_cows": None,             # cap cumulative BUY_ANIMAL COW (None = uncapped)
    "reactive_alpha": {},         # reactive mode: per-item reservation = alpha*base (0 => sell all)
    "shed_pressure": 85,          # reactive: if shed>=this, sell everything (avoid overflow)
    "endgame_step": 680,          # reactive: sell everything from here
    "wheat_reserve_per_animal": 3, # reactive: keep this much wheat/animal in shed for FEED
}
# <<<CONFIG

# Compact market model (base, T, below_func, below_target, above_func, above_target)
_MP = {
    "WHEAT": (25,400,"sqrt",0.80,"log",0.20), "CARROT": (35,450,"log",0.20,"sqrt",0.70),
    "TOMATO": (60,200,"linear",0.40,"sqrt",0.60), "STRAWBERRY": (120,100,"sqrt",0.70,"linear",1.60),
    "MELON": (250,300,"log",0.20,"sq",3.60), "EGG": (50,332,"linear",0.40,"log",0.20),
    "MILK": (160,122,"sqrt",0.60,"linear",1.60), "WOOL": (200,105,"log",0.20,"sq",3.20),
    "FERTILIZER": (100,200,"linear",0.40,"linear",0.40),
}
import math as _math
def _shape(f, x):
    x = max(0.0, x)
    if f == "linear": return x
    if f == "sq": return x*x
    if f == "sqrt": return _math.sqrt(x)
    if f == "log": return _math.log(1.0+x)
    return x
def _price(item, inv):
    b,T,bf,bt,af,at = _MP[item]
    if inv < 10000:
        return max(1, int(round(b + (bt*b/_shape(bf,T))*_shape(bf, 10000-inv))))
    return max(1, int(round(b - (at*b/_shape(af,T))*_shape(af, inv-10000))))

# Sell priority (highest realized value first) for the <=10 order budget.
_SELL_PRIORITY = ("STRAWBERRY","MELON","WOOL","MILK","WHEAT","EGG","TOMATO","CARROT","FERTILIZER")
_COWS_BOUGHT = 0

def _count_animals(obs):
    farms = obs.get("farms") or []
    pid = int(obs.get("player", 0) or 0)
    if pid >= len(farms):
        return 0
    n = 0
    for row in farms[pid].get("tiles") or []:
        for t in row or []:
            if isinstance(t, dict) and "animal" in t and t.get("animal"):
                n += 1
    return n

def _reactive_sells(obs, step, skip_items):
    shed = (obs.get("private") or {}).get("shed") or {}
    inv = ((obs.get("market") or {}).get("inventory") or {})
    shed_total = sum(max(0, int(v or 0)) for v in shed.values())
    endgame = step >= CONFIG["endgame_step"]
    pressure = shed_total >= CONFIG["shed_pressure"]
    wheat_reserve = _count_animals(obs) * CONFIG.get("wheat_reserve_per_animal", 3)
    orders = []
    for item in _SELL_PRIORITY:
        if item in skip_items:
            continue
        have = int(shed.get(item, 0) or 0)
        # Keep wheat reserved for FEED unless it's the very end of the game.
        if item == "WHEAT" and not endgame:
            have = max(0, have - wheat_reserve)
        if have <= 0:
            continue
        if item == "FERTILIZER" and not CONFIG["sell_fertilizer"]:
            continue
        alpha = CONFIG["reactive_alpha"].get(item, 0.0)
        if endgame or pressure or alpha <= 0:
            qty = have
        else:
            base = _MP[item][0]; thresh = alpha * base
            m = int(inv.get(item, 10000) or 10000); qty = 0
            while qty < have and _price(item, m + qty) >= thresh:
                qty += 1
        if qty > 0:
            orders.append(["SELL", item, qty])
    return orders

def _apply_market_config(action, obs, step):
    global _COWS_BOUGHT
    orders = list(action.get("market", []) or [])
    if CONFIG["max_cows"] is not None:
        kept = []
        for o in orders:
            if isinstance(o, list) and len(o) >= 2 and o[0] == "BUY_ANIMAL" and o[1] == "COW":
                n = int(o[2]) if len(o) >= 3 else 1
                room = max(0, CONFIG["max_cows"] - _COWS_BOUGHT)
                take = min(n, room); _COWS_BOUGHT += take
                if take > 0:
                    kept.append(["BUY_ANIMAL", "COW", take])
            else:
                kept.append(o)
        orders = kept
    if CONFIG["market_mode"] == "reactive":
        nonsell = [o for o in orders if not (isinstance(o, list) and o and o[0] == "SELL")]
        orders = nonsell + _reactive_sells(obs, step, skip_items=set())
    elif not CONFIG["sell_fertilizer"]:
        orders = [o for o in orders
                  if not (isinstance(o, list) and len(o) >= 2 and o[0] == "SELL" and o[1] == "FERTILIZER")]
    action["market"] = orders[:10]


def agent(obs, config=None):
    global _LAST_STEP, _CLONE_CONFIDENCE, _COWS_BOUGHT
    step = min(int(obs.get("step", 0) or 0), len(_TRACE) - 1)
    if step == 0 or step <= _LAST_STEP:
        _CLONE_CONFIDENCE = 0
        _COWS_BOUGHT = 0
    _LAST_STEP = step
    _update_clone_profile(obs, step)
    if step >= 717:
        return _terminal_action(obs)
    action = copy.deepcopy(_TRACE[step])
    _apply_market_config(action, obs, step)
    _front_run(action, obs, step)
    _terminal_liquidation(action, obs, step)
    return action
'''

out = head + EXT
open(os.path.join(ROOT, "agent", "controller_base.py"), "w").write(out)
print("wrote agent/controller_base.py:", out.count(chr(10)) + 1, "lines")

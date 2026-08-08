"""Diversified procedural agent: v19 scheduler + N geese on free UNLOCKED tiles.
Overrides _build_animal_plan (add geese) AND _animal_site_active (accept goose tiles).
Usage: python build_diversified_proc.py [N]  -> writes _dvproc.py"""
import sys, os
N = int(sys.argv[1]) if len(sys.argv) > 1 else 4
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "..", "..", "01-v19", "main.py")).read()
a = 'tasks.append(_task(5, pos, ["BUILD_PASTURE"], None, "build"))'
b = 'tasks.append(_task(5, pos, (["BUILD_COOP"] if animal == "GOOSE" else ["BUILD_PASTURE"]), None, "build"))'
assert src.count(a) == 1; src = src.replace(a, b)
c = 'elif isinstance(tile, dict) and tile.get("kind") == "PASTURE" and "animal" not in tile:'
d = 'elif isinstance(tile, dict) and tile.get("kind") == ("COOP" if animal == "GOOSE" else "PASTURE") and "animal" not in tile:'
assert src.count(c) >= 1; src = src.replace(c, d, 1)
e = 'for animal in ("COW", "SHEEP"):'
f = 'for animal in ("COW", "SHEEP", "GOOSE"):'
assert src.count(e) >= 1, "buy-loop anchor"; src = src.replace(e, f)
tail = '''

_N_GEESE = %d
_GEESE_TILES = set()
def _quad(x, y): return ("N" if y < 5 else "S") + ("W" if x < 5 else "E")
_orig_build_animal_plan = _build_animal_plan
def _build_animal_plan(cows, sheep):
    plan = _orig_build_animal_plan(cows, sheep)
    used = set(plan)
    cands = [(x, y) for y in range(10) for x in range(10)
             if _quad(x, y) in ("NE", "SW") and (x, y) not in used]
    cands.sort(key=lambda p: abs(p[0] - 4.5) + abs(p[1] - 4.5))
    _GEESE_TILES.clear()
    for pos in cands[:_N_GEESE]:
        plan[pos] = "GOOSE"; _GEESE_TILES.add(pos)
    return plan
_orig_site_active = _animal_site_active
def _animal_site_active(pos, day, unlocked):
    if pos in _GEESE_TILES:
        q = _quad(pos[0], pos[1])
        if q == "NW": return day >= 4
        if q == "NE": return day >= 8 and "NE" in unlocked
        if q == "SW": return day >= 12 and "SW" in unlocked
        return False
    return _orig_site_active(pos, day, unlocked)
configure_strategy({"use_fixed_schedule": False})

def _dvproc_entry(obs):
    try: return _V19_PREVIOUS_AGENT(obs)
    except Exception: return {"farmer": ["PASS"], "hands": [], "market": []}
''' % N
open(os.path.join(HERE, "_dvproc.py"), "w").write(src + tail)
print(f"wrote _dvproc.py N={N}")

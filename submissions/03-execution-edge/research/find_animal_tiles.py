"""Instrument the engine to record, for seat 0 (kyle), every BUILD_PASTURE / BUILD_COOP /
PLACE action with its (step, actor_idx, tile). This maps kyle's animal tiles back to the
exact tape actions, so build_diversified.py can convert N cow-tiles -> goose-coops in place.

Run: python submissions/03-execution-edge/research/find_animal_tiles.py
Writes: research/animal_tiles.json
"""
import os, sys, json, contextlib, io, warnings
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
KYLE = os.path.join(HERE, "..", "..", "02-kyle-r33", "main.py")

with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture as K

events = []            # (seat, step, idx, op, item, pos)
farm2seat = {}
cur = {"step": 0}
_orig_apply = K._apply_unit_action


def _apply(farm, private, idx, action, *a, **k):
    if isinstance(action, list) and action and action[0] in ("BUILD_PASTURE", "BUILD_COOP", "PLACE", "PICKUP"):
        pos = tuple(K._farmer_position(farm, idx))
        seat = farm2seat.get(id(farm), -1)
        item = action[1] if len(action) > 1 else None
        events.append((seat, cur["step"], idx, action[0], item, pos))
    return _orig_apply(farm, private, idx, action, *a, **k)


K._apply_unit_action = _apply

with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 0}, debug=False)
    _orig_interp = env.interpreter        # patch the INSTANCE (run() calls this), not the module ref

    def _interp(state, e):
        obs0 = state[0].observation
        day = int(getattr(obs0, "day", 0) or 0)
        hour = int(getattr(obs0, "hour", 0) or 0)
        cur["step"] = day * 24 + hour
        for i, f in enumerate(obs0.farms):
            farm2seat[id(f)] = i
        return _orig_interp(state, e)

    env.interpreter = _interp
    env.run([os.path.abspath(KYLE), os.path.abspath(KYLE)])

s0 = [e for e in events if e[0] == 0]
builds = {}   # pos -> (step, idx, kind)
places = {}   # pos -> list of (step, idx, item)
pickups = []  # (step, idx, item)
for seat, step, idx, op, item, pos in s0:
    if op in ("BUILD_PASTURE", "BUILD_COOP"):
        builds.setdefault(pos, (step, idx, op))       # first build on the tile
    elif op == "PLACE" and item in ("COW", "SHEEP", "GOOSE"):
        places.setdefault(pos, []).append((step, idx, item))
    elif op == "PICKUP" and item in ("COW", "SHEEP", "GOOSE"):
        pickups.append((step, idx, item))


def _match_pickup(place_step, place_idx, animal):
    """The PICKUP that loaded this animal: same actor idx, same day, latest step <= place."""
    day = place_step // 24
    cands = [(s, i, it) for (s, i, it) in pickups
             if i == place_idx and it == animal and s // 24 == day and s <= place_step]
    if not cands:
        return None
    s, i, it = max(cands, key=lambda c: c[0])
    return {"step": s, "idx": i}


# A tile is an animal tile if something was placed on it; match to its build + pickup.
tiles = []
for pos, plist in places.items():
    step, idx, item = plist[0]                          # first (successful) placement
    b = builds.get(pos)
    tiles.append({"pos": list(pos), "animal": item,
                  "place": {"step": step, "idx": idx},
                  "pickup": _match_pickup(step, idx, item),
                  "build": {"step": b[0], "idx": b[1], "kind": b[2]} if b else None})

cows = [t for t in tiles if t["animal"] == "COW"]
sheep = [t for t in tiles if t["animal"] == "SHEEP"]
print(f"seat-0 animal tiles: {len(tiles)}  (COW {len(cows)}, SHEEP {len(sheep)})")
print("\nCOW tiles (pos | build step/idx | place step/idx):")
for t in sorted(cows, key=lambda t: t["place"]["step"]):
    b = t["build"]
    print(f"  {str(t['pos']):8} build={b['kind']}@s{b['step']}/i{b['idx']} "
          f"place=PLACE COW @s{t['place']['step']}/i{t['place']['idx']}")

out = os.path.join(HERE, "animal_tiles.json")
json.dump({"cows": cows, "sheep": sheep}, open(out, "w"), indent=1)
print(f"\nwrote {out}")

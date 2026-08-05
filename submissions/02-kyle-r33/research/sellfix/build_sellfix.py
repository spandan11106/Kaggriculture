"""Build the v19_sellfix variants: byte-copy of agent/main.py + the wrapper tail,
with the two lever flags baked in for clean attribution.

  v19_sellfix.py   -> both levers
  v19_sellonly.py  -> Lever A (milk/wool sell-filter) only
  v19_placeonly.py -> Lever B (placement robustness) only

Re-run after editing agent/main.py or variants/_sellfix_tail.py.
Usage: python scripts/build_sellfix.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = open(os.path.join(HERE, "..", "..", "..", "01-v19", "main.py")).read()  # the v19 agent this wraps
TAIL = open(os.path.join(HERE, "_sellfix_tail.py")).read()

CONFIGS = [
    ("v19_sellfix",   True,  True),
    ("v19_sellonly",  True,  False),
    ("v19_placeonly", False, True),
]

for name, sell, place in CONFIGS:
    body = BASE + "\n" + TAIL + f"\nENABLE_SELLFIX = {sell}\nENABLE_PLACEFIX = {place}\n"
    path = os.path.join(HERE, name + ".py")
    open(path, "w").write(body)
    print(f"wrote variants/{name}.py  (sellfix={sell}, placefix={place}, {len(body):,} B)")

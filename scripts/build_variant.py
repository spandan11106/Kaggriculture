"""Build self-contained agent variants by swapping the CONFIG block in controller_base.py."""
import os, re

ROOT = os.path.join(os.path.dirname(__file__), "..")
BASE = os.path.join(ROOT, "agent", "controller_base.py")
OUTDIR = os.path.join(ROOT, "variants")
MARK = re.compile(r"# >>>CONFIG.*?# <<<CONFIG", re.S)


def _default_config(base_src):
    m = MARK.search(base_src)
    body = "\n".join(l for l in m.group(0).splitlines() if not l.lstrip().startswith("#"))
    ns = {}
    exec(body, ns)
    return ns["CONFIG"]


def build(name, overrides):
    base_src = open(BASE).read()
    cfg = dict(_default_config(base_src))
    cfg.update(overrides)
    block = "# >>>CONFIG\nCONFIG = " + repr(cfg) + "\n# <<<CONFIG"
    out = MARK.sub(lambda _m: block, base_src, count=1)
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, name + ".py")
    open(path, "w").write(out)
    return path


VARIANTS = {
    "c28_refactor":    {},                                   # must tie c27 (neutrality check)
    "c28_react":       {"market_mode": "reactive"},
    "c28_react_hold":  {"market_mode": "reactive",
                        "reactive_alpha": {"FERTILIZER": 0.6, "MILK": 0.55, "WOOL": 0.5}},
    "c28_6cow":        {"max_cows": 6},
    "c28_7cow":        {"max_cows": 7},
    "c28_nofertsell":  {"sell_fertilizer": False},
}

if __name__ == "__main__":
    for name, ov in VARIANTS.items():
        p = build(name, ov)
        print("built", os.path.relpath(p, ROOT))

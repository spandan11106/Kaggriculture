"""Instrument the real engine to log every EXECUTED sell (player,item,price) and
quantify how much revenue the open-loop tape leaves on the table per good.

Runs in-process (monkeypatches the engine module), so games are serial.
"""
import argparse, os, sys, warnings, contextlib, io
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analysis"))
import economics as E

with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture as K

BASE = {k: E.MARKET_PARAMS[k]["base"] for k in E.MARKET_PARAMS}

_LOG = []            # list of (player, item, price)
_FARM2PLAYER = {}

_orig_pm = K._process_market
_orig_cu = K._commit_unit

def _pm(state, env):
    farms = state[0].observation.farms
    for pid, f in enumerate(farms):
        _FARM2PLAYER[id(f)] = pid
    return _orig_pm(state, env)

def _cu(op, item, price, farm, private, market):
    ok = _orig_cu(op, item, price, farm, private, market)
    if ok and op == "SELL":
        _LOG.append((_FARM2PLAYER.get(id(farm), -1), item, price))
    return ok

K._process_market = _pm
K._commit_unit = _cu


def run_game(path_a, path_b, seed):
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
        env.run([os.path.abspath(path_a) if os.path.isfile(path_a) else path_a,
                 os.path.abspath(path_b) if os.path.isfile(path_b) else path_b])
    final = env.steps[-1]
    return float(final[0].reward), float(final[1].reward)


def analyze(path_a, path_b, seeds, focus_player=0):
    global _LOG, _FARM2PLAYER
    per_item = {}   # item -> list of prices (for focus_player)
    rewards = []
    for s in seeds:
        _LOG = []; _FARM2PLAYER = {}
        r0, r1 = run_game(path_a, path_b, s)
        rewards.append((r0, r1))
        for (pid, item, price) in _LOG:
            if pid == focus_player:
                per_item.setdefault(item, []).append(price)
    return per_item, rewards


def report(per_item, rewards, label):
    print(f"\n===== MARKET DIAGNOSTIC: {label}  ({len(rewards)} games) =====")
    print(f"mean reward: P0={sum(r[0] for r in rewards)/len(rewards):,.0f}  "
          f"P1={sum(r[1] for r in rewards)/len(rewards):,.0f}")
    print(f"{'item':11} {'units':>6} {'revenue':>10} {'avg$':>6} {'base':>5} "
          f"{'%dumped(<$5)':>12} {'%low(<50%base)':>15} {'@base_rev':>10} {'capture%':>8}")
    order = ["MELON","STRAWBERRY","MILK","WOOL","EGG","TOMATO","CARROT","WHEAT","FERTILIZER"]
    grand_cap, grand_base = 0, 0
    for it in order:
        prices = per_item.get(it, [])
        if not prices:
            continue
        n = len(prices); rev = sum(prices); avg = rev/n
        base = BASE[it]
        dumped = sum(1 for p in prices if p < 5)/n*100
        low = sum(1 for p in prices if p < 0.5*base)/n*100
        base_rev = n*base
        cap = rev/base_rev*100 if base_rev else 0
        grand_cap += rev; grand_base += base_rev
        print(f"{it:11} {n:>6} {rev:>10,.0f} {avg:>6.0f} {base:>5} {dumped:>11.0f}% "
              f"{low:>14.0f}% {base_rev:>10,.0f} {cap:>7.0f}%")
    print(f"{'TOTAL':11} {'':>6} {grand_cap:>10,.0f} {'':>6} {'':>5} {'':>12} {'':>15} "
          f"{grand_base:>10,.0f} {grand_cap/grand_base*100 if grand_base else 0:>7.0f}%")
    print("  avg$ = mean realized sell price;  @base_rev = units x base;  capture% = revenue / @base_rev")
    print("  high %dumped on premiums = revenue lost to gluts = the market-policy opportunity")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("agent_a", nargs="?", default="agent/main.py")
    ap.add_argument("agent_b", nargs="?", default="agent/main.py")
    ap.add_argument("--seeds", type=int, default=6)
    args = ap.parse_args()
    seeds = list(range(args.seeds))
    per_item, rewards = analyze(args.agent_a, args.agent_b, seeds, focus_player=0)
    report(per_item, rewards, f"P0={os.path.basename(args.agent_a)} vs {os.path.basename(args.agent_b)}")

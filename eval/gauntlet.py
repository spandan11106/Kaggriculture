"""Paired-seat H2H evaluation for Kaggriculture agents.

Agents are loaded as ISOLATED file-path agents (each in its own namespace) so that
module-global state (e.g. c27's _CLONE_CONFIDENCE) can't leak between the two seats
or across games — this also matches how Kaggle actually runs each main.py.

Usage:
  python eval/gauntlet.py A.py B.py --seeds 20            # A vs B, both seats
  python eval/gauntlet.py A.py --vs starter random pass   # A vs each baseline
"""
import argparse
import os
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor

warnings.filterwarnings("ignore")
os.environ.setdefault("PYTHONWARNINGS", "ignore")

EPISODE_STEPS = 720


def _play(args):
    """Run one game: returns (reward0, reward1, status0, status1). Runs in a subprocess."""
    path_a, path_b, seed = args
    # Silence the noisy env import in each worker.
    import contextlib, io
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        from kaggle_environments import make
        env = make("kaggriculture",
                   configuration={"episodeSteps": EPISODE_STEPS, "seed": int(seed)},
                   debug=False)
        env.run([path_a, path_b])
    final = env.steps[-1]
    return (float(final[0].reward), float(final[1].reward),
            str(final[0].status), str(final[1].status))


def _resolve(agent):
    """Abspath a file agent; pass through builtin names ('starter','random','pass')."""
    return os.path.abspath(agent) if os.path.isfile(agent) else agent


def h2h(path_a, path_b, seeds, both_seats=True, workers=None):
    """A vs B over `seeds`; if both_seats, also play with seats swapped. Returns (rows, summary)."""
    path_a = _resolve(path_a)
    path_b = _resolve(path_b)
    jobs = []            # (a_path, b_path, seed, a_is_A, seat)
    for seed in seeds:
        jobs.append((path_a, path_b, seed, True, 0))
        if both_seats:
            jobs.append((path_b, path_a, seed, False, 1))
    workers = workers or min(len(jobs), max(1, (os.cpu_count() or 2) - 1))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(_play, [(j[0], j[1], j[2]) for j in jobs]))

    rows = []
    errors = 0
    for (a_path, b_path, seed, a_is_A, seat), (r0, r1, s0, s1) in zip(jobs, results):
        # Map engine seat rewards back to A / B.
        a_reward, b_reward = (r0, r1) if a_is_A else (r1, r0)
        a_status, b_status = (s0, s1) if a_is_A else (s1, s0)
        if a_status != "DONE" or b_status != "DONE":
            errors += 1
        margin = a_reward - b_reward
        rows.append({"seed": seed, "seat_of_A": seat, "A": a_reward, "B": b_reward,
                     "margin": margin, "A_win": margin > 0, "tie": margin == 0,
                     "A_status": a_status, "B_status": b_status})
    n = len(rows)
    wins = sum(r["A_win"] for r in rows)
    ties = sum(r["tie"] for r in rows)
    losses = n - wins - ties
    margins = [r["margin"] for r in rows]
    mean_margin = sum(margins) / n if n else 0.0
    # sample std of margin
    if n > 1:
        mu = mean_margin
        var = sum((m - mu) ** 2 for m in margins) / (n - 1)
        std = var ** 0.5
    else:
        std = 0.0
    summary = {"games": n, "A_wins": wins, "losses": losses, "ties": ties,
               "A_winrate": round(wins / n, 4) if n else 0.0,
               "mean_margin": round(mean_margin, 1), "margin_std": round(std, 1),
               "errors": errors}
    return rows, summary


def _fmt(name_a, name_b, summary):
    return (f"{name_a} vs {name_b}: {summary['A_wins']}-{summary['losses']}-{summary['ties']} "
            f"(wr {summary['A_winrate']:.2f}) margin {summary['mean_margin']:+.0f}±{summary['margin_std']:.0f} "
            f"errors={summary['errors']} n={summary['games']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent_a")
    ap.add_argument("agent_b", nargs="?", default=None)
    ap.add_argument("--vs", nargs="*", default=None,
                    help="baseline names/paths to play A against (e.g. starter random pass)")
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--one-seat", action="store_true")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()

    seeds = list(range(args.seed0, args.seed0 + args.seeds))
    both = not args.one_seat
    name_a = os.path.basename(args.agent_a)

    opponents = []
    if args.agent_b:
        opponents.append(args.agent_b)
    if args.vs:
        opponents.extend(args.vs)
    if not opponents:
        opponents = ["starter"]

    for opp in opponents:
        rows, summary = h2h(args.agent_a, opp, seeds, both_seats=both, workers=args.workers)
        print(_fmt(name_a, os.path.basename(opp), summary))


if __name__ == "__main__":
    main()

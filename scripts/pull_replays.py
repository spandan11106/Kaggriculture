"""Pull a submission's episode replays, classify W/L, and extract compact traces.

For each episode of a submission:
  - download the replay JSON (via the kaggle CLI) if not already cached,
  - identify our seat from info.TeamNames, read final rewards -> W/L/margin,
  - join the opponent to the public leaderboard (rank/score),
  - extract a per-day money curve for both seats + final farm composition,
  - PRUNE the ~28 MB replay unless it's a LOSS (keep losses for deep analysis).

Compact per-episode traces are written to summary.json (small); a committable
digest is written to analysis/loss_report_<sub>.md by scripts/loss_report.py.

Usage:
  python scripts/pull_replays.py 55245235 "Spandan Mhapsekar"
Resumable: episodes already in summary.json are skipped (no re-download).
"""
import csv, glob, json, os, subprocess, sys

SUB = sys.argv[1] if len(sys.argv) > 1 else "55245235"
US = sys.argv[2] if len(sys.argv) > 2 else "Spandan Mhapsekar"
DIR = f"replays/live_{SUB}"
EP_CSV = f"{DIR}/episodes.csv"
SUMMARY = f"{DIR}/summary.json"
TPD = 24


def load_leaderboard():
    files = sorted(glob.glob(f"{DIR}/leaderboard.csv") + glob.glob("/tmp/kaggriculture-publicleaderboard-*.csv"))
    lb = {}
    if files:
        for r in csv.DictReader(open(files[-1], encoding="utf-8-sig")):
            lb[r["TeamName"]] = (int(r["Rank"]), float(r["Score"]))
    return lb


def farm_composition(farm):
    counts = {}
    for row in farm.get("tiles", []) or []:
        for t in row or []:
            if not isinstance(t, dict):
                continue
            kind = t.get("kind")
            if kind == "PLANT":
                counts[t.get("crop", "PLANT")] = counts.get(t.get("crop", "PLANT"), 0) + 1
            elif kind in ("COOP", "PASTURE"):
                a = t.get("animal")
                key = a if a else kind
                counts[key] = counts.get(key, 0) + 1
            elif kind == "WEED":
                counts["WEED"] = counts.get("WEED", 0) + 1
    return counts


def money_curve(steps, seat):
    out = []
    ndays = (len(steps) + TPD - 1) // TPD
    for d in range(ndays):
        idx = min((d + 1) * TPD - 1, len(steps) - 1)
        try:
            out.append(round(steps[idx][0]["observation"]["farms"][seat]["money"]))
        except Exception:
            out.append(None)
    return out


def process(eid, lb, cache):
    if eid in cache:
        return cache[eid]
    path = f"{DIR}/episode-{eid}-replay.json"
    if not os.path.exists(path):
        subprocess.run(["kaggle", "competitions", "replay", str(eid), "-p", DIR],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(path):
        return {"ep": eid, "error": "download_failed"}
    j = json.load(open(path))
    teams = j.get("info", {}).get("TeamNames", ["?", "?"])
    rewards = [float(x) if x is not None else 0.0 for x in j.get("rewards", [0, 0])]
    statuses = j.get("statuses", ["?", "?"])
    seat = teams.index(US) if US in teams else 1
    opp_seat = 1 - seat
    opp = teams[opp_seat]
    margin = rewards[seat] - rewards[opp_seat]
    result = "WIN" if margin > 0 else ("TIE" if margin == 0 else "LOSS")
    rank, score = lb.get(opp, (None, None))
    steps = j.get("steps", [])
    last = steps[-1] if steps else []
    try:
        final_farms = last[0]["observation"]["farms"]
        comp_us = farm_composition(final_farms[seat])
        comp_opp = farm_composition(final_farms[opp_seat])
    except Exception:
        comp_us, comp_opp = {}, {}
    rec = {
        "ep": eid, "opp": opp, "opp_rank": rank, "opp_score": score,
        "us_seat": seat, "us": round(rewards[seat]), "opp_reward": round(rewards[opp_seat]),
        "margin": round(margin), "result": result,
        "us_status": statuses[seat], "opp_status": statuses[opp_seat],
        "money_us": money_curve(steps, seat), "money_opp": money_curve(steps, opp_seat),
        "comp_us": comp_us, "comp_opp": comp_opp,
    }
    # keep only LOSS replays; delete wins/ties to bound disk
    if result != "LOSS":
        try:
            os.remove(path)
        except OSError:
            pass
    return rec


def main():
    lb = load_leaderboard()
    ids = [row["id"] for row in csv.DictReader(open(EP_CSV))]
    cache = {}
    if os.path.exists(SUMMARY):
        for r in json.load(open(SUMMARY)):
            cache[r["ep"]] = r
    out = []
    for i, eid in enumerate(ids):
        rec = process(eid, lb, cache)
        out.append(rec)
        json.dump(out, open(SUMMARY, "w"), indent=2)  # incremental save
        if "error" in rec:
            print(f"[{i+1}/{len(ids)}] {eid} ERROR {rec['error']}", flush=True)
        else:
            s = f"{rec['opp_score']:.0f}" if rec["opp_score"] else "  ?"
            print(f"[{i+1}/{len(ids)}] {eid} {rec['result']:4} m={rec['margin']:+8d} "
                  f"vs {rec['opp'][:24]:24} (rank {str(rec['opp_rank']):>4}, {s})", flush=True)
    n = len(out)
    w = sum(r.get("result") == "WIN" for r in out)
    l = sum(r.get("result") == "LOSS" for r in out)
    t = sum(r.get("result") == "TIE" for r in out)
    print(f"\nDONE: {w}W-{l}L-{t}T of {n}  (kept {l} loss replays)")


if __name__ == "__main__":
    main()

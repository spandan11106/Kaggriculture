# Kaggriculture — Work Log

_Session date: 2026-08-04. Goal: win the Kaggriculture competition (top-10 each win $5,000; final leaderboard = Bradley-Terry over Oct 1–15 games on each team's latest-2 submissions, locked Sep 30)._

---

## TL;DR / current state

- **v19 is SUBMITTED and LIVE** on the leaderboard (submission `55245235`, status COMPLETE). Rating settled at **2563.2 → rank 70 / 1590 (top 4.4%)** by 2026-08-05 — up from the 679→955 day-one provisional readings; games play cleanly (no error episodes). Before this session the account had **zero** submissions — the biggest single action taken. **Gap to the money: the top-10 prize cutoff is ~2835, so v19 is ~270 pts / ~60 ranks short.** See "Live status" below.
- **v19 is the real baseline** (not c27): a 5,598-line procedural + 4-medoid-ensemble + clone-gated closed-loop controller. Extracted & SHA-verified to `agent/main_v19.py`. Beats c27 **10-2**.
- Built a **fast, correct evaluation harness** (isolated file-path agents) + a **market diagnostic** + a **replay→tape distiller** (validated to reproduce a recorded game exactly).
- **Key finding:** naive market/allocation tweaks all LOSE to the tuned baseline — the agents are tightly-coupled systems. This matches the v19 notebook's own ablation: **route-refresh (distillation) is the dominant lever (+10 wins); market/closed-loop wrappers add ~+1.**

---

## Live status — 2026-08-05 (day-2 check)

Pulled `kaggle competitions submissions / leaderboard / episodes`:

| Metric | Value |
|---|---|
| v19 public score | **2563.2** (day-1 readings were 679 → 955, very provisional) |
| Rank | **70 / 1590** teams — top **4.4%** (team "Spandan Mhapsekar") |
| Live stability | episodes all `COMPLETED`, **no error states** — agent is stable at scale |
| LB shape | top 3092.3 ("somewhere after"); median 681; min 112 |
| **Top-10 prize cutoff** | **~2835** (10th place). v19 is **~270 pts / ~60 ranks short of the money.** |

**Read:** v19 is a legitimate top-5% agent that plays cleanly live, but it is **not yet in prize territory**. The ~270-pt gap reframes the roadmap — route-refresh distillation and the fertilizer→strawberry edge aren't just "beat the mirror" academics; they're the concrete levers to close a *measured* gap to the top-10. The field is still early (most submissions dated Aug 4–5) and the payout ranking is the Oct 1–15 Bradley-Terry window, so there's runway — but the leaders already sit at ~2900–3100.

---

## Quick start for agents

```bash
# activate the engine env (Python 3.11)
source /opt/miniconda3/etc/profile.d/conda.sh && conda activate kaggri

# A/B two agents (paired-seat, both seats, N seeds). winrate>0.50 => first agent wins.
python eval/gauntlet.py agent/main_v19.py agent/main_c27.py --seeds 20
python eval/gauntlet.py agent/main_v19.py --vs starter random --seeds 8

# per-good realized sell-price diagnostic (in-process, instruments the engine)
python eval/market_diagnostic.py agent/main_v19.py agent/main_v19.py --seeds 6

# replay JSON -> faithful open-loop tape opponent (distillation primitive)
python scripts/replay_to_tape.py <replay.json> <player 0|1> variants/<name>.py

# check live submission score / leaderboard
kaggle competitions submissions kaggriculture
kaggle competitions leaderboard kaggriculture --show
```

**Ground rules that cost real wins if ignored** (learned this session):
- Load agents as **isolated file paths** in eval — v19/c27 use module globals; sharing a process corrupts self-play.
- **Never** naively rewrite an agent's market orders: wheat is animal FEED, and the shed cap is 100 (overflow discarded). Both are load-bearing.
- When distilling from a replay, the action at env-step `i` is `steps[i+1].action` (post-action observations). `replay_to_tape.py` already handles this.
- Promotion = beat the current baseline (**v19**) from **both seats** over many seeds — a high bank vs `starter` proves nothing.

## Environment & access

- Real engine needs **Python ≥3.11**; created conda env **`kaggri`** (Py 3.11) with `kaggle-environments==1.32.3` + `kaggle` CLI + numpy/pandas/scipy/cma. (`ml` is Py 3.9 — used only for pure-Python analysis.)
  - Activate: `source /opt/miniconda3/etc/profile.d/conda.sh; conda activate kaggri`
- **Kaggle API working**: token at `~/.kaggle/access_token`; `userHasEntered: True`.
- Authoritative engine source vendored at `env_ref/kaggriculture.py` (+ json/README/AGENTS), pulled from GitHub master (last changed 2026-08-03).

---

## Repository layout

| Path | What |
|---|---|
| `env_ref/` | Vendored engine source + docs (authoritative mechanics) |
| `analysis/economics.py` | Ground-truth market absorption curves, per-tile ROI, town demand |
| `agent/main_v19.py` | **Current best baseline** (SHA `9f18c729…`, 393,699 B) |
| `agent/main.py` | = v19 (canonical current agent) |
| `agent/main_c27.py` | Old benchmark tape agent |
| `agent/controller_base.py` | CONFIG-driven c27 (for A/B experiments); `scripts/gen_controller.py` builds it |
| `eval/gauntlet.py` | Paired-seat H2H, isolated file-path agents, parallel |
| `eval/market_diagnostic.py` | Instruments engine to log realized sell prices |
| `scripts/replay_to_tape.py` | Replay JSON → faithful open-loop tape agent (distillation primitive) |
| `scripts/analyze_tape.py` | Decodes a tape's field/market schedule |
| `scripts/build_variant.py` | Builds `variants/*.py` from CONFIG presets |
| `submission/` | `main.py` (=v19) + `submission.tar.gz` (what was uploaded) |
| `replays/local_v19.json` | Local v19-vs-v19 replay (format reference) |

---

## What was learned about the game (from engine + real games)

- **Town demand dominates the market.** It continuously drains the demanded goods, keeping them *scarce* — so open-loop "sell everything" already captures ~106% of base. In a v19 mirror game (per player, per game): **strawberry sells at $181** (base 120), **wheat $46** (base 25), melon $212, milk $138, wool $171. Strawberry (~$48.5k/game) and wheat (~$39k/game) are the biggest earners — **not** melon.
- Two **hard constraints** the top agents carefully manage: **wheat is a feed input** (14 animals × ~1/day); the **100-item shed must be kept clear** (overflow is discarded).
- The converged meta: **8 cows + 6 sheep, no geese**, NE+SW quadrants, 12 hands/day, ~21 melon + ~44 strawberry seeds. Empty markets nobody supplies: **eggs, carrots, tomatoes** (town demands them).

---

## Experiments run (all A/B'd against a baseline on the gauntlet)

**c28 market/allocation tweaks vs c27** (20 seeds, both seats) — **ALL LOST:**

| Variant | Result | Why |
|---|---|---|
| Reactive market (fixed wheat reserve) | 0-40, −15.6k | Tape's batched timing beats greedy reactive selling |
| Reactive market (buggy) | 0-40, −77k | Sold wheat reserved for feed → animals starved |
| Trim to 6 / 7 cows | −7k / −3k | 8 cows is correct; trimming loses milk+fertilizer |
| Stop selling fertilizer | 0-40, **−163k** | Fertilizer clogs the shed → everything else discarded |

**Conclusion:** mirror-match gains are **not** in market execution or naive allocation. This independently reproduces the v19 notebook's ablation (route refresh +10 wins; closed-loop wrapper +1).

---

## v19 discovery & submission

- Found + decoded the **v19 notebook** (`41-49-future-unseen…ipynb`, dated today). v19 uses a **train/holdout split**, 4 **train-only medoid experts**, Himanshu's route for both seats, a disabled state-distance gate, and a **clone-gated closed-loop late-market controller** (`collision_score = (1+opp_exposure)·glut·max(1,price)·log1p(qty)`).
- Its **mirror match is the failure cluster** (1/4 vs the source it clones) — the real open problem.
- Validated v19: self-play 6-6-0 / +0 / 0 errors (passes Kaggle validation); vs starter/random 8-0.
- **Submitted** `submission.tar.gz` → ref `55245235`, COMPLETE. Rating settled at **2563.2 → rank 70/1590 (top 4.4%)** by 2026-08-05 (see "Live status"); ~270 pts short of the top-10 cutoff.

---

## Distillation pipeline — primitive built

- `scripts/replay_to_tape.py`: converts a Kaggle replay JSON into a faithful open-loop **tape opponent** (the unit both route-refresh distillation and the fresh-snapshot gate need).
- **Gotcha solved:** kaggle-environments stores **post-action observations**, so the action at env-step `i` is `steps[i+1].action` (a +1 shift). Verified: the rebuilt tape reproduces a recorded game **exactly** (`[110419, 110038]`).

---

## Strategic conclusions

1. **Route refresh (distillation) is the dominant lever** — confirmed twice (my null experiments + v19's ablation). The pipeline to pull fresh top-team replays → medoids → gate vs v19 is the highest-EV work.
2. **The mirror is the ceiling.** Beating a cloned source requires a genuine edge the source lacks — the one production thesis with real numbers is fertilizer→FERTILIZE strawberries (~$181 vs $58), which must *consume* fertilizer to avoid shed clog.
3. **Portfolio diversity matters** for the final 2 slots — pick a decorrelated slot-B to hedge the "meta-shift kills both" knockout.
4. Being **on the ladder early** banks rating certainty into the Oct 1–15 final window.

---

## Next steps (priority order)

1. **Route-refresh pipeline** — need the external `download_top_replays.py` (fetches *other teams'* submission IDs/replays via the Kaggle sim-episodes API with score-matching). Either paste it, or I rebuild via the `ListEpisodes` endpoint. Then: pull current top-N → per-author train-only medoid → gate vs v19 (both seats, fresh chronological snapshot).
2. **Robustness eval + slot-B** — build a diverse opponent set (distilled real leaders + baselines + a market-dumper), find where v19 loses, design a decorrelated 2nd submission.
3. **Fertilizer→strawberry** production edge (needs a re-distilled base or procedural layer) — the one quantified way to beat the mirror.
4. **Monitor `55245235`** — now rank 70/1590 (2563.2), ~270 pts below the top-10 line; pull loss replays vs the ~2900+ leaders to find where those ~270 pts leak.

_Blocker for #1: the "download other teams' replays" script (external, not in repo)._

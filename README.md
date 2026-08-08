# Kaggriculture — Work Log

_Session dates: 2026-08-04 → 08. Goal: win the Kaggriculture competition (top-10 each win $5,000; final leaderboard = Bradley-Terry over Oct 1–15 games on each team's latest-2 submissions, locked Sep 30)._

---

## TL;DR / current state

- **NEW (2026-08-08): `V14` clone-preemption SHIPPED → submission `55348049` (scoring).** The current best agent by far: a **Kakuteki-frontier tape** (competitor submission `55334137`, action-level reproduction) **+ a live overlay** — clone-preemption *front-running*, price-impact/demand market-order ranking, weed repair, terminal liquidation. Local (paired both seats, 0 errors): **beats v19 16-0 (+10.7k) and kyle 16-0 (+11.2k), sweeps the distilled panel 12-0** (mengfei/kenmatsu/ali), robust at `townCenterSellInterval=24`. **Active latest-2 pair is now V14 + kyle_r33** (v19 rolls off). Agent + provenance notebook + full investigation in `submissions/03-execution-edge/`. This validated the session's thesis: **the win = distill the *current frontier* + FRONT-RUN (aggression), not restraint.**
- **(2026-08-05): `kyle_r33` distilled tape SHIPPED** → submission `55260946` (PENDING). Beats the v19 baseline **0.88 (35-5, +4687/game, 40 games, 0 errors)** and is robust vs a 5-opponent panel. Its build is **byte-identical to v19's** — it's the *same* meta executed ~5% better. Distillation is now the empirically-confirmed dominant lever (see "Distillation win"). v19 preserved at `submissions/01-v19/main.py`; resubmit if kyle underperforms live.
- **v19 is SUBMITTED and LIVE** on the leaderboard (submission `55245235`, status COMPLETE). Rating settled at **2563.2 → rank 70 / 1590 (top 4.4%)** by 2026-08-05 — up from the 679→955 day-one provisional readings; games play cleanly (no error episodes). Before this session the account had **zero** submissions — the biggest single action taken. **Gap to the money: the top-10 prize cutoff is ~2835, so v19 is ~270 pts / ~60 ranks short.** See "Live status" below.
- **v19 is the real baseline** (not c27): a 5,598-line procedural + 4-medoid-ensemble + clone-gated closed-loop controller. Extracted & SHA-verified to `submissions/01-v19/main.py`. Beats c27 **10-2**.
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

**Read:** v19 is a legitimate top-5% agent that plays cleanly live, but it is **not yet in prize territory**. The ~270-pt gap turns the roadmap from "beat the mirror" academics into a *measured* deficit to close — see **Loss forensics** below for where it actually leaks. The field is still early (most submissions dated Aug 4–5) and the payout ranking is the Oct 1–15 Bradley-Terry window, so there's runway — but the leaders already sit at ~2900–3100.

---

## Distillation win — kyle_r33 tape shipped (2026-08-05)

After the sell-fix dead end (see below), fanned out parallel research agents. Two findings reframed the problem, then a distillation sweep produced a shippable win.

**Research findings:**
1. **v19's build is a FROZEN, position-locked action tape** (`_V19_RUNTIME["experts"]["himanshu_kumar"]["actions"]`) — NOT reconfigurable. `STRATEGY`/`configure_strategy` feed only dead, shadowed pre-v19 code (proven: overriding `cows/sheep` leaves the built farm at 8/6 and the reward byte-identical). Naive tape edits desync and collapse the reward (sheep→goose swap → 24k). **Only a coherent new tape changes the build → distillation is the only build lever.**
2. **Economics (theoretical):** the meta over-invests in milk — under 2-player supply the 5th cow onward is net-negative; **eggs/geese are a wide-open market nobody supplies** (~$1.2–1.4k/tile). A diversified mix models +$34k/game self-play — but needs a novel *coherent* tape (not shippable same-day), so parked as future work.
3. **The milk/wool sell leak is STRUCTURAL** — both clones flood milk/wool faster than the town drains → permanent glut → marginal unit ~$1. A θ-threshold sell-hold filter (Lever A) did **not** recover it (capture flat, verified). The edge isn't sell-side; it's whole-game execution baked into the tape.

**The distillation sweep (the win):** distilled the strongest top-30 opponents from the saved loss replays into open-loop tapes (`scripts/replay_to_tape.py`) and A/B'd vs v19 (`eval/gauntlet.py`, both seats):

| distilled tape | vs v19 | robustness (vs panel) |
|---|---|---|
| **kyle_r33** | **35-5 (0.88), +4687** | beats mengfei .85, kenmatsu .90, ali .85, starter/random 1.00; **0 errors** |
| mengfei_r32 | 17-3 (0.85), +5182 | strong, but loses to kyle (.15) |
| kenmatsu4_r28 | 2-22 (0.08) | FRAGILE — open-loop desync off its recording seed |
| ali_r43 | 3-21 (0.12) | FRAGILE |

**Key insight:** kyle_r33's build is **byte-identical to v19's** (8 cow / 6 sheep / 14 pasture / 21 melon / 44 straw / 65 wheat). So kyle isn't a different strategy — it's **~5% better EXECUTION of the same meta** (watering/care/harvest/sell timing across the 720 steps). This is the back-half execution leak; it lives in the tape, which is why no wrapper could fix it but distilling a better executor does.

**SHIPPED:** `submissions/02-kyle-r33/main.py` = kyle_r33 tape → submission **55260946**. Validated: self-play 0 errors (Kaggle-valid), beats v19 0.88 / 40 games, robust vs the 5-opp panel. Should rank near kyle (r33, ~2698) = **top-35**. Caveat: open-loop *deterministic clone* — can't adapt. Natural next refinement: a **hybrid** = kyle's execution tape wrapped in v19's adaptive market controller.

**Loader gotcha (fixed, load-bearing):** `kaggle_environments.agent.get_last_callable` returns the LAST callable *inserted into the module namespace*, not the one named `agent`. A wrapper appended to main.py is silently ignored if any later line inserts another callable (e.g. `_base_agent = agent`). The entry must be the last newly-defined callable — see `variants/_sellfix_tail.py`.

---

## Loss forensics — where the ~270 pts leak (2026-08-05)

Pulled all 55 public replays of `55245235` (`scripts/pull_replays.py`), classified W/L, joined each opponent's leaderboard rank, and traced **ground-truth money curves** + final composition (`scripts/loss_report.py` → `submissions/02-kyle-r33/research/loss-report.md`). Loss replays kept under `replays/live_55245235/` (gitignored).

**Record: 40W–14L (74%)** — but it splits hard by opponent strength:

| Opponent tier | games | W–L | winrate | mean margin |
|---|--:|---|--:|--:|
| **stronger than v19** | 13 | **5–8** | **38%** | −91 (coin-flip; all losses close, −244…−6.5k) |
| weaker/equal | 41 | 35–6 | 85% | +38.8k (inflated by blowouts + 4 opponent crashes at +117k…+139k) |

**The leak is back-half execution on an IDENTICAL build — not the opening, not allocation:**
- v19 and the opponent are **dollar-for-dollar identical through ~day 10–12** (the converged 8-cow/5-sheep/6-straw opening is a solved near-mirror; final compositions match to ±0.1 tile on average).
- From **day 13 on, v19 bleeds value every day**, worst on the **final sell days (d22–29)**. By day 15 v19 trails in **100%** of the 8 strong-opponent losses (mean gap: d10 −57 → d15 −1.1k → d25 −3.4k → final −3.2k).
- **No catastrophic bug:** 0 non-DONE episodes; animal counts are monotonic (nobody starves). Losses are *efficiency*, not failure.

**Mechanism — premium-good sell execution.** In the Kyle loss both seats dump near-identical late quantities (v19/Kyle: milk 159/171, straw 148/165, wool 134/134), but the realized-value gap concentrates in **milk, strawberry, wool** — exactly the premiums with `above_target>1` that crash to the $1 floor on gluts (final-day strawberry sank 149→108 intraday as inventory was dumped). Wheat/melon are ~even. _Caveat: qty×price-at-order overstates the absolute gap (both crash their own price mid-order) — this is direction, not magnitude; the money curve is the reliable size._

**This revises the earlier thesis.** "Market execution doesn't matter; route-refresh is the only lever" was concluded from **self-play mirrors**, where both agents dump identically so the gap is invisible. Against real top-30 opponents, **back-half premium sell timing/spreading is precisely where the ~270 pts leak** — now a first-class, testable lever: A/B a smarter late-market policy on the gauntlet against a **distilled real-opponent tape** (`replay_to_tape.py`), *not* self-play (which is blind to it).

**Two upset losses flagged for turn-by-turn forensics:** Chakrabhuana (r189) **−13,485** and Md. Hamid (r279) **−5,519** — same back-half bleed, amplified; in Chakrabhuana v19 also fielded **one fewer sheep (13 vs 14 animals)** → less back-half wool. The Chakrabhuana replay is the single biggest anomaly to dissect next.

---

## Quick start for agents

```bash
# activate the engine env (Python 3.11)
source /opt/miniconda3/etc/profile.d/conda.sh && conda activate kaggri

# A/B two agents (paired-seat, both seats, N seeds). winrate>0.50 => first agent wins.
python eval/gauntlet.py submissions/02-kyle-r33/main.py submissions/01-v19/main.py --seeds 20
python eval/gauntlet.py submissions/01-v19/main.py --vs starter random --seeds 8

# per-good realized sell-price diagnostic (in-process, instruments the engine)
python eval/market_diagnostic.py submissions/01-v19/main.py submissions/01-v19/main.py --seeds 6

# replay JSON -> faithful open-loop tape opponent (distillation primitive)
python scripts/replay_to_tape.py <replay.json> <player 0|1> <out.py>

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
**Organized by submission** — each `submissions/NN-name/` is self-contained (its exact agent + all research for it); shared infra lives at the repo root.

| Path | What |
|---|---|
| `submissions/01-v19/` | **Submission 1** — v19 (`55245235`): `main.py` + `research/` (c27/c28 ablation framework, notebooks, tapes) |
| `submissions/02-kyle-r33/` | **Submission 2** — kyle_r33 distilled tape (`55260946`): `main.py` + `research/` (loss forensics, distilled tapes, sell-fix dead-end, design spec) |
| `submissions/03-execution-edge/` | **Submission 3** — **V14 clone-preemption** (`55348049`, current best): `main.py` (V14) + provenance notebook + `RESULTS.md` (full investigation, Parts 1–7) + `agent.py` (from-scratch clean-room agent, dead-end) + `research/` (prior-art report, pipelines) |
| `env_ref/` | *Shared:* vendored engine source + docs (authoritative mechanics) |
| `eval/gauntlet.py` | *Shared:* paired-seat H2H, isolated file-path agents, parallel |
| `eval/market_diagnostic.py` | *Shared:* instruments the engine to log realized sell prices |
| `analysis/economics.py` | *Shared:* ground-truth market curves, per-tile ROI, town demand |
| `scripts/replay_to_tape.py` | *Shared:* replay JSON → open-loop tape agent (distillation primitive) |
| `scripts/pull_replays.py` | *Shared:* download + classify a submission's episode replays (W/L, opponent rank, money curves) |
| `scripts/loss_report.py` | *Shared:* turn `pull_replays` output into a loss-forensics digest |
| `scripts/analyze_tape.py` | *Shared:* decode a tape's field/market schedule |
| `replays/` | Downloaded replays + local references (gitignored; regenerable) |

Each submission folder has its own `README.md` (id, what/why, results, research index).

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

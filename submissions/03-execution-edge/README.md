# Submission 3 — V14 "Clone Preemption" (frontier tape + front-running)

- **Kaggle submission:** `55348049` (2026-08-08) · status PENDING → scoring. Active latest-2 pair is now **V14 (`55348049`) + kyle_r33 (`55260946`)**; v19 (`55245235`) rolls off.


- **Agent (`main.py`):** V14 — decoded from the pasted notebook `84-84-base-public-holdout-v14-clone-preemption.ipynb`. A frontier-grade agent = a **719-turn tape reconstructed from Kakuteki's top public submission (`55334137`)** (reproduced at the action level, 2876/2876 audit per the notebook) **plus a live overlay**: clone-preemption front-running, market-order ranking by price-impact/demand, actor-local weed repair, and terminal liquidation.
- **Why it wins:** it combines the two things every hand-built approach this session lacked — the **current-frontier build/execution** (Kakuteki, stronger than kyle r33) **and the front-running structure the game-theory research validated** (`_preempt_shift`: move ahead of the opponent's large premium SELL on the next turn; params `_PREEMPT_FRACTION=2.0`, window steps 120–680, `_PREMIUM = STRAWBERRY/MELON/MILK/WOOL`).

## Results (my harness, kaggle-environments 1.32.3, paired-seat both seats)

| Opponent | Result | Margin |
|---|---|---|
| **kyle_r33** (Submission 2) | **16-0-0 (1.00)** | +11,160 |
| **v19** (Submission 1) | **16-0-0 (1.00)** | +10,698 |
| mengfei_r32 (distilled) | 12-0-0 | +11,602 |
| kenmatsu4_r28 (distilled) | 12-0-0 | +15,528 |
| ali_r43 (distilled) | 12-0-0 | +11,193 |
| starter / random | 8-0-0 | +188k |
| self-play | 0-0 tie, **0 errors** (Kaggle-valid) | — |
| kyle @ `townCenterSellInterval=24` | **12-0-0** | +10,112 |

**100% win rate vs the entire repo + distilled real-opponent panel, 0 errors, robust across engine (1.32.3) and config (interval 12 & 24).** Decisively supersedes v19 + kyle.

## Provenance / caveats
- V14 is a **distilled reconstruction of a competitor's (Kakuteki) public submission** + a novel preemption overlay — the same distillation approach the repo already ships (`kyle_r33` = distilled Kyle). Sourced from the pasted notebook.
- Targets `kaggle-environments==1.32.6`; validated clean on the local `1.32.3` (tape did not desync; still wins). Re-verify on the live engine before/after submitting.
- The notebook's own eval used `townCenterSellInterval=24`; confirmed V14 still wins there.

## Recommendation
**Ship V14 as the primary submission.** It dominates the current portfolio (v19 + kyle) 16-0. For the 2-slot portfolio, V14 is slot-A; a decorrelated slot-B (e.g. a preemption-off V14 variant, or kyle as a hedge) guards against a meta-shift — but V14 is the clear lead agent.

## Folder contents
| Path | What |
|---|---|
| `main.py` | **shipped agent — V14** (decoded from the notebook) |
| `84-...-v14-clone-preemption.ipynb` | the source notebook (provenance, audits, eval protocol) |
| `research/v14_main.py` | decoded V14 source (readable copy) |
| `agent.py` | the from-scratch clean-room scheduler (documented dead-end; ~5× below V14) |
| `RESULTS.md` | full investigation log (Parts 1–7) |
| `research/` | pipelines + prior-art report from the investigation |

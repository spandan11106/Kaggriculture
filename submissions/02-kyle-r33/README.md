# Submission 2 — kyle_r33 (distilled)

- **Kaggle submission:** `55260946` (2026-08-05) · status PENDING → scoring
- **Agent (`main.py`):** an open-loop distilled tape of competitor **Kyle (rank 33, ~2698)**, extracted from a live loss replay via `scripts/replay_to_tape.py`. Kyle's build is **byte-identical to v19's** (8 cow / 6 sheep / 14 pasture / 21 melon / 44 straw / 65 wheat) — so this is the **same meta executed ~5% better** (watering / care / harvest / sell timing across the 720 steps).
- **Result vs v19 baseline:** **35-5 (0.88 winrate), +4,687/game** over 40 games, both seats, **0 errors**. Robust vs a 5-opponent panel (beats mengfei .85, kenmatsu .90, ali .85, starter/random 1.00). Self-plays clean (Kaggle-valid). Should rank near Kyle (~**top-35**).

## Why (the research trail)
Forensics on Submission 1's losses (`research/loss-report.md`) showed the leak is **back-half execution on an identical build**, concentrated in milk/wool — but that leak is **structural** (both clones flood milk/wool faster than the town drains → permanent glut), so no sell-side fix works (see `research/sellfix/`). And v19's build is a **frozen tape** (not reconfigurable). The only lever that changes execution is a **new tape** → distill a stronger executor. Kyle was the strongest, most robust candidate; kenmatsu4/ali tapes were fragile off-seed.

## What's here
| Path | What |
|---|---|
| `main.py` | the submitted agent (Kyle's distilled tape) |
| `research/design-spec.md` | the sell-fix + placement-robustness design spec (the approach that proved structural) |
| `research/loss-report.md` | full loss forensics of Submission 1 (40W-14L; where the points leak) |
| `research/distilled-tapes/` | the 4 distilled top-30 opponent tapes A/B'd vs v19 (kyle ✓, mengfei ✓, kenmatsu ✗-fragile, ali ✗-fragile) |
| `research/sellfix/` | the **dead-end** late-market sell-filter wrapper (θ-hold didn't recover the structural glut) + the loader-gotcha fix. Regenerate: `python research/sellfix/build_sellfix.py`. |

## Caveats / next
- Open-loop **deterministic clone** — can't adapt. Natural refinement: a **hybrid** = Kyle's execution tape wrapped in v19's adaptive market controller.
- Forensic data (loss replays, leaderboard CSV) lives in gitignored `replays/live_55245235/` — regenerate with `scripts/pull_replays.py 55245235 "Spandan Mhapsekar"`.

_Uses the shared eval harness (`/eval`), engine reference (`/env_ref`), tools (`/scripts`), and economics (`/analysis`) at the repo root._

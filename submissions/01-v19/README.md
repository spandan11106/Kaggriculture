# Submission 1 — v19

- **Kaggle submission:** `55245235` (2026-08-04) · status COMPLETE · public score ~2558, rank ~70/1590 (top 4.4%)
- **Agent (`main.py`):** a 5,598-line procedural agent — a 4-medoid ensemble over decoded top-player policies executing a **frozen action tape** (`_V19_RUNTIME`, the "himanshu_kumar" board recording), wrapped in a clone-gated closed-loop late-market controller. Distilled from the v19 notebook (train/holdout split, train-only medoid experts).
- **Result:** first-ever submission on the account (climbed 679 → ~2560). Beats the c27 benchmark 10-2.

## What's here
| Path | What |
|---|---|
| `main.py` | the submitted agent (v19) |
| `research/main_c27.py` | the older c27 benchmark tape agent that v19 was validated against |
| `research/controller_base.py` | CONFIG-driven c27 for A/B experiments (built by `gen_controller.py`) |
| `research/build_variant.py`, `research/gen_controller.py` | the c27/c28 experiment framework |
| `research/c28-ablations/` | 6 market/allocation ablations — **all LOST** to the tuned baseline (reactive market 0-40; cow trims −7k; stop-selling-fertilizer −163k via shed clog). Regenerate: `python research/build_variant.py`. |
| `research/notebooks/` | source notebooks (v19 replication + zero-to-top findings) + extracted code/md |
| `research/tapes/` | v19 self-play open-loop tapes (format reference) |

## Key learnings
- The build is a **frozen tape** — `STRATEGY`/`configure_strategy` are dead, shadowed code; only a new coherent tape changes what the agent builds.
- **Naive market/allocation tweaks all lose** (the c28 ablations). The dominant lever is route-refresh (distillation) — which led directly to **Submission 2**.

_Uses the shared eval harness (`/eval`), engine reference (`/env_ref`), and economics (`/analysis`) at the repo root._

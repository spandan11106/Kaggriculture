# Design — v19 late-market sell-fix + animal-placement robustness

_Date: 2026-08-05 · Baseline: v19 (`agent/main.py`, submission 55245235, rank ~70/1590, score 2563.2)_

## Problem (measured, from live replays)

Forensics on all 55 public replays of 55245235 (`scripts/pull_replays.py`, `scripts/loss_report.py`,
`analysis/loss_report_55245235.md`):

- v19 goes **5–8 (38%) vs opponents stronger than itself**; every loss is close (−244…−6.5k) on a
  near-identical, often **byte-identical** build (many strong opponents are v19-clones → these are
  mirror losses). Money curves are dollar-for-dollar even through ~day 10–12, then v19 bleeds every
  day, worst on the final sell days.
- **Exact realized sell prices** (instrumented engine, v19 vs a distilled top-30 tape):
  strawberry 151% / melon 86% capture are already well-managed; **milk 84% (37% of units sold below
  ½ base) and wool 80% (24% below ½ base, 10% dumped to the $1 floor)** are the leak. v19
  batch-dumps the cow/sheep product streams into gluts.
- In the biggest mirror loss (Chakrabhuana, −13,485), v19 **bought 14 animals but only ever fielded
  13** — one premium producer's entire back-half output forfeited.

## Goal / non-goals

**Goal:** recover the milk/wool sell leak and the missing animal, raising v19's margin vs strong
(top-30) opponents — **without regressing any other capability.** We are top-100 and intend to stay
there; a change that trades one area for another is a failure, not a win.

**Non-goals:** touching the opening/build macro-strategy, the route, the closed-loop controller, or
any non-milk/wool market order. No changes to wheat (animal feed) or shed mechanics. Not chasing the
leaderboard top-10 in this iteration — only closing measured leaks safely.

## Approach

A **separate variant**, never editing the live baseline. `variants/v19_sellfix.py` is a byte-copy of
`agent/main.py` with its `agent()` renamed to `_base_agent`; a thin new `agent(obs)` calls it and
post-processes the returned action. The 5,598 tuned lines are untouched. Self-contained so it loads
under the gauntlet's isolated file-path loader.

Two levers, each behind an independent module-level flag so they can be tested alone or together:

### Lever A — milk/wool sell-filter (`ENABLE_SELLFIX`)

Post-filter that rewrites **only** `action["market"]` entries of the form `["SELL","MILK"|"WOOL",q]`.
Every other order (wheat sells, all BUYs, HIRE, BUY_LAND, strawberry/melon/etc. sells) passes through
verbatim.

Mechanism — **threshold-cap** (uses the ground-truth curve `economics.price_at_inventory`, **inlined**
into the variant — ~15 lines of `MARKET_PARAMS` + the shape function — so the file stays self-contained
under the isolated file-path loader, which won't resolve a local `import`):

- For each milk/wool sell, read live `market.inventory[item]`. Find the largest quantity `k` such that
  the marginal unit still clears at ≥ `THETA·base` (θ=0.75). Cap the order at `k`; the rest stays in
  the shed for the next town-demand tick to re-lift scarcity (town continuously drains milk & wool).
- **Shed-pressure override:** if shed occupancy (non-seed items) exceeds `SHED_HI=85`, disable the cap
  and pass the full sell through — avoiding overflow-discard is strictly more important than price.
- **End-game flush:** for `day ≥ FLUSH_DAY=28` (and always on the final day), disable the cap and
  liquidate — unsold inventory is worth $0.

### Lever B — animal-placement robustness (`ENABLE_PLACEFIX`)

**Root-cause first.** Before writing any retry, pin *why* the 14th animal failed in the Chakrabhuana
replay (and check whether it recurs in clean in-process games): structure-count short vs weed-blocked
build/place tile vs out-of-time. Only then write the minimal conservative fix that matches the cause
(e.g. DIG a blocking weed then build/place; or free a farmer-turn to build the 14th structure). If the
cause turns out to be rare seed variance with no safe cheap fix, Lever B is dropped and we ship A
alone — documented, not forced.

## Hard safety invariants (pass/fail, must be exactly zero)

These are the failure modes that sank prior market experiments (fertilizer −163k from shed clog;
reactive-market starved animals). Any nonzero value blocks promotion outright:

1. **0 shed overflows** caused by held milk/wool (instrument end-of-day drop discards).
2. **0 animals lost** that v19 would have kept (compare final animal counts vs baseline per seed).
3. **0 non-DONE episodes** (no crashes/timeouts introduced).
4. **Wheat/feed orders byte-identical** to baseline (the filter must never alter them).

## Validation — the non-regression gate (centerpiece)

Aggregate winrate is insufficient: it can hide a subpopulation regression. Promotion requires
**Pareto non-regression** across every segment below, on **paired seeds** (same seed for variant and
baseline to cut variance), **both seats**, ≥20 seeds:

**Opponent panel**
- _Must-improve (target):_ strong top-30 tapes where v19 currently loses — Kyle (r33), kenmatsu4
  (r28); distilled via `replay_to_tape.py` from the saved loss replays.
- _Must-not-regress (guardrail):_ v19 mirror; ≥1 mid-tier tape v19 currently **beats** (re-pull one
  won episode, e.g. prvsiyan r23); built-in `starter` and `random`.

**Segments checked (variant must be ≥ baseline on each, within noise):**
- Winrate & mean margin **per opponent**, and **per seat** (seat 0 / seat 1 separately).
- **Per-good capture%** from `market_diagnostic`: milk/wool must rise; **strawberry, melon, wheat,
  egg, tomato, carrot capture must not fall** (catches "fixed milk, broke strawberry").
- The four hard safety invariants above = 0.

**Non-regression criterion (removes "within noise" ambiguity):** judged on **paired-seed mean margin**
(same seed both agents). A guardrail segment _blocks promotion_ if its paired mean-margin delta is
negative **and** larger than 1 SEM (a real drop, not sampling noise); per-good capture% must be **≥
baseline − 2 points**. Ties (delta within 1 SEM of zero) pass.

**Promotion rule:** promote `v19_sellfix` only if it is **strictly better** on the milk/wool target
**and the strong-opponent margin**, **and no worse** on every guardrail segment and per-good capture,
**and** all four safety invariants are zero — from **both seats**. Otherwise: narrow/iterate, do not
ship.

**Attribution (resolves the bundle):** run three configs — sell-only, place-only, both — through the
same gate. If either lever regresses a segment, ship only the lever(s) that pass.

## Parameters (module-level, swept by the gate)

`THETA=0.75` (marginal-price floor as fraction of base) · `SHED_HI=85` (shed-pressure flush trigger) ·
`FLUSH_DAY=28` (end-game liquidation). Milk & wool only; extendable to other premiums only if the gate
proves it helps.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Holding milk/wool overflows the shed → discard (the −163k failure mode) | `SHED_HI` flush override; invariant #1 = 0 |
| Held inventory left unsold at game end | `FLUSH_DAY` end-game flush; final-day force-sell |
| Filter perturbs wheat/feed → animals starve | Filter only matches MILK/WOOL; invariant #4 byte-check |
| Improves milk/wool but breaks another good's timing | Per-good capture% regression check in the gate |
| Placement-retry wastes farmer-turns that did useful work | Root-cause-first; conservative; place-only config tested independently |
| Open-loop tape ≠ real adaptive opponent | Panel + mirror + baselines; tape is a fixed strong target, not the only signal |

## Deliverables

`variants/v19_sellfix.py` · a reusable gate harness (extends `eval/gauntlet.py` +
`eval/market_diagnostic.py` with per-segment/per-good regression output) · distilled opponent tapes ·
a results table in `analysis/`. Promote to `agent/main.py` + resubmit only on a clean gate pass.

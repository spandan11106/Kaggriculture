# Submission 3 — Planning Doc: closing the back-half execution gap

_Status: **PLANNING** (no agent shipped yet). Date: 2026-08-05._
_Author trail: synthesized from a repo map (engine / v19 agent / economics / eval infra) + a 6-field research sweep with an adversarial fact-check pass, then reconciled against the repo's own `loss-report.md`. Read the **Diagnosis** and **Honesty ledger** sections before trusting any dollar figure below._

> ### ⚠️ UPDATE 2026-08-05 — lever C (the sell pacer) was BUILT, TESTED, and REFUTED. See `RESULTS.md`.
> A drain-aware premium-sell pacer built on kyle's tape **loses to kyle 1-23 (−10k/game)**, with clean controls (a `pace=[]` passthrough ties kyle 10-10, proving the wrapper is faithful). **Mechanism:** pacing a shared premium lifts the price for *both* players (opponent free-rides → 0 relative gain) while holding inventory overflows the 100-shed and discards other produce (net −). **kyle sells at the competitive equilibrium; sell-timing has ≈0 relative EV.** This resolves the structural-vs-pacing fork (§7 Q1) as *effectively structural + shared-market-symmetric*, and **de-prioritizes levers C, D, G, F′ and E.** The only lever the data still supports for *winning more* is **lever F (diversification)** — produce uncontested egg/carrot/tomato goods. Ship-order below is now: keep v19 + kyle as the safe portfolio; the real frontier is a diversified coherent tape.

---

## 0. TL;DR — the whole plan in one screen

- **The gap:** v19 sits at rank ~70/1590 (rating ~2563), **~270 pts / ~$3.2k-per-game below the top-10 money cutoff (~2835)**. That gap is **not** a build/allocation problem — the opening is a near-solved mirror. It is **back-half sell execution** into a price-impact market that crashes premiums (milk/wool/strawberry) to the $1 floor.
- **The trap:** this leak is **provably invisible to self-play** — two clones dump identically, so the realized-price gap is symmetric and cancels. Every sell-timing lever **must** be A/B'd against **non-clone real/distilled top-30 opponents**, or self-play will greenlight a live regression (it already has — see the c28 ablations).
- **The one clean insertion point:** most of v19's 5,598 lines are **dead code**. The live agent is a **frozen `himanshu` tape replay** + a **late-market controller** that only fires against a near-mirror opponent. The controller (`main.py:5536–5580`) is the only live, mutable, obs-reading surface — but it currently almost never fires against the opponents you actually lose to.
- **The sequenced program (revised by the critique):**
  1. **Ship the hybrid** (kyle's better tape inside v19's controller) — near-certain, no-network, build-identical win. **Do this first.**
  2. **Build the real-opponent validation gate** in parallel (it unblocks everything downstream).
  3. **Compute the drain ceiling** (1–2 hrs) — this single number settles whether the leak is *fixable pacing* or *structural*, and bounds how many dollars a sell-pacer can ever recover.
  4. **Then, gated on that:** the drain-aware sell **pacer**, the **clone-gate widening**, the **opponent-exposure-reactive** sell, and the empty-market **diversification** slot-B.
- **The pivotal fork (needs your input):** is the back-half leak **structural** (README-02's claim: both clones flood premiums faster than the town drains → no sell-side fix helps) or a **fixable pacing problem** (the execution-research claim)? A cheap POV-k A/B settles it. **This reroutes the entire program.**

---

## 1. The game, in one paragraph (why this is a market-execution problem)

Kaggriculture is a 2-player farming-economy sim: 720 turns (24/day × 30 days), one farmer/hand action + up to **10 market orders** per turn, winner = **most bank money** (unsold inventory scores **$0**). You plant/raise, then **sell into a shared dynamic market**: every product starts at inventory `I0 = 10,000`; `price(inv) = base + sign·amp·f(|inv − I0|)`. Selling raises inventory → price falls. The premiums **strawberry / melon / milk / wool** use `above_target` of **1.6 / 3.6 / 1.6 / 3.2** (VERIFIED in `env_ref` `MARKET_PARAMS`), i.e. **super-linear glut impact** — even a modest dump drives them straight to the **$1 floor**. A "town" (center + shops unlocking every 3 days) continuously **drains** demanded goods, and the drain **scales up after day 10 and again after day 20**, slowly recovering price between your sells. The competition payout is a **Bradley-Terry** tournament over games played **Oct 1–15** on each team's **latest-2 submissions, locked Sep 30**; top-10 teams win $5k each. → **Selling premiums well is an optimal-liquidation problem against a recovering, super-linear-impact market.**

---

## 2. Architectural ground truth (read this before touching code)

The deep-read of `submissions/01-v19/main.py` (5,598 lines) found the live agent is far simpler than the file size suggests. **Everything here is verified against the code, not the README.**

| Fact | Where |
|---|---|
| **Live entry point** is the **SECOND** `agent()` — it does `return _v19_apply_control(obs, _v19_closed_loop_action(obs, step))` with a bare-`except` fallback of `{'farmer':['PASS'],'hands':[],'market':[]}`. | `main.py:5587` |
| The **entire STRATEGY / `configure_strategy` procedural farm-builder is DEAD** — it lives only inside the FIRST `agent()`, which is rebound to `_V19_PREVIOUS_AGENT` and **never called**. `_assign_actions`, `_crop_plan`, `_animal_plan`, `_build_tasks` are all reachable only from that dead subtree. **Confirms: STRATEGY knobs cannot change the built farm.** | first `agent()` `:4382`; rebind `:5584`; `configure_strategy` `:2368` |
| The build is a **frozen 719-step tape**: `_V19_RUNTIME = json.loads(zlib.decompress(base64.b85decode(...)))`. Keys: `experts` (`automatylicza`, `haoran_huang430`, `himanshu_kumar`, `subin_an`), each with a 719-step `actions` list + 30 daily `prototypes_by_day`. | `_V19_RUNTIME` `:4454` |
| **The "4-medoid ensemble" is INERT.** Decoded: `distance_strength = 0.0`, `stay_bonus = 0.0`, `board_by_seat = {0: himanshu_kumar, 1: himanshu_kumar}`. The per-day expert score collapses to a constant argmax → **himanshu for both seats, board AND market**. The ensemble machinery runs but changes nothing. | `_v19_closed_loop_action` `:5356` |
| **The controller only fires in the last ~40 steps against a near-mirror.** Logic: at `step==718` → forced full liquidation; `elif step>=680 AND _v19_clone_distance(obs)<=2` → append liquidation to spare market slots; **else return the tape unchanged.** | `_v19_apply_control` gate `:5579`; forced clear `:5577–5578` |
| **The `collision_score` sell ranker** (the thing that dumps premiums): `score = (1 + opp_exposure[item]) · GLUT_WEIGHT[item] · max(1, price) · log1p(qty)`, sort desc, emit top-10 SELL. **It is a greedy "dump the biggest glut now" ranker with no model of price recovery.** | `_v19_inventory_market` `:5536`; score `:5547–5551` |
| `GLUT_WEIGHT`: MELON 3.6, WOOL 3.2, STRAWBERRY 2.0, MILK 2.0, EGG 1.5, TOMATO 1.3, others 1.0. | `:5349` |
| `_v19_opponent_exposure` reads the **opponent's VISIBLE farm** each turn (their crop yields + animals via COW→MILK/SHEEP→WOOL/GOOSE→EGG) — never their shed. **This adaptive signal exists but is buried inside the greedy ranker.** | `:5515` |
| `_v19_clone_distance` = public-signature distance (hands, quadrants, per-type counts); the gate fires only when `<= 2` (near-perfect mirror). **This is why the leak is self-play-blind AND why the controller is a live no-op vs real opponents.** | `:5502` |
| `_v19_projected_shed` enforces the **100-item shed cap** and simulates same-turn DROP/PLACE — this is the `qty` fed to the ranker. | `:5423` |
| **kyle_r33** (Submission 2) is a **9-line open-loop tape**, indexed `day*24+hour` (not `obs['step']`, which is stripped for player 1). **Build tally byte-identical to v19** (8 COW / 6 SHEEP / 6 MILK-pasture / 12 WOOL-pasture / 3 STRAW-pasture / 21 MELON / 44 STRAW / 65 WHEAT / 20 PLACE-WHEAT; only delta is fertilizer 6 vs 4). Its ~5% edge is entirely in **130 differing market steps + a refined final-liquidation profile** (v19 blunt-dumps `SELL … 100` at step 718; kyle trickles). | `submissions/02-kyle-r33/main.py` |

**Implications that drive the plan:**
- The **only** safe place to change behavior without desyncing the tape is the **controller** (`5536–5580`) and the **decoded `_V19_RUNTIME` blob** (swap which tape/weights it replays).
- The controller is currently a **self-play-only no-op** — improving its sell policy (lever C) is worthless until the gate is widened to fire vs real opponents (lever D). These two are a package.
- The one adaptive signal already wired in — **opponent exposure from the visible farm** — is buried in the greedy ranker. Surfacing it is the cheapest attack on the close coin-flip losses (**new lever G**, added per the critique).

---

## 3. Diagnosis — where the points actually leak (corrected)

⚠️ **Correction from the synthesis:** the executive summary originally claimed "the *entire* deficit is d22–29 execution." The repo's own `loss-report.md` **partly contradicts** this. The honest picture:

- **Record:** 40W–14L live. Splits hard by opponent strength: vs stronger-than-v19 opponents it's a **coin-flip, 5–8, mean margin only −91** (all losses close, −244 … −6.5k). vs weaker/equal, 35–6.
- **The money gap opens at ~day 15 (−1,058), not day 22.** Of the 8 stronger-opponent losses, roughly **half diverge in the FIRST half** (kenmatsu4 last-lead ~d7, Ali ~d8, Chakrabhuana ~d6, Hamid ~d10, Mengfei ~d12). So "dollar-identical mirror through d10–12" does **not** hold for those games.
- **What is well-supported:** the losses are **efficiency, not failure** (0 non-DONE episodes, no starved animals, monotonic counts); the realized-value gap concentrates in the **premiums** (milk / strawberry / wool) that crash to the $1 floor; and **self-play cannot see any of it**.

**Net corrected diagnosis:** the deficit is **execution efficiency in the back ~two-thirds of the game (≈ d13 onward), with a meaningful mid-game (d13–20) component — not a d22–29-only problem.** This matters for design: a controller gated at **`step>=680` (≈ d28) cannot touch a d15 leak.** Any real fix must lower the insertion point into the mid-game.

> **The single most important open question** (Section 7): is this leak *pacing* (fixable by selling premiums slower as the town recovers price) or *structural* (production simply exceeds total town absorption, so some flooring is forced no matter what)? README-02 asserts structural and the θ-hold sellfix dead-ended on it; the optimal-execution research says it's a super-linear-impact pacing problem. **We do not yet know, and it reroutes the whole plan.** A drain-ceiling calc + a cheap POV-k A/B settle it.

---

## 4. The levers (prioritized, with honest gain labels)

Each lever: **thesis → research basis → concrete steps → expected gain → effort/risk → how to validate.** Gains are labeled **[VERIFIED]** (measured in-repo), **[HYPOTHESIS]** (modeled/asserted, not yet measured), or **[INDIRECT]**. The original synthesis ranks are preserved in brackets for traceability; the **execution order** is the revised one from the critique.

### Ship-order at a glance

| Order | Lever | Type | Network? | Gain | Risk | Gate |
|--:|---|---|:-:|---|---|---|
| **1st** | **A. Hybrid** (kyle tape + v19 controller) | ship | no | moderate–high, near-certain | med (desync) | self-play OK here + panel |
| **2nd (∥)** | **B. Validation gate** (real-opponent panel) | infra | yes | indirect (unblocks all) | med (unofficial API) | self-validating |
| **2nd (∥)** | **F′. Drain-ceiling calc** (1–2 hrs) | analysis | no | decides C's ceiling | low | settles the fork |
| 3rd | **G. Opponent-exposure-reactive sell** (NEW) | edit | no | direct on −91 margin | low–med | panel + 14 loss replays |
| 4th | **C. Drain-aware sell pacer** | edit | no | high **if** pacing | high | POV-k first, then DP, panel-gated |
| 5th | **D. Widen the clone-gate** | edit | no | multiplies C | med | panel; only after C |
| 6th | **E. Turn on the market-expert ensemble** | edit | no | low, cheap fallback | med | per-expert diagnostic |
| 7th | **F. Diversify into empty markets** (slot-B) | new tape | no | highest ceiling, lowest confidence | high | measure supply first |

---

### Lever A — Ship the hybrid: kyle's tape inside v19's controller  ·  [synthesis rank 2] · **DO FIRST**
- **Thesis:** kyle_r33 has a byte-identical build but ~5% better back-half execution (**beats v19 0.88 [VERIFIED]**) yet is pure open-loop with no controller. v19 has the clone-gated controller but the inferior himanshu tape. Compose both: kyle's `actions` as the tape `_v19_closed_loop_action` replays, `_v19_apply_control` unchanged on top. Two already-proven wins at near-zero marginal risk.
- **Research basis:** multi-teacher **policy distillation** (Rusu 2016 — a merge can beat individual teachers); behavioral-cloning compounding-error framing (Ross & Bagnell 2010) explains why kyle only wins where its trajectory stays inside tape coverage.
- **Steps:**
  1. Decode `_V19_RUNTIME` (`:4454`), replace `experts['himanshu_kumar']['actions']` with kyle's 720-step tape, re-encode to the b85/zlib blob. **Reconcile the 720-vs-719 index/length mismatch** (v19 uses `obs['step']` clamped to 718; kyle uses `day*24+hour`) — the +1 replay→tape shift is already solved, do **not** re-derive it.
  2. Keep `distance_strength=0` (no expert-switching), keep `_v19_apply_control` untouched.
  3. **Verify build-tally parity** after transplant + confirm the Kaggle loader binds the intended `agent` **last** in the namespace (the `get_last_callable` gotcha that silently mis-loads).
  4. Run the panel gate + safety invariants: require **0 non-DONE, 0 desync, non-regression on all guardrails**.
- **Expected gain:** **[HYPOTHESIS, well-founded]** ≥ kyle-alone (already 0.88 vs v19) plus the controller's clone-gated liquidation. Cheapest path to a shippable improvement over current v19.
- **Effort:** Medium (~½ day). **Risk:** Medium — index/schema mismatch desyncs and collapses reward, but the build-tally + 0-non-DONE + paired-gate chain catches it immediately.
- **Validation:** **This is the one lever where the self-play mirror is a VALID check** (build is identical, so no self-play-blindness concern); still make the *promotion* decision on the real-opponent panel.

### Lever B — Build the real-opponent validation gate  ·  [synthesis rank 1] · **PARALLEL, not blocking**
- **Thesis:** every sell-timing lever targets a leak self-play is **provably blind to**. Until we can A/B against a panel of **non-clone** real top-30 opponents with per-good capture% and paired-seed significance, we cannot tell a real fix from a self-play mirage — the c28 ablations already show naive tweaks pass self-play yet lose live.
- **Research basis:** EGTA + **Nash averaging** (Balduzzi 2018, "Re-evaluating Evaluation" — clone-invariant evaluation, VERIFIED); dueling-bandit / Copeland-winner budgeted evaluation (Yue 2012 / Zoghi 2015 — VERIFIED, conceptual mapping); the `design-spec.md` Pareto non-regression gate.
- **Steps:**
  1. `scripts/download_top_replays.py` — thin JSON-RPC client to `competitions.EpisodeService/ListEpisodes` for top-N ids from `leaderboard.csv`, then fetch replays; score-match to keep only genuinely strong opponents; reuse `pull_replays.py`'s W/L + money-curve + leaderboard-join logic. **⚠ `pull_replays.py` has NO network code — this is net-new against an unofficial endpoint** (may need session cookies/CSRF vs API token, may be dead/rate-limited). **Ask the user to paste their existing external version first.**
  2. Feed replays → `replay_to_tape.py` to build a panel of distilled tapes; **record each tape's provenance seed in the header** (currently missing) so the open-loop panel can be seed-pinned (kenmatsu/ali were fragile precisely because they desynced off-seed).
  3. Add a **paired-seed `--gate`** mode to `gauntlet.py:h2h()` — same seeds both variants, both seats, report per-opponent per-seat **mean-margin delta + SEM** with a **>1-SEM pass/fail**, one Pareto pass/fail table over the panel.
  4. Refactor `market_diagnostic.py:analyze()` to log **both** players, run each game in a subprocess (the engine monkeypatch is process-local), and **return a structured per-good capture dict** the gate asserts on.
  5. Add `eval/safety_invariants.py`: log end-of-day **shed overflow discards**, final animal counts, and a byte-diff of wheat/feed orders — the four hard invariants must be exactly 0. **Also assert the 10-orders/turn slot budget is feasible** (per the critique — see Risks).
- **Expected gain:** **[INDIRECT but gating]** converts ~$0 of untestable levers into testable ones. Engine compute is free (~40-game paired run ≈ 25s).
- **Effort:** Medium (~4–6 hrs; **optimistic** — the network piece is the risk). **Risk:** Medium (unofficial endpoint). **Fallback:** if the endpoint is dead, distill our own **14 loss replays** as a minimal non-clone (but narrow, seed-fragile) panel.
- **Validation:** self-validating — the gate must **reproduce the known live leak** (premium under-capture) on a distilled top-30 tape, else it's measuring the wrong signal.

### Lever F′ — Compute the drain ceiling (pre-work for C)  ·  [added by critique] · **1–2 hrs, do early**
- **Thesis:** from `_town_consume` + `TOWN_CENTER_DEMAND_SCHEDULE = [(20,4),(10,2),(0,1)]` + the shops' unlock schedule, sum the **maximum non-flooring premium absorption** (milk/wool/strawberry/melon) over turns 312–718 and compare to v19's **actual cumulative premium production**. **This one number settles the structural-vs-pacing fork and bounds lever C's max recoverable dollars.** If cumulative production exceeds cumulative drain, **no pacing dominates** — some flooring is forced, and effort should shift to diversification (lever F). ⚠ The dedicated engine-mechanics reader **died on a transient API error**, so the exact per-phase recovery rates still need to be re-derived from `env_ref/kaggriculture.py` (`_town_consume` ~`:697`, `MARKET_PARAMS` ~`:41`) — treat that as the first task here.

### Lever G — Opponent-exposure-reactive selling  ·  [added by critique] · **cheap, direct**
- **Thesis:** `_v19_opponent_exposure` (`:5515`) already reads the opponent's visible farm every turn, but the signal is buried inside the greedy `collision_score`. Re-weight/extract it to **sell premiums one turn AHEAD of a detected opponent dump**, into a not-yet-crashed price. This is the **cheapest direct attack on the −91 coin-flip margin** — no network, no offline DP, no new tape, and testable on the existing 14 loss replays.
- **Research basis:** opponent modeling / type-based reasoning (Albrecht & Stone 2018) — though note the medoids are self-state route selectors, so this is genuinely new "predict-the-opponent's-dump" logic, not reuse.
- **Risk:** must not fire so early it dumps into its own glut; gate behind the panel + safety invariants.

### Lever C — Drain-aware sell pacer (replace greedy `collision_score` + smooth the step-718 dump)  ·  [synthesis rank 3] · **❌ REFUTED 2026-08-05 (see RESULTS.md) — built, tested, loses to kyle 1-23. Do not build the DP.**
- **Thesis:** `collision_score` is a greedy "dump the biggest glut now" ranker with **no model of price recovery**, so it front-loads premium sells and floors milk/wool/strawberry — the measured leak. Replace it with a schedule solved **offline over the true nonlinear `price(inv)` curve + known town-drain dynamics**, deployed as a **state-threshold control law**, and **smooth the blunt step-718 clearance** so the final turn clears only residual.
- **Research basis:** Bertsimas-Lo DP (1998, VERIFIED theorem — uniform dumping is provably suboptimal under **super-linear** impact, which the premiums have); Almgren-Chriss slow-liquidation frontier for floor-risk-dominated regimes (2000); **POV** participation-rate heuristic as the light first iteration (sell = fraction of the town's per-turn absorption); Scarf **(s,S)/base-stock** threshold control (1960) as the deployable form given a frozen tape; optimal-stopping free boundary for terminal clearance. **⚠ Obizhaeva-Wang's terminal-block is REFUTED as harmful here** (it endorses exactly the d29 dump that loses) — smooth, don't block. The drain is **not** a constant resilience ρ (it steps at d10/d20) → use a **numerical DP over the true curve**, not the closed forms.
- **Steps:** extract per-phase drain-recovery rates (F′) → solve a Bertsimas-Lo-style Bellman DP for the optimal per-turn milk/wool/strawberry sell qty that keeps realized price above a per-product threshold (~0.75·base) **while guaranteeing full liquidation by turn 718** → reimplement `_v19_inventory_market` (`:5536`) + the score block (`:5547–5551`) as the threshold/POV pacer → **smooth the `step==718` clearance** (`:5577–5578`) so most premium liquidation moves into preceding paced days → wrap all new logic **exception-safe** (the live `agent()` bare-except silently returns empty market = forfeited sells) → keep feeding 14 animals, respect the 100-shed cap, keep flushing fertilizer (stop-selling-fertilizer lost **−163k [VERIFIED]**).
- **Expected gain:** **[HYPOTHESIS]** high **if** the leak is pacing; **bounded by the drain ceiling (F′)** and possibly ~$0 if structural. The original "$2.2k / ~70% of the gap" figure is **unmeasured** — treat as a target, not a finding.
- **Effort:** Medium-High (~1–2 days). **Risk:** High — (a) an unsold-inventory hold scores $0, so the pacer must be **provably exhaustive by 718**; (b) the **structural-vs-pacing fork is unresolved** and determines whether this works at all. **First A/B a cheap POV-k variant** before investing in the full DP.
- **Validation:** panel only (self-play blind). Milk/wool capture% must **rise**, others not fall >2pts, four safety invariants exactly 0, strong-opponent margin up from **both** seats.

### Lever D — Widen/lower the clone-gate  ·  [synthesis rank 4] · **only after C**
- **Thesis:** the gate `step>=680 AND clone_distance<=2` (`:5579`) almost never fires vs the structurally-different opponents where losses happen → the controller is a **self-play-only no-op**. Lowering the step floor (≈ 624 / d26, and lower into the mid-game to reach the d15 leak) and raising the distance threshold makes any improved sell policy actually engage live.
- **Research basis:** **Restricted Nash Response** bounded-regret p-knob (Johanson-Zinkevich-Bowling 2007, VERIFIED) — trade exploitation vs bounded worst-case loss; raise p only once a better default (C) exists.
- **Risk:** firing more often with a **bad** sell policy imports worse timing than the tape (the `collision_score` **is** the leak) — strictly gate behind C. **First instrument `clone_distance` on the panel to measure whether the controller *ever* fires live.**

### Lever E — Turn on the inert market-expert ensemble  ·  [synthesis rank 5] · **cheap fallback**
- **Thesis:** `distance_strength=0` makes the 4-expert market ensemble a constant pick. If any of automatylicza / haoran_huang430 / subin_an has a **better back-half market schedule** than himanshu, a non-zero `distance_strength` imports it **without writing a new sell model** — board stays himanshu so the build never desyncs (market-only risk).
- **Steps:** evaluate each embedded expert's **market** tape in isolation on `market_diagnostic` (decides go/no-go) → if one beats himanshu on back-half capture, set `distance_strength>0` and tune the per-day argmax. **Drop if none beats himanshu.**
- **Note:** likely subsumed by C if C succeeds; useful as a cheap complement/fallback.

### Lever F — Diversify into empty egg/carrot/tomato markets (slot-B exploiter)  ·  [synthesis rank 6] · **highest ceiling, lowest confidence**
- **Thesis:** eggs/carrots/tomatoes are town-drained with **zero current supply**, so they sell at/above base all game and **decorrelate** the premium end-dump (breaking the milk/wool synchronization that floors them). Highest-ceiling lever and the natural **decorrelated slot-B** — but requires a **novel coherent tape** (build change) and is riskiest.
- **Research basis:** concave-return separable knapsack / marginal-return allocation (Ibaraki-Katoh 1988 — cap premiums at the floor-crash point, redirect capital); **AlphaStar league** main+exploiter portfolio + Nash-averaging clone-invariance (Vinyals 2019 / Balduzzi 2018 — two byte-identical builds add no coverage); **PSRO** best-response-to-a-mixture (Lanctot 2017 — breed the exploiter against the real top-30, not a clone).
- **⚠ Critical refinement (critique):** don't treat the three as a generic "empty market." The **per-shop drain differs**: carrots (PET_CAFE only) vs eggs (BAKERY + BRUNCH_SPOT, 2 shops) vs tomatoes (PIZZA + FARMERS_MARKET) have **very different sustained ceilings** that decide slot-B viability. Compute per-good absorption first.
- **Steps:** **first measure** whether real top-30 opponents actually leave these markets empty in the Oct window (the entire upside rests on it) → if empty, design a coherent diversified tape (swap ~2 marginal cows → 3–4 geese, add carrot/tomato tiles), preserving the free-fertilizer stream (trimming cows without reinvestment lost **−3–7k [VERIFIED]**), the feed load, the 100-shed cap → build via `replay_to_tape.py` from a hand-authored/PSRO-bred coherent trajectory (**not** by editing the frozen tape — a sheep→goose swap lost **−24k [VERIFIED]**) → A/B on the panel → ship as slot-B **only if** it improves worst-case Bradley-Terry coverage over a second copy of slot-A.
- **Expected gain:** **[HYPOTHESIS, low confidence]** — the modeled "+$3.5k/game" and README's "+$34k self-play" are **unvalidated and self-play is blind**; real upside likely smaller and entirely contingent on the empty-market assumption.

---

## 5. Research mapping (fields → techniques → what they buy us)

Adversarial verification **downgraded several claims** — those are marked ✗ REFUTED / ~ STRETCH so we don't build on them.

| Field | Techniques we use | Applies to | Refuted / caveats (do NOT build on) |
|---|---|---|---|
| **Optimal execution / liquidation** | Bertsimas-Lo DP, Almgren-Chriss slow-liquidation frontier, POV participation rate, (s,S)/base-stock threshold, optimal-stopping terminal boundary | **Lever C** (+ G) | ✗ Obizhaeva-Wang terminal-**block** is harmful here; drain is time-varying (d10/d20 steps) → numerical DP, not closed forms |
| **Decision-time search / MPC** | Receding-horizon control, Rolling-Horizon Evolution over macro market-actions seeded by the tape, determinization over the 3 stochastic elements, macro-actions/progressive-widening | Higher-ceiling alt impl of **C/D** (plan only the tail, keep the solved opening) | ✗ MCTS/AlphaZero "guaranteed optimal" REFUTED for this adversarial/imperfect-info setting — use search as a heuristic improver, not for optimality |
| **Imitation / offline RL / distillation** | Policy distillation (multi-teacher merge → the hybrid), BC compounding-error framing, IQL/CQL offline-value intuition, trajectory stitching | **Lever A** (hybrid); design intuition for C's thresholds | ✗ DAgger "free expert queries from the sim" REFUTED (sim gives dynamics, not the optimal action — that's the unsolved problem); ✗ IQL-stitching as literal tape-splicing REFUTED (emits a reactive policy, not an open-loop splice) |
| **Combinatorial optimization / OR** | Concave-return separable knapsack / marginal-return allocation, MILP tile/animal check, DP/rollout over the known sim | **Lever F** (diversification allocation) | ✗ "RCPSP-NP-hardness justifies freezing" and "Solomon-VRPTW for sell-timing" REFUTED as category errors; ~ Ibaraki-Katoh separability doesn't strictly hold (shared price couples sells) — directional only, validate empirically |
| **Opponent modeling / robust selection** | Restricted Nash Response bounded-regret p-knob, type-based ensemble schedule selection, minimax-regret / DRO 2-slot portfolio, dueling-bandit budgeted evaluation | **D** (gate widening), **E** (expert selection), **B** (evaluation), portfolio (**F** slot-B) | ~ the 4-medoid ensemble is a **self-state route selector, not an opponent-type model** — true opponent-type inference from the visible farm is **new work** (lever G); dueling-bandits is conceptual (submissions lock Sep 30, no live arm selection) |
| **Self-play / EGTA** | Nash averaging (clone-invariant portfolio eval), PSRO/double-oracle best-response to the panel | **B** (gate), portfolio (**F**) | _(one verify agent for this area died on a transient API error — treat its claims as unverified, but the Nash-averaging clone-invariance result is independently verified in the opponent-modeling area)_ |

---

## 6. Experiment sequence (revised per critique — E2 first)

```
E0  Gate infra (Lever B)            ─┐  parallel
E2  Hybrid ship (Lever A)  ◀ FIRST  ─┤  (E2 does NOT block on E0's network piece;
F′  Drain-ceiling calc     ◀ 1–2hr  ─┘   its win is self-play-mirror-checkable)
        │
        ▼  F′ output settles the fork
E1  POV-k probe (cheap): structural-vs-pacing decision on the panel
        │  pacing? → E3 ; structural? → pivot to E5(F)
        ▼
E_G Opponent-exposure-reactive sell (Lever G)   ← cheap, testable on 14 loss replays now
E3  Full DP pacer (Lever C)         ← only if E1 says "pacing" AND F′ ceiling > production
E4  Widen clone-gate (Lever D)      ← after E3
E5  Expert-schedule probe (Lever E) ← drop if no expert beats himanshu
E6  Diversification (Lever F)       ← measure empty-market supply FIRST
        ▼
Sep 30  Portfolio lock: decorrelated pair maximizing worst-case Bradley-Terry
        coverage. Do NOT ship two byte-identical builds. Gate the swap on
        non-regression vs the CURRENTLY-LIVE pair (no recovery time in Oct 1–15).
```

**Acceptance gates (every code lever):** paired-seed, both seats, vs the distilled real-opponent panel; per-good capture% moves in the intended direction; **four safety invariants exactly 0** (0 shed-overflow from held goods, 0 animals lost, 0 non-DONE, wheat/feed byte-identical) + **10-slot order-budget feasible**; promotion requires beating the baseline from **both** seats over many seeds.

---

## 7. Open questions for you (genuine forks)

1. **STRUCTURAL vs PACING — the pivotal fork.** README-02 says the back-half leak is structural (clones flood premiums faster than the town drains → no sell-side fix recovers it); the execution research says it's a fixable super-linear-impact pacing problem. **Do you want to run the drain-ceiling calc (F′, 1–2 hrs) + a cheap POV-k A/B (E1) to settle this before committing to the full DP pacer (lever C)?** This reroutes the whole program toward pacing (C/D/E/G) or diversification (F).
2. **`download_top_replays.py`.** The README names your **external** version as the blocker. **Can you paste it?** (Saves the ~1–2 hr JSON-RPC rebuild and the risk of the unofficial `ListEpisodes` endpoint being dead/rate-limited.) If not — do you have Kaggle **session cookies**, or only an API token? (The endpoint may need cookies/CSRF.)
3. **Effort / timeline before Sep 30.** Priority = a **safe incremental ship** (hybrid + pacer as slot-A, near-certain modest gain) OR a **high-ceiling swing** (diversification slot-B, larger modeled upside but rests on the unverified empty-market assumption)?
4. **Slot-B portfolio choice.** Nash-averaging says two byte-identical builds add no coverage. The decorrelated second submission should be: (a) the **diversified egg/carrot/tomato tape** (highest ceiling, riskiest), (b) a **distinct sell-pacer parameterization** tuned as an exploiter vs the specific top-30 you lose to, or (c) a **receding-horizon planner** variant? Depends on which of E3/E6 validates.

---

## 8. Honesty ledger (critique's corrections — read before quoting numbers)

The adversarial critic rated the underlying synthesis **"needs rework on the diagnosis, then ship the low-risk slice,"** and flagged these — all folded into the doc above, listed here so nothing is buried:

- **Diagnosis overclaim (FIXED in §3):** "entire deficit is d22–29 execution" is contradicted by `loss-report.md` — the gap opens **d15**, and ~half the stronger-opponent losses diverge in the **first half**. A d680-gated controller can't touch a d15 leak → lever C/D must reach the mid-game.
- **Fabricated numbers → relabeled as HYPOTHESES:** `milk ~84% / wool ~80% capture`, the "$2.2k / ~70% of the gap," and lever-F's "+$3.5k/game" and "+$34k self-play" are **not measured** — the panel that would measure them doesn't exist yet (that's lever B). They are targets/hypotheses, not findings.
- **"Strictly dominates" overclaim:** a paced schedule can only dominate **up to the drain ceiling**. Verified: town-center absorbs each premium only **2/day (d0–9), 4/day (d10–19), 8/day (d20–29)** + a few shop units. Against 8 cows + 6 sheep producing daily, **if cumulative production > cumulative drain, some flooring is forced and no pacing dominates.** Compute the ceiling (F′) **before** building the DP.
- **"Only safe insertion point" is also LOW-LEVERAGE** until the gate is widened — lever C's live impact is conditional on lever D landing.
- **Lever B effort is optimistic** — `download_top_replays.py` is genuinely net-new against an unofficial endpoint; it's a single point of failure for the whole gated program.
- **10-orders/turn throttle** could **starve** a paced "trickle many goods" policy of order slots and force the very terminal dump it tries to avoid — assert slot-budget feasibility in `safety_invariants.py`.
- **Portfolio swap risk:** shipping a new pair **replaces both** currently-ranked submissions with no recovery time inside Oct 1–15 — gate any slot-B on non-regression vs the **currently-live pair**, not just vs v19.
- **Missing levers surfaced:** opponent-exposure-reactive selling (**added as lever G**), buy-side/demand manipulation (unexplored), per-shop drain differentiation for slot-B (folded into F), and measuring the frozen tape's **own** seed-desync across the randomized Oct games (part of the leak may be tape desync, not sell timing — measurable now with the existing gauntlet across many seeds).

**Critic's single highest-EV next action:** **ship lever A (the hybrid) first** — same-repo, no-network, build-identical, self-play-mirror-checkable — then run B/F′ in parallel and treat C/F as gated research.

---

## 9. Appendix — verified reference points

**v19 live path:** entry `main.py:5587` → `_v19_apply_control(obs, _v19_closed_loop_action(obs, step))`. Controller `:5573`; gate `:5579` (`step>=680 and clone_distance<=2`); forced clear `:5577–5578`. Ranker `_v19_inventory_market:5536`, `collision_score:5547–5551`. Signals: `_v19_opponent_exposure:5515` (opponent visible farm), `_v19_clone_distance:5502`, `_v19_projected_shed:5423` (100-shed cap). Runtime blob `_V19_RUNTIME:4454` (`distance_strength=0`, `stay_bonus=0`, `board_by_seat` both `himanshu_kumar`). Dead builder: first `agent():4382` → `_V19_PREVIOUS_AGENT:5584`; `configure_strategy:2368`.

**Engine (re-verify — the dedicated reader died):** `MARKET_PARAMS` premium `above_target` STRAWBERRY 1.6 / MELON 3.6 / MILK 1.6 / WOOL 3.2 (~`env_ref/kaggriculture.py:41`); `_town_consume` (~`:697`); `TOWN_CENTER_DEMAND_SCHEDULE = [(20,4),(10,2),(0,1)]`; shops draining the empty markets — EGG: BAKERY + BRUNCH_SPOT; CARROT: PET_CAFE (2×); TOMATO: PIZZA + FARMERS_MARKET.

**Build tally (v19 = kyle, VERIFIED byte-identical):** 8 COW / 6 SHEEP / 6 MILK-pasture / 12 WOOL-pasture / 3 STRAW-pasture / 21 MELON / 44 STRAW / 65 WHEAT / 20 PLACE-WHEAT (fertilizer 4 vs 6).

**Prior dead-ends (VERIFIED, don't repeat naively):** c28 reactive market 0–40; cow trim −3…−7k (without reinvestment); stop-selling-fertilizer −163k (shed clog); sheep→goose naive tape edit −24k; θ-hold sellfix flat (didn't recover the glut).

_Uses the shared eval harness (`/eval`), engine reference (`/env_ref`), tools (`/scripts`), and economics (`/analysis`) at the repo root. Supersedes nothing yet — this is the design for the next agent, not an agent._

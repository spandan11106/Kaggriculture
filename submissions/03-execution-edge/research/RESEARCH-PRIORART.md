# Prior-art research: how analogous Kaggle Simulations comps were actually won

_Date: 2026-08-06. Source: deep-research workflow (5-angle fan-out + 3-vote adversarial verification). The synthesis step and ~15 verification votes were killed by a session limit (resets 03:10 IST) — the shared-market/Cournot-Nash angle, the MuZero/RHEA decision-time-tractability claims, and the Halite Hungarian-assignment claim are UNVERIFIED and flagged below. 9 claims survived verification._

## Headline

**There is no single dominant method** — winners of analogous economy/RTS sims split across deep-RL self-play, receding-horizon rule-based planning, imitation/behavioral-cloning, and pure heuristics. But two verified data points **directly update our conclusion**:

1. **The Lux AI Season 2 winner (1st / 646 teams) was a hand-written receding-horizon FORWARD-SIMULATION planner — no neural net.** This is the single most transferable result, because Kaggriculture's engine is a **fully known deterministic simulator** — the exact precondition that makes forward-simulation planning work. This is the "decision-time search" lever from the original plan, and it's **not** a multi-week ML project.
2. **MILP beats RL on long-horizon scheduling by 2×–13× (unit commitment).** Strong, quantified evidence that a ground-up optimizer can beat a learned/distilled policy on a coherent resource-allocation schedule — supporting the offline-solver path.

## Verified prior art (what won each comp)

| Comp | Winning method | Verified detail | Vote | Source |
|---|---|---|---|---|
| **Lux AI S1** | **Deep RL self-play** | FAIR IMPALA + UPGO + TD-λ; **no MCTS** (forward inference only). Self-play **beat the rules-based agent within ~1 month, improving monotonically** → rules abandoned. | 2-1 / 3-0 | [writeup](https://www.kaggle.com/competitions/lux-ai-2021/writeups/toad-brigade-toad-brigade-s-approach-deep-reinforc) |
| Lux AI S1 (caveat) | — | **Pure self-play was UNSTABLE**; stabilized with a **frozen-teacher KL loss** to prevent "strategic cycles." *(directly relevant to a converged equilibrium.)* | 3-0 | same |
| **Lux AI S2** | **Rule-based + receding-horizon planning** | Hand-written Python (`role.py`/`mode.py`/`strategy.py`, ~15 `role_*` files), **no NN weights**. Uses **decision-time forward simulation**, tunable lookahead `FUTURE_LEN=51`. | 3-0 | [repo](https://github.com/ryandy/Lux-S2-public) |
| **Kore 2022** | **Imitation / behavioral cloning** | "train a supervised learning agent that **imitates top teams on the leaderboard**." **← exactly the distilled-tape moat we found.** | 2-1 | [discussion](https://www.kaggle.com/competitions/kore-2022/discussion/340035) |
| **Halite IV** | **Pure heuristics** | "100% rule-based bot with lots of parameters" → **3rd–4th** (1505 elo). | 3-0 | [repo](https://github.com/0Zeta/HaliteIV-Bot) |
| **Unit commitment** (OR benchmark, not a game) | **MILP > RL** | MIP "consistently produces lower-cost schedules than RL"; RL avg cost **>2× MIP** (50-gen), **13× worse** in worst case. | 3-0 | [paper](https://www.sciencedirect.com/science/article/abs/pii/S0306261923010231) |

## What this means for Kaggriculture (synthesis)

- **Highest-signal, most tractable path: a decision-time receding-horizon planner** (the Lux S2 pattern). Kaggriculture's engine is deterministic and known → we can simulate forward from any observation and pick actions by short-horizon lookahead. This is the one method that **directly attacks the execution moat** (a planner adapts to the live board, unlike a frozen tape) **and** naturally supports diversification (it evaluates any build). No training infra, no GPU. This *upgrades* the original plan's "decision-time search" lever from deprioritized to **primary candidate**.
- **Offline OR/MILP schedule solver** is corroborated (MILP≫RL on scheduling) — viable for generating the diversified 720-step build+route+sell plan offline.
- **Self-play RL is proven able to surpass hand-crafted agents** (Lux S1) — but it's the heaviest path (training infra + compute), and the Lux S1 team **explicitly hit the "strategic cycles" problem** (our converged-monoculture equilibrium) and needed frozen-teacher regularization to escape it. So RL *can* break the equilibrium, but only with anti-cycling machinery.
- **Imitation/BC winning Kore** independently confirms our "distilled tape" moat is a real, recurring phenomenon — not a Kaggriculture quirk.

## ⚠️ Gaps (killed by the session limit — re-run after 03:10 IST)

- **The SHARED-MARKET / Cournot-Nash / optimal-execution-vs-adversary angle was NOT verified.** None of the analogous games has a shared price-impact market with the free-ride dynamic that defeated our partial fixes. So prior art covers *execution quality*, **not** Kaggriculture's distinctive strategic problem. This is the most important unresolved question.
- Unverified: MuZero/Sampled-MuZero & RHEA/p-RHEA tractability-at-long-horizon claims; Halite linear-sum-assignment (Hungarian) detail; the two-player shared-price deviation-asymmetry claims.

## Bottom line

Prior art says the **execution moat is beatable** — by a **receding-horizon forward-simulation planner** (proven vs 646 teams in the most similar comp) or an **offline MILP scheduler** (proven ≫RL on scheduling), both of which exploit our known deterministic engine. The **shared-market strategic problem remains Kaggriculture-specific and unaddressed by prior art** — that's the frontier to research next.

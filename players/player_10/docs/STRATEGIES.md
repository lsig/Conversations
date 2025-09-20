## Player10 Strategies

Scope: brief descriptions of implemented strategies, decision rules, and key thresholds.

### OriginalStrategy
- Default Player10 behavior (no altruism).
- Cases:
  - **First turn opener**: prefer single-subject items; tie-break by highest importance.
  - **Keepalive**: if there are already two consecutive pauses, pick a safe item to avoid a third.
  - **Freshness after pause**: immediately after a pause, prefer items novel w.r.t. last 5 non-pause turns.
  - **General scoring**: choose the item maximizing canonical delta.

### AltruismStrategy
- Selection-aware variant comparing our best Δ to others’ expected Δ.
- Gate (speak vs hold): speak if `Δ_self ≥ E[Δ_others] - τ`
  - Lower τ by `ε_fresh` if last turn was a pause and our best item is fresh.
  - Raise τ by `ε_mono` if our best item would trigger monotony.
- Uses EWMA performance tracking (global and per-player, with minimum samples) to estimate `E[Δ_others]`.

**Key thresholds (simple definitions)**
- **τ (tau)**: base tolerance margin in the altruism gate. Higher τ makes us more willing to speak (because `E[Δ_others] - τ` is lower).
- **ε_fresh**: freshness bonus that decreases τ when we’re fresh after a pause (makes speaking slightly easier).
- **ε_mono**: monotony safety that increases τ when our best item risks monotony (makes speaking slightly harder).

**Shared rules and signals**
- **Canonical delta**: `Δ = importance + coherence + freshness - monotony`.
- **Coherence window**: up to 3 items on each side, without crossing pause boundaries.
- **Freshness window**: last 5 non-pause items before a pause.
- **Monotony**: penalty if any subject would appear in each of the last 3 non-pause items.
- **Safety**: avoid three consecutive pauses (keepalive).

**Selection forecasting** (used by altruism)
- 0.5 weight to current speaker; remaining probability distributed uniformly among the first proposer tier (minimum-contribution players), excluding self.

**Config knobs** (see `agent/config.py`)
- ALTRUISM_USE_PROB, TAU_MARGIN (τ), EPSILON_FRESH (ε_fresh), EPSILON_MONO (ε_mono), MIN_SAMPLES_PID, EWMA_ALPHA, CURRENT_SPEAKER_EDGE, context windows, and weights.


### Motivation: from average-threshold to selection-aware altruism

Historically, Player10 spoke when its best item’s score beat a global average threshold (not recent). This improved quality over always speaking, but it ignored a key factor: who is likely to speak next and how strong they are.

We extend that rule by forecasting the expected strength of the next contributor(s), not just the unconditional average. Two ingredients:

- Selection model: 50% weight on the current speaker (if any), with the remaining 50% spread uniformly across the minimum-contribution tier (excluding self).
- Skill model: Each player’s expected Δ is an EWMA mean; until we have enough samples for a player, we fall back to the global EWMA.

Decision rule (altruism gate):
- Speak if `Δ_self ≥ E[Δ_others] - τ`
- Where `E[Δ_others] = Σ_i (w_i · μ_i)`, with `w_i` from the selection model and `μ_i` from EWMA tracking.
- τ adjustments:
  - Freshness: `τ := τ - ε_fresh` if last turn was a pause and our best item is fresh.
  - Monotony risk: `τ := τ + ε_mono` if our best item would trigger monotony.

Assumptions and simplifications:
- If selected, others will contribute (no explicit pass probability); their expected Δ is their EWMA mean.
- We may stochastically mix strategies: with probability p (ALTRUISM_USE_PROB) use the altruism gate; otherwise use the original Player10 scoring.

Why this is better than “compare to average”:
- It conditions on who is likely to be chosen next and their learned quality.
- It reduces unnecessary proposals when a stronger contributor is very likely next, and encourages speaking when the likely next contributors are weaker.

Behavioral summary:
- Safety: if there are already 2 trailing pauses, propose a safe item (avoid early termination).
- After a pause: we first try a freshness-maximizing pick; otherwise we use the altruism gate.
- Otherwise: we use the altruism gate (or original scoring if the stochastic switch chooses it).

Formula recap:
- Speak if: `Δ_self ≥ (Σ_i w_i μ_i) - [τ₀ - ε_fresh·1[fresh] + ε_mono·1[mono-risk]]`



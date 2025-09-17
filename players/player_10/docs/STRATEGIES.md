### Player10 Strategies

Scope: brief descriptions of implemented strategies, decision rules, and key thresholds.

**OriginalStrategy**
- Default Player10 behavior (no altruism).
- Cases:
  - **First turn opener**: prefer single-subject items; tie-break by highest importance.
  - **Keepalive**: if there are already two consecutive pauses, pick a safe item to avoid a third.
  - **Freshness after pause**: immediately after a pause, prefer items novel w.r.t. last 5 non-pause turns.
  - **General scoring**: choose the item maximizing canonical delta.

**AltruismStrategy**
- Selection-aware variant comparing our best Δ to others’ expected Δ.
- **Gate (speak vs hold)**: speak if Δ_self ≥ E[Δ_others] − τ
  - Lower τ by ε_fresh if last turn was a pause and our best item is fresh.
  - Raise τ by ε_mono if our best item would trigger monotony.
- Uses EWMA performance tracking (global and per-player, with minimum samples) to estimate E[Δ_others].

**Key thresholds (simple definitions)**
- **τ (tau)**: base tolerance margin in the altruism gate. Higher τ makes us more willing to speak (because E[Δ_others] − τ is lower).
- **ε_fresh (epsilon-fresh)**: freshness bonus that decreases τ when we’re fresh after a pause (makes speaking slightly easier).
- **ε_mono (epsilon-mono)**: monotony safety that increases τ when our best item risks monotony (makes speaking slightly harder).

**Shared rules and signals**
- **Canonical delta**: Δ = importance + coherence + freshness − monotony.
- **Coherence window**: up to 3 items on each side, without crossing pause boundaries.
- **Freshness window**: last 5 non-pause items before a pause.
- **Monotony**: penalty if any subject would appear in each of the last 3 non-pause items.
- **Safety**: avoid three consecutive pauses (keepalive).

**Selection forecasting** (used by altruism)
- 0.5 weight to current speaker; remaining probability distributed uniformly among the first proposer tier (minimum-contribution players), excluding self.

**Config knobs** (see `agent/config.py`)
- ALTRUISM_USE_PROB, TAU_MARGIN (τ), EPSILON_FRESH (ε_fresh), EPSILON_MONO (ε_mono), MIN_SAMPLES_PID, EWMA_ALPHA, CURRENT_SPEAKER_EDGE, context windows, and weights.



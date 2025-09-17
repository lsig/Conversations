### Player10 Strategies (Concise)

Scope: brief descriptions of implemented strategies and decision rules.

OriginalStrategy
- Default Player10 behavior without altruism.
- Cases:
  - First turn opener: prefer single-subject items; tie-break by highest importance.
  - Keepalive: if there are already two consecutive pauses, pick a safe item to avoid a third.
  - Freshness: immediately after a pause, prefer items novel w.r.t. last 5 non-pause turns.
  - General scoring: choose item maximizing canonical delta.

AltruismStrategy
- Selection-aware variant comparing our best Δ to others’ expected Δ.
- Gate: propose if Δ_self ≥ E[Δ_others] − τ, with τ adjusted by context:
  - Lower τ by ε_fresh if last turn was pause and our best item is fresh.
  - Raise τ by ε_mono if our best item would trigger monotony.
- Uses EWMA performance tracking (global and per-player, with minimum samples) to estimate E[Δ_others].

Shared rules and signals
- Canonical delta: Δ = importance + coherence + freshness − monotony.
- Coherence window: consider up to 3 items on each side without crossing pause boundaries.
- Freshness window: last 5 non-pause items before the pause.
- Monotony: penalty if any subject would appear in each of the last 3 non-pause items.
- Safety: always avoid three consecutive pauses (keepalive).

Selection forecasting (used by altruism)
- 0.5 weight to current speaker; remaining probability distributed uniformly among the first proposer tier (minimum-contribution players), excluding self.

Config knobs (see agent/config.py)
- ALTRUISM_USE_PROB, TAU_MARGIN, EPSILON_FRESH, EPSILON_MONO, MIN_SAMPLES_PID, EWMA_ALPHA, CURRENT_SPEAKER_EDGE, context windows, and weights.



# Trajectory Refinement — What We're Adding and Why (Team Briefing)

## The situation, honestly

Watching the demo, the AI-fused (orange) trajectory visibly drifts from the true recorded path (blue) — most noticeably during tight, low-speed turns and after the simulated GPS outage. **This is not the backend being broken.** Frame-by-frame review confirmed the fused trail genuinely follows the real route through the whole 11-minute drive, including every zigzag turn. What's visible is our real, honestly-measured error (currently ~86–167 metres depending on the drive) at map scale, which looks like more than it is because a town block on the map is only a few hundred metres wide.

**We're adding one well-established technique to tighten this, without touching or faking anything that already works.**

## The one-sentence explanation for judges

> "Because our demo replays a recorded drive rather than live sensors, we can run an additional offline smoothing pass — RTS smoothing, a standard technique in navigation since 1965 — that uses information from *after* a GPS outage to refine the estimate *during* it. We show this as a clearly separate 'offline analysis' output, never confused with what a real-time phone could actually know."

## What's being added, in order

1. **RTS Smoother** (in progress) — the main piece. An offline backward pass over the already-computed trajectory. Legitimate specifically *because* we're replaying recorded data.
2. **ZARU** (Zero Angular Rate Update) — a small addition that corrects gyroscope bias whenever the vehicle is confirmed stopped, which bounds heading drift (the likely main cause of the turn-wander).
3. *(Conditional, only if needed after 1+2)* Tuning how strongly the physics constraint (NHC) is trusted during sharp turns specifically.
4. *(Explicitly NOT doing)* Magnetometer-based heading correction — too risky this close to the deadline (magnetic interference from the vehicle's own metal body is a real, hard problem). We say this is future work if asked, and that's a fine, honest answer.

## The most important thing to get right in the pitch

**Two outputs, always shown separately, never blended:**
- **Real-time estimate** — what the system would actually know while driving. This is the one that matters for the "does this work" claim.
- **Offline smoothed estimate** — the same system, but with a post-processing pass that uses the full recorded drive. Presented explicitly as analysis, not real-time capability.

**If a judge asks "does your phone see the future" — the answer is a clean no, and that's exactly why we kept the two outputs separate.** This distinction is a strength to state proactively, not a weakness to hope nobody notices.

## Numbers to have ready (locked, final — do not requote older placeholder figures)

| Sequence | Real-time (baseline) | Offline smoothed (RTS+ZARU) | Improvement |
|---|---|---|---|
| S3b (development, 11 min) | 85.8m mean overall | 51.9m mean overall | 39.5% |
| **S1 (unseen validation, 86 min)** | 166.5m mean overall | **51.5m mean overall** | **69.1%** |

**The generalization headline:** despite S1 being 8× longer and never tuned on, the smoothed result lands at essentially the same absolute accuracy as the development sequence (51.5m vs 51.9m) — this is the single strongest sentence to say to a judge.

We measure improvement two ways, not one — overall AND specifically during the GPS outage window — so we never accidentally claim credit for post-outage correction as if it fixed the hardest part. Both numbers hold up: during-outage error dropped 24–72% depending on the sequence (S1's outage baseline was unusually severe, giving the smoother more room to help exactly where it matters most).

We validate on two independent drives — the one we develop against (S3b) and a second, completely different one we never tune on (S1). Both showed real, large, honestly-measured improvement.

## If asked "why does offline matter if it can't improve the real-time line"

This is the sharpest, most likely question — have this exact answer ready, don't improvise it live:

> "You're right that the real-time line can't be improved by information that hasn't happened yet — that's a hard physical limit, not something our engineering could fix. What the offline pass actually proves is that our underlying estimator — the Kalman filter, the physics constraints, the GNSS classifier — is fundamentally accurate: given the complete picture, it converges very closely to the truth. That tells us the real-time system's limitation is purely about not knowing the future, not about the approach being wrong. And there's a real path to bring part of this benefit into near-real-time — a fixed-lag smoother that looks only a few seconds ahead instead of the whole drive — which is a natural next step beyond this MVP."

Three things this answer does: admits the real constraint honestly, explains what was actually learned, shows you know the real engineering frontier beyond the demo.

## If asked "why not just add more AI/ML"

The honest, strong answer: our intelligent layer is a rule-based GNSS reliability classifier plus the Kalman filter, which is the mathematically optimal estimator for this exact fusion problem. RTS smoothing is a natural, well-understood extension of the same statistical framework — not a new unvalidated model bolted on days before demo. We chose techniques we could fully verify and defend in the time available, over ones that might look more impressive but that we couldn't rigorously validate.

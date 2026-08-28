# Intelligent Dead Reckoning Navigation System — Project Brief

**Repo:** Codewiz-cpp/Intelligent_Dead_Reckoning_Navigation_System
**Track:** SIH — ISRO problem statement (ground vehicle positioning under GNSS/NavIC outage)
**Team:** Ayaan, Aryan B., Anurag, (+ others as confirmed)
**Status as of this doc:** Pre-code — architecture decided, kickoff not yet started

---

## Problem, one sentence
A smartphone's motion sensors (accelerometer + gyroscope) are far too noisy to track a vehicle's position by simple integration during a GNSS/NavIC outage — we need physics + targeted ML + map constraints to keep the position estimate usable until satellite signal returns.

## What we're building
A hybrid Android navigation system: a classical Error-State Extended Kalman Filter (ES-EKF) as the fusion backbone, a small CNN+GRU network for AI-assisted velocity estimation, a lightweight bias-correction network, non-holonomic vehicle constraints, and HMM-based map matching against OpenStreetMap road data — all running on-device via TensorFlow Lite.

## Why this architecture (not the alternatives)
Three architectures were compared:
- **A — Classical only (EKF + map matching, no ML):** robust and explainable, but likely reads as "not AI enough" for a problem statement that explicitly asks for AI/ML.
- **B — End-to-end learned inertial odometry:** impressive on paper, but fragile — no physics constraints, no error bounds, high risk of a catastrophic failure live in a demo.
- **C — Hybrid (chosen):** physics core stays authoritative and never fails catastrophically; ML components (velocity estimator, bias corrector, GNSS quality classifier) are additive and degrade gracefully if they underperform.

## Known gaps to address (from architecture review — don't let these slide)
1. **NavIC relevance is currently thin.** This is an ISRO PS — we need to explicitly surface which constellation each GNSS fix came from (`GnssStatus`, check for IRNSS) rather than treating "GNSS" as generic. This matters for sponsor credibility, not just technical completeness.
2. **Ground truth is circular without RTK.** Using the phone's own GNSS as "ground truth" to score inertial accuracy during a *simulated* outage is only as good as consumer GNSS (~2–5 m). State this limitation honestly in the pitch instead of overclaiming precision.
3. **No demo-level fallback.** Module-level fallbacks exist (see ARCHITECTURE.md), but there's no plan for "live demo sensors misbehave" — need a pre-recorded backup run.
4. **EKF tuning is the single highest silent-failure risk** — higher than the ML components, because a badly tuned filter fails quietly and confusingly rather than obviously.

## Team roles (fill in as confirmed)
| Role | Person | Owns |
|---|---|---|
| Navigation / Sensor Fusion | — | INS, EKF, NHC, alignment |
| ML / Data | — | Velocity estimator, bias corrector, GNSS quality classifier |
| Android | — | Sensor capture, TFLite integration, UI |
| Mapping | — | OSM processing, HMM map matching |
| Testing/Docs | Ayaan (default until reassigned) | Failure-mode testing, this doc set |

## Presentation MVP scope decision
Given limited time before presentation, the demo surface is a **static web visualization** (`/frontend`, see ARCHITECTURE.md), not a live Android app. The Python EKF/INS pipeline exports precomputed trajectory JSON; the website replays it on a map with an error/confidence chart alongside. Native Android build remains on the roadmap but is not the presentation-critical path.

## Current phase
**Phase 0 — Kickoff, not yet started.** See ROADMAP.md for the full phased plan and PROJECT_LOG.md for the running decision/status log.

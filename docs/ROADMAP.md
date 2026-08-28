# Roadmap

Ordered so the highest-silent-failure-risk component (EKF stability) gets validated before time is sunk into ML training on top of it.

> **ACTIVE PLAN: 3-day MVP sprint (Aug 29 → Sept 3, present Sept 4).** The phased plan below is the full production arc; the MVP sprint at the top is what the team is executing right now. See docs/MVP_PLAN (the final PDF) for the hour-by-hour breakdown.

## MVP SPRINT (current — web demo, no Android)
Crux = EKF + NHC producing a believable position through a simulated GNSS outage. One AI component (GNSS quality detector). No deep-learning training, no Android build, map matching optional (nearest-road only if at all).

**Day 1 (Aug 29)** — Backend: Part I (load/understand IO-VNBD at its real 10 Hz rate) + Part II (minimal INS + ES-EKF, GNSS-only fusion, confirm no divergence). Frontend: scaffold Vite+React+Tailwind+Leaflet+Recharts, mock replay with dummy JSON.
**Day 2 (Aug 30)** — Backend: Part III (NHC + outage simulation, export the 3 JSON files) + Part V (GNSS quality detector, scikit-learn or rule-based). Frontend: swap in real JSON, add outage banner + status badge + uncertainty circle + metrics panel.
**Day 3 (Aug 31)** — Integration, polish, error/velocity charts, responsive pass, deploy to Vercel, test on phone + laptop, record fallback video.
**Sept 1–3** — Buffer for slippage + rehearsal (the sprint is scoped for 3 days but the deadline is the 4th, so these are genuine safety days — don't treat them as extra scope).

Key MVP risk fallbacks (from the plan): dataset too complex → synthetic IMU+GNSS in Python; EKF diverges → complementary filter for attitude + keep NHC; time short → GNSS detector becomes a pure rule-based threshold; schema mismatch → freeze JSON schema at end of Part III.

---

## Full production arc (post-MVP reference)

## Phase 0 — Kickoff (before any of this)
- [ ] Confirm team roles (see PROJECT_BRIEF.md)
- [ ] Confirm repo access for all collaborators, agree on branch/commit convention (see CONTRIBUTING.md)
- [ ] Verify IO-VNBD dataset is actually downloadable and inspect its real format
- [ ] Confirm at least one team member is comfortable owning EKF tuning specifically — this is the highest-risk role to leave unfilled
- [ ] Set up shared dev environment / pinned dependency versions

## Phase 1 — Dataset understanding
- [ ] Download + parse IO-VNBD (IMU, GNSS, odometry, ground truth)
- [ ] Visualize trajectories, sensor stats, identify outage periods
- [ ] Document actual coordinate conventions found (don't assume from spec)

## Phase 2 — Minimal classical system (start here, not with ML)
- [ ] Basic strapdown INS
- [ ] Basic ES-EKF with GNSS position/velocity fusion only (no NHC, no ML, no map matching yet)
- [ ] Confirm trajectory doesn't diverge — this is the first real milestone
- [ ] Add NHC constraints (cheap, high impact) — visible drift improvement, good early demo checkpoint
- [ ] Only proceed to ML once you've confirmed classical+NHC isn't already "good enough" for the demo bar

## Phase 3 — AI velocity estimator
- [ ] Extract training windows (IMU → GNSS/odometry velocity labels)
- [ ] Train CNN+GRU on IO-VNBD
- [ ] Validate, quantize to TFLite

## Phase 4 — Bias corrector + GNSS quality detector
- [ ] Train small MLP bias corrector
- [ ] Train/threshold GNSS quality classifier
- [ ] Explicitly check for IRNSS/NavIC constellation flag in classifier features

## Phase 5 — Map matching
- [ ] Process OSM extract into road graph
- [ ] Implement HMM + Viterbi map matching
- [ ] Integrate as EKF pseudo-measurement

## Phase 6 — Mobile deployment
- [ ] Android sensor capture (IMU + GNSS, log constellation type)
- [ ] Port pipeline to Kotlin, integrate TFLite models
- [ ] Build map UI (MapLibre + offline tiles)

## Phase 7 — Real-world data + fine-tuning
- [ ] Collect 30–60 min real driving data across mounting configs
- [ ] Fine-tune velocity estimator + bias corrector on custom data
- [ ] Document ground-truth limitation explicitly (consumer GNSS-bounded unless RTK available)

## Phase 8 — Robustness testing
- [ ] Run through failure-mode table (ARCHITECTURE.md)
- [ ] Battery/latency optimization
- [ ] Prepare demo-level fallback: pre-recorded successful run as backup

## Phase 6b — Presentation website (MVP, parallel to Phase 6–8, not blocking them)
- [ ] Scaffold `/frontend` with Vite + React + Tailwind (see ARCHITECTURE.md for exact stack)
- [ ] Export trajectory JSON from the Python pipeline (ground truth / GNSS-only / classical / AI-enhanced / map-matched)
- [ ] Build Leaflet map with overlaid trajectories + animated replay
- [ ] Add Recharts panel for position error / confidence over time
- [ ] Deploy to Vercel, confirm auto-deploy from repo works

## Phase 9 — Demo prep
- [ ] Finalize demo scenario (simulated tunnel/outage)
- [ ] Prepare metrics display, talking points
- [ ] Rehearse with the fallback plan in place
- [ ] Confirm presentation website is the primary demo surface; native Android build (if any) is secondary/optional given time constraints

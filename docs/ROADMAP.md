# Roadmap

Ordered so the highest-silent-failure-risk component (EKF stability) gets validated before time is sunk into ML training on top of it.

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

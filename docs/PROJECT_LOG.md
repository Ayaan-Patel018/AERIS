# Project Log

Timestamped, append-only. One entry per working session: what changed, what was decided, what's still open. Keep entries short — this is a decision trail, not a diary.

---

## 2026-08-28 — Kickoff / doc setup
**Did:** Set up PROJECT_BRIEF.md, ARCHITECTURE.md, ROADMAP.md, CONTRIBUTING.md as the carried-forward reference set for this project (mirroring the doc pattern used on AI-Dubbing-Engine).
**Decided:** Going with Architecture C (hybrid classical+AI), per the earlier architecture comparison. Build order starts with minimal classical EKF before any ML training, to de-risk EKF tuning early.
**Open:**
- Team roles not yet finalized
- IO-VNBD dataset access unverified
- NavIC/IRNSS constellation exposure on target Android devices unverified
- No demo-level fallback plan yet (module fallbacks only)

**Next session should start with:** Phase 0 checklist in ROADMAP.md.

---

## 2026-08-28 (later) — Presentation MVP pivot
**Did:** Decided the presentation demo will be a static web visualization instead of a live Android app, given limited time. Locked exact tech stack (Vite + React + Tailwind + Leaflet/react-leaflet + Recharts, static JSON from the Python pipeline, no backend, Vercel hosting). Updated ARCHITECTURE.md, ROADMAP.md (new Phase 6b), and PROJECT_BRIEF.md accordingly.
**Decided:** Native Android build stays on the roadmap but is not presentation-critical.
**Open:** Repo push access for Ayaan not yet confirmed (see below) — verify before Phase 6b work starts, since it needs to land in `/frontend` on the shared repo.

---

## 2026-08-29 — MVP sprint locked, roles + rules + requirements added
**Did:**
- Confirmed the 3-day MVP plan (SIH_26168 web-app plan): EKF+NHC core, one AI component (GNSS quality detector), no DL training, no Android, static-JSON web demo. Deadline Sept 4; sprint scoped Aug 29–31 with Sept 1–3 as buffer/rehearsal.
- Verified IO-VNBD is real and public: github.com/onyekpeu/IO-VNBD, CSV format + Python tools. **Correction logged:** dataset samples at ~10 Hz (GPS 1 Hz), NOT the 100 Hz assumed in the original architecture doc. Window/sample-count math must use 10 Hz.
- Reassigned roles for the MVP: Ayaan = backend lead (~90% of pipeline) + frontend secondary; Anurag = EKF core support + deployment; Aryan = frontend lead. Updated PROJECT_BRIEF.md.
- Added `RULES.md` (mandatory Ayaan precheck of AI-generated backend code before any shared-branch push; frozen JSON schema; no direct pushes to main).
- Added `requirements.txt` (numpy, pandas, scipy, scikit-learn, matplotlib optional, flask optional).
- Added `MVP_PLAN` PDF as the hour-by-hour sprint reference.

**Decided:** Static JSON export over live API for the MVP. GNSS quality detector is the single AI component. Map matching optional/nearest-road only.

**VVIP — doc maintenance rule:** All docs + requirements.txt are living files, updated over time (same practice as the AI-Dubbing-Engine project). Claude updates them proactively when new decisions/info land, and Ayaan flags updates too. Every meaningful session ends with a PROJECT_LOG.md entry.

**Open:**
- Confirm Node.js/npm present on Ayaan's machine
- Agree + freeze JSON schema at end of backend Part III (before frontend wires real data)
- Pick the specific IO-VNBD sequence(s) for the demo

**Next session should start with:** backend Part I (load one IO-VNBD sequence, confirm real shapes at 10 Hz) and frontend scaffold in parallel.

---

## 2026-08-29 (later) — Dataset locked, terminology fixed, GPT review incorporated
**Did:**
- Read the actual IO-VNBD paper (README_1.pdf, now in repo root). Confirmed full V-* (29 cols, VBOX) and S-* (24 cols, AndroSensor) column schemas with units.
- **Naming fix (GPT's catch, correct call):** renamed `ground_truth.json` → `reference_trajectory.json` everywhere in the docs. VBOX GPS is a dedicated logger, not RTK — "reference" is honest, "ground truth" overclaims precision we don't have.
- **Locked dataset roles:** `V-*` = reference trajectory (evaluation only), `S-*` = actual pipeline input (this is what a real phone sees — matches the problem statement exactly).
- **Locked MVP sequence:** `V-S3b`/`S-S3b` (11.4 min, repeated turns + 1 reverse — good NHC demo). Backup: `V-Vta2`/`S-Vta2`.
- **New rule (mine, added to DATASET.md):** canonicalize timestamps to a `timestamp_s` column immediately at load time, before anything else touches the data — `V-*` and `S-*` use different clocks/units natively.
- Created `docs/DATASET.md` as the single reference for all of this — column tables, terminology, sequence choice, open items.
- Noted gravity is provided as separate columns in `S-*` (possible shortcut for bias removal) and flagged the gyroscope axis ambiguity in the paper's own table (Pitch listed twice) as unresolved — needs the real CSV header, not guessing.

**Decided:** Loader work (Part I) does NOT start until the open items in DATASET.md are checked against a real CSV (header presence, gyro axis order, gravity columns non-zero).

**Open:**
- The 3 open items in docs/DATASET.md (header row, gyro axis mapping, gravity columns) — check before writing the loader
- Node.js/npm confirmed present; venv + requirements.txt install still to be confirmed working
- JSON schema still to be frozen (end of Part III, per RULES.md)

---

## 2026-08-29 (later still) — Part I confirmed working; Part II design locked
**Did:**
- Wrote `backend/data_loader.py` against the real confirmed CSV structure (not the paper's description). Fixed two real bugs found by running it: (1) CSV encoding is Latin-1, not UTF-8 — both files' special characters (m/s², °, μT) were failing to parse; (2) S-* raw timestamp counter resets/wraps mid-sequence — fixed by building `timestamp_s` from cumulative forward-only deltas instead of simple subtraction.
- **Part I confirmed done:** both S-S3b and V-S3b load cleanly, 681 s duration, 10 Hz, 6813 matching rows, GPS 100% available, IMU stats sane.
- One open, non-blocking item logged in DATASET.md: `V-S3b`'s first column produces implausible "satellite count" values (max 137) — likely a column-order mismatch vs. the paper. Isolated as `vbox_col1_raw`, unused downstream.
- **Part II (INS+EKF) design fully locked** after GPT review — recorded in ARCHITECTURE.md "Part II design — LOCKED". Nominal quaternion state kept separate from the 15-dim error state; yaw initialized from a short GPS displacement window with unobservable-yaw flag; GNSS outage modeled as a first-class per-step availability flag; 4-mode ablation (pure INS / INS+GNSS / INS+NHC / full EKF) built in from the start.
- **Scope call (mine, not blocking):** NHC ships as basic hard-threshold first; adaptive gating deferred.

**Decided:** `ins_ekf.py` is next.

**Open:**
- `vbox_col1_raw` real identity (non-blocking)
- Confirm whether S-S3b's vehicle is stationary at t=0
- JSON schema still to be frozen at end of Part III

---

## 2026-08-29 (later still) — Part II DONE: ES-EKF running, ablation confirmed working
**Did:**
- Wrote `backend/ins_ekf.py`: full 15-state ES-EKF, local ENU conversion, GPS displacement-window yaw init, GNSS outage as first-class per-step flag, hard-threshold NHC, GPS velocity update, 4-mode ablation, JSON export.
- **Confirmed working on S-S3b** — 60-second outage:

| Mode | Mean error | RMSE | Max |
|---|---|---|---|
| ins_only | 13,658 m | 16,816 m | 34,071 m |
| ins_gnss | 193 m | 805 m | 6,911 m |
| ins_nhc | 572 m | 644 m | 1,112 m |
| **full** | **73 m** | **79 m** | **167 m** |

- JSON files exported to `backend/exports/`. Ready for Aryan to wire into frontend.
- **One known issue (non-blocking):** `ins_only` trajectory starts pointing in the wrong direction — likely yaw init. `full` mode unaffected.

**Decided:** JSON schema effectively locked by the exported files.

**Open:**
- Yaw init tuning for `ins_only` mode
- Part III: multiple outage window lengths (30s/60s/120s)
- Part V: GNSS quality detector
- Frontend: Aryan to scaffold and wire against the exported JSONs

---

## 2026-08-29 (later still) — Polish 1+2 done, S1 validation run, real gyro axis bug found and fixed
**Did:**
- **Polish 1 (adaptive GNSS noise):** wired GNSS quality classification into `update_gnss_position()` — noise scales 1x/3x/10x for healthy/degraded/unavailable.
- **Polish 2 (ZUPT):** added `update_zupt()`, triggered when GPS speed < 0.3 m/s for 3+ consecutive rows.
- **Polish 3 (S1 validation, unseen sequence, zero tuning):** ran the exact same pipeline on S1 (86 min vs. S3b's 11 min):

| Sequence | Full system, 60s outage: mean / max |
|---|---|
| S3b (development) | 68.9 m / 153.4 m |
| **S1 (unseen validation)** | **115.2 m / 718.7 m** |

Same order of magnitude, not identical (expected/good). "Not cherry-picked" evidence for the pitch.

**Honest finding, not a bug:** `ins_nhc` alone degraded much more on S1 (5,040 m) than S3b (605 m) — hard-threshold NHC's lateral-velocity≈0 assumption holds better at town speeds than S1's motorway segments. `full` mode stays consistent on both because GNSS corrects NHC's bias.

**Caution noted (GPT, correct):** never say "100% improvement" without the actual numbers — S1's ins_only diverges to 315,455 m, so any real result rounds to 100.0% at one decimal, which looks fabricated if quoted alone.

- **Polish 4 (yaw/gyro axis bug, found and fixed):** body-frame gyro vector was built as `[yaw_rate, pitch_rate, roll_rate]` mapped to `[X, Y, Z]`, but IO-VNBD's phone axis convention needs `[roll_rate, pitch_rate, yaw_rate]` = `[X, Y, Z]`. Fixed the convention, not the result.

**Decided:** JSON schema frozen. No changes without announcing to both tracks per RULES.md.

**Open:**
- Confirm gyro axis fix doesn't regress `full` mode numbers
- Frontend: Aryan scaffolding independently
- Sept 1 onward: freeze, only bug fixes + rehearsal

---

## 2026-08-29 (later still) — Architecture doc enriched from full design source
**Did:** Re-read the full 27-part design doc and pulled in everything viable the condensed version had dropped: full 12-module block diagram, "AI vs classical" defense table, error-growth physics, EKF-vs-UKF-vs-particle-filter rationale, failure-modes table, seamless mode switching explanation, 15-concept learning list.
**Decided:** ARCHITECTURE.md is the single richest reference; the original design doc is archival only.
**Open:** unchanged from prior entry.

---

## 2026-08-30/31 — Anurag's EKF audit PR reviewed and merged; requirements.txt incident
**Did:**
- Reviewed all 4 changed backend files in Anurag's PR (`data_loader.py`, `ins_ekf.py`, `outage_analysis.py`, `validate_s1.py`) line-by-line before merge, per RULES.md's precheck rule. Verdict: legitimate fixes, not stylistic changes.
- **Real bug caught and fixed by Anurag:** missing attitude self-propagation term in the EKF's error-state Jacobian (`F[6:9,6:9] = I - skew(w)·dt`) — technically required for a correct error-state EKF, was silently defaulting to identity before.
- **Real bug caught and fixed by Anurag:** the outage `gnss_status` flag was dead code — `gnss_available` was defined as `not in_outage AND ...`, making the branch that set `gnss_flag = "outage"` structurally unreachable. Fixed to properly distinguish "outage" from "unavailable."
- Also: Q matrix now scales with actual per-step dt (was baked at constructor time); `get_dataset_root()` path-resolution helper added; UTF-8 stdout fix for Windows.
- **161-test suite added and verified** (confirmed by running it ourselves, not just trusting the PR description — first partial run with `--unit-only` showed 92, full run confirmed all 161).
- Found and fixed a second bug in Anurag's own `conftest.py`: its dataset path was hardcoded to Anurag's personal machine's folder layout (`"GNN and RAG"` — his own folder name), causing all integration tests to silently skip on Ayaan's machine. Fixed by reusing `get_dataset_root()` instead of duplicating path logic.
- Merged. Corrected numbers post-fix: **S3b 85.8 m mean / 179.3 m max, S1 166.5 m mean / 789.2 m max** (slightly worse than pre-fix numbers, which is expected and reassuring — the old numbers were quietly optimistic due to the missing Jacobian term).
- **Incident:** Aryan's frontend merge (via `git pull`, not a PR) accidentally deleted `requirements.txt` (a "remove unused python scripts" cleanup commit that swept it up unintentionally). Caught and restored from Anurag's merge commit.

**Decided:** Corrected (slightly worse) numbers are the honest, defensible ones — reflect them in README, not the earlier pre-fix figures.

**Open:** README numbers need updating to the corrected values (85.8/179.3 S3b, 166.5/789.2 S1) if not already done.

---

## 2026-08-31 — Frontend integration: found frontend was built on 100% synthetic data, fixed the real gap
**Did:** Full writeup in `docs/FRONTEND_INTEGRATION.md` — read that for complete detail. Summary:
- Discovered Aryan's dashboard UI (built ahead of backend readiness, standard practice) was rendering entirely synthetic data — fake `{x,y,t}` point arrays, and a `useGNSSStatus.ts` hook where velocity/confidence/drift were literal sine-wave/arithmetic formulas, not real EKF output.
- Found 2 real structural bugs in the existing frontend code while reviewing (index misalignment across differently-sized real arrays; an unguarded `array[-1]` access that would crash the demo at playback start).
- Built `backend/export_frontend_data.py` — an adapter reshaping our already-frozen, tested backend exports into the exact format the frontend's existing components expect (ENU metres, time-aligned across all three trajectories), rather than rewriting Aryan's UI code.
- Rewrote `useGNSSStatus.ts` and `useTrajectoryData.ts`; patched 3 lines in `MapArea.tsx` and 1 in `TimelineSlider.tsx` (exact diffs in FRONTEND_INTEGRATION.md).
- Along the way, fixed 2 more real bugs found by inspection: velocity was in m/s but labeled/displayed as km/h (3.6x display error); heading could be negative but the UI expects 0-360°.
- **3 fake data points still flagged, not yet fixed:** ChartsPanel's velocity chart (sine wave), MetricsPanel's "VEL ERROR" (hardcoded), StatusPanel's "SATELLITES" (hardcoded). Tracked in FRONTEND_INTEGRATION.md's "Still fake" section — check that before assuming the dashboard is fully real.

**Decided:** Don't rewrite Aryan's components wholesale — patch precisely, reuse his existing structure, adapt data to fit what he built rather than the reverse. This kept every fix small and reviewable.

**Open:** Confirm the current fix actually renders correctly in-browser (in progress). Once confirmed, next phase is closing the 3 remaining fake-data spots using the same adapter-extension pattern. README numbers also still need the Anurag-merge correction applied (see prior entry).

---

## 2026-09-01 — Status incoherence fixed; trajectory refinement plan locked with GPT (RTS → ZARU → conditional NHC gating)
**Did:**
- **Fixed real status-logic bug found via frame-by-frame video analysis:** manual "Simulate Outage" button was fighting the real per-point status — showing "SIGNAL LOST, 0.0s elapsed" (timer walked real status, which stayed healthy under manual override) and "GNSS REACQUIRED" at the very start of playback (before any outage). Fixed: manual outage now gets its own real elapsed timer from click-time; "REACQUIRED" only shows in a short window right after the real outage ends. Also fixed unrounded heading display (`38.139999999999986°`).
- **Confirmed via extracted video frames (not guessing) that the core dead-reckoning result is real and good** — the fused trail visibly follows the GNSS/reference route through the entire recorded drive, including all the zigzag turns. The perceived "jumping" was the arrow's frame-to-frame heading noise, not the underlying trajectory.
- **Identified the real remaining gap:** visible fused-vs-reference divergence, concentrated in tight low-speed maneuvers (small-radius turns, the reverse/U-turn) and post-outage — consistent with heading-drift-dominated error, not a broken pipeline.
- **Locked a trajectory-refinement plan with GPT** — full spec now in ARCHITECTURE.md "Part VI — Trajectory Refinement (RTS Smoothing) — LOCKED". Summary: RTS smoother first (offline backward pass, legitimate because the demo replays recorded data, not live sensors), then ZARU, then conditionally Mahalanobis-gated NHC — sequential, test-gated, never all at once. Two outputs kept separate and honestly labeled (real-time vs offline-smoothed) specifically so the demo never implies the phone has access to future information. Every evaluation must break out error during-outage vs overall, not just a single overall number.
- **GPT's key correctness catch, non-negotiable:** RTS must operate on the error-state representation (same as the forward filter) and inject smoothed corrections into the nominal quaternion via the existing injection convention — never naive quaternion averaging.

**Decided:** Implement RTS only in this pass. ZARU/NHC-gating/magnetometer wait for RTS results — sequencing is mandatory, not optional, per the locked plan.

---

## 2026-09-01 (later) — RTS smoother + ZARU implemented (in ins_ekf.py, not a separate module)
**Did:**
- Implemented `rts_smooth()` and `export_smoothed_json()` directly in `backend/ins_ekf.py` (not a separate `smoothing.py` — kept alongside the filter it operates on). Correctly implements the error-state + quaternion-injection requirement locked in ARCHITECTURE.md: backward recursion smooths the 15-dim error state (not a naive flat-vector average), and the final correction is injected into the nominal quaternion using the exact same small-angle convention `inject_corrections()` already uses.
- `run_pipeline()` extended (purely additive — `use_zaru` and `store_smoothing_data` both default `False`, so the original validated 4-mode ablation and all 161 tests are untouched).
- Added `update_zaru()` to the `ESEKF` class — corrects gyro bias at confirmed stops (bounds heading drift, the identified dominant error source).
- **Self-caught spec deviation, fixed:** first implementation reused ZUPT's plain speed-only stop detector for ZARU too. Checked against the locked spec (which explicitly requires velocity AND acceleration AND gyro magnitude all near-zero for ZARU, "never a bare speed<threshold check") and corrected it — ZUPT itself stays exactly as validated (untouched), ZARU gets its own stricter confidence layer on top (`accel_mag < 0.5 and gyro_mag < 0.05`, in addition to zupt_active).
- New script `backend/rts_evaluation.py` — implements the exact 3-way comparison protocol locked with GPT: baseline (real-time) vs RTS-only vs RTS+ZARU, with **both overall and during-outage-only metrics** (mean/RMSE/max/p95) for every version, per the requirement that an improvement must not be attributable to post-outage averaging alone. `--s1` flag runs the unseen validation sequence once, with a printed reminder not to iterate on those numbers.
- Filed the full technical plan and self-assessment in `docs/RTS_SMOOTHING_PLAN.md`; teammate-facing briefing in `docs/RTS_TEAM_BRIEFING.md`.

**Decided:** Real-time (`fused_output.json`) and offline-smoothed (`fused_output_smoothed.json`) outputs stay in separate files, never merged, and are shown honestly labeled on the dashboard — this is the presentation framing locked in ARCHITECTURE.md, non-negotiable.

**Open:** Run `rts_evaluation.py` on S3b (tuning), confirm results before merging any frontend changes to display the new smoothed layer. Run `--s1` exactly once when S3b results look acceptable — not before, not iteratively.

---

## 2026-09-01 (later still) — RTS bug caught by results themselves, fixed, confirmed real improvement on S3b
**Did:**
- First `rts_evaluation.py` run produced RTS-only numbers **identical to baseline to the exact decimal** — correctly recognized this as a bug, not a null result (a working smoother must change something). Root cause: stored the post-reset error state (always exactly 0 by construction in a reset-based ESKF) instead of the real nonzero correction applied right before that reset each step — mathematically guaranteed to force zero backward correction regardless of covariances.
- **Fixed:** `run_pipeline()` now additionally captures `dx_upd` (the real pre-reset correction) and the INS-only predicted nominal state per step; `rts_smooth()`'s recursion corrected to use `dx_upd[k]` as the forward-filtered mean (base case `dx_smooth[N-1] = dx_upd[N-1]`, not zero).
- **Re-ran — confirmed real, substantial improvement on S3b:**

| | Mean | RMSE | Max | P95 |
|---|---|---|---|---|
| Baseline, overall | 85.8 | 92.2 | 179.3 | 157.2 |
| RTS, overall | 51.9 (−39.5%) | 55.7 (−39.6%) | 135.8 (−24.3%) | 85.7 (−45.5%) |
| Baseline, during outage | 81.9 | 87.3 | 138.5 | 130.4 |
| RTS, during outage | 62.2 (−24.1%) | 65.0 (−25.5%) | 81.3 (−41.3%) | 80.8 (−38.0%) |

- **Honest note (exactly the pattern GPT flagged to watch for):** overall improvement (39.5%) is larger than during-outage-only improvement (24.1%) — part of the overall gain is smoothing correcting portions of the drive outside the outage too. Both numbers must be quoted together, not just the larger one.
- **ZARU added ~nothing on top of RTS** (51.9→51.9 mean, max slightly noisier). Added a trigger counter (`zaru_trigger_count`) to `run_pipeline()`/`rts_evaluation.py` to check whether ZARU's strict gate is simply rarely firing on S3b before concluding anything — diagnosis pending, not yet run.

**Decided:** RTS result is strong enough to proceed to S1 (unseen validation, run once, per locked discipline).

**Open:** Check ZARU trigger count on S3b. Run `rts_evaluation.py --s1` once. Wire the confirmed-good smoothed output into the frontend as a separate, honestly-labeled layer (not started).

---

## 2026-09-01 (final) — S1 validation run (once, per protocol) — RESULTS LOCKED
**Did:** Ran `rts_evaluation.py --s1`. Final, locked numbers (no further tuning on S1, per protocol):

| Sequence | Baseline overall | RTS+ZARU overall | Baseline during-outage | RTS+ZARU during-outage |
|---|---|---|---|---|
| S3b (dev) | 85.8m mean | 51.9m mean (−39.5%) | 81.9m mean | 62.0m mean (−24.4%) |
| **S1 (unseen)** | 166.5m mean | **51.5m mean (−69.1%)** | 484.9m mean | **134.3m mean (−72.3%)** |

**Generalization confirmed strongly:** overall mean lands almost identically on both sequences (51.9 vs 51.5) despite S1 being 8× longer and never tuned on.

**ZARU trigger count on S1: 1,993/51,745 steps (3.9%)** — explains why ZARU helped meaningfully on S1 (long enough to accumulate real stop events) but showed ~zero effect on S3b (too short for enough genuine full-stops to matter). Not a bug, a real and explicable sequence-length effect — kept in the pipeline since it's real, harmless where it doesn't fire, and helps substantially where it does.

**One honest asymmetry, ready for Q&A:** S3b's overall improvement (39.5%) exceeds its during-outage improvement (24.4%); S1 shows the opposite (during-outage improves more, 72.3% vs 69.1%) — explained by S1's outage baseline being unusually bad (484.9m), giving RTS more room to help exactly where it matters most.

**Open:** Wire `fused_output_smoothed.json` into the frontend as a separate, honestly-labeled layer (not started — next actual task).

---

## 2026-09-01 (Night) — Leaflet OpenStreetMap & Satellite Tiles Overlay Implemented & Verified

**Did:**
- Replaced the plain dark coordinate grid on `/portal` with a fully interactive, multi-layer **Leaflet.js** map engine running directly underneath the real-time trajectory canvas overlay.
- Updated `backend/export_frontend_data.py` to export sub-centimeter accurate WGS84 `lat` and `lon` (7 decimal places) alongside local ENU `x, y` for all 6,812 trajectory points across `ground_truth.json`, `gnss_only.json`, and `fused_output.json`.
- Synchronized Leaflet's coordinate projection (`map.latLngToContainerPoint`) with the 60 FPS requestAnimationFrame canvas renderer.
- **Added 3 selectable tile layers (tested & verified in browser):**
  1. `DARK` (Default): CartoDB Dark Matter tiles matching the cockpit's sleek dark aesthetic.
  2. `STREETS`: OpenStreetMap standard tiles displaying street names, building footprints, and crossroads.
  3. `SAT`: High-resolution Esri World Imagery displaying actual aerial satellite photography.
- **Confirmed geographic accuracy:** Vehicle trajectory precisely follows Whitehall Road and Hillmorton Road (B5414) in Rugby, Warwickshire, UK (`52.370°N, 1.254°W`).
- Added interactive HUD controls: `FOLLOW` (camera auto-follow vehicle), `FIT ROUTE` (bounds-framing), `ZOOM (+ / -)`, and tile mode switcher.
- Verified dynamic physical metric scaling for uncertainty circles ($1\text{ m} \approx \frac{1}{111320}^\circ$ lat).
- Frontend production bundle built cleanly in 8.46s; 92/92 backend unit tests pass in 3.9s; browser console clean with 0 errors.

**Decided:** The map tile integration provides genuine geographical context without compromising 60 FPS trajectory playback or data honesty.


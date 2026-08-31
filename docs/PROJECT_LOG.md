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

**Open:** README numbers need updating to the corrected values (85.8/179.3 S3b, 166.5/789.2 S1) if not already done.

---

## 2026-08-31 (Night) — Closed all remaining fake data spots, verified full frontend in live browser

**Did:**
- Performed end-to-end frontend audit and live browser verification with screenshots and recording.
- **Fixed all 3 previously flagged fake data spots:**
  1. `ChartsPanel.tsx`: Replaced synthetic `Math.sin(...)` velocity curve with real EKF velocity data from `fused[i].velocity` (scaled to km/h) and nulling out during GNSS outage.
  2. `MetricsPanel.tsx`: Replaced hardcoded `0.4 m/s` VEL ERROR with honest `— (no ref)` and renamed generic estimator badge `ACTIVE` -> `ES-EKF`.
  3. `StatusPanel.tsx`: Replaced hardcoded `11`/`0` satellite counts with honest dynamic status label (`available` vs `—`).
- **Enhanced Charts Visibility:**
  - Added dynamic Y-axis bound annotations (`{maxErr}m` and `{maxV} km/h`).
  - Added clear legend tags (`FUSED` vs `GNSS`).
- Verified zero compilation/TS errors in production Vite build (1.38s build time).
- Verified live interactive playback and panel toggling via browser subagent recording.

**Decided:** Frontend is now 100% truthful to backend outputs — no synthetic values or hardcoded placeholders remain in active dashboard view.

**Open:**
- Add Leaflet / OSM map tile layer underneath the trajectory canvas for enhanced geographical realism during SIH demo.
- Upgrade GNSS quality classifier from rule-based to ML model (Module 3).


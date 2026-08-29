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

**VVIP — doc maintenance rule:** All 7 markdown docs + requirements.txt are living files, updated over time (same practice as the AI-Dubbing-Engine project). Claude updates them proactively when new decisions/info land, and Ayaan flags updates too. Every meaningful session ends with a PROJECT_LOG.md entry.

**Open:**
- Confirm Node.js/npm present on Ayaan's machine
- Agree + freeze JSON schema at end of backend Part III (before frontend wires real data)
- Pick the specific IO-VNBD sequence(s) for the demo

**Next session should start with:** backend Part I (load one IO-VNBD sequence, confirm real shapes at 10 Hz) and frontend scaffold in parallel.

---

## 2026-08-29 (later still) — Dataset locked, terminology fixed, GPT review incorporated
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
- **Part I confirmed done:** both S-S3b and V-S3b load cleanly, 681 s duration, 10 Hz, 6813 matching rows, GPS 100% available, IMU stats sane. Raw trajectory plot overlays both traces correctly — the repeated left/right turns pattern (the reason we picked this sequence) is clearly visible.
- One open, non-blocking item logged in DATASET.md: `V-S3b`'s first column produces implausible "satellite count" values (max 137) — likely a column-order mismatch vs. the paper. Isolated as `vbox_col1_raw`, unused downstream, doesn't block anything.
- **Part II (INS+EKF) design fully locked** after GPT review — recorded in detail in ARCHITECTURE.md "Part II design — LOCKED". Key upgrades over the original plan: nominal quaternion state kept separate from the 15-dim error state (avoids Euler singularities — this is the technically correct ES-EKF, not just "an EKF with 15 numbers"); yaw initialized from a short GPS displacement window instead of one heading sample, with an explicit unobservable-yaw flag if the vehicle starts stationary; GNSS outage modeled as a first-class per-step availability flag from day one, not bolted on later; a 4-mode ablation (pure INS / INS+GNSS / INS+NHC / full EKF) built into `ins_ekf.py` from the start — this gives the position-error-vs-time comparison chart "for free," which is the single most persuasive SIH figure.
- **Scope call (mine, not blocking):** NHC ships as basic hard-threshold first; Mahalanobis/residual adaptive gating is a should-have added only after the 4-mode ablation works end to end, so it can't quietly eat a day we don't have.

**Decided:** `ins_ekf.py` is next. Local ENU conversion, nominal+error state separation, and the 4-mode ablation are all mandatory parts of the first implementation, not later additions.

**Open:**
- `vbox_col1_raw` real identity (non-blocking)
- Confirm whether S-S3b's vehicle is stationary at t=0 (affects whether yaw-init needs the unobservable-flag path)
- JSON schema still to be frozen at end of Part III

---

## 2026-08-29 (later) — Architecture doc enriched from full design source
**Did:** Re-read the full 27-part design doc and pulled in everything viable that the condensed version had dropped:
- Replaced the small pipeline sketch with the full 12-module block diagram (ARCHITECTURE.md), with a note that 100 Hz was the design target but IO-VNBD is ~10 Hz.
- Added "AI vs classical" defense table, the error-growth physics (bias → time² drift), and the EKF-vs-UKF-vs-particle-filter rationale — the three things judges probe hardest.
- Added condensed failure-modes table + the "seamless mode switching" explanation (why the tunnel transition looks smooth, not teleporting).
- Added the 15-concept learning list to PROJECT_BRIEF.md for the backend lead.
**Decided:** ARCHITECTURE.md is now the single richest reference; the original DeepSeek doc is archival only.
**Open:** unchanged from prior entry (Node.js check, JSON schema freeze, demo sequence pick).

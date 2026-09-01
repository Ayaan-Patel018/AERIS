# PROMPT FOR AI AGENT — AERIS Trajectory Accuracy Improvement

*(Copy everything below this line into the AI agent, and attach the files listed in "FILES TO GIVE THE AGENT". Written to be self-contained — the agent needs no other context.)*

---

## CONTEXT

You are working on **AERIS** (SIH 26168, ISRO problem statement): a smartphone-only dead-reckoning navigation system for ground vehicles that keeps estimating position through GNSS outages. **No OBD-II / wheel odometry allowed — phone-grade sensors only.** The backend is a working, tested Python pipeline:

- **Repo:** github.com/Ayaan-Patel018/Intelligent_Dead_Reckoning_Navigation_System
- **Architecture:** quaternion strapdown INS + 15-state Error-State EKF (nominal state + error state, Joseph-form updates) + Non-Holonomic Constraints (lateral/vertical body velocity ≈ 0) + ZUPT + rule-based GNSS quality classifier with adaptive measurement noise (1×/3×/10×).
- **It works:** 161-test suite passes; validated on two independent sequences.

**Current measured accuracy (60 s simulated GNSS outage):**
- S3b (11.4 min, town, repeated tight turns): **85.8 m mean / 179.3 m max** position error vs a VBOX reference trajectory
- S1 (86 min, unseen validation, zero re-tuning): **166.5 m mean / 789.2 m max**
- Baselines on the same data: raw INS ≈ 12,600 m mean; GNSS-only spikes to km-scale during outage; NHC-only ≈ 490 m.

## THE PROBLEM TO SOLVE

On the demo map, the fused trajectory visibly diverges from the true path during/after the outage and especially through **tight low-speed maneuvers** (small-radius turns, loops, the reverse/U-turn near the end of S3b). 85–180 m of error is a large fraction of the map at town-block scale. **Goal: reduce fused-vs-reference divergence — especially heading-drift-driven wander — using legitimate estimation techniques only.**

## HARD CONSTRAINTS (do not violate)

1. **No cheating:** never snap/correct the fused output using the reference (V-*) trajectory — it's evaluation-only. No map-matching against the reference path in disguise.
2. **S1 stays untouched:** tune on S3b only; S1 is run once with final parameters as unseen validation. Do not iterate on S1 numbers.
3. **Don't break the frozen JSON schema.** New outputs (e.g., a smoothed trajectory) go to NEW files (e.g., `fused_output_smoothed.json`), never by changing existing fields/files' meaning.
4. **All 161 tests must still pass** (`python run_tests.py`).
5. **Phone-only sensor budget** — no adding data sources that a phone wouldn't have.
6. Propose changes as a reviewable diff of specific functions, not a rewrite of `ins_ekf.py`.

## RANKED DIRECTIONS TO EXPLORE (start at #1)

1. **RTS smoother (Rauch–Tung–Striebel fixed-interval smoothing).** The demo replays a *precomputed* trajectory, so an offline backward smoothing pass is fully legitimate. Store per-step (nominal state, error covariance P, transition F) during the forward EKF pass, then run the standard RTS backward recursion. Typically cuts peak outage error substantially because future GNSS reacquisition information flows backward through the outage window. Export as a separate `fused_output_smoothed.json` and present BOTH in the demo, honestly labeled ("real-time filter" vs "post-processed"). This is the highest-impact legitimate option.
2. **ZARU (Zero Angular Rate Update):** when ZUPT detects the vehicle stationary, also apply a zero-angular-rate pseudo-measurement to sharpen gyro-bias estimation — heading drift is the dominant error driver, and this is ~20 lines.
3. **Mahalanobis-gated NHC:** scale/reject the NHC pseudo-measurement when its innovation is statistically large (hard cornering violates lateral-velocity≈0); currently it's always hard-applied, which injects error during aggressive maneuvers — plausibly part of the tight-turn wander.
4. **Magnetometer yaw aiding (higher risk):** the dataset has magnetometer columns, currently unused. A yaw update with strong outlier rejection could bound heading drift during outages — but in-vehicle magnetic distortion is severe, so gate aggressively and only keep it if S3b improves without S1 degrading.

## DATASET (needed to run anything)

**IO-VNBD** (Onyekpe et al., Coventry University): github.com/onyekpeu/IO-VNBD — clone it INSIDE the repo root as `IO-VNBD/` (it's gitignored). ~10 Hz smartphone IMU, ~1 Hz GPS; CSVs are **Latin-1 encoded with header rows**.
- Dev sequence: `IO-VNBD/Synchronised V abd S datasets/Categorised IOVNB Dataset/S (Driver A)/S3b/` → `S-S3b.csv` (smartphone input) + `V-S3b.csv` (reference, evaluation only)
- Validation: same path, `S1/`
- Full column reference: `docs/DATASET.md` in the repo. Loader already handles encoding, timestamp wrap-around, unit conversions, and the gyro axis order (roll,pitch,yaw → X,Y,Z) — do not re-derive these, read `backend/data_loader.py`.

## FILES TO GIVE THE AGENT (in priority order)

1. `backend/ins_ekf.py` — the whole filter (INS, ESEKF class, NHC, ZUPT, pipeline loop, export). Nearly all changes land here.
2. `backend/data_loader.py` — how data is loaded/cleaned (read-only context).
3. `backend/outage_analysis.py` — evaluation protocol (30/60/120 s scenarios, metrics tables).
4. `backend/validate_s1.py` — unseen-sequence validation runner.
5. `docs/DATASET.md` + `docs/ARCHITECTURE.md` — column reference and locked design decisions.

## VALIDATION PROTOCOL (how we accept or reject your change)

1. `cd backend && python run_tests.py` → all 161 pass.
2. `python outage_analysis.py` → produce the before/after metrics table for S3b (all 4 modes, 30/60/120 s).
3. `python validate_s1.py` → S1 numbers with the SAME final parameters, run once.
4. Deliver: the diff, the two before/after tables, and one sentence per change explaining the estimation-theory justification. A change is accepted only if S3b improves **and** S1 does not get materially worse.

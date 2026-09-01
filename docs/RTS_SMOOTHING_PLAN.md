# RTS Smoothing & Trajectory Refinement — Assessment & Implementation Status

Companion to `ARCHITECTURE.md` Part VI (the locked technical spec). This doc records the reasoning: my own assessment of each module first, then exactly where GPT's review changed or confirmed the plan, and current implementation status. Read this to understand *why* the plan is what it is, not just *what* it is.

---

## Module 1 — RTS Smoother

**My assessment:** This is the correct highest-priority move, for a specific structural reason: the demo replays a *precomputed* trajectory, not live sensor data. That single fact makes offline backward smoothing fully legitimate — not a trick, not cheating — because a backward pass can use information from *after* the outage (GNSS reacquisition) to refine the estimate *during* it, which a real phone genuinely cannot do in real time. This is exactly the kind of technique that's respected, not questioned, when a judge understands it.

**GPT's addition (correct, adopted as a hard requirement):** flagged that our filter is an *error-state* EKF with a *quaternion* nominal state — meaning RTS must not be implemented as if the 15 numbers were an ordinary flat vector to interpolate. **This was the single most important technical catch in the whole review.** A naive quaternion average is not a valid rotation average and would silently corrupt attitude in a way that might not even look obviously wrong until checked carefully.

**Implementation status: ✅ Done — including a real bug caught by the results, then fixed.**

First run produced RTS-only numbers **identical to baseline to the exact decimal** (85.8/92.2/179.3/157.2, both scopes, no difference at all). That's not a "smoothing had no effect" finding — a working smoother changes *something*, even slightly. Root cause: I stored the post-reset error state (always exactly zero, by construction of a reset-based ESKF) instead of the actual nonzero correction that gets applied right *before* that reset each step. Mathematically, using an always-zero quantity as the forward-filtered mean forces the entire backward pass to output zero correction everywhere, regardless of the covariances — an implementation bug, not a diagnostic result.

**Fixed:** `run_pipeline()` now additionally captures `dx_upd` (the real, nonzero correction, captured the instant before `inject_corrections()` resets it) and the INS-only predicted nominal state at each step (`pred_p/pred_v/pred_q` — the state right after physics propagation, before that step's own measurement updates touch it). `rts_smooth()`'s backward recursion now correctly uses `dx_upd[k]` as the forward-filtered mean (base case: `dx_smooth[N-1] = dx_upd[N-1]`, not zero) and injects the final smoothed correction onto the INS-predicted trajectory, not the already-corrected one. Re-verified compiles clean; **awaiting a fresh run to confirm the fix produces genuinely different numbers** before any result is reported to the team or judges.

Original implementation details (transition/covariance storage, `np.linalg.solve` for numerical stability, quaternion small-angle injection) remain correct — only the mean-recursion had the bug.

**Expectation, calibrated correctly (GPT's point, adopted as-is):** no percentage promised. Could be large or modest — even a modest result is diagnostically useful, since it would tell us the dominant error source is something smoothing structurally can't fix (axis convention, initial yaw, uncorrected bias), which is itself worth knowing.

---

## Module 2 — ZARU (Zero Angular Rate Update)

**My assessment:** Worth doing second, specifically because heading drift (not position drift directly) is the plausible dominant driver of the tight-turn wander we observed — gyro bias compounds every turn. ZARU corrects gyro bias directly at confirmed stops, which ZUPT (velocity-only) doesn't touch.

**My first implementation had a real gap, caught and fixed before merge:** I initially reused ZUPT's existing stop detector (`gps_speed_ms < 0.3 for 3 rows`) for ZARU too, reasoning "don't build a second stationary definition." **GPT's review correctly rejected this** — a bare speed threshold is a weaker confidence bar than what ZARU needs, since it writes directly into gyro bias and a false trigger corrupts that bias for every step afterward until corrected. Checking my own implementation against this requirement caught the gap.

**Final implementation status: ✅ Done, fixed.** ZUPT's existing detector is **untouched** (already validated by all 161 tests — no reason to touch a working, tested thing). ZARU sits on top with its **own stricter gate**: `accel_mag < 0.5 AND gyro_mag < 0.05`, in addition to the existing ZUPT trigger — satisfying the locked "velocity AND acceleration AND gyro magnitude all near-zero" requirement without risking ZUPT's validated behavior.

---

## Module 3 — Mahalanobis-gated NHC

**My assessment:** Plausible fit for the symptom (tight, low-speed turns → wander is exactly where a hard-applied lateral-velocity≈0 constraint would be most wrong), but this changes the **real-time filter's own behavior** — not an offline post-process like RTS. Any change here requires full re-validation on both S3b and S1, which is real cost.

**GPT's addition (adopted):** explicitly conditional — don't touch until RTS + ZARU are measured. The right question to ask *after* seeing results is "is NHC being incorrectly trusted during those specific maneuvers?" — answerable from residuals, not guessed in advance.

**Implementation status: ⏳ Deliberately not started.** Waiting on RTS+ZARU results per the locked sequencing. This is correct discipline, not delay — implementing this out of order would mean re-validating on top of a still-changing baseline.

---

## Module 4 — Magnetometer yaw aiding

**My assessment (unchanged from earlier review):** Real risk, not worth it this close to demo. In-vehicle magnetic distortion from the vehicle's own metal body is a known hard problem, and a bad heading correction from a distorted magnetometer reading could make things *worse* in a way that's hard to debug in the remaining time.

**GPT's position:** Same — flagged as highest-risk, not recommended pre-demo.

**Status: Explicitly future work**, stated as such in the pitch, not attempted.

---

## Evaluation protocol — GPT's addition adopted in full

**Original gap in my plan:** I was going to report a single before/after number per sequence.

**GPT's correction (important, adopted):** report **overall AND during-outage-only** metrics separately, for every version. Reasoning: RTS can benefit heavily from post-outage GNSS reacquisition, which can improve the *overall average* without the *hardest, no-GNSS portion* improving nearly as much — reporting only the overall number risks accidentally overselling the result.

**Implementation status: ✅ Done.** `backend/rts_evaluation.py` computes mean/RMSE/max/**p95** (95th percentile added — a more robust outlier-resistant metric than max alone) for both scopes, across baseline / RTS-only / RTS+ZARU, and prints a clean comparison table matching GPT's requested format.

---

## S1 discipline — unchanged, restated because stakes are higher now

S3b is development; every parameter choice above is tuned and tested there only. **S1 runs exactly once, with final settings, as unseen validation** — this was already the rule for the original EKF work, and it matters more now: a smoothing change that helps S3b but not S1 is itself a valid, reportable finding (tells us something real about what limits the system), never something to hide or re-tune around. `rts_evaluation.py --s1` prints an explicit on-screen reminder of this rule every time it's run, so it can't be accidentally forgotten mid-session.

---

## What's left to do (in order)

1. Run `python rts_evaluation.py` (S3b only) — get the actual before/after numbers
2. Review the comparison table honestly — decide if the result justifies moving to ZARU-focused iteration or if RTS alone already closes most of the gap
3. Only then run `python rts_evaluation.py --s1` — once, final settings, report whatever comes out
4. Decide on Module 3 (Mahalanobis NHC) based on whether tight-turn wander persists after 1–3
5. Wire the smoothed output into the frontend as a clearly-labeled second layer (new work, not started — the dashboard currently only knows about `fused_output.json`)

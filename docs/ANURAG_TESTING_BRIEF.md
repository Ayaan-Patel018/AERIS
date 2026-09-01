# For Anurag — What Changed, What to Test, How

## What changed on the backend since your last PR

On top of your merged EKF audit (attitude self-propagation, Q scaling, outage flag, 161-test suite), two new capabilities were added, purely additive — nothing in your existing code paths changed:

1. **RTS (Rauch-Tung-Striebel) offline smoother** — a backward post-processing pass over an already-completed forward run. New function `rts_smooth()` in `ins_ekf.py`, new script `rts_evaluation.py`.
2. **ZARU (Zero Angular Rate Update)** — corrects gyro bias at confirmed stops. New `update_zaru()` method on `ESEKF`, opt-in via `use_zaru=True` (defaults `False` everywhere it isn't explicitly turned on).

**Results (locked, S3b dev / S1 unseen validation):** RTS+ZARU cuts mean position error 39.5% on S3b and 69.1% on S1, with strong generalization (51.9m vs 51.5m overall mean — nearly identical despite S1 being 8× longer and never tuned on).

## What to test on your end

**1. Confirm the test suite independently — don't just trust that it passed for someone else.**
```powershell
git pull origin main
cd backend
python run_tests.py --verbose
```
Expect: 161 PASS, 37 SKIP (skips are dataset-dependent integration tests — normal if you don't have IO-VNBD cloned locally, not a failure). If you get a different pass count, stop and flag it before anything else moves forward.

**2. Run the new evaluation yourself, confirm you get the same numbers.**
```powershell
python rts_evaluation.py
```
Should reproduce: baseline 85.8m mean → RTS+ZARU 51.9m mean on S3b. If your numbers differ meaningfully from this, something's inconsistent between machines/data — worth catching now, not on demo day.

**3. Deployment-specific checks (this is really your lane):**
- The `backend/exports/` folder has grown significantly (new `rts_comparison/` subfolder with S3b + S1 comparison JSONs and plots). Check this isn't causing any git/Vercel size issues:
  ```powershell
  git count-objects -vH
  ```
- If Vercel deploys the frontend from `/frontend` only (per the original setup), the backend exports folder growing shouldn't affect deploy size at all — but confirm this assumption is still true, don't just assume it.
- Once Aryan's frontend wiring (4th smoothed layer) is merged, do a fresh deploy and test the smoothed layer toggle actually loads and renders on the deployed version, not just locally — this is exactly the kind of thing that works on localhost and silently fails on a CDN/build step.

**4. Fallback video — re-record if you already made one.**
If your recorded fallback demo predates this session's fixes (the status-logic fix, the playback-timing fix, or this new smoothed layer), it's now out of date. Re-record once Aryan's frontend changes land, so the fallback matches what's actually being presented live.

## What to say if a judge asks you specifically about the backend math you audited

You found and fixed 3 real bugs in the EKF (missing attitude self-propagation term in the error-state Jacobian, Q matrix not scaling with actual timestep, a genuinely unreachable code branch in the outage flag). If asked "how do you know the filter is mathematically correct," that audit — plus the 161-test suite covering covariance symmetry/PSD/error-state mechanics — is your answer. It's a strong one; you don't need to oversell it.

## One thing to have ready: the offline-smoothing question

You may get asked why an "offline" result matters if it can't improve the real-time line. Short answer, keep it ready: *"The offline pass can't fix the real-time system — it can't use information that hasn't happened yet, that's a hard physical limit, not a shortcut we took. What it proves is that the underlying filter is fundamentally accurate — given the complete picture, it converges very close to the truth. That tells us the real-time limitation is purely 'no future information,' not 'wrong approach.'"* Full version of this Q&A is in `docs/RTS_TEAM_BRIEFING.md`.

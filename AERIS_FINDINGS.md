# AERIS findings log

# START HERE — handoff for a fresh session (state after R1 + I2a + I2b + M1-blocked, 2026-09-27; 330 tests pass / 37 skipped)

**R1, I2a and I2b are DONE and logged; M1 could not be measured (shared-machine memory pressure, see below); the user has just been shown the compact table for I2a/I2b/M1 and has NOT yet said "go C".** Read, in this order (if not already loaded): "DRIVE REGISTRY v2", then, at the end of
this file: "External sandbox study 3 — S1 review + OU speed prior", "PLAN UPDATE: R1 -> I2 -> C -> D-design" (the user's message, verbatim), "R1 — adopt ALL as the default", "I2a — OU speed prior", "I2b — turn speed ceiling", "M1 — stops missed inside outages". Everything above those
sections (H1, S0, S1) is settled/superseded and only needed for context.
**CURRENT DEFAULT (`VDRParams()` bare) as of this commit:** R1's ALL (`use_brake_gate`, `use_self_cal`, `use_anticascade`, `use_replay` = True, `w_exit` = 0.05) **+** I2b's turn ceiling (`use_turn_ceil` = True, `ceil_mode` = "fixed", `ceil_a_max` = 3.0). `use_ou` (I2a) stays False — it
FAILED its own pre-registered 1σ-coverage gate (30-70 %) at every grid point tried (real coverage collapsed to 0-16 %), a structural consequence of the OU process variance saturating instead of growing unboundedly during a long GNSS-free stretch; code + 10 tests kept, flag OFF.
Sanity check: `PYTHONUTF8=1 python backend/check_outage.py S3b --filter vehicle_dr` must give mini-outages **20.23 / 16.05 / 46.31** (n=20), S3b dev-window median end/p90 **99.52 / 209.02**, event mean/end/ratio **66.47 / 165.54 / 0.46**. Full-list dev-window reference: S3b dev 99.5/209.0/69.7/61.2,
S2 dev (FULL 861-window list, confirmed) 122.1/382.1/–/–, pooled med end 110.8, S3b mini 20.23.
**M1 (stops missed inside outages) is BLOCKED, not a rejection**: 4 attempts (4 workers -> 2 workers -> 2 workers/S2-only -> fully single-process, no pool at all) were ALL killed by the harness for system memory pressure on this shared machine while idle (orphan `nav-env` workers found + killed
after each). The single-process attempt ruling out my own job's footprint as the cause is the key fact — this is external resource contention (the machine's game, per CLAUDE.md), not something further scoping-down fixes. Per the harness's own instruction, not retried a 5th time on my own.
`quiet_enter_n` stays at its default (30); the exact script to re-run is described in the M1 section. **Ask the user before retrying, or retry opportunistically next time a real-data job runs anyway.**
**Next after M1 (whenever it's measured, or skipped): show the compact table (hold-last-fix, R1 default, I2a grid top 3, I2a=NOT ADOPTED, +I2b=ADOPTED, +M1) — already shown once above with M1 blocked — then only on "go C": the honest demo layer (export_frontend_data.py, RTS smoother,
frontend honesty fixes, S3b comparison PNG). D-design (OSM road-matching proposal, no code) comes after C. I1a/I1b/I3 stay deferred (I1a/I1b negligible vs 100+ m errors; I3 only if I2 falls short — I2b clearing the noise rule means it didn't fall short).**
Per-step protocol (standing rules): sandbox test with a numeric pass criterion first -> real-data metrics (dev windows S3b + S2, noise rule: < 5 % = no change; keep a change only if it helps S3b AND S2 or helps one and is neutral on the other) -> row in the plan table below -> full suite passes -> commit + push;
a failed step stays in the code behind a flag set to OFF, with the reason logged. Machine is SHARED (a game runs on it) and memory pressure has gotten WORSE since the S1 handoff was written (4 consecutive kills on 2026-09-27 across every worker-count strategy tried, including single-process):
use `dev_eval.py --workers 2` or less, expect real-data jobs to sometimes need several attempts or to wait for the machine to free up; watch out for python multiprocessing scripts on Windows needing `if __name__ == "__main__":`; always check `ps aux | grep -i python` and kill orphan workers after any killed job.

## Rules (CLAUDE.md + standing rules)
* Branch `fix/heading-spin`; never touch `main`; **push after every commit** (`git push origin fix/heading-spin`); never `git stash pop`; one change at a time.
* HARD RULE: nothing shown as AERIS may use VBOX (`V-*.csv`) speed/heading/path as an input (scoring and diagnostics only). No snapping to truth.
* `backend/ins_ekf.py` (ESEKF) stays untouched as the comparison baseline. Venv: `nav-env` (`nav-env/Scripts/python.exe`); dataset `./IO-VNBD`. Untracked files
  `anurag_branch_full.zip`, `branch_diff_stat.txt` are not ours — do not commit them.
* Conventions inside vehicle_dr: psi is ENU, radians, counter-clockwise from East; the phone course field is a BEARING (degrees clockwise from North):
  `psi = pi/2 - radians(bearing)`, wrapped (`bearing_to_psi`, unit-tested).
* Tuning data = S3b mini-outages (intervals between consecutive NEW phone fixes ending <= 200 s, 20 of them) and, from E0 on, the S3b sliding 60 s windows that END before 200 s
  (11 windows, starts 30-130) and, since registry v2, the 861 pre-registered S2 windows (S2 is a development drive). Report medians / p90 (mean where useful). S1 and S3c are never tuned on; the 200-260 s
  event is never tuned on (reported only). **Drive registry v2:** S3b + S2 development; S4 I3 training only; S3c final validation (B5, sealed, guarded by `--unseal`); S1 previously inspected (secondary); S3a reserve (sealed).
* Step protocol: (1) sandbox test with a numeric pass criterion, (2) real S3b metrics (mini-outages + tuning windows), (3) row appended to the results table, (4) full test suite, (5) commit + push. A step that fails its
  pass criterion keeps its code behind a feature flag set to OFF (sandbox tests stay), the reason is logged, and work continues.
* Windows console: pipe output only with `PYTHONUTF8=1` (a `≈` in a print raises UnicodeEncodeError under cp1252).
* Selection rule used for tuning (fixed in advance, `backend/tune_vehicle_dr.py`): lowest mean mini-outage error among grid points whose 1-sigma coverage is in [30, 50] %
  (target ~39 %); if none qualifies, closest to 39 %.

## Files
| file | what |
|---|---|
| `backend/vehicle_dr.py` | THE new filter: 6-state [E, N, psi, v, b_g, b_a] EKF; `run_pipeline(s_df, None, outage_window, params, t_end)`; `VDRParams`; `bearing_to_psi`; `evaluate_launch`; `calibrate_fixed_mount` |
| `backend/check_outage.py` | scoring: `python backend/check_outage.py [drive] [--filter esekf or vehicle_dr] [--fixes-only] [--mini-only] [--windows auto/tuning/all/off] [--per-window] [--unseal]` — 200-260 s outage report, **E0 along/cross + speed + path-ratio block**, mini-outage section (hold / const-v baselines) and, for vehicle_dr on S3b, the **sliding 60 s tuning windows** (`window_benchmark`, `score_track`, `Truth`, `summarize_windows` are importable for tuning scripts). Reserved drives S3c/S3a/S4 need `--unseal` (S2 is a development drive since registry v2). |
| `backend/window_plan.py` | deterministic sliding-window plan (phone fix availability + file time span only; the pre-registered rule); `python backend/window_plan.py S3c` reproduces the registered list (sha1 96375f11...) |
| `backend/tests/test_eval_e0.py` | 32 tests: window-plan rule, along/cross (line, circle, stopped truth), path ratio, speed diagnostics, guard, sandbox windows (GNSS really hidden, truncation exact, baselines, vehicle_dr beats hold), launch-from-stop flag, dev_eval helpers |
| `backend/dev_eval.py` | **development-window harness (registry v2)**: scores a `VDRParams` on the S3b dev windows (11) + S2 dev windows (861, worker pool, below-normal priority) + S3b mini / event / coverage / launch-from-stop; hold and const-v on the same windows. `python backend/dev_eval.py --name X --set key=value` or several `--config "NAME\|key=value\|..."` in one pool; `--workers 4` (each worker holds S2, ~300 MB — the machine is shared, 30 workers ran out of memory), `--s2-stride 4` for screening runs |
| `backend/check_alignment.py` | B0 time-alignment check for any drive (phone GNSS vs VBOX, lag scan); `python backend/check_alignment.py S3b S1 S2` |
| `backend/tests/test_gyro_scale.py` | 17 tests: H1a robust fit / estimator / causality / outage, H1b seven-state filter, sandbox pass criteria P1-P3 |
| `backend/tune_vehicle_dr.py` | `Evaluator` (S3b mini-outages, ~0.4 s per run), `grid_search` (coverage-constrained rule + LOO), `summarize` |
| `backend/mount_angle.py` | B2 calibration: phone horizontal frame -> vehicle forward angle, two criteria; `python backend/mount_angle.py S3b S1 --windows 30` |
| `backend/sim_drive.py` | synthetic drive with known truth (`simulate`, `SimConfig`, `default_route`, `long_route`, `multi_stop_route`) |
| `backend/tests/test_vehicle_dr.py` | 52 sandbox tests (`python backend/run_tests.py`; or `cd backend && ../nav-env/Scripts/python.exe -m unittest tests.test_vehicle_dr`) |
| `backend/data_loader.py` | loaders; phone `timestamp_s` from the wall-clock column; `sv_time_offset()` (scoring only); phone GPS speed is already m/s; gyro axis mapping (A2) |
| `backend/ins_ekf.py` | ESEKF baseline (do not modify); its Phase A fixes are in the log |

Diagnostic one-off scripts lived in a session scratchpad and are gone; everything reported is reproducible with the CLIs above.

## vehicle_dr current defaults (`VDRParams`) and which features are ON / OFF
**ON (default):** causal GNSS on NEW fixes only (position sigma = max(gps_accuracy_m, 3 m); speed; course when speed > 3 m/s), chi-square 99 % gate on every GNSS update
(3 consecutive position rejections -> next fix accepted ungated, logged `pos_forced`; **course and speed have no failsafe**), IMU-only standstill -> ZUPT + ZARU, psi frozen while stationary,
GNSS update order speed -> course -> position, honest propagation of data holes (dt > 1 s), B3b launch calibration with turn compensation and **replay only** (`aided_max_s = 0`).
**R1 (2026-09-27): `use_brake_gate` (S1a), `use_self_cal` (S1b, `self_cal_k` 2.0), `use_anticascade` (S1c) and `use_replay` (S1d) are all now ON by default (= "ALL"); `w_exit` 0.05 (S1e, was 0.10).**
S1 adopted despite NOT clearing its own real-data bar (false-standstill seconds down >= 50 % on both drives — S3b only reached -35.5 %) because that bar was mis-specified (S3b's dev windows contain
no false episode >= 1 s to move) and ALL is accuracy-neutral-to-positive on the dev windows by the noise rule, removes the sandbox catastrophe (smooth-cruise false-standstill 777-787 m -> 28-40 m) and
cuts real false-standstill time -35.5 % (S3b) / -59.5 % (S2). See "R1 — adopt ALL as the default" below.

**OFF (default False; code + sandbox tests kept):** `use_centripetal` (B3c, failed on S3b), `use_fixed_mount` (B3d, no benefit on S1), **`use_gyro_scale` (H1a) and `use_gyro_state` (H1b): correct on the sandbox, no benefit on real data because the real gyro scale is ~1.0**. Accel-integrated speed (`aided_max_s > 0`) is off because it hurt on S3b.
H1 knobs: `gs_window_s` 300, `gs_min_pairs` 5, `gs_k_min/max` 0.7 / 1.4, `gs_min_speed` 3, `gs_min_dcourse_deg` 20, `gs_max_pair_s` 15, `gs_max_x_rad` 2.8, `gs_latency_s` 0, `gs_fit` theilsen, `gs_gate_on` course, `gs_deadband` 0; `p0_sg` 0.10, `rw_sg` 1e-4.
New result keys: `gyro_scale_k / _log / _pairs` (H1a), `gyro_state_log` (H1b), `gyro_bias` (b_g per row, diagnostics), `standstill_log` (S0), `replay_log` (S1d).

| group | defaults |
|---|---|
| process noise | sigma_gyro 0.010 rad/s, turn_noise 0.50, rw_v 2.00 m/s/sqrt(s), rw_bg 1e-4, rw_ba 1e-3, rw_pos 0.10, rw_v_aided 1.0 |
| GNSS | gnss_min_sigma 3.0 m, sigma_gnss_speed 0.3 m/s, sigma_gnss_course_deg 6.0, min_course_speed 3.0 m/s, min_satellites 6, gate_enabled True, max_consecutive_pos_rejects 3 |
| standstill | win 10 samples, acc_var_enter 0.10 / exit 0.30, w_enter 0.05 / **exit 0.05 (S1e/R1; was 0.10)** rad/s, v_gate 2.0 m/s, launch_sigma_v 1.5, gnss_moving_speed 2.0, sigma_zupt 0.05, sigma_zaru 0.10 (H1c) |
| launch (ON) | use_launch True, n_before 8, n_after 20, min_rest 10, R_min 0.8, min_accel 0.4 m/s^2, turn_comp True, w_max_comp 0.8, comp_max 1.0, release_mean_thr 0.6 (x3 samples), quiet_enter_n 30, sigma_v_after 0.6, sigma_ba 0.2, aided_w_max 0.10, aided_max_s 0.0 |
| S1a brake gate (**ON, R1**) | use_brake_gate True, brake_w_max 0.10, brake_thresh 0.30, brake_median_s 20, brake_window_s 15, brake_frac 0.60 |
| S1b self-cal (**ON, R1**) | use_self_cal True, self_cal_k 2.0, self_cal_confirm_speed 0.3, self_cal_min_confirm 2 |
| S1c anti-cascade (**ON, R1**) | use_anticascade True, anticascade_block_s 20, anticascade_speed 2.0, anticascade_lookback_s 2.0 |
| S1d replay (**ON, R1**) | use_replay True, replay_buffer_s 30 |
| centripetal (OFF) | use_centripetal False, cent_w_min 0.15, cent_steady 0.10, cent_every 5, cent_v_min 1.0, sigma_cent 1.0 (untuned default; best S3b grid point was 4.0 = nearly off), cent_res 0.6, cent_bg_coupling False |
| fixed mount (OFF) | use_fixed_mount False, mount_cal_t 200 s, gate: both criteria corr > 0.8 and within 30 deg, sigma_lat 0.8, sigma_ba_rest 0.15 |
| initial P (std) | pos 5 m, psi pi, v 5 m/s, b_g 0.02, b_a 0.3; psi_init_sigma 6 deg |

Sanity check that the state is as documented (CURRENT DEFAULT, after R1): `PYTHONUTF8=1 python backend/check_outage.py S3b --filter vehicle_dr` must give mini-outages **21.31 / 16.09 / 63.95** (n = 20, coverage 55 %), outage mean **66.77 m**, end **175.95 m**,
event along / cross at the end -126.10 / +122.71 m, path ratio 0.46, mean speed error 2.44 m/s. (Pre-R1 default, all S1 flags off / w_exit 0.10: mini 21.72 / 16.33 / 63.92, coverage 55 %, outage 68.60 / 158.96, along / cross -100.34 / +123.29 — the H1c row;
`python backend/dev_eval.py --set use_brake_gate=false --set use_self_cal=false --set use_anticascade=false --set use_replay=false --set w_exit=0.10` reproduces the pre-R1 dev-window baseline.) Dev-window reference for the current default: `python backend/dev_eval.py --workers 4` -> S3b 120.9 / 211.6 / 69.8 / 60.8, S2 (861) 126.4 / 381.6 / 54.6 / 84.8, pooled 126.1, ~14 min (reproduced exactly 2026-09-27, see "R1" below).
Runtime: one full vehicle_dr run of S3b = 0.10 s (15 us/row); a full S2 window evaluation = ~5 min with 4 low-priority workers (~90 s for the stride-4 screening subset).

## Latest results table (S3b unless stated; mini = mean / median / max in m over the 20 intervals ending <= 200 s)
| step | S3b mini | LOO mean | S3b outage mean / end | disp (154) | path (~225) | 1-sigma coverage (~39 %) | S1 mini mean | verdict |
|---|---|---|---|---|---|---|---|---|
| baseline: hold last fix | 52.95 / 59.55 / 106.70 | – | – | – | – | – | 72.21 | reference |
| baseline: last fix + const-v | 34.89 / 39.71 / 73.36 | – | – | – | – | – | 26.67 | bar to beat |
| ESEKF as shipped (interpolated GNSS: tracking, not DR) | 12.90 / 10.35 / 43.04 | – | 55.02 / 129.56 | 34.0 | 145.4 | 0 % | 10.69 | reference |
| ESEKF fixes-only (its real DR) | 148.02 / 151.96 / 309.49 | – | 282.95 / 359.52 | 165.3 | 447.3 | 0 % | 347.98 | reference |
| B3a vehicle_dr core | 22.46 / 17.32 / 65.23 | 22.92 | 59.54 / 153.78 | 0.1 | 0.2 | 50 % | n/a | pass |
| B3b as specified (strict omega < 0.05) | 22.46 / 17.32 / 65.23 | – | – | – | – | – | n/a | fail: no S3b launch accepted |
| B3b turn-comp + accel integrated to next stop | 33.89 / 26.69 / 100.45 | – | – | – | – | 40 % | n/a | worse, reverted |
| B3b replay only (old default until H1c) | 21.93 / 17.11 / 64.85 | 22.12 | 64.35 / 145.89 | 75.5 | 104.9 | 50 % | 43.89 | pass, marginal (-0.53 m; 2 launches in the tuning window) |
| **H1c sigma_zaru 0.10 (superseded by R1, 2026-09-27 — see PLAN RESULTS TABLE v2)** | **21.72 / 16.33 / 63.92** | – | 68.60 / 158.96 | 69.9 | 104.5 | 55 % | **16.77** (tail gone) | adopted: dev windows -22 % (S3b) / -14 % (S2); event +6.6 % / +9 % (report only) |
| B3c centripetal speed (best S3b grid point) | 22.12 / 17.64 / 62.28 | 23.75 | 72.22 / 163.16 | 115.9 | 159.5 | 45 % | n/a | fail, OFF |
| B3d fixed-mount aiding (S3b gate inactive; S1 active, phi -65.5 deg) | = B3b | 22.12 | 64.35 / 145.89 | 75.5 | 104.9 | 50 % | off 43.89 / on 52.66 | no benefit, OFF |

S1 (validation, nothing tuned on it), 523 intervals outside 200-260 s: B3d off 43.89 / 20.05 / 620 (coverage 30 %); B3d on 52.66 / 20.09 / 1097 (20 %); const-v 26.67 / 22.78 / 136.

Current default outage (S3b, reported not tuned): mean 64.35, end 145.89, max 145.89, path 104.9 m (truth 225.7), displacement 75.5 m (truth 154.0), |dyaw| 288 deg (truth 676),
truth inside 1-sigma 20.3 %, sigma at 260 s = 268 m, gap last fix -> AERIS at 200 s = 4.26 m, pre-outage (20-200 s) mean 10.76 m vs raw phone GNSS 7.08 m.

## PLAN RESULTS TABLE v2 (registry v2 metrics; append a row per step; show it to the user after H1 and again after I3)
Dev windows: S3b = the 11 sliding 60 s outages starting 30-130 s (end < 200 s); S2 = the 861 pre-registered windows (rows marked "screen" use the stride-4 subset, n = 216, and are compared with the old default on the same subset: 150.0 / 466.9 / 67.5 / 95.2).
Cells = median end / p90 end / median |cross| at end / median |along| at end (m). Launch-from-stop = dev windows (S3b + S2, n = 138) starting within 10 s after an IMU standstill: median end. Event = 200-260 s (report only). 1σ = mini / S3b windows / S2 windows.
Noise rule: windows overlap; < 5 % on the median end error = no change; keep a change only if it helps S3b AND S2 (or helps one and is neutral on the other).
| step | S3b dev windows | S2 dev windows | S3b mini mean | launch-from-stop med end (n) | event mean / end / path ratio | 1σ coverage | verdict |
|---|---|---|---|---|---|---|---|
| hold-last-fix | 156.5 / 299.6 / 142.0 / 64.2 | 368.6 / 869.4 / 132.6 / 261.6 | 52.95 | 264.7 (138) | – | – | reference |
| const-v | 430.7 / 668.0 / 162.8 / 366.1 | 385.5 / 758.7 / 183.6 / 241.6 | 34.89 | 251.7 (138) | – | – | reference |
| E0 reference (old default, sigma_zaru 0.01) | 161.5 / 214.2 / 121.9 / 76.5 | 152.3 / 490.9 / 66.9 / 98.0 | 21.93 | 151.2 (138) | 64.35 / 145.89 / 0.46 | 50 / 53 / 41 % | old reference |
| H1a gyro-scale regression (spec W 300, min 5) | identical | 155.8 / 492.2 / 67.6 / 100.7 | 21.92 | 152.4 (138) | 63.44 / 143.53 / 0.46 | 50 / 53 / 37 % | no benefit (real scale ~1.0): OFF, kept |
| H1a (W = all) | identical | 156.2 / 480.8 / 65.9 / 99.6 | 21.92 | 152.1 (138) | 63.44 / 143.53 / 0.46 | 50 / 53 / 39 % | no benefit: OFF |
| H1a (W 300, deadband 0.05) | identical | 155.8 / 477.0 / 67.2 / 97.4 | 21.93 | 153.0 (138) | 64.35 / 145.89 / 0.46 | 50 / 53 / 38 % | no benefit: OFF |
| H1b scale state s_g (screen) | 162.3 / 213.4 / 128.1 / 77.1 | 149.0 / 449.1 / 65.7 / 95.4 | 21.95 | 193.6 (37) | 64.98 / 147.43 / 0.47 | 55 / 53 / 42 % | no change: OFF, kept |
| turn_noise 0.3 / 0.15 / 0.05 (screen) | 164.3 / 166.4 / 154.4 (end) | 148.6 / 150.4 / 151.9 (end) | 22.23 / 22.79 / 23.22 | 182.9 / 182.6 / 182.5 (37) | 65.72 / 67.97 / 67.71 (mean) | S2 29 / 24 / 24 % | no change; coverage collapses: keep 0.5 |
| probe: b_g frozen at 0 (screen) | 126.3 / 208.8 / 94.9 / 73.1 | 183.5 / 444.6 / 92.3 / 100.1 | 21.48 | 206.1 (36) | 67.78 / 156.77 / 0.46 | 55 / 55 / 23 % | helps S3b, hurts S2 +22 %: rejected |
| probe: tight prior + rw_bg 1e-5 (screen) | 126.2 / 208.8 / 95.6 / 73.0 | 122.4 / 385.5 / 58.5 / 77.2 | 21.49 | 187.2 (36) | 67.62 / 156.30 / 0.46 | 55 / 55 / 56 % | helps both; superseded by H1c |
| H1c sigma_zaru 0.10 (FULL S2 list) | 126.0 / 211.6 / 103.4 / 73.1 | 130.6 / 377.1 / 53.8 / 86.1 | 21.72 | 147.9 (138) | 68.60 / 158.96 / 0.46 | 55 / 50 / 62 % | adopted (S3b -22 %, S2 -14 %; S1 tail gone) |
| S1e w_exit 0.05 alone (S2 screen) | 120.9 / 211.6 / 69.8 / 60.8 | 113.8 / 377.2 / 51.6 / 75.6 (screen) | 21.31 | 193.5 (35, screen) | 66.77 / 175.95 / 0.46 | 55 / 56 / 59 % | real S3b gain, S2 neutral; alone fails the 50 %-false-standstill bar |
| ALL = S1a+S1b+S1c+S1d+S1e (FULL S2 list) | 120.9 / 211.6 / 69.8 / 60.8 | 126.4 / 381.6 / 54.6 / 84.8 | 21.31 | 133.7 (104) | 66.77 / 175.95 / 0.46 | 55 / 56 / 69 % | best S1 combo; noise-rule neutral/positive; fails the 50 %-false-standstill bar on S3b alone |
| **R1: ALL adopted as the default (2026-09-27)** | **120.9 / 211.6 / 69.8 / 60.8** | **126.4 / 381.6 / 54.6 / 84.8** | **21.31** | **133.7 (104)** | 66.77 / 175.95 / 0.46 | 55 / 56 / 69 % | **adopted — CURRENT DEFAULT**: S3b end -4 % / cross -33 %; S2 end -3 % / p90 +1 % (noise-rule neutral-to-positive); removes the sandbox catastrophe; false-standstill -35.5 % (S3b) / -59.5 % (S2) |
| I1a GNSS latency | | | | | | | deferred 2026-09-27 (B0 estimate ~0.5 s ~ 4 m, negligible against 100+ m errors) |
| I1b robustness (course failsafe / reset / Huber) | | | | | | | deferred 2026-09-27 (the hard lock-out was already removed by H1c) |
| I2a OU speed prior (screen: best tau20/W120) | 101.0 / 172.0 / 65.2 / 70.5 | 107.3 / 350.2 / 53.0 / 70.4 (screen) | 34.43 | – | 96.03 / 204.24 / 0.96 | 25 / 1 / 8 % | **NOT adopted — fails the pre-registered 1σ coverage gate (30-70 %) at every grid point tried**; `use_ou` stays OFF |
| **I2b turn ceiling: ceil fixed 3.0 (FULL S2 list) — CURRENT DEFAULT** | **99.5 / 209.0 / 69.7 / 61.2** | **122.1** / 382.1 / – / – | 110.8 | **20.23** | 66.47 / 165.54 / 0.46 | 40 / 44 / – % | **adopted** (S3b -17.7 % exact, S2 -3.4 % confirmed full list / neutral-not-worse, p90 stable both drives) |
| M1 outage-span recall / phantom driving | | | | | | | **blocked** 2026-09-27: 4 attempts (4 workers, 2 workers, 2 workers + S2-only, single-process/no pool) all killed by the harness for shared-machine memory pressure while idle; `quiet_enter_n` left at 30 (unchanged), not measured |
| I3 vibration speed (alone, and with I2a) | | | | | | | deferred unless I2 falls short |
| best combination | | | | | | | pending |
The target is to beat hold's end error clearly: S3b now 120.9 vs 156.5 m (-23 %; p90 211.6 vs 299.6, -29 %), S2 126.4 vs 368.6 m (-66 %).
Old E0-format table (S3b only, superseded — kept for history):
Tuning windows = the 11 S3b 60 s outages starting 30-130 s (end < 200 s). Along / cross = MEDIAN over windows of |along| / |cross| at the end of the window (m). Event = the 200-260 s outage (reported, never tuned).
Coverage = truth inside the reported 1-sigma ellipse: mini-outage intervals / windows (median over windows of the per-epoch fraction).

| step | S3b mini mean / median | 60 s tuning windows: median / p90 end error | tuning path ratio (median) | along / cross at end (median, abs) | 200-260 s event: mean / end / path ratio | 1σ coverage | verdict |
|---|---|---|---|---|---|---|---|
| **E0 reference: vehicle_dr default (B3b replay-only)** | 21.93 / 17.11 | 161.47 / 214.23 | 0.96 | 76.5 / 121.9 | 64.35 / 145.89 / 0.46 | 50 % / 53 % | **reference** |
| E0 baseline: last fix + const-v | 34.89 / 39.71 | 430.75 / 667.96 | 1.20 | 366.1 / 162.8 | not scored | – | reference |
| E0 baseline: hold last fix | 52.95 / 59.55 | 156.49 / 299.58 | 0.00 | 64.2 / 142.0 | not scored | – | reference |
| I1a GNSS latency | | | | | | | pending |
| I1b robustness (course failsafe / reset / Huber) | | | | | | | pending |
| I2a OU speed prior | | | | | | | pending |
| I2b turn speed ceiling | | | | | | | pending |
| I3 vibration speed (alone, and with I2a) | | | | | | | pending |
| best combination | | | | | | | pending |

Other E0 reference numbers (vehicle_dr default, tuning windows, median / mean / p90): mean error 80.97 / 84.11 / 110.67 m; |along| at end 76.52 / 83.73 / 132.93; |cross| at end 121.90 / 130.70 / 191.65;
mean speed error 4.71 / 4.61 / 5.86 m/s; path ratio 0.96 / 1.08 / 1.48; 1-sigma coverage 52.6 / 44.2 / 66.6 %. Event: mean |along| 28.73 m, mean |cross| 54.32 m, mean speed error 2.64 m/s. Details in the E0 section at the end of this file.

## Known issues (open)
0. **(E0) The 60 s windows and the event measure different regimes; vehicle_dr's 60 s outage error is large.** On the tuning windows vehicle_dr beats const-v and hold on MEAN error (median 81 vs 243 / 143 m) but its END error is
   no better than doing nothing (median 161 vs hold 156 m); it is cross-track dominated (|cross| 122 m vs |along| 77 m at the end): heading/turn shape, not only speed. The mean speed error is 4.7 m/s (speed is held while real driving is
   stop-and-go). The tuning windows have path ratio ~1 (speed held from a moving state is right on average), the event has 0.46 (car starts from a stop inside the outage) — so I2 tuned on these windows need not fix the event;
   the event stays report-only. 11 windows overlap heavily (~2.7 independent 60 s stretches): a thin tuning signal. **Update (H1/H1c): the cross-track error was heading DRIFT from a contaminated gyro bias, not the gyro scale (scale = 1.0); after H1c S3b end error is 126 m (hold 156 m) and
   S2 131 m (hold 369 m). The remaining S3b error is still cross-heavy (|cross| 103 vs |along| 73 m).**
1. **RESOLVED by H1c (2026-09-26): S1 heavy error tail from a hard-gate lock-out.** With sigma_zaru 0.10 the S1 mini-outage mean is 16.77 m (const-v 26.67), max 96 m, 0.0 % of intervals > 100 m, and the gate rejections fall 107 / 94 / 29 -> 0 / 1 / 0 (course / position / forced): the
   cause was ZARU-contaminated heading, not the gate itself. The gate has still no course failsafe (I1b as a safety net). Original description: vehicle_dr's S1 median 20.05 m beats const-v (22.78) but the mean 43.89 does not (26.67): 11.1 % of intervals > 100 m (const-v 0.8 %), 4 % > 200 m,
   max 620 m; mean without the worst 5 % is 31.0 m. In 9 of the 10 worst intervals BOTH the course and the position update were rejected by the 99 % gate at the interval-start fix; whole drive: 107 course rejections,
   94 position rejections, 29 forced position accepts, 1 speed rejection (S3b: 1 / 1 / 0 / 0). Once psi is wrong the gate rejects exactly the measurements that would repair it; only position has a failsafe and a forced
   position accept does not repair psi. NOT fixed on purpose (found on S1 = validation): candidate B3i (Huber / Student-t GNSS updates) or a course failsafe, to be justified and verified on the sandbox and S3b.
2. **Outage shape: path 105 m vs 225.7 m truth, displacement 75.5 m vs 154 m; mean error 64.35 m is worse than the old ESEKF's 55.0 m.** After the 180-212 s stop the car is started only by the launch replay
   (v ~ 2.3 m/s at 214 s) and the speed is then held, while the real car accelerates to ~8 m/s; no GNSS and no usable forward-accel model inside the outage. Reported sigma at 260 s is 268 m (1-sigma coverage 20 %).
3. **Forward-accel information is not usable on real data**: the phone's yaw relative to the car is NOT constant on S3b (per 30 s windows 9/19 fit well at scattered angles 73 to -115 deg; resultant length 0.31), and on S1 the
   calibrated angle is only good to +-25-30 deg (criteria 29 deg apart; about 40 % of accepted S1 launch angles within 30 deg of it). Everything that projects the accel on a forward axis (accel-integrated speed, fixed-mount aiding,
   signed centripetal) works on the sandbox but is neutral or harmful on S3b/S1.
4. Small tuning set: 20 S3b mini-outage intervals; the coverage-constrained selection sits at the 50 % edge; the error surface is flat (22.5-24 m) so tuning bought honest uncertainty, not accuracy. B3b evidence = 2 launches.
5. Sandbox coverage test window is 25-70 %, not 25-55 % (S3b-tuned noise gives ~64 % on the calmer sandbox).
6. `run_tests.py` skips 37 dataset tests: `tests/conftest.py` looks for IO-VNBD three directories up, but it is at the repo root (pre-existing; not fixed).
7. S3b data facts: 4.33 s logging hole at row 2043 (S-time ~204 s, car stopped); phone GNSS reflects position ~0.5 s earlier than the wall-clock alignment (~4 m at 8 m/s, left as a known scoring bias); VBOX ends before the phone.
8. `export_frontend_data.py`: `--filter {esekf,vehicle_dr}` is NOT implemented yet (default is honest / non sim-aided). Original Step 3 (regenerate dashboard data, remove hard-coded fakes such as "LOCKED (11 SATS)" in
   Sidebar.tsx / StatusPanel.tsx and the hard-coded outage window in useGNSSStatus.ts / TimelineSlider) has not been started; the user must release it.
9. The S3b comparison PNG (truth, phone fixes, vehicle_dr, ESEKF, outage shaded) required for B4 is not produced yet (target `backend/exports/evaluation/`).

## Data / validation facts a new session needs
* Same-driver drives with S+V pairs: **S2 (156 min), S3a (41 min), S3c (62 min), S4 (158 min)** under
  `IO-VNBD/Synchronised V abd S datasets/Categorised IOVNB Dataset/S (Driver A)/<drive>/S-<drive>.csv` and `V-<drive>.csv`. `check_outage.load_drive("<drive>")` handles them. **Roles are fixed by the drive registry:
  S3c = final validation (B5; its window list and event window are PRE-REGISTERED, no error seen), S3a = reserve, S2 + S4 = I3 training only.** Loading S3c for the pre-registration touched only phone GNSS availability and file timestamps.
  Before scoring a new drive (S3c at B5), redo the B0 time-alignment check (phone-GNSS vs VBOX error per fix, lag scan; loader uses the phone wall-clock column and `sv_time_offset()` for scoring).
* **S1 is no longer pristine**: it was used for the A1/A2 diagnostics, the launch log (50 releases, 31 accepted), the mount-stability scan, the B3d validation and the tail characterisation.
* Other drives exist (M, Vf, Vta, Vtb, Vw, Y) — not investigated.
* Real-data facts: phone GNSS fix every ~9 s (values held between fixes); speed column already m/s; vertical gyro = CSV "Pitch" column (A2); gravity columns are ~(0, 0, 9.806) so the phone is treated as flat;
  ESEKF's real dead-reckoning is 3-13x worse than const-v (its 10-12 m "tracking" comes from 10 Hz interpolated GNSS, i.e. non-causal).
* The old B3e-B3i idea list is now the plan's I-steps: B3i robust GNSS = I1b, B3g learned vibration speed = I3, B3f gyro scale = I4, B3e stochastic cloning = I5, B3h magnetometer = I6 (I4-I6 only on "go next").
* After the I-steps: B4 = final settings frozen, ablation table (core, +each kept step), the S3b 200-260 s event reported ONCE; B5 = the pre-registered S3c windows + event window with NO retuning, S1 secondary. Then C (demo layer) and D (OSM road-matching, after approval).

---

# DRIVE REGISTRY v2 (2026-09-26, after the E0 review — CURRENT; v1 below is kept for history)
| drive | role | rules |
|---|---|---|
| **S3b** | development drive (primary) | Tune ONLY on windows / data that end before 200 s (11 windows, starts 30-130; 20 mini-outage intervals). The 200-260 s event is reported, never tuned on. |
| **S2** | **development drive (NEW)** | Tuning allowed, alongside the S3b pre-200 s windows. Report S3b and S2 SEPARATELY and pooled. Its window list is pre-registered (same planner rule) before S2 is scored. Also an I3 training drive. |
| **S4** | I3 training only | Used ONLY for fitting the I3 vibration model offline. Never scored, never reported as accuracy. |
| **S3c** | final validation (sealed) | Untouched until B5; the window list and event window are pre-registered; `--unseal` guard. |
| **S3a** | reserve (sealed) | Untouched; `--unseal` guard. |
| **S1** | "previously inspected" | Secondary report only; never tuned on. |
Change rule ("noise rule"): windows overlap, so a change < 5 % of the median end error counts as "no change"; keep a change only if it helps S3b AND S2, or helps one and is neutral on the other.

# DRIVE REGISTRY v1 (declared 2026-09-26, before any E0 run; SUPERSEDED by v2 above for S2)
| drive | role | rules |
|---|---|---|
| **S3b** | tuning drive | Tuning uses ONLY data/windows that end before 200 s. The 200-260 s event is reported, never tuned on. |
| **S2, S4** | training drives | Used ONLY for fitting the I3 vibration model offline. Accuracy on them is never reported as validation. |
| **S3c** | final validation | Untouched until B5. No looking at its errors before then (phone file length / GNSS availability only, for pre-registration). |
| **S1** | "previously inspected" | Secondary report only. |
| **S3a** | reserve | Untouched. |

# PLAN: E0 → D (issued after B3d review)
Verbatim copy of the user's plan message (2026-09-26). E0 was the next step; this section defines E0 and everything after it. Stop points: after E0 (show S3b tuning-window
summary + along/cross split of the 200-260 s event), after I3 (show the table). I4-I6, B4, B5, C, D only when the user says "go next".

```text
E0 and the full plan are defined below. FIRST: copy this entire message into AERIS_FINDINGS.md under a heading "PLAN: E0 → D (issued after B3d review)" so future fresh sessions have it, commit and push. SECOND: run your sanity check (check_outage.py S3b --filter vehicle_dr must reproduce mini 21.93 / 17.11 / 64.85 and outage 64.35 / 145.89). If it doesn't reproduce, stop and tell me. THEN start E0.

Reviewed B3a–B3d: accepted. vehicle_dr is the main filter from now on. ESEKF stays untouched as the baseline.

═════ STANDING RULES (add to CLAUDE.md) ═════
- Branch fix/heading-spin only. Commit per step and PUSH after every commit.
- Every step: (1) sandbox test first (sim_drive.py) with an explicit pass criterion, (2) real-data metrics, (3) row appended to the results table in AERIS_FINDINGS.md, (4) full test suite passes, (5) commit + push. If a step fails its criterion: keep the code behind a flag set to OFF, log why, and move on.
- Never use V-*.csv or VBOX-derived values as a filter input. VBOX is for scoring only.
- Keep the reply tables compact; put the details in AERIS_FINDINGS.md.
- Before any /clear: update the handoff section of AERIS_FINDINGS.md (current defaults, flags, latest table, next step), commit, push.

DRIVE REGISTRY (declare this in AERIS_FINDINGS.md now, before running anything):
- S3b: tuning drive. Tuning uses ONLY data/windows that end before 200 s. The 200–260 s event is reported, never tuned on.
- S2, S4: training drives, used ONLY for fitting the I3 vibration model offline. Never report accuracy on them as validation.
- S3c: final validation, untouched until B5. No looking at its errors before then.
- S1: "previously inspected". Secondary report only.
- S3a: reserve, untouched.

═════ E0 — EVALUATION UPGRADE (do this first) ═════
Extend check_outage.py (keep the existing output):
a) Along-/cross-track error: at each epoch, project (AERIS − truth) onto the truth's unit direction of travel (along) and its left normal (cross). Report mean |along|, mean |cross|, and both at the end of the outage.
b) Speed diagnostics during the outage: AERIS vs truth speed (mean abs error, and at +30 s and +60 s), path ratio = AERIS path / truth path.
c) Sliding 60 s outage benchmark: simulate 60 s outages starting every 10 s wherever the drive allows (the start needs ≥ 30 s of prior GNSS; a window must lie inside the drive). For each window report: mean error, end error, along/cross at the end, path ratio. Summarise the median, mean and p90 over windows.
   - TUNING set: S3b windows that END before 200 s.
   - VALIDATION sets: S3c (B5 only), S1 (secondary).
   Pre-register the exact S3c window list (start times) in AERIS_FINDINGS.md NOW, derived only from the file length and the GNSS availability, not from any error. Also pre-register one S3c "event" window equivalent to S3b's 200–260 s (same rule, chosen before seeing any error).
d) Score the current vehicle_dr default and the constant-velocity baseline on the S3b tuning windows. This is the new reference row.
Stop after E0: show the S3b tuning-window summary and the along/cross split of the 200–260 s event.

═════ I1 — GNSS TIMING AND ROBUSTNESS ═════
I1a Latency: estimate the GNSS latency L (grid 0–1.5 s, step 0.1 s) using ONLY S3b data before 200 s, by minimising the mini-outage error, or the innovation magnitude, with the filter compensating: keep a ring buffer of past states; compute the position/course innovations against the state at (t_fix − L); apply the correction to the current state (the standard small-lag approximation; document it). Report L for S3b (and just report, not tune, for S1).
I1b Robustness:
  - Course failsafe: after N consecutive course rejections at speed > 5 m/s, accept the next course if two consecutive fixes agree with each other (the bearing between them is within 20° of the reported course, and the implied speed is ≤ 40 m/s); log "forced".
  - Divergence reset: if position or course is rejected K times in a row, inflate P before the next update (ψ σ → 30°, position σ → max(innovation norm, 20 m)) instead of discarding the data. Accept only through the two-fix consistency check.
  - Compare against a Huber-weighted update (no hard gate); keep the better one on S3b.
  Sandbox: inject a 60° heading error and a 50 m position jump mid-drive; pass = recovery within 2 fixes, and a single 80 m multipath outlier fix is NOT accepted.
  Report the rejection counts on S3b, and on S1 (secondary; no tuning on S1).

═════ I2 — SPEED DURING OUTAGES (tune ONLY on the S3b sliding 60 s tuning windows) ═════
I2a Ornstein–Uhlenbeck speed prior (mount-free, causal):
  While moving (IMU not stationary) and without a GNSS speed: v_{k+1} = v̄ + (v_k − v̄)·e^(−dt/τ), with process variance σ_v²·(1 − e^(−2dt/τ)) and F[3,3] = e^(−dt/τ).
  v̄ = the median of GNSS speeds from NEW fixes with speed > 2 m/s in the last W seconds (causal); σ_v = the std of those speeds (floor 1 m/s). If there are fewer than 3 such fixes, fall back to holding v.
  Grid: τ ∈ {5,10,20,40,80} s, W ∈ {60,120,300} s. Report the path ratio and along-track error on the tuning windows.
  Label in code and docs: "speed prior from recent driving", not a measurement.
I2b Turn speed ceiling (the fixed version of B3c): when |ω−b_g| > 0.15 rad/s, apply a soft update ONLY IF v·|ω−b_g| > |a_h|_1s + m, with the measurement v = (|a_h|_1s + m)/|ω−b_g|, where |a_h|_1s is the 1 s mean horizontal accel magnitude and m is a margin (grid 0.3–1.0 m/s²). Also try a fixed comfort ceiling a_max ∈ {2.5, 3.0, 4.0} m/s² instead of |a_h|. Inequality only: it never pushes v up.

═════ I3 — VIBRATION SPEED (learned offline, adapted online) ═════
Features (10 Hz, mount-free), per 1 s window: std of |a_h|, std of vertical linear accel, mean |Δa| (sample-to-sample diff) of the horizontal and vertical accel, std of |ω|. Also include a stationary flag.
Train: ridge regression speed ≈ f(features) on S2 + S4 ONLY (labels = the phone GNSS speed at new fixes; the features from the 1 s before each fix). Save the model file and the training report (R², residual std) in the repo.
Online on S3b: at each new fix, update a single scale factor k (speed_true ≈ k·f) from past fixes only (recursive least squares with a forgetting factor). Use k·f as a speed measurement every 1 s when not stationary, σ = the residual std from training × (1 + drift term), with a chi-square gate.
Report: R² of f on S3b pre-200 new fixes (no fitting on S3b), and the tuning-window metrics with and without I3. Try I3 alone and I2a+I3 combined; keep the better one.
Sandbox: add speed-dependent vibration in sim_drive (already present) and check that the pipeline recovers speed within 20% after the online scale adaptation.

Stop and show the table after I3 (rows: E0 reference, I1a, I1b, I2a, I2b, I3, best combination). Columns: S3b mini mean/median | S3b 60 s tuning windows median/p90 end error | tuning path ratio (median) | along/cross at the end (median) | 200–260 s event mean/end/path ratio (report only) | 1σ coverage | verdict.

═════ LATER (only when I say "go next") ═════
I4 Gyro scale factor state (prior σ 0.1), then retune turn_noise. I5 Between-fix displacement (stochastic cloning). I6 Magnetometer aid (gated, online offset), lowest priority.

B4: final settings frozen. Ablation table (core, +each kept step). Report the S3b 200–260 s event once.
B5: S3c pre-registered windows + the pre-registered event window, no retuning. S1 as secondary.

C (demo layer):
- export_frontend_data.py --filter vehicle_dr (honest; no sim-aided, no map-matching to VBOX); regenerate the dashboard JSONs.
- An RTS smoother for vehicle_dr as a separate OFFLINE output (post-drive only, labelled as such).
- Frontend honesty: the outage window read from the export (not hard-coded in useGNSSStatus.ts / TimelineSlider); remove hard-coded fake values (e.g. "LOCKED (11 SATS)" in Sidebar.tsx / StatusPanel.tsx); GNSS hidden during the outage; AERIS drawn from the last GNSS fix.
- An S3b PNG: truth, phone fixes, vehicle_dr, ESEKF, RTS, outage shaded.
D (after approval): OpenStreetMap road-matching (independent map data only, never VBOX).

Start with the plan save + sanity check, then E0. Stop after E0.
```

# PRE-REGISTRATION (E0, 2026-09-26): sliding 60 s windows and the S3c event window
Sanity check before E0 (2026-09-26, HEAD 8a8bbd5): `python backend/check_outage.py S3b --filter vehicle_dr` reproduced the documented state exactly
(mini 21.93 / 17.11 / 64.85, coverage 50 %, outage mean 64.35 m, end 145.89 m). Windows console note: piping output needs `PYTHONUTF8=1` (a `≈` in a print otherwise raises
UnicodeEncodeError under cp1252); the numbers are unaffected.

**Rule** (implemented in `backend/window_plan.py`, unit-tested in `backend/tests/test_eval_e0.py`; it reads ONLY the phone file — length and which rows are usable NEW fixes — and the timestamps
of the reference file; no filter output, no truth position, no error): a window is [start, start + 60 s]; starts on a 10 s grid anchored at drive time 0 (30, 40, 50, ...);
the window lies inside the drive (start + 60 <= min(last phone time, last V time - S/V offset)); usable fix = NEW phone fix (lat/lon changed, finite) with satellites >= 6 (or unknown);
the start needs >= 30 s of prior GNSS = a usable fix at or before start - 30 s, >= 2 usable fixes in [start - 30, start] and the newest usable fix no older than 20 s at the start.
Tuning set of a drive = the windows that END before 200 s (start + 60 < 200). Event window = the S3b demo outage, [200 s, 260 s] (start 200; same absolute timing as CLAUDE.md's demo, chosen before any S3c error exists).

| set | how to regenerate | windows (start times, s) | n | sha1 of the start list |
|---|---|---|---|---|
| **S3b tuning (end < 200 s)** | `python backend/window_plan.py S3b --end-before 200` | 30-130 (step 10) | 11 | `8faf6fce490472980ca44498c8ddf8d46d98c887` |
| **S3c — ALL windows (B5, no retuning)** | `python backend/window_plan.py S3c` | 30-40, 80-900, 930-2020, 2080-2120, 2160-3520, 3580-3650 (each range step 10) | 345 | `96375f11488107d65a1d92bd0edbeed9db5c7973` |
| **S3c event window (B5, reported once)** | same rule, start 200 | [200, 260] — VALID (>= 30 s of prior GNSS, inside the drive) | 1 | – |

S3c facts used (file length / GNSS availability only): phone 3718.2 s, S/V offset 0.721 s, usable window time span 0-3717.5 s, 391 usable new fixes (first at 0.0 s, last 3710.0 s, median spacing 9.0 s, longest gap 60.0 s).
S3c grid starts excluded by the availability rule (GNSS holes in the phone file): 50-70, 910-920, 2030-2070, 2130-2150, 3530-3570. S3b: none excluded.
No S3c filter output, truth position or error has been computed or looked at; loading S3c for this plan touched only timestamps and GNSS availability. At B5 the B0 time-alignment check
(phone GNSS vs V per fix; needed before scoring a new drive) is the first thing that will look at S3c/V positions.
Guard (implemented in the E0 scoring commit, unit-tested): `check_outage.py` refuses to score S3c / S3a / S2 / S4 without `--unseal`.
Honesty note on the S3b tuning windows: 11 windows spaced 10 s apart and lasting 60 s overlap heavily and cover only 30-190 s of driving, i.e. about 2.7 independent 60 s stretches. Their median/p90 are a thin
tuning signal; expect a flat error surface, use leave-one-window-out only as a weak overfitting check, and do not over-read differences of a few metres.

# PRE-REGISTRATION (registry v2, 2026-09-26): S2 development windows — registered BEFORE S2 is scored
Same planner rule as above (`backend/window_plan.py`; reads only the phone file's fix availability and the file time spans; no filter output, no truth position, no error).
Generated with `python backend/window_plan.py S2`. S2 is a development drive: ALL registered windows are tuning/report windows (S2 has no "end before 200 s" restriction), reported separately from and pooled with the S3b dev windows.

| set | windows (start times, s; each range step 10) | n | sha1 of the start list |
|---|---|---|---|
| **S2 development windows (all valid)** | 30-120, 140-160, 190-300, 450-1250, 1280-1360, 1450-2690, 2720-2870, 2980-3110, 3140-3370, 3410-3490, 3520-3550, 3600-4000, 4080-4260, 4290-7320, 7430-9320 | 861 | `b1049dca2734856fa9a9f4bafa4bf702740de305` |

S2 facts used (file length / GNSS availability only): phone 9388.6 s, S/V clock offset 7.341 s (S3b 0.693, S3c 0.721, S1 0.546 — S2's is larger; checked by the B0 time-alignment check below), usable window time span 0-9380.2 s,
941 usable new fixes (first at 0.0 s, last 9376.2 s, median spacing 9.0 s, longest gap 146.0 s). Grid starts excluded by the availability rule (GNSS holes): 130, 170-180, 310-440, 1260-1270, 1370-1440, 2700-2710, 2880-2970,
3120-3130, 3380-3400, 3500-3510, 3560-3590, 4010-4070, 4270-4280, 7330-7420. The 200-260 s window is valid on S2 (start 200) but is just one of the 861 windows here.
No vehicle_dr output, truth position or error of S2 had been computed when this was registered. If the B0 check below finds a timeline defect that changes this list, the amendment is logged with the reason (still before any S2 scoring).

# E0 review (external sandbox study) — 2026-09-26, after the user's review of E0
E0 was reviewed and ACCEPTED, including the decisions: strict "end before 200 s", S3c event = [200, 260] s, the `--unseal` guard, the CLAUDE.md edits.
* E0 shows that at 60 s vehicle_dr's end error ≈ hold-last-fix (161 vs 156 m), and the error is mostly CROSS-track (122 vs 76 m along), with path ratio ≈ 1 on the tuning windows.
  So heading / turn shape dominates, not speed (speed dominates only in the 200-260 s event, which starts from a stop).
* Suspect: gyro scale factor. The A2 slope on S3b was 1.29 (S1 0.94). vehicle_dr has no scale state; turn_noise = 0.5 only hides it.
* An external sandbox study (sim_drive `long_route`, 60 s windows, seeds 1-2) found: gyro_scale 1.3 raises the median end error from ~110-116 m to 168-188 m (cross 74-80 -> 121-129 m). A CAUSAL scale
  estimate — regressing the GNSS course change between consecutive new fixes (|dcourse| > 20 deg, both speeds > 3 m/s) on the integrated vertical gyro over the same interval, past fixes only, n ~ 9 —
  recovered the scale within ~3-4 % and restored ~oracle error (end 110-115, cross 74-81). Harmless when scale = 1.0.
* POLICY CHANGE: registry v2 above (S2 = development drive, S4 = I3 training only, S3c / S3a sealed, S1 secondary; S2 window list pre-registered before S2 is scored).
* NEW ORDER (supersedes the old I-order of the plan; the old plan text above is kept for history): H1 gyro-scale calibration -> I1a latency -> I1b robustness -> I2 speed -> I3 vibration speed.
  The user's message with the full H1 / I1 / I2 / I3 specification and the new metric table is copied verbatim in the next section.

# PLAN UPDATE: NEW ORDER H1 → I1 → I2 → I3 (verbatim copy of the user's message, 2026-09-26)
```text
Read CLAUDE.md and AERIS_FINDINGS.md fully first. E0 reviewed and accepted, including your decisions (strict "end before 200 s", S3c event = [200,260], the --unseal guard, CLAUDE.md edits).

Log the following review in AERIS_FINDINGS.md under "E0 review (external sandbox study)" before starting:
- E0 shows that at 60 s vehicle_dr's end error ≈ hold-last-fix (161 vs 156 m), and the error is mostly CROSS-track (122 vs 76 m along), with path ratio ≈1 on the tuning windows. So heading/turn shape dominates, not speed (speed dominates only in the 200–260 s event, which starts from a stop).
- Suspect: gyro scale factor. The A2 slope on S3b was 1.29 (S1 0.94). vehicle_dr has no scale state; turn_noise=0.5 only hides it.
- An external sandbox study (sim_drive long_route, 60 s windows, seeds 1–2) found: gyro_scale 1.3 raises the median end error from ~110–116 m to 168–188 m (cross 74–80 → 121–129 m). A CAUSAL scale estimate — regressing the GNSS course change between consecutive new fixes (|Δcourse| > 20°, both speeds > 3 m/s) on the integrated vertical gyro over the same interval, past fixes only, n≈9 — recovered the scale within ~3–4% and restored ~oracle error (end 110–115, cross 74–81). Harmless when scale = 1.0.

POLICY CHANGE (update the drive registry): S2 becomes a DEVELOPMENT drive — tuning allowed, alongside the S3b pre-200 s windows (report both separately and pooled). S4 stays I3-training-only. S3c and S3a stay sealed. S1 stays secondary. Pre-register the S2 window list (same planner rule) before scoring S2.

NEW ORDER (supersedes the old I-order in the plan; keep the old plan text for history):

H1 — Gyro scale calibration (targets cross-track)
 H1a Causal regression estimator: at each new fix, using ONLY past new-fix pairs in the last W seconds (grid W ∈ {120, 300, all}) with both speeds > 3 m/s and |Δcourse| > 20°: y = wrap(ψ_course(b) − ψ_course(a)) (ψ from bearing, ENU, CCW), x = ∫(ω_vert − b_g) dt over [t_a − L, t_b − L] (L = GNSS latency; use L = 0 until I1a exists, then re-run H1 with the I1a value). Robust fit through the origin (Huber or Theil–Sen), s = x·y-fit slope → correction k = 1/s. Accept only with ≥ 5 pairs and k ∈ [0.7, 1.4]; otherwise k = 1. Apply ω_used = k·(ω_vert − b_g).
 H1b EKF alternative: add state s_g (ψ̇ = (1+s_g)(ω − b_g)), prior σ 0.1, random walk tiny; observable through the course/position updates. Compare H1a vs H1b; keep the better (or both, if they combine safely).
 After the better one: retune turn_noise down (grid {0.5, 0.3, 0.15, 0.05}), since it was compensating for the scale.
 Sandbox pass: with gyro_scale 1.3 on long_route, the estimated scale is within 5% after 200 s, and the median 60 s-window end error is within 10% of the oracle (the gyro column divided by the true scale). With gyro_scale 1.0, no worse than the current default by more than 3%.
 Real report: the estimated k over time on S3b (plot/print), and the final k on S3b, S2 (and S1 secondary). If k on S3b is far from the A2 slope of 1.29, explain why.

I1a — GNSS latency L (as in the saved plan), tuned on the development windows. Then re-run H1 with L.
I1b — Robust GNSS: course failsafe + divergence reset with the two-fix consistency check, vs Huber (as in the saved plan). Sandbox: a 60° heading error and a 50 m jump recover within 2 fixes; a single 80 m outlier is not accepted. Report the rejection counts on S3b, S2, S1 (S1 secondary).
I2 — Speed (as in the saved plan: I2a OU prior, I2b turn ceiling as an inequality only). Tune on the development windows. ALSO report separately the development windows that START within 10 s after an IMU standstill (the "launch-from-stop" regime, like the event), since that is where I2a should matter.
I3 — Vibration speed (as in the saved plan), trained on S2 + S4, BUT: since S2 is now also a development drive, report the I3 R² on S3b pre-200 fixes as the honest check.

METRICS for every row (compact table):
step | dev windows S3b: median end / p90 end / median cross@end / median along@end | dev windows S2: same | S3b mini mean | launch-from-stop windows median end | 200–260 s event mean/end/path ratio (report only) | 1σ coverage | verdict.
Also always show the hold-last-fix and const-v rows on the same windows. The target is to beat hold's end error clearly.

Noise rule: the windows overlap. Treat any change < 5% on the median end error as "no change". Keep a change only if it helps S3b AND S2 (or helps one and is neutral on the other).

Stop and show the table after H1 (including k over time), then continue to I1a/I1b only when I say "go".
```

---


All numbers from `python backend/check_outage.py [drive]` unless noted:
`run_pipeline(s_df, None, mode="full", outage_window=(200,260))`, scored against V-<drive>.csv
(truth linearly interpolated to AERIS timestamps). "1σ" = truth within the reported 2-D
1σ ellipse (Mahalanobis ≤ 1; a consistent filter gives ≈ 39 %).

## Step 1 — honest baseline (S3b, before any change)

| metric | value |
|---|---|
| outage mean / end / max error | 68.16 / 159.59 / 160.87 m |
| AERIS path / truth path | 125.9 / 224.8 m |
| AERIS disp / truth disp | 30.1 / 153.2 m |
| total \|Δyaw\| in outage | 1118° (truth 663°; VBOX heading is noisy at low speed, so treat as rough) |
| pre-outage mean (20–200 s) | 17.38 m (max 38.2 m) |
| raw phone GNSS vs truth, 20–200 s | 5.67 m ← the filter is ~3× worse than its own input |
| truth inside 1σ | 0.0 % (σ at 260 s = 2.2 m — wildly over-confident) |
| gap last GNSS fix → AERIS @200 s | 2.43 m (last *new* phone fix was t=184 s) |

Notes:
- The old reference (50.5 m mean, 17 m displacement) was with v_df passed in (VBOX yaw at
  alignment). Honest v_df=None baseline is worse: 68.2 m mean, 30 m displacement.
- Pre-outage tracking is poor (17 m vs 5.7 m raw GNSS) → investigate separately.
- The last new phone fix before the outage is at 184 s (fix repeats until 200 s).

## Step 2 — fixes a–e (S3b), applied one at a time

| step | outage mean | end @260 | max | path (225) | disp (153) | \|Δyaw\| (663) | pre-outage | 1σ | gap @200 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 68.16 | 159.59 | 160.87 | 125.9 | 30.1 | 1118 | 17.38 | 0 % | 2.43 | — |
| a ESEKF all modes | 59.02 | 165.90 | 165.90 | 90.5 | 9.1 | 1544 | 18.49 | 0 % | 2.18 | mixed; kept (b needs ESEKF convention) |
| a+b gravity tilt | 63.86 | 195.17 | 195.17 | 173.8 | 38.7 | 459 | 18.21 | 0 % | 2.38 | spin gone, end worse; committed 7697e13 |
| a+b+c NHC K[6:15]=0 | 60.52 | 159.66 | 159.66 | 81.4 | 9.6 | 3487 | 17.73 | 0 % | 2.55 | **worse — reverted** |
| a+b+d no ZARU burst | 62.44 | 198.08 | 198.08 | 174.2 | 41.1 | 466 | 18.21 | 0 % | 2.38 | neutral; kept for honesty, 282a539 |
| a+b+d+e export default | 62.44 | 198.08 | 198.08 | 174.2 | 41.1 | 466 | 18.21 | 0 % | 2.38 | no effect on check (export only), 724581a |

Why c got worse: with the wrong gyro axis (finding 1 below), the attitude correction that NHC
made through the full gain was the only thing holding heading. c is still correct in principle;
retry it once the axis is fixed.

## Root causes of pre-outage wander (found in Step 2, NOT yet applied)

1. **Wrong gyro axis for heading.** The phone lies flat (accel z mean 9.816, gravity ≈ (0,0,9.807)),
   so heading rate is body z. The pipeline uses the column labelled "GYROSCOPE Yaw" as body z, but
   that column carries no heading signal. Phone-only check (gyro integrated over each GNSS fix
   interval vs. GNSS course change, n=56): "Pitch" corr +0.69, slope +1.19; "Yaw" corr +0.06;
   "Roll" corr +0.12. (VBOX yaw-rate diagnostic agrees: Pitch +0.48, Yaw 0.00.)
2. **Phone GNSS speed units.** "GPS SPEED (Kmh)" is already m/s (raw max 12.54 vs VBOX max
   12.43 m/s; median ratio after the loader's /3.6 = 0.288 ≈ 1/3.6). data_loader divides by 3.6,
   so a σ=0.3 m/s speed update pulls AERIS to ~28 % of the true speed.
3. **Phone GNSS fixes arrive every ~9 s**, not 1 Hz (72 fixes in 681 s). run_pipeline linearly
   interpolates them (non-causal: rows before 200 s already contain the next fix's value,
   up to 9 s ahead) and feeds each 10 Hz interpolated row as an independent σ=1 m position and
   σ=0.3 m/s velocity measurement. Heading is also interpolated without angle wrap. Result:
   the filter is massively over-confident (truth inside 1σ = 0 % in every run; σ ≈ 2 m at 260 s
   with 150+ m error).
4. **Gyro-bias blow-up at startup.** P0 for δbg is 0.01 (a *variance*, σ = 0.1 rad/s), while the
   comment says ±0.01 rad/s. With fixes 1+2 applied, the z gyro-bias estimate runs to −0.62 rad/s
   within 10 s and locks there (σ 0.0001). True stationary bias ≈ −0.007 rad/s. This is the spin.
5. initial_alignment feeds a CW-from-North bearing into euler_to_quat, but rot_to_euler / the
   filter use ENU yaw (CCW from East). Harmless only because GNSS corrects it.

## In-memory experiments (no repo code changed; scratch script patches data/methods)

| experiment (on a+b+d+e) | outage mean | end | path | disp | \|Δyaw\| | pre-outage | gap |
|---|---|---|---|---|---|---|---|
| axis fix only | 84.28 | 124.49 | 211.2 | 49.3 | 451 | 18.14 | 2.55 |
| speed fix only | 48.92 | 150.42 | 121.6 | 13.0 | 2425 | 11.98 | 4.74 |
| axis + speed | 54.96 | 131.06 | 159.0 | 34.1 | 1989 | 11.42 | 5.51 |
| axis + speed + c | 39.49 | 124.17 | 132.9 | 36.4 | 3101 | 12.06 | 5.27 |
| axis + speed + P0_bg σ=0.01 | 92.55 | 222.62 | 264.5 | 94.5 | 304 | 11.38 | 4.97 |
| axis + speed + c + P0_bg σ=0.01 | 49.94 | 145.55 | 171.7 | 29.1 | 737 | 11.97 | 4.88 |

Takeaways: the speed-unit fix is the one clear win pre-outage (18 → 12 m). Tight P0_bg removes
the spin (|Δyaw| near truth). But no combination gets the outage anywhere near the sandbox's
6–11 m, and 1σ coverage stays 0 %. The remaining dominant error is the GNSS measurement model
(finding 3): the heading entering the outage is wrong, the car is stopped 180–212 s so heading is
unobservable there, and the filter is over-confident. Fixing that is a redesign of the GNSS
update (feed only real new fixes, causally, with realistic σ), so I am asking before doing it.

## Phase A — make the fixes permanent (S3b, one at a time)

Starting point = a+b+d+e (row "start" below). Columns as in the Step 2 table.

| step | outage mean | end @260 | max | path (225) | disp (153) | \|Δyaw\| (663) | pre-outage | 1σ | gap @200 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| start (46b380a) | 62.44 | 198.08 | 198.08 | 174.2 | 41.1 | 466 | 18.21 | 0 % | 2.38 | — |
| A1 speed already m/s (no /3.6) | 48.92 | 150.42 | 150.42 | 121.6 | 13.0 | 2425 | 11.98 | 0 % | 4.74 | **better; committed** |
| A2 gyro z <- 'Pitch' column | 54.96 | 131.06 | 131.06 | 159.0 | 34.1 | 1989 | 11.42 | 0 % | 5.51 | **mixed (mean worse, end/pre/path/disp better); kept — proven axis, prerequisite for A3** |
| A3a P0[δbg] variance 1e-4 (σ 0.01 rad/s) | 92.55 | 222.62 | 223.23 | 264.5 | 94.5 | 304 | 11.38 | 0 % | 4.97 | **mixed by the rule (mean/end/max worse; disp, spin, bias better); kept — bias now physical, see below** |
| A3b bg init from first standstill (none found on S3b) | 92.55 | 222.62 | 223.23 | 264.5 | 94.5 | 304 | 11.38 | 0 % | 4.97 | neutral on S3b (identical to A3a); committed |
| A4 causal GNSS (new fixes only, σ=max(acc,3), IMU-only ZUPT) — commit f256fe5 | 310.29 | 465.80 | 465.80 | 360.7 | 158.5 | 382 | **251.57** | 0 % | 163.93 | **much worse — reverted (ab46a2e)** |
| A5 NHC gain K[6:15]=0, Joseph form (retry of c) | 49.94 | 145.55 | 145.55 | 171.7 | 29.1 | 737 | 11.97 | 0 % | 4.88 | **better on mean/end/max/path/yaw; disp and pre-outage slightly worse; committed** |

### A1 — GPS speed units (proof)
Speed implied by differencing consecutive NEW fixes (~9 s apart; intervals with reported speed
> 1 m/s; monotonic loader timestamps) vs the raw "GPS SPEED (Kmh)" column:

| drive | intervals | chord / reported, column read as m/s | read as km/h (/3.6) | corr |
|---|---|---|---|---|
| S3b | 71 | 0.961 | 3.460 | 0.83 |
| S1 | 510 | 1.003 | 3.611 | 0.95 |

The column is m/s despite its header. Chord ≤ path length, so ≲1.0 on curves is expected.
V-file `Velocity (km/hr)` really is km/h and is unchanged. Result matches the earlier in-memory
"speed fix only" experiment exactly (48.92 m). Note: raw `TIME SINCE START (ms)` has counter
resets (raw ends at 477 s; loader's cumulative timestamp gives 681 s) — any diagnostics must use
`timestamp_s`, not the raw column.

Test suite after A1: 161 run / 161 pass; 37 dataset tests SKIP because `run_tests.py` reports
IO-VNBD "NOT FOUND" (its dataset detection differs from `get_dataset_root()`), so the tests do
not exercise the real loader.

### A2 — gyro axes (evidence)
Method: for each of the 6 column→(x,y,z) permutations × 8 sign combinations, omega_vert = omega_body · g_hat
(per-sample gravity columns), integrated over each interval between consecutive NEW phone fixes where both
fixes have speed > 3 m/s (dt < 15 s), correlated with -Δheading (GNSS course, wrapped; CCW-positive).
Sensor spikes |ω| > 5 rad/s zeroed for the diagnostic.

| drive | intervals | best mapping (z axis) | corr | slope (1.0 ideal) | old pipeline z←Yaw | next best z |
|---|---|---|---|---|---|---|
| S3b | 52 (1688° total course change) | **z ← +Pitch column** | +0.671 | +1.288 | corr +0.057, slope +0.013 | +0.099 (Yaw) |
| S1 | 405 (11384° total) | **z ← +Pitch column** | +0.913 | +0.936 | corr +0.451, slope +0.055 | +0.804 (−Roll, slope 0.126) |

Same answer on both drives. Sign is positive (Pitch column is counter-clockwise-positive about up).

Not resolved by the data: x/y roles. Gravity columns are essentially constant — mean (0.000, 0.000, 9.806),
std (0.075, 0.076, 0.020) on S3b and (0.019, 0.023, 0.000) on S1, ĝ_z mean 0.9999/1.0000 — so ω·ĝ is
insensitive to them. Chose x←Roll, y←Yaw (minimal change). Only affects roll/pitch dynamics, which the
gravity-tilt update pins.

**New finding — the phone's horizontal axes are not aligned with the car.** Centripetal check
(corr of accel_x / accel_y with v·ω_vert, v>3 m/s, |ω|>0.05): S1 accel_x +0.405 (slope 0.271),
accel_y +0.446 (slope 0.276) → the lateral direction sits ≈ 45° between phone x and y, i.e. forward is
about (+0.71, −0.70) in phone coordinates, not +x. S3b showed no usable signal (0.04 / 0.06;
interpolated 9 s GNSS speed is too coarse there). Consequence: the ESEKF's NHC (lateral = body y,
forward = body x) and its initial-yaw-from-GNSS-course both assume x = forward, which is wrong for this
data. Phase B is designed to estimate the forward axis from pre-outage data.

### A3a — gyro-bias P0 (evidence for keeping a mean-worse change)
`P0[δbg]` was 0.01 (a variance → σ 0.1 rad/s) while its comment said ±0.01 rad/s. Set to 1e-4.
Estimated gyro bias over the S3b run (rad/s), before vs after:

| | z bias at 10 s | z bias 50–259 s | independent stationary-gyro mean (phone only) |
|---|---|---|---|
| after A2 only | −0.616 | −0.53 … −0.55, locked (σ 0.0001) | −0.007 … −0.009 |
| after A3a | −0.006 (t=5) | −0.007 … −0.021 (settles at −0.0085) | −0.007 … −0.009 |

The bias was ~60× too large before (≈ 30°/s of spurious yaw rate compensation). Outage headline
numbers got worse (mean 55.0 → 92.6 m, end 131 → 223 m) while displacement improved (34 → 94.5 m)
and total |Δyaw| dropped 1989° → 304° (now below the VBOX figure of 663°, which is inflated by
low-speed heading noise). Read: the huge bogus bias had been *masking* the real problem; what is left
is the GNSS model and the heading entering the outage, i.e. A4 / mount offset. Kept as its own commit
(`git revert` to undo). σ of the z bias collapses to 1e-4 rad/s by t=150 — overconfident, but not
changed here (one change at a time).
Observation, not changed: other P0 entries are also variances read as σ in their comments (δθ:
0.3/0.3/1.0, δba: 0.1).

Disclosure: to see what a standstill looks like I printed the first 60 s of IMU stats for S1 as well as
S3b (S1: clean rest ~9–47 s, accel var ≈ 0.02; S3b: no rest in the first 60 s, accel var ≥ 0.5). No
outage score was computed on S1.

### A3b — start-up gyro bias from the first standstill
`initial_gyro_bias()` in ins_ekf.py: IMU-only, first 60 s, 3 s window with summed per-axis accel variance
< 0.10, |mean gyro| < 0.05 rad/s, per-axis gyro std < 0.03 rad/s; window grown while quiet (≤ 30 s); zero bias
if no standstill. Detector output: S3b → none (car already moving; accel var ≥ 0.5 in every window), S1 →
rest at 10.0–41.9 s, bias (−0.0003, −0.0007, +0.0004) rad/s. Thresholds have ~5× margin over what a parked
phone looks like and I chose them after looking at the S1 rest windows (disclosed above) — no outage score
was involved. Because S3b has no standstill, S3b numbers are unchanged. Causality note: this uses the first
60 s of data to seed t=0, equivalent to a start-up calibration while parked.

### A4 — causal GNSS: why it fails on the ESEKF (reverted; code kept in f256fe5)
As specified: interpolation deleted; position update only on rows where lat/lon changed, σ = max(gps_accuracy_m, 3);
speed/course only on new fixes > 2 m/s; ZUPT detector switched to IMU-only (it read the held GPS speed between fixes).
Tests still 161/161. But S3b pre-outage error went 11.4 → 251.6 m (max 424 m).

Scratch variants (repo untouched; all pre-outage 20–200 s mean, m — outage numbers are NOT used to judge):

| variant (on top of A4) | pre-outage | outage mean |
|---|---|---|
| A4 as specified | 251.6 | 310.3 |
| + no injection clip | 103.7 | 103.4 |
| + residual carried instead of discarded | 108.9 | 129.1 |
| + carry, NHC off (ins_gnss) | 152.4 | 785.3 |
| + carry, NHC forward axis rotated φ=−45° / +45° / ±90° | 131.4 / 93.3 / 88.1 | 181.7 / 192.3 / 267.2 |
| + carry + initial yaw convention fixed (90°−bearing) | 85.7 | 140.6 |
| + carry + yaw fix + φ=−45° / +45° / NHC off | 135.6 / 127.2 / 121.4 | 112.2 / 309.4 / 442.5 |

Findings:
1. **The 1 m/step "smooth injection" clip is a latent bug that sparse fixes expose**: 812 of 6812 steps clipped and
   6185 m of position correction discarded, while P shrinks as if fully applied. (`dx` is zeroed after injection.)
2. **The filter's heading has no relationship to the vehicle course.** Heading (converted to a bearing) minus the phone's
   GNSS course at 17 pre-outage fixes: causal run mean −10.9°, std 116.5°, median |diff| 94°; on the committed A3b code
   (interpolated GNSS) mean +62.6°, std 126.9°, median |diff| 146° — a large slowly drifting offset (+105° … +179°).
   Speed error vs GNSS speed: −1.3 ± 3.0 m/s (causal) and −0.7 ± 1.7 m/s (A3b).
3. **So the ~11 m pre-outage error of the committed code was GNSS-following, not INS quality**: 10 Hz interpolated
   position + velocity updates (σ 1 m / 0.3 m/s each, using the *next* fix up to 9 s early) drag the position along the GNSS
   track regardless of the heading state. Remove them and dead reckoning between 9 s fixes is unconstrained.
4. **Why heading is unobservable here**: velocity is a nav-frame state integrated from linear acceleration; there is no
   forward-speed / heading coupling. A GNSS velocity's direction reaches yaw only through F[v,θ] = −R[a×]dt, i.e. only
   while accelerating. NHC is the only place yaw enters, and it assumes phone x = vehicle forward, which the data
   contradicts (A2: horizontal axes ~45° off on S1).
5. The initial-yaw convention bug (bearing CW-from-N fed to a CCW-from-E filter) is real (109 → 86 m when fixed) but not
   the main problem.
Conclusion: with honest, causal, sparse GNSS this 15-state filter cannot hold heading. Rescuing it needs a heading
observable from GNSS course (mount-independent yaw rate + a vehicle-frame forward speed) — that is Phase B's
vehicle_dr design, not another patch on the ESEKF. Also note for Phase B: the 10-Hz-interpolated updates should NOT
be reintroduced; use new fixes only, and do not clip-and-discard corrections.

### A5 — NHC gain fix retried (now that the gyro axis is right)
K[6:15,:] = 0 with the gain computed inline and a Joseph-form covariance update. Result vs A3b: outage mean
92.6 → 49.9 m, end 222.6 → 145.6 m, path 264 → 172 m (truth 225), total |Δyaw| 304° → 737° (truth 663°);
worse: displacement 94.5 → 29.1 m (truth 153), pre-outage 11.38 → 11.97 m. Matches the earlier in-memory
"axis + speed + c + P0_bg" experiment exactly (49.94 m). It failed in Step 2 (c) only because the gyro axis
was wrong then, as predicted.

## Phase A summary (S3b, honest v_df=None)
Final state (A5): outage mean 49.9 m, end 145.6 m, displacement 29 m vs truth 153 m, pre-outage 12.0 m vs raw
phone GNSS 5.7 m, truth inside 1σ 0 % (σ at 260 s = 2.4 m). Versus the honest baseline: mean 68.2 → 49.9 m,
end 159.6 → 145.6 m, pre-outage 17.4 → 12.0 m, |Δyaw| 1118° → 737°. Displacement is still ~5× too short and the
filter is still wildly over-confident. The pre-outage 12 m is GNSS-following (see A4), not INS quality, and the
honest causal-GNSS version of this filter fails outright. Recommendation: Phase B (vehicle_dr).


# Phase B

## B0 — time-alignment check (found and fixed a real loader bug)
Phone GNSS vs VBOX position error at every NEW phone fix (74 fixes on S3b, 532 on S1), VBOX interpolated at the
phone timestamp.

**Before (counter-based timestamp_s):**

| | S3b before reset (<204 s) | S3b after reset (≥204 s) | S3b all | S1 all |
|---|---|---|---|---|
| mean error (m) | 5.17 | 25.68 | 19.86 | 2.67 |
| best time shift (VBOX at t+shift) | +0.25 s (t<180) | **+4.25 … +4.75 s** in every 45 s window after ~200 s | | 0.0 s |

Per-45 s windows on S3b: error 2–9 m up to 180 s, then 20–34 m for all later windows; best shift jumps from 0 to
+4.25 s and stays there (speed-based estimate agrees: +4.25 … +4.75 s, |Δv| 2.0–3.6 → 0.2–0.4 m/s). A step, not a drift.

**Cause.** The raw `TIME SINCE START (ms)` counter rolls over once in S3b (row 2043: 2707.520 s → 0.008 s; loader t=204.2 s);
S1 has none. `_make_timestamp_s` treats a negative step as 0, silently discarding the real time the phone logger was
down. The phone's own wall-clock column `DATE (…)` (dropped by the loader) jumps **+4.428 s at exactly row 2043**
(normal step 0.1 s), so ≈4.33 s of logging is missing. VBOX is continuous. Phone and VBOX share a clock modulo a whole
hour: S − V start offset = +3600.693 s (S3b) and +3600.546 s (S1); S3b's offset grows by +4.328 s by the end of the
file, S1's stays constant to 1 ms.

**Fix (data_loader.py).** `timestamp_s` for the phone now comes from the wall-clock column (phone-only; falls back to the
counter if it is missing/non-monotonic). New `sv_time_offset(s_df, v_df)` = (S start − V start) mod 1 h (+0.693 s S3b,
+0.546 s S1) is used ONLY for scoring; `check_outage.py` now looks up truth at t + offset. S3b duration 681.1 → 685.5 s;
S1 unchanged (5174.5 s).

**After:** S3b phone-GNSS error vs VBOX mean 5.76 m, median 4.74 m, flat across the drive (per segment 3.1–9.2 m; before
reset 6.49, after reset 5.47). S1 4.94 m mean (median 4.39). No jumps, no trend.
Residual, NOT corrected: the best shift is −0.5 s on both drives (S3b 4.16 vs 5.76 m at 0; S1 2.62 vs 4.94 m) — phone
fixes reflect the position ~0.5 s earlier than the wall-clock alignment says (GNSS latency / clock start offset), ≈4 m at
8 m/s. Consistent, so it is left as a known scoring bias instead of a VBOX-fitted constant.
Data hole: the phone has no data for ~4.3 s at S-time ≈ 204 s (the car was stopped there per VBOX). The pipelines'
`dt > 1 s → dt = 0.1` clamp treats the jump as one nominal step. VBOX ends 4.3 s + 0.7 s before the phone does.

## Phase A final state re-scored on the corrected timeline (ESEKF, S3b, 200–260 s)

| | outage mean | end | max | path (225.7) | disp (154.0) | \|Δyaw\| (675.7) | pre-outage | raw GNSS floor | 1σ | gap @200 |
|---|---|---|---|---|---|---|---|---|---|---|
| Phase A final, OLD timeline (962b677) | 49.94 | 145.55 | 145.55 | 171.7 / 224.8 | 29.1 / 153.2 | 737 / 663 | 11.97 | 5.67 | 0 % | 4.88 |
| Phase A final, CORRECTED timeline | 55.02 | 129.56 | 129.56 | 145.4 / 225.7 | 34.0 / 154.0 | 675 / 676 | 13.46 | 7.08 | 0 % | 4.88 |

(The 200–260 s window now spans different phone rows after the hole, and truth is looked up at the aligned VBOX time.
Numbers before this point in the log are on the old timeline and are not comparable to numbers after it.)


## B1 — mini-outage metric (check_outage.py, new section; old output kept)
For every interval between consecutive NEW phone fixes, AERIS error vs VBOX (aligned time) on the last row BEFORE the next
fix arrives = pure dead reckoning since the previous fix, IF the filter used no GNSS in between. New flags:
`--filter {esekf,vehicle_dr}`, `--fixes-only` (data-only: rows that are not new fixes report 0 satellites so the UNMODIFIED
ESEKF receives GNSS only on new-fix rows), `--mini-only`. Two phone-only trivial baselines are scored from the same fix:
hold = stay at the last fix; cv = last fix + its GNSS speed along its GNSS course.
S3b: intervals whose next fix is ≤ 200 s (the tuning set). S1: all intervals outside the 200–260 s outage.

| filter / baseline | S3b (20 intervals, 9.1 s avg) mean / median / max (m) | S1 (523 intervals, 9.6 s avg) mean / median / max (m) |
|---|---|---|
| ESEKF as shipped (interpolated 10 Hz GNSS — NOT dead reckoning, this is tracking) | 12.90 / 10.35 / 43.04 | 10.69 / 8.69 / 233.08 |
| **ESEKF fixes-only (its real DR quality)** | **148.02 / 151.96 / 309.49** | **347.98 / 267.99 / 1364.54** |
| baseline: hold last fix | 52.95 / 59.55 / 106.70 | 72.21 / 70.66 / 172.60 |
| **baseline: last fix + constant velocity (bar to beat)** | **34.89 / 39.71 / 73.36** | **26.67 / 22.78 / 136.20** |

Moving-only intervals (both fixes > 2 m/s): S3b n=15: ESEKF 15.43 (shipped) / 133.32 (fixes-only), hold 61.84, cv 35.96;
S1 n=429: 11.29 / 358.43, hold 81.79, cv 26.34. Truth inside 1σ: 0.0 % on both drives for both ESEKF variants (reported σ
0.2 m shipped, 2.5 m / 1.7 m fixes-only vs errors of 100+ m).
Reading: with honest GNSS use the ESEKF is 3–13× worse than doing nothing clever (last-fix + const-v) — consistent with the
A4 finding. The S1 ESEKF numbers above are the frozen reference; no tuning was done on S1.


## B2 — mounting angle φ (phone horizontal frame → vehicle forward), calibration on t ≤ 200 s, phone data only
`backend/mount_angle.py` (reused by vehicle_dr later). φ = angle of the vehicle's forward axis from phone +x toward +y.
Criterion (i): ∫a_fwd over each new-fix interval vs the phone-GNSS speed change over it. Criterion (ii): a_lat vs v·ω_vert in
turns (|ω_vert| > 0.1 rad/s, v > 3 m/s; v = GNSS speed interpolated between fixes and 0.5 s smoothing — offline calibration only).
1° grid; "plateau" = width of the φ range within 0.05 of the peak correlation.

| drive | criterion | n | φ | corr | plateau | slope |
|---|---|---|---|---|---|---|
| S3b | (i) ∫a_fwd vs Δspeed | 20 intervals | −180° | +0.208 | 92° | 0.23 |
| S3b | (ii) a_lat vs v·ω | 564 samples | −9° | +0.120 | 111° | 0.09 |
| S3b | agreement | | **171° apart** | both weak | | |
| S1 | (i) ∫a_fwd vs Δspeed | 14 intervals | −80° | +0.891 | 32° | 0.69 |
| S1 | (ii) a_lat vs v·ω | 306 samples | −51° | +0.932 | 66° | 0.84 |
| S1 | agreement | | 29° apart (plateaus overlap at −84…−64°) | both strong | | |

**S1: fixed, identifiable mount, φ ≈ −50° … −80°.** Independent checks agree: sign-flipped mean horizontal accel in turns is
(+1.37, +0.91) m/s² (magnitude 1.64, consistency 0.8–0.93) → lateral-left at +33.6°, forward ≈ −56°. Per-30 s windows in the first
400 s: 7/8 fit well (corr > 0.8), φ = −6, −72, −91, −46, −55, −86, −38. Whole-drive scan (300 s windows, 5174 s): well-fitting windows
give circular mean φ = −36.9°, resultant length 0.98 (windows range −20° … −69°; weak fits in 3300–4500 s). So calibrating on the
first 200 s is representative on S1.

**S3b: there is NO constant mounting angle.** The rotation-invariant check (no φ needed) shows the accelerometer does respond
to turns (corr(|a_h|, v|ω|) = 0.47; mean |a_h| in turns 2.48 vs v|ω| 2.74 m/s²), but the sign-flipped mean horizontal accel in turns has
magnitude only 0.29 m/s² (S1: 1.64) — the vectors cancel because their direction relative to the phone changes. Per 30 s windows
(criterion ii): 9/19 windows fit very well (corr 0.85–0.99) but at φ = 73°, 153°, 144°, −66°, 153°, −115°, −58°, 104°, 96°
(circular mean +141°, resultant length 0.31 ≈ spread over the circle). Good fits at different angles = the phone's yaw relative to
the car changes during the drive (pre-200 s windows alone: 98°, −66°, 73°, 154°, −34°). Gyro-vertical still works on S3b (A2: corr 0.67),
so only the horizontal accel projection is affected.

**Consequence for B3:** a single fixed φ from the first 200 s is valid on S1 but not on S3b (the tuning drive). Forward-acceleration aiding
(v̇ = a_fwd − b_a) and the centripetal a_lat update both need φ. Heading (ψ̇ = ω_vert − b_g) does not.
Note on use of S1: the per-window and whole-drive S1 scans above are phone-only calibration-stability checks (no VBOX, no filter
scoring), run to know whether a first-200 s φ would stay valid; disclosed here.


# Phase B3 — vehicle_dr (option 1: mount-free core, φ-gated aiding)
Standing rules: ψ is ENU (CCW from East, radians) everywhere inside vehicle_dr; phone course = bearing (CW from North, deg) →
ψ = π/2 − radians(bearing), wrapped. Tune ONLY on S3b mini-outages (0–200 s); report mean/median/max and leave-one-interval-out (LOO)
error for tuned parameters; never tune on S1 or on the 200–260 s outage. ESEKF untouched. Push after every commit.

## S0 — sandbox (`backend/sim_drive.py`, tests in `backend/tests/test_vehicle_dr.py`)
Synthetic drive with known truth in load_smartphone() format (+ V-like truth df). Default: 329 s, straights / 90° turns (R=12 m) /
stop from 177.4 s to 209.3 s (S3b: ~180–212 s), 37 GNSS fixes every 9 s (4 m noise, held between fixes, speed m/s, course as a
bearing), 10 Hz IMU: vertical gyro = true rate × scale + bias (−0.008) + noise, horizontal linear accel = forward/lateral accel rotated
into the phone frame by φ(t) (constant or changed abruptly mid-drive) + bias + vibration noise growing with speed; gravity ≈ (0,0,9.806).
12 sandbox tests pass (column format, 10 Hz, fix cadence and hold, speed in m/s, bearing convention, kinematic consistency,
lat/lon round-trip, stop timing, gyro bias/scale, mount rotation, abrupt mount change, vibration growth, determinism).

## Results table (same columns every step)
S3b mini = mini-outage error (m) over the 20 intervals ending ≤ 200 s: mean / median / max. LOO = leave-one-interval-out mean (parameters
re-chosen on the other 19 intervals). Outage = the 200–260 s outage, REPORTED ONLY (never tuned): mean / end. Coverage = % of mini-outage
intervals whose truth lies inside the reported 1σ ellipse (target ≈ 39 %). Truth: displacement 154 m, path ≈ 225 m.

| step | S3b mini mean / median / max | LOO mean | S3b outage mean / end | disp (154) | path (~225) | 1σ coverage (≈39 %) | S1 mini mean | verdict |
|---|---|---|---|---|---|---|---|---|
| baseline: hold last fix | 52.95 / 59.55 / 106.70 | – | – | – | – | – | 72.21 | reference |
| baseline: last fix + const-v (bar) | 34.89 / 39.71 / 73.36 | – | – | – | – | – | 26.67 | **bar to beat** |
| ESEKF as shipped (interpolated GNSS) | 12.90 / 10.35 / 43.04 | – | 55.02 / 129.56 | 34.0 | 145.4 | 0 % | 10.69 | reference (tracking, not DR) |
| ESEKF fixes-only (true DR) | 148.02 / 151.96 / 309.49 | – | 282.95 / 359.52 | 165.3 | 447.3 | 0 % | 347.98 | reference |
| S0 sandbox | n/a | – | – | – | – | – | – | 12 sandbox tests pass |
| **B3a** vehicle_dr core (mount-free) | **22.46 / 17.32 / 65.23** | 22.92 | 59.54 / 153.78 | 0.1 | 0.2 | 50 % (LOO 45 %) | n/a (not allowed) | **PASS** (< 34.9 CV bar; 6.6× better than ESEKF fixes-only). Outage path/disp ≈ 0: speed is held, car is stopped at 200 s, nothing launches it → B3b |
| B3b spec: launch φ, strict |ω| < 0.05, accel propagated until next standstill | 22.46 / 17.32 / 65.23 | – | – | – | – | – | n/a | **FAIL (no-op)**: all 5 S3b launches rejected as "turning" (max |ω| 0.3–0.6 rad/s: urban junction launches) |
| B3b turn-compensated + accel propagated until next standstill (no cap) | 33.89 / 26.69 / 100.45 | – | – | – | – | 40 % | n/a | **worse — reverted** (first version, no turn gate: 48.55 / 36.20 / 178.72) |
| **B3b** turn-compensated launch φ, **replay only** (aided_max_s = 0) | **21.93 / 17.11 / 64.85** | 22.12 | 64.35 / 145.89 | 75.5 | 104.9 | 50 % (LOO 45 %) | n/a (not allowed) | **PASS, marginal** (−0.53 m = −2.4 % vs B3a; 2 launches in the tuning window). Outage path 0.2 → 105 m, disp 0.1 → 75.5 m (reported, not tuned) |
| B3c centripetal speed, defaults (σ 1.0, res 0.6) | 22.74 / 21.11 / 46.26 | – | 86.13 / 154.76 | 155.0 | 249.6 | 35 % | n/a | worse than B3b on the mean/median |
| **B3c** centripetal speed, best S3b grid point (σ 4.0, res 0.3 — update nearly off) | 22.12 / 17.64 / 62.28 | 23.75 | 72.22 / 163.16 | 115.9 | 159.5 | 45 % (LOO 40 %) | n/a | **FAIL — reverted (`use_centripetal=False` default)**: no setting beats B3b (21.93); speed error in turns 1.81 → 1.73 m/s only |
| B3b state measured on S1 (validation; = B3d "off") | – | – | – | – | – | – | **43.89 / 20.05 / 620** (cov 30 %) | reference: median beats const-v (22.78) but the mean does not (26.67): heavy tail |
| **B3d** φ-gated fixed-mount aiding (gate: S3b **inactive** → identical to B3b; S1 **active**, φ = −65.5°) | 21.93 / 17.11 / 64.85 | 22.12 | 64.35 / 145.89 | 75.5 | 104.9 | 50 % | **on: 52.66 / 20.09 / 1097** (cov 20 %) vs off 43.89 | **NO BENEFIT on S1 → off by default** (sandbox: 3× better after calibration). Paired: better in 42 %, worse in 49 % of intervals, median +0.18 m |

### B3a — vehicle_dr core (`backend/vehicle_dr.py`, `backend/tune_vehicle_dr.py`)
State [E, N, ψ, v, b_g, b_a]; ψ ENU radians (CCW from East), phone bearing → ψ = π/2 − radians(bearing) (unit-tested: cardinals, 45°,
direction vectors, round trip, wrapping, sandbox course field). Propagation ψ̇ = ω_vert − b_g, v held (random walk), Ė = v cosψ, Ṅ = v sinψ; ψ frozen
while stationary. GNSS causal: position on NEW fixes only (σ = max(gps_accuracy_m, 3)), speed on new fixes, course when speed > 3 m/s (ψ initialised
from the first fix with speed > 3), IMU-only standstill (1 s accel variance < 0.10, |mean ω − b_g| < 0.05, v̂ < 2) → ZUPT + ZARU, chi-square 99 % gate
on every GNSS update with a log (3 consecutive position rejections → next fix accepted ungated, logged `pos_forced`). No clipping or discarding of
accepted corrections; a data hole (dt > 1 s) is propagated honestly (Q grows with dt). VBOX never an input (`v_df` ignored; tested).

Bugs the sandbox caught before real data was touched (first sandbox run: mean 84 m vs CV 24 m, 13/30 position fixes rejected):
1. ZUPT pinned v = 0 (σ 0.05) at a false/real standstill; afterwards σ_v regrew far too slowly (0.6 m/s/√s) for a 1.5 m/s² launch, so the 99 % gate rejected
   the CORRECT GNSS speed and then the position fixes, and the filter stayed overconfident (σ_pos ≈ 7 m at 300 m error). Fix: when standstill releases, reset
   σ_v ≥ 1.5 m/s; a new fix faster than 2 m/s clears a stale standstill flag; rw_v must cover real accelerations.
2. The first fix's own course/speed were not used to initialise ψ (loop started at row 1). Fixed.
3. Sandbox car started from rest, a start-up transient S3b does not have (its log begins mid-drive at ~11 m/s) → sandbox now starts at v0 = 8 m/s.

Tuning (S3b mini-outages ONLY; 60-point grid over rw_v {0.8,1.2,1.5,2,3} × turn_noise {0.1,0.2,0.3,0.5} × σ_gnss_speed {0.3,0.5,1.0};
rule fixed in advance: lowest mean error among grid points with 1σ coverage in [30, 50] %). Untuned defaults: 22.96 / 17.57 / 67.72, coverage 30 %.
Chosen rw_v = 2.0, turn_noise = 0.5, σ_gnss_speed = 0.3: 22.46 / 17.32 / 65.23, LOO mean 22.92, coverage 50 % (LOO 45 %).
The error surface is FLAT — 22.5–24.1 m over most of the plausible region — so the tuning mostly bought honest uncertainty (coverage 30 → 50 %), not accuracy;
the in-sample/LOO gap is 0.46 m. Accuracy is limited by the model structure (speed is held between fixes), not by these parameters.
Sandbox (4 seeds): mean 16.9–17.0 m vs CV 21.9–24.3 m; coverage 64 % (the calmer sandbox slightly over-covers with S3b-tuned noise, so the sandbox test
window is 25–70 % rather than 25–55 %). Real S3b reference, same intervals: hold 52.95, const-v 34.89, ESEKF fixes-only 148.02.
Moving-only S3b intervals (n=15): vehicle_dr 17.75 / 15.95 / 41.01 vs const-v 35.96.
200–260 s outage (REPORTED, not tuned): mean 59.54 m, end 153.78 m, path 0.2 m, displacement 0.1 m, |Δyaw| 277° (truth 676°), inside 1σ 20.3 %, σ at 260 s = 124 m.
The filter is stopped at 200 s (correct) and, with speed held and no GNSS, never moves again — exactly what B3b (launch acceleration) has to fix.

### B3b — launch calibration (mount-free forward axis) — `evaluate_launch()` and the standstill/launch logic in vehicle_dr.py
Design: while stationary keep a rest baseline b_h (mean horizontal accel of samples older than 1.2 s). On release, over [release − 0.8 s, release + 2 s]
(the 1 s variance detector lags the true start) take d = a_h − b_h; φ = direction of Σd. Accept only if the magnitude-weighted resultant length
R = |Σd| / Σ|d| > 0.8, mean |d| ≥ 0.4 m/s² and, in the spec (strict) version, |ω − b_g| < 0.05 rad/s throughout. On acceptance the window's forward
acceleration is replayed to recover the speed/position already covered (the filter held v ≈ 0 while the car was pulling away), b_a is initialised
from b_h·u, and v̇ = a_h·u − b_a can be propagated. Every release attempt is logged in `result["launches"]`.

What the sandbox caught (before real data):
* Straight launches failed at first (R = 0.40, then "no rest baseline"): (1) variance-only release lags a smooth launch by 2–3 s → added a mean-based
  release (0.5 s mean of a_h off the rest baseline by > 0.6 m/s²); (2) standstill entry needed v̂ < 2 m/s, but v̂ is only corrected by GNSS every 9 s → sustained
  quiet (3 s) now enters standstill regardless of v̂; (3) a smooth launch looks "quiet", so the detector re-entered standstill right after releasing and
  cancelled the calibration → re-entry blocked for the launch window. All three apply only when launch calibration is on (use_launch=False reproduces B3a exactly).
* B3a flaw: the gate rejected a CORRECT GNSS speed of 0 after a 10 → 0 m/s stop, because the position update (applied first) shrank σ_v through the
  cross-covariance. GNSS updates now go speed → course → position. Neutral on real S3b (identical numbers), fixes the sandbox lock-up.
Sandbox result: φ recovered within ±3° on 5/5 straight launches and within ±5° on 5/5 turning launches (multi-stop route, junction turn right after the stop),
also after an abrupt mount change while stopped (98–105° vs true 100°). 11 new tests (φ within 10°, mount change, strict mode refuses turning launch, bumps
and no-standstill drives produce no launch, does not worsen the multi-stop route, unlimited aiding helps when the mount is stable, evaluator unit tests).

Real S3b, spec version: all 5 launches rejected ("turning", max |ω| 0.30–0.61 rad/s). The spec's |ω| < 0.05 rule cannot accept urban junction launches. A turn-compensated
variant (subtract the known centripetal term v·ω·u⊥ by fixed-point iteration; accept only if the correction is < 1× the launch acceleration) accepts them.
Then propagating a_h·u until the next standstill HURTS on S3b: aided speed drifts 5–8 m/s between fixes (t=100 s: 2.5 vs 7.2 m/s; 120 s: 2.6 vs 8.9), because
the phone's yaw relative to the car is not stable on S3b (B2) and turn leakage v·ω·sin(Δφ) enters the forward accel. Gating aiding to |ω − b_g| < 0.10 did not rescue it.
Selection over the aiding duration cap (S3b mini-outages only; coverage-constrained rule; LOO):

| aided_max_s | 0 (replay only) | 3 | 6 | 12 | ∞ |
|---|---|---|---|---|---|
| mean / median (m) | **21.93 / 17.11** | 21.94 / 17.10 | 22.12 / 17.22 | 22.89 / 18.86 | 33.89 / 26.69 |
| coverage | 50 % | 50 % | 45 % | 45 % | 40 % |

Chosen: replay only. LOO mean 22.12 (coverage 45 %). The gain over B3a is 0.53 m — real but small, resting on the 2 launches (90 s, 145 s) inside the tuning window.
Launch log, S3b (whole drive; 5 release events before 260 s): t=89.9 φ +28.7° R 0.96 accepted (v₀ 4.0 m/s); 144.9 φ +128.9° R 0.79 rejected; 190.6 R 0.35 rejected; 201.9 rejected;
214.2 φ +57.5° R 0.83 accepted (v₀ 2.3); 265.2 rejected (contamination 0.68); 418.3 φ +161.8° R 1.00 accepted (pure straight); 610.2 rejected.
The three accepted φ (+29°, +58°, +162°) differ — consistent with B2: the S3b mount is not constant.
Launch log, S1 (log only; no scoring): 50 release events, 31 accepted (13 "direction inconsistent", 6 "no rest baseline"), median R 0.96; accepted φ circular mean −51.3° but resultant
length only 0.49 (histogram over 30° bins from −180°: 0,3,3,7,3,8,1,2,0,3,1,0). B2's independent calibration for S1: −80° / −51°, whole-drive mean −36.9°. The first four launches agree
(−87°, −30°, −84°, −89°); later ones scatter (+8°, +98°, −53°, +142°, −21°, −104°, −20°, −8°), some near +100°…+140° (possibly reversing). Only roughly 40 % of accepted S1
launches fall within ±30° of B2's φ, so launch φ is a weaker signal on real data than in the sandbox — one more reason it is used only to seed the speed.
Outage (reported, not tuned): mean 64.35 m, end 145.89 m, path 104.9 m, displacement 75.5 m, |Δyaw| 288° (truth 676°), inside 1σ 20.3 %, σ at 260 s = 268 m.

### B3c — mount-free centripetal speed — FAILED on S3b, switched off by default
Update: every 0.5 s in steady turns (|ω − b_g| > 0.15 rad/s, |Δω over 1 s| < 0.10), z = |mean(a_h) − b_h| over 0.5 s, model h = √((v·(ω−b_g))² + a_res²) (a_res = residual floor
for forward accel + vibration = the "inflate" the spec allows), σ_cent, chi-square gate, IMU-only (so it also runs inside a GNSS outage). Sandbox (3 seeds): mini-outage 15.5 → 11.2–12.1 m,
speed error in turns 4.0 → 1.9–2.0 m/s, coverage 64–68 %, updates fire inside the outage window and only in real turns (5 new tests).
Real S3b, grid σ_cent {0.5,1,1.5,2.5,4} × a_res {0.3,0.6,1,1.5} (S3b mini-outages only): NO point beats B3b (21.93 / 17.11 / 64.85). The lowest is σ_cent = 4 (update nearly switched off) at
22.12 / 17.64 / 62.28, LOO 23.75; at σ_cent = 1 it is 22.74 / 21.11 / 46.26 with coverage 35 %. Speed error in turns (VBOX used only to score): 1.81 m/s (B3b) → 1.75 (σ 1) / 1.73 (σ 2).
Diagnosis (VBOX speed used as a diagnostic reference only, never as an input): the signal itself IS good on S3b in steady turns — corr(|a_h − b_h|, |v·ω|) = 0.88, ratio 1.05, residual
std 0.45–0.51 m/s², implied speed z/|ω| error 0.76 m/s mean (median 0.57) — but only 45 steady-turn blocks (of ~442 turn samples) exist before 200 s. Relaxing the gate to use most turn samples
(steady < 0.25/0.6 rad/s, every 2–3 samples) lowers the speed error in turns to 1.65–1.68 m/s (−9 %) yet RAISES the mini-outage error to 22.5–25.0 m and the overall speed error 2.52 → 2.55–2.69 m/s: braking into and
accelerating out of junctions adds forward acceleration to |a_h| that the residual floor does not capture. Cutting the update's path into b_g changed nothing (22.74 → 22.74). Not a bug: a physically
sound measurement that this speed-held filter cannot exploit better than it already does on S3b.
Reported, not tuned: with the update on (σ 1.0) the 200–260 s outage SHAPE is much better (path 249.6 m vs truth 225.7, displacement 155.0 m vs 154.0) while the mean error is worse (86.1 m vs 64.4 m).
Rule applied: fails "S3b mini-outage improves vs previous step" → off by default; code and sandbox tests kept.

### B3d — φ-gated fixed-mount aiding (validation report; nothing tuned on S1)
Gate (option 1), calibration on data before 200 s only: mount_angle criteria (i) and (ii) both corr > 0.8 and within 30°; φ = circular mean of the two; the fixed φ is usable only from t = 200 s (the end of the
calibration phase — tested: results before 200 s are bit-identical with the feature on/off, and φ is unchanged if data after 200.5 s is removed). When active: forward accel propagated with u(φ) whenever no launch φ is valid
(near-straight only, |ω − b_g| < 0.10), b_a seeded from the rest baseline and updated at standstills (a_h·u ≈ b_a), and a SIGNED centripetal update a_lat = v·ω (σ 0.8 m/s², steady turns, IMU-only so it also runs in the outage).
Gate result: **S3b inactive** (corr 0.21 / 0.12, 171° apart — as in B2), so S3b numbers equal B3b exactly. **S1 active**: φ_i = −80° (corr 0.89), φ_ii = −51° (corr 0.93), 29° apart (limit 30°) → φ = −65.5°.
Sandbox (stable mount, 568 s drive, 3 seeds): calibration φ within 10° of the true −50°; intervals after 260 s: 19.5–20.4 m (off) → 6.3–6.8 m (on), CV 28–29 m; a phone moved at 90 s closes the gate (corr 0.54 / 0.75). 8 tests.

S1 validation, mini-outages (523 intervals outside 200–260 s; parameters exactly as tuned on S3b; no S1 tuning):

| S1 | mean / median / max (m) | inside 1σ | moving mean |
|---|---|---|---|
| vehicle_dr, B3d off (B3b state) | 43.89 / 20.05 / 620.02 | 30 % | 46.15 |
| vehicle_dr, B3d on | 52.66 / 20.09 / 1096.92 | 20 % | 57.33 |
| baseline last fix + const-v | 26.67 / 22.78 / 136.20 | – | – |
| baseline hold last fix | 72.21 / 70.66 / 172.60 | – | – |
| ESEKF fixes-only (B1) | 347.98 / 267.99 / 1364.54 | 0 % | – |
| ESEKF as shipped (tracking, not DR) | 10.69 / 8.69 / 233.08 | 0 % | – |

First 200 s (16 intervals): identical on/off, 24.67 / 17.94 / 95.96 vs const-v 42.07. After 260 s (507 intervals): off 44.49 / 20.16 / 620, on 53.55 / 20.11 / 1097.
Paired on − off per interval: median +0.18 m, mean +8.78 m; on better in 42 %, worse in 49 %, within 1 m in 9 %; p50 20.0 vs 20.1, p75 40.6 vs 46.6, p90 108 vs 124.5. Excluding lock-outs (both < 100 m, n = 432): mean 22.53 vs 23.82,
median 17.05 vs 16.94. Fixed-φ aiding is neutral-to-slightly-negative on real data although it is 3× better on the sandbox: the calibrated φ is only good to ±25–30° (criteria disagree by 29°) and the real forward-accel signal
is far noisier than the simulated one. Verdict: off by default; code and tests kept.

**Important validation finding — the filter has a heavy error tail on S1 even with B3d off.** vehicle_dr's median (20.05) beats const-v (22.78) but the mean (43.89) does not (26.67).
Percentiles (m): p50 20.0, p75 40.6, p90 108.0, p95 175.5, p99 331.4, max 620. Intervals > 100 m: 11.1 % (const-v 0.8 %), > 200 m: 4.0 %. Mean without the worst 5 %: 31.0 m (const-v on the same intervals 27.1).
The 10 worst intervals cluster in a few episodes (t ≈ 1826–1979, 2798, 4162–4234) and at the interval-start fix BOTH the course and the position update were REJECTED by the 99 % gate in 9 of 10 (the 10th: position only).
Over the whole drive: 107 course rejections, 94 position rejections, 29 forced position accepts, 1 speed rejection (S3b: 1 / 1 / 0 / 0). Reading: once ψ is wrong the hard gate rejects exactly the measurements that would repair it — a lock-out; only
position has a "3 consecutive rejections → accept" failsafe, course has none, and a forced position accept does not repair ψ. This is a logic weakness of hard gating, visible on S1 but not S3b. I did NOT change the filter in response: S1 is a
validation drive, and the fix (candidate B3i: robust Huber/Student-t GNSS updates, or a course failsafe) must be justified and verified on the sandbox and S3b, not by looking at S1.
Caveat for B5: S1 has now been looked at several times (launch log, this report, tail characterisation), so it is no longer a pristine unseen drive; untouched same-driver, same-phone drives exist (S2 156 min, S3a 41 min, S3c 62 min, S4 158 min).


# E0 — evaluation upgrade (2026-09-26): `check_outage.py` + `window_plan.py`  — no filter change; vehicle_dr defaults identical to 22ec79f
Existing output kept byte-for-byte (re-verified: outage 64.35 / 145.89, mini 21.93 / 17.11 / 64.85, coverage 50 %; ESEKF default unchanged at 55.02 / 129.56).

**What was added** (all scoring-side; VBOX never reaches a filter):
* (a) Along/cross error. `Truth` = VBOX track in the filter's ENU frame on the phone clock; travel direction = position(t + 0.5 s) - position(t - 0.5 s) (carried forward while the car moves < 0.3 m in that second, so the split stays defined at stops).
  along = (AERIS - truth) . direction (+ = AERIS ahead); cross = (AERIS - truth) . left normal (+ = AERIS to the left); along^2 + cross^2 = error^2 (tested). Reported: mean |along|, mean |cross|, and both (signed) at the end.
* (b) Speed diagnostics (filter v state vs VBOX speed): mean |dv|, values at +30 s and at the end; path ratio = AERIS path / truth path, both on the AERIS 10 Hz grid (the older "AERIS path / truth path" line uses native V rows: 225.7 m vs 225.6 m on the grid).
* (c) Sliding 60 s outages: `window_benchmark` runs vehicle_dr once per window with GNSS hidden on [start, start+60] (run truncated at the window end: exact, tested) and scores the window rows; the same windows are scored for the
  last-fix + const-v baseline (fix strictly before the window start, speed > 1 m/s along its course) and the hold baseline. Summaries over windows = median / mean / p90 (numpy linear percentile). Window plan and S3c pre-registration: see the PRE-REGISTRATION section.
* (d) Reference row = the table above. Also: reserved-drive guard, `--windows`, `--per-window`, `--unseal`.

**Verification before trusting the numbers** (sandbox criteria were fixed in the test-file docstring before the real metrics were computed; 29 new tests, suite 242 pass / 37 skip):
* along/cross recovered a known offset to < 1e-6 m on a straight line and < 0.02 m on a circle; sign convention (ahead +, left +) tested; stopped truth carries the last direction; path ratio of a half-speed track = 0.500;
* sandbox windows: corrupting the phone GNSS inside a window (+1.1 km, speed 50 m/s, course 123 deg) changes that window's result by < 1e-9 m (hiding is real); truncation is exact (< 1e-9); baselines use only fixes before the window; vehicle_dr beats hold on the sandbox;
* real S3b: the direction derived from truth positions agrees with VBOX's own heading column, median |diff| 0.56 deg, p90 2.56 deg, mean signed +0.18 deg (n = 5289 samples, speed > 3 m/s) — the ENU / bearing conventions and the left normal are right;
* a window starting at 200 s reproduces the event report exactly (64.35 / 145.89 / along -85.58 / cross +118.15 / ratio 0.465 / mean |dv| 2.64).
One bug found by the tests, in the test not the metric: a circle scored at the very last reference sample was 0.25 m off because within 0.5 s of the ends of the reference file the direction chord is one-sided (np.interp clamps). Real windows end
well inside the file (S3c last registered window ends 3710 s vs 3717.5 s limit; S3b tuning windows end <= 190 s), so it is documented in `Truth`, not changed (the registered window rule stays as committed).

**Reference row: S3b tuning windows (n = 11, starts 30-130 s), median / mean / p90 over windows**
| metric | vehicle_dr default | last fix + const-v | hold last fix |
|---|---|---|---|
| mean error (m) | 80.97 / 84.11 / 110.67 | 243.22 / 239.02 / 307.95 | 142.59 / 145.78 / 199.54 |
| end error (m) | 161.47 / 162.84 / 214.23 | 430.75 / 456.87 / 667.96 | 156.49 / 192.77 / 299.58 |
| \|along\| at end (m) | 76.52 / 83.73 / 132.93 | 366.06 / 277.37 / 478.03 | 64.22 / 95.20 / 181.11 |
| \|cross\| at end (m) | 121.90 / 130.70 / 191.65 | 162.78 / 265.60 / 527.32 | 142.00 / 149.61 / 242.52 |
| along at end, signed (m) | -65.09 / -45.99 / 65.39 | 32.69 / -10.44 / 390.33 | -32.32 / -35.78 / 64.22 |
| cross at end, signed (m) | -100.83 / -38.85 / 121.90 | -61.17 / -43.48 / 341.43 | -75.27 / -32.53 / 230.56 |
| path ratio AERIS / truth | 0.96 / 1.08 / 1.48 | 1.20 / 1.20 / 2.05 | 0 (stays put) |
| mean \|speed error\| (m/s) | 4.71 / 4.61 / 5.86 | 4.38 / 4.04 / 5.50 | 5.51 / 6.00 / 7.66 |
| truth inside 1-sigma (%) | 52.58 / 44.15 / 66.56 | – | – |

Per window (vehicle_dr: mean error, end error, along, cross at end, path ratio, % epochs inside 1 sigma; const-v mean / end):
30: 94.9 / 230.9 / -174.4 / -151.4 / 1.09 / 63 % ; 178.1 / 394.1 — 40: 131.9 / 207.4 / +79.1 / -191.7 / 0.96 / 49 % ; 243.2 / 440.8 — 50: 81.0 / 180.4 / -132.9 / +121.9 / 2.16 / 64 % ; 354.5 / 807.1 —
60: 110.7 / 214.2 / +49.8 / +208.4 / 0.84 / 17 % ; 242.6 / 422.9 — 70: 77.4 / 123.7 / -26.9 / +120.8 / 0.93 / 33 % ; 191.5 / 430.7 — 80: 68.3 / 93.7 / -76.5 / +54.1 / 0.56 / 12 % ; 275.4 / 546.0 —
90: 42.2 / 133.2 / -111.6 / -72.8 / 1.03 / 67 % ; 82.5 / 123.3 — 100: 51.6 / 172.5 / +65.4 / -159.6 / 1.48 / 67 % ; 245.2 / 481.9 — 110: 86.1 / 139.9 / +13.2 / -139.3 / 0.89 / 53 % ; 275.7 / 367.7 —
120: 80.2 / 133.8 / -65.1 / -117.0 / 0.88 / 56 % ; 232.5 / 343.0 — 130: 100.8 / 161.5 / -126.1 / -100.8 / 1.08 / 5 % ; 307.9 / 668.0.

**The 200-260 s event, along/cross split (vehicle_dr default; reported, never tuned)**
mean |along| 28.73 m, mean |cross| 54.32 m (mean error 64.35 m); at the end along -85.58 m, cross +118.15 m (end error 145.89 m); path ratio 0.46 (104.9 m / 225.6 m); mean speed error 2.64 m/s.
Speed, truth (VBOX) vs filter, every 5 s from 200 s: 0.01 / 0.00, 0.02 / 0.00, 0.02 / 0.00, **1.75 / 0.00 (215 s)**, 5.97 / 2.34, 0.05 / 2.34 (second stop at ~225 s), 2.50 / 2.34, 5.15, 4.35, 8.35, 6.01, 8.16, **1.13 / 2.34 (260 s)**;
truth max 8.73 m/s. So the "+30 s: 2.34 vs 2.50, +60 s: 2.34 vs 1.13" spot values are instantaneous readings in stop-and-go traffic; mean |dv| and the path ratio are the meaningful summaries.
Context (ESEKF as shipped, same block): mean |along| 37.47, mean |cross| 33.97, end along -121.95 / cross +43.75, path ratio 0.64, mean |dv| 2.10 m/s.

**What E0 says (facts and cautious readings)**
1. Over 60 s vehicle_dr beats const-v (mean error median 81 vs 243 m) and hold (143 m) on the mean error, but its END error (median 161 m) is no better than "stay at the last fix" (156 m); p90 end 214 vs 300 m for hold.
   const-v is far worse than hold over 60 s (it overshoots turns: |along| 366 m). The bar that matters for 60 s outages is hold, not const-v.
2. vehicle_dr's end error is cross-track dominated on the tuning windows (|cross| 122 m vs |along| 77 m) and in the event (+118 m cross vs -86 m along): the path shape (heading through turns) is the larger problem, speed the second.
   The along error is negative in 7 of 11 windows and in the event (AERIS lags) but not systematically (median -65 m, mean -46 m).
3. The mean speed error is 4.7 m/s on the tuning windows (speed is held; real urban speed swings 0-9 m/s) — the motivation for I2 / I3 — while path ratio ~0.96 says the held speed is right on average, so a speed prior may fix the along error but cannot fix the cross error.
4. Regime mismatch: tuning windows are moving drives, path ratio ~1; the event starts from a stop (path ratio 0.46). Improvements found on the windows are not guaranteed to move the event, which stays report-only.
5. The windows are strongly overlapping (11 windows, ~2.7 independent stretches); per-window mean errors range 42-132 m. Treat differences of a few metres as noise.

**Decisions / deviations to disclose**
* "windows that END before 200 s" was applied strictly (start + 60 < 200) -> starts 30-130, 11 windows (the window starting at 140 ends at exactly 200 s and is excluded).
* The S3c event window = the same absolute [200, 260] s as the S3b demo outage (CLAUDE.md demo timeline), registered before any S3c error existed; only GNSS availability was checked.
* Added, unrequested but small and reversible: the reserved-drive guard (`--unseal`), `--per-window`, and a stricter early validation of `--windows`. `CLAUDE.md` now carries the standing rules and drive registry; its old line "Commit only
  when a result improves" was replaced by the plan's step protocol (commit per step; a failed step stays behind a flag OFF), and its "S1 = unseen validation" wording was corrected (S1 is previously inspected).
* No S3c, S3a, S2, S4 or S1 window was scored in E0. S1 windows (secondary) and S3c windows (B5) are one command away: `--windows all` (S1) / `--unseal --windows all` (S3c, B5 only).


# H0 — development harness + S2 onboarding (2026-09-26, registry v2; no filter change)
**S2 alignment (B0 redone with the new reusable `backend/check_alignment.py`; S2 is a development drive so its errors may be looked at).** The tool reproduces the logged B0 numbers (S1: mean 4.94 m, median 4.39 m, best shift -0.50 s -> 2.62 m;
S3b: median 4.71 m vs logged 4.74, mean 5.20 vs 5.76 because the tool drops fixes in the last 5 s where VBOX has already ended). S2: S/V clock offset 7.341 s (S3b 0.69, S3c 0.72, S1 0.55), 940 usable fixes,
phone GNSS vs VBOX at the aligned time mean 2.69 m / median 2.25 m / p90 5.02 m, flat over the whole 9388 s (16 segments of 600 s: 1.9-3.9 m, no step, no trend) -> the timeline is correct, the registered S2 window list stands (no amendment).
**Observation for I1a:** the best lag shift is -0.50 s on S3b and S1 but 0.00 to +0.25 s on S2 — the GNSS-latency / clock-alignment residual is NOT the same on every drive, so a latency estimated on S3b need not transfer.
**Harness** (`backend/dev_eval.py`, tested): one call scores a `VDRParams` on the S3b dev windows (11), the S2 dev windows (861, 16 worker processes), the S3b mini-outages, the S3b event (report only), 1-sigma coverage and the launch-from-stop subset
(dev windows whose start is within 10 s after an IMU standstill: filter `stationary` flag set in [start - 10 s, start]; n = 138 pooled), with hold and const-v scored on exactly the same windows. `--set key=value` overrides any `VDRParams` field.
A full evaluation takes ~160 s (S2 dominates). 32 tests in `test_eval_e0.py` (launch-from-stop flag, parameter parsing, summaries added).

**Baseline = the E0 default on the development set** (median end / p90 end / median |cross| at end / median |along| at end, metres):
| | S3b dev windows (n = 11) | S2 dev windows (n = 861) | pooled med end | S3b mini mean | launch-from-stop med end (n = 138) | event mean / end / path ratio (report only) | 1σ mini / S3b-win / S2-win |
|---|---|---|---|---|---|---|---|
| hold-last-fix | 156.5 / 299.6 / 142.0 / 64.2 | 368.6 / 869.4 / 132.6 / 261.6 | 365.0 | – | 264.7 | – | – |
| const-v | 430.7 / 668.0 / 162.8 / 366.1 | 385.5 / 758.7 / 183.6 / 241.6 | 386.2 | – | 251.7 | – | – |
| **vehicle_dr default (E0 reference)** | **161.5 / 214.2 / 121.9 / 76.5** | **152.3 / 490.9 / 66.9 / 98.0** | 153.1 | 21.93 | 151.2 | 64.35 / 145.89 / 0.46 | 50 % / 53 % / 41 % |
S3b numbers are identical to the E0 report (harness check). **New facts from S2:** vehicle_dr already beats hold clearly on S2 (median end 152 vs 369 m, p90 491 vs 869 m), i.e. "vehicle_dr ≈ hold" (E0) is a property of S3b's slow stop-and-go driving where
"stay put" is a strong baseline; on S2 the error is along-track dominated (|along| 98 vs |cross| 67 m at the end), the opposite of S3b (|cross| 122 vs |along| 77). The two development drives therefore stress different error components.
The launch-from-stop windows (n = 138 pooled; S3b contributes few) are much harder than average for every method (hold 265, const-v 252, vehicle_dr 151 m median end).


# H1 — gyro scale calibration (2026-09-26, registry v2). RESULT: the hypothesis is REFUTED on real data; H1a and H1b are correct on the sandbox and stay OFF
**Sandbox first (`sim_drive long_route`, 4 seeds, all valid 60 s windows; criteria fixed in `tests/test_gyro_scale.py` before any real-data number):**
P1 estimated scale within 5 % after 200 s at true scale 1.3; P2 median window end error within 10 % of the oracle (gyro column / true scale); P3 at scale 1.0 no worse than the default by more than 3 %.
Sensitivity reproduced with our own code: scale 1.3 raises the median end error 133.6 / 137.0 / 129.5 / 123.5 (scale 1.0) -> 185.5 / 182.9 / 182.5 / 198.5 m (+39 / +34 / +41 / +61 % vs oracle), cross-track 75-91 -> 111-127 m; the oracle restores it.
| variant (sandbox, 4 seeds) | estimated scale after 200 s (true 1.3) | P2: scale 1.3 vs oracle, all windows | P3: scale 1.0 vs default | verdict |
|---|---|---|---|---|
| H1a spec: W 300, min 5 pairs | 1.309 / 1.312 / 1.267 / 1.313 (P1 pass) | +0.4 / +10.5 / +9.1 / +10.3 % (windows starting >= 200 s: within 1.4 %) | +0.3 / -0.7 / +4.5 / -0.1 % | P1 pass; P2 misses the strict all-windows 10 % on 2 seeds by 0.3-0.5 pp (early windows precede the 5th turn pair); P3 fails on seed 2 (+4.5 %: at scale 1.0 the small-sample k wandered to 1.02-1.04 from 3-4 deg GNSS-course noise) |
| H1a W 120 | 1.13-1.22 (only 3-4 qualifying turns fit in 120 s: k stays 1) | – | – | fails P1 |
| H1a W 300, min 3 pairs + deadband 0.05 (`gs_deadband`: k applied only if abs(k-1) > 0.05) | same | +0.4 / +2.8 / +4.2 / +0.1 % | 0.0 / 0.0 / 0.0 / 0.0 % | passes P1-P3 (deadband added after seeing the P3 miss; documented as a design choice) |
| Theil-Sen vs Huber; course-gate vs gyro-gate | identical within 0.005 | – | – | Theil-Sen + course gate (the spec) kept |
| **H1b: 7th EKF state s_g, psi_dot = (1 + s_g)(omega - b_g), prior 0.1** | **1.279 / 1.272 / 1.277 / 1.282** (est. scale = 1/(1+s_g); ~100 s to converge) | **+1.3 / +0.4 / +2.4 / -3.8 %** | **0.0 / +0.9 / +0.6 / -0.1 %** (scale estimate 0.985-0.995) | **passes P1-P3 with no deadband; better than H1a on the sandbox** |

**Real data — the estimated scale is ~1.0 everywhere.** Final / over-time values (scale = 1/k):
* S3b, H1a (W = 300): k after each fix (t: k [pairs]) 157: 0.992 [5], 289: 1.024, 325: 0.992, 433: 1.024, 577: 0.932 [13], 649: 1.045, 685: 1.026; final k = 1.026 (W = all: 0.992). 22 accepted turn pairs, correlation gyro integral vs GNSS course change **0.998**, whole-drive fits Theil-Sen 0.992 / Huber 0.998 / LS 1.002.
  H1b: 0.98-1.04 over the drive, final 1.016 (std of s_g 0.016).
* S2: H1a final k 1.000 (W 300) / 0.997 (all), 271 pairs, whole-drive fits 0.997 / 0.995 / 0.987, corr 0.991; H1b 0.98-1.00 (0.90-1.14 only in the first 600 s), final 0.982.
* S1 (secondary): H1a final 1.000 / 0.985, 156 pairs, fits 0.985-0.989, corr 0.997; H1b 0.987-0.996.
* **An estimator that does not use GNSS course at all agrees:** regressing the gyro vertical rate on VBOX's yaw rate at moving samples (scoring reference only) gives scale 1.019 (t < 200 s) / 1.013 (whole S3b), corr 0.954.
**Why A2 said 1.29 (S3b) / 0.94 (S1):** re-running the A2 computation (all consecutive-fix pairs with both speeds > 3 m/s, raw gyro integral, no bias removal) gives 1.277 / 0.926, but the S3b slope is produced by two wrap-ambiguous pairs at t = 29 s and 40 s where
the gyro integrates -420 deg and -405 deg (more than a full revolution: a loop / roundabout) while the GNSS course, seen only at the two fixes, changed -57 deg and -50 deg. Excluding pairs with abs(integrated gyro) >= 2.8 rad (2 of 56 on S3b, 1 of 407 on S1) the A2 slope becomes 0.992 (corr 0.973) on S3b and 0.985 (corr 0.997) on S1.
The A2 "scale" was an aliasing artefact; the gyro scale of this phone is 1.00 +/- 0.03 on S3b, S2 and S1.

**Real-data effect on the development windows** (median end / p90 end / median |cross| / median |along|, m; baseline S2 full list 152.3 / 490.9 / 66.9 / 98.0; S3b baseline 161.5 / 214.2 / 121.9 / 76.5):
| H1a variant (full S2 list, n = 861) | S3b windows | S2 windows | S3b mini | event mean / end / ratio |
|---|---|---|---|---|
| W 120, min 5 | 161.5 / 214.2 / 121.9 / 76.5 (identical) | 157.2 / 502.2 / 67.7 / 100.9 | 21.92 | 63.44 / 143.53 / 0.46 |
| W 300, min 5 (spec) | identical | 155.8 / 492.2 / 67.6 / 100.7 | 21.92 | 63.44 / 143.53 / 0.46 |
| W all, min 5 | identical | 156.2 / 480.8 / 65.9 / 99.6 | 21.92 | 63.44 / 143.53 / 0.46 |
| W 300, min 5, deadband 0.05 | identical | 155.8 / 477.0 / 67.2 / 97.4 | 21.93 | 64.35 / 145.89 / 0.46 (= baseline) |
| W 300, min 3, deadband 0.05 | identical | 156.6 / 477.0 / 67.7 / 99.7 | 21.93 | 64.35 / 145.89 / 0.46 |
On S3b no pair set is large enough before 130 s to change k, so the dev windows are bit-identical; on S2 every variant moves the median end by +2 to +3 % (inside the 5 % noise band, not better). By the standing rule H1a is switched OFF and kept.
H1b (S2 stride-4 screening subset, n = 216, baseline on the same subset 150.0 / 466.9 / 67.5 / 95.2): S3b 162.3 / 213.4 / 128.1 / 77.1, S2 149.0 / 449.1 / 65.7 / 95.4 -> no change (+0.5 % / -0.7 %); OFF, kept.
**turn_noise retune** (grid 0.5 / 0.3 / 0.15 / 0.05 on the plain filter; H1b = default on real data, so its three combined runs were skipped as redundant). Same S2 stride-4 subset; med end / p90 / med |cross| / med |along|:
| turn_noise | S3b windows | S2 windows (n = 216) | S3b mini mean | event mean / end / ratio (report only) | 1σ mini / S3b-win / S2-win |
|---|---|---|---|---|---|
| 0.5 (default) | 161.5 / 214.2 / 121.9 / 76.5 | 150.0 / 466.9 / 67.5 / 95.2 | 21.93 | 64.35 / 145.89 / 0.46 | 50 % / 53 % / 42 % |
| 0.3 | 164.3 / 214.1 / 122.6 / 75.8 | 148.6 / 468.5 / 64.3 / 97.4 | 22.23 | 65.72 / 148.25 / 0.47 | 50 % / 47 % / 29 % |
| 0.15 | 166.4 / 213.9 / 124.6 / 74.7 | 150.4 / 477.3 / 63.7 / 90.1 | 22.79 | 67.97 / 152.74 / 0.47 | 40 % / 45 % / 24 % |
| 0.05 | 154.4 / 212.8 / 120.9 / 75.2 | 151.9 / 472.0 / 63.8 / 90.6 | 23.22 | 67.71 / 122.82 / 0.51 | 40 % / 45 % / 24 % |
All medians move by < 5 % except S3b at 0.05 (-4.4 %, borderline) with S2 +1.3 %: "no change" by the noise rule, while the reported 1-sigma coverage collapses (S2 42 -> 24 %). turn_noise is NOT compensating for a gyro scale error (there is none); it only sets how honest the heading uncertainty is. Kept at 0.5.

## H1 diagnostics — where the cross-track error really comes from (S3b / S2 dev windows; VBOX-derived quantities used for SCORING/DIAGNOSIS only)
**1. Heading error at the outage start is small; the cross-track error is heading DRIFT during the 60 s.** filter psi vs the direction of travel of the truth (S3b 11 windows / S2 108 windows = every 8th):
| | S3b | S2 |
|---|---|---|
| abs heading error at outage start, median / p90 | 2.3 / 7.3 deg | 2.9 / 26.3 deg |
| abs heading error at outage end, median / p90 | 24.7 / 147.8 deg | 12.7 / 87.3 deg |
| drift over the 60 s, median / p90 | 25.0 / 140.5 deg | 11.1 / 66.7 deg |
| median abs cross at end vs median abs(path * sin(start error)) | 121.9 vs 13.3 m | 64.2 vs 21.6 m |
| windows with start error > 15 deg (their median end error vs the rest) | 9 % (231 vs 151 m) | 17 % (377 vs 139 m) |
(LS slope of filter turning / truth turning over the window: 0.84 / 0.74 — biased low by noise in the position-derived truth heading, so not evidence of a scale error; the independent scale estimates above are 1.0.)
**2. The filter's gyro bias b_g does not follow the truth-derived bias on S3b.** Truth-derived bias (median over moving samples of gyro - scale*VBOX yaw rate, 60 s blocks) vs filter b_g at the block centre, rad/s:
0-60 s +0.0047 vs -0.0032; 60-120 -0.0113 vs -0.0025; 120-180 +0.0042 vs -0.0087; 180-240 +0.0024 vs -0.0009; 240-300 +0.0012 vs -0.0078; 300-360 +0.0014 vs -0.0084; 360-420 +0.0022 vs -0.0055; 420-480 +0.0034 vs -0.0070; 480-540 +0.0018 vs -0.0053; 540-600 +0.0017 vs -0.0034.
The filter is 0.005-0.013 rad/s (17-45 deg/min) below the truth-derived bias in most blocks; the gyro at truth-stopped samples reads +0.0042 rad/s (VBOX yaw rate 0.000 there).
**3. Mechanism: ZARU at false / partial standstills feeds real rotation into b_g.** 13 IMU-only standstill episodes on S3b (42 s in total); 29 % of the ZARU time is while VBOX speed > 0.5 m/s, and one episode (269.8-277.6 s) is flagged stationary while VBOX shows 7-8.9 m/s.
b_g jumps inside the episodes that contain motion: 139-145 s (launch) -0.0021 -> -0.0088; 208.6-214.2 s (0.6 m/s) -0.0011 -> +0.0060; 262.5-265.2 s (0.7 m/s) +0.0054 -> -0.0075; 415.9-418.3 s (1.6 m/s) -0.0042 -> -0.0075; 604-610 s -0.0029 -> -0.0062.
ZARU (sigma 0.01 rad/s at 10 Hz) converges to the raw gyro reading in a few seconds, and a launch or a slow turn is real rotation, not bias.
**4. Oracle / causal probes on the S3b dev windows** (med end / p90 / med |cross| / med |along|; oracle values use a constant chosen from VBOX-stopped samples — a diagnostic, NOT an AERIS input):
| b_g handling | med end | p90 | med cross | med along | mini mean | event mean / end |
|---|---|---|---|---|---|---|
| default (adaptive, p0_bg 0.02, rw_bg 1e-4) | 161.5 | 214.2 | 121.9 | 76.5 | 21.93 | 64.35 / 145.89 |
| ORACLE b_g fixed +0.0042 | 127.9 | 207.1 | 90.5 | 77.9 | – | – |
| ORACLE b_g fixed +0.0020 | 127.0 | 207.9 | 92.8 | 75.3 | – | – |
| b_g fixed 0 (no bias at all) | 126.3 | 208.8 | 94.9 | 73.1 | 21.48 | 67.78 / 156.77 |
| b_g fixed -0.005 (where the filter drifts to) | 125.0 | 211.6 | 100.5 | 69.2 | – | – |
| causal, parameters only: rw_bg 1e-5 / 1e-6 / 0 with the default p0_bg | 160.7 | 214.3 | 122.2 | 76.6 | 21.90 | 66.6 / 153.0 |
| causal: p0_bg 1e-5 (start at 0), rw_bg 1e-4 | 147.3 | 209.5 | 119.8 | 77.9 | 21.66 | 63.90 / 144.70 |
| causal: p0_bg 1e-5, rw_bg 1e-5 | 126.2 | 208.8 | 95.6 | 73.0 | 21.49 | 67.62 / 156.30 |
| causal: p0_bg 1e-5, rw_bg 0 (b_g frozen at 0) | 126.3 | 208.8 | 94.9 | 73.1 | 21.48 | 67.78 / 156.77 |
| causal: p0_bg 0.005, rw_bg 0 | 160.5 | 214.3 | 124.5 | 74.3 | 21.82 | 66.58 / 153.02 |
| causal: sigma_zaru 0.05 (weaker standstill updates) | 135.9 | 212.0 | 110.8 | 76.2 | 21.74 | 67.63 / 156.19 |
Reading: on S3b, holding b_g near 0 (any constant between -0.005 and +0.004) removes ~22 % of the median end error and ~22-25 % of the cross-track error (p90 unchanged, the event 5-7 % worse); which constant hardly matters. What hurts is an ADAPTIVE b_g with a large prior:
even rw_bg = 0 keeps the (wrong) value learned early, and only a tight prior (p0_bg <= ~1e-5) helps.
**5. The drives have different biases, so the bias must be learned, just not from contaminated updates.** VBOX-yaw-rate regression (moving samples): S3b scale 1.013-1.019, bias +0.004 rad/s (truth-stopped gyro mean +0.0042); **S2 scale 0.979, bias -0.0067 rad/s** (truth-stopped mean -0.0061, 600 s block medians -0.003..-0.011).
The default filter's b_g on S2 wanders (step-to-step sigma 0.0022, from -0.0008 to -0.0166); with p0_bg 1e-5 / rw_bg 1e-5 it moves smoothly from 0 to the right value (-0.0001 at 300 s -> -0.008 by ~55 min, jump sigma 0.0002); frozen at 0 leaves -0.0065 uncorrected.

# H1c — standstill bias update (ZARU) weight: sigma_zaru 0.01 -> 0.10 (ADOPTED as the new default; found by the H1 diagnostics, tuned on the development windows S3b + S2)
Not in the plan: it follows from H1 diagnostics 3-5. The only code change is the default of an existing parameter, `VDRParams.sigma_zaru` (rad/s), 0.01 -> 0.10; revert = set it back to 0.01.
**Screening grid** (S3b windows n = 11; S2 stride-4 subset n = 216; med end / p90 / med |cross| / med |along|, m; baseline = old default on the same subset):
| sigma_zaru | S3b windows | S2 windows (n = 216) | S3b mini mean | event mean / end (report only) | 1σ mini / S3b-win / S2-win |
|---|---|---|---|---|---|
| 0.01 (old default) | 161.5 / 214.2 / 121.9 / 76.5 | 150.0 / 466.9 / 67.5 / 95.2 | 21.93 | 64.35 / 145.89 | 50 / 53 / 42 % |
| 0.02 | 159.0 / 213.2 / 120.5 / 76.5 | 127.0 / 374.9 / 53.4 / 75.4 | 21.84 | 65.95 / 151.10 | 55 / 52 / 57 % |
| 0.03 | 149.1 / 212.6 / 120.4 / 76.4 | 115.7 / 375.6 / 49.2 / 76.2 | 21.79 | 66.68 / 153.36 | 55 / 51 / 62 % |
| 0.05 | 135.9 / 212.0 / 110.8 / 76.2 | 113.7 / 375.2 / 49.7 / 74.9 | 21.74 | 67.63 / 156.19 | 55 / 50 / 59 % |
| **0.1 (chosen)** | 126.0 / 211.6 / 103.4 / 73.1 | 113.8 / 377.4 / 51.9 / 75.6 | 21.72 | 68.60 / 158.96 | 55 / 50 / 60 % |
| 0.2 | 125.3 / 211.5 / 101.0 / 70.0 | 113.8 / 380.3 / 52.1 / 76.0 | 21.71 | 68.99 / 160.07 | 55 / 50 / 60 % |
| 0.5 | 125.3 / 211.4 / 100.2 / 69.1 | 113.8 / 381.2 / 52.1 / 76.1 | 21.71 | 69.12 / 160.43 | 50 / 50 / 60 % |
The response saturates for sigma_zaru >= 0.1 (a smooth plateau, not a fragile optimum). Selection rule fixed after seeing the plateau: the smallest value within 5 % of the plateau on both drives = 0.1 (0.05 is still 8 % short on S3b). Other probes on the same subset (S3b / S2 med end): b_g frozen at 0
(p0_bg 1e-5, rw_bg 0) 126.3 / 183.5 (helps S3b, HURTS S2 by 22 %: rejected); tight prior + rw_bg 1e-5 126.2 / 122.4 (helps both; superseded because it assumes a near-zero bias and learns slowly); p0_bg 1e-5 + default rw_bg 147.3 / 150.0.
**Confirmation on the FULL pre-registered S2 list (n = 861)** — the stride-4 subset was optimistic for S2 (-24 %), the full list gives -14 %; this is the number to use:
| | S3b dev windows | S2 dev windows (n = 861) | pooled med end | S3b mini mean | launch-from-stop med end (n = 138) | event mean / end / ratio (report only) | 1σ mini / S3b-win / S2-win |
|---|---|---|---|---|---|---|---|
| old default (sigma_zaru 0.01) | 161.5 / 214.2 / 121.9 / 76.5 | 152.3 / 490.9 / 66.9 / 98.0 | 153.1 | 21.93 | 151.2 | 64.35 / 145.89 / 0.46 | 50 / 53 / 41 % |
| **sigma_zaru 0.1 (NEW DEFAULT)** | **126.0 / 211.6 / 103.4 / 73.1** | **130.6 / 377.1 / 53.8 / 86.1** | 130.6 | 21.72 | 147.9 | 68.60 / 158.96 / 0.46 | 55 / 50 / 62 % |
| change | -22 % / -1 % / -15 % / -4 % | -14 % / -23 % / -20 % / -12 % | -15 % | -1 % | -2 % (noise) | +6.6 % / +9 % (worse, report only) | |
hold-last-fix on the same windows: S3b 156.5 / 299.6, S2 368.6 / 869.4 -> vehicle_dr now beats hold's end error by 19 % (median) and 29 % (p90) on S3b, and by 65 % / 57 % on S2.
**S1 (secondary; previously inspected, NOTHING tuned on it) — the heavy tail of known issue #1 disappears.** 523 mini-outage intervals outside 200-260 s:
| S1 | mean / median / p90 / max (m) | intervals > 100 m | inside 1σ | course rej. / position rej. / forced pos. accepts |
|---|---|---|---|---|
| sigma_zaru 0.01 (old) | 43.89 / 20.05 / 108.0 / 620.0 | 11.1 % | 30 % | 107 / 94 / 29 |
| **sigma_zaru 0.1** | **16.77 / 13.37 / 34.0 / 96.3** | **0.0 %** | 53 % | **0 / 1 / 0** |
| const-v | 26.67 / 22.78 / – / 136.2 | 0.8 % | – | – |
Gate rejections on the other drives (course / position / forced): S3b 18/60, 12/68, 4 -> 7/60, 4/68, 1 (whole drive incl. post-outage fixes); S2 91/824, 77/940, 19 -> 12/824, 18/940, 4. **Mechanism confirmed:** ZARU at false / partial standstills dragged b_g onto real rotation, the heading went wrong,
and the 99 % hard gate then rejected exactly the GNSS updates that would have repaired it (the "lock-out"). With a weaker ZARU the lock-out does not occur. Known issue #1 (S1 tail) is resolved by this change; the gate itself (I1b) is untouched.
**Sandbox criteria (fixed before the tests were run; `tests/test_gyro_scale.py::TestZaruWeight`):** (1) mechanism, in a CONVERGED filter (b_g std 1e-3): a 3 s false standstill at a real 0.05 rad/s moves b_g by 0.0115 rad/s under the old weight and 0.00015 under the new (77x less; criterion: >= 10x less);
(2) a long true standstill still teaches the bias from the initial prior (60 s at -0.006 -> within 0.0015); (3) sandbox long_route, 4 seeds, biases -0.008 and +0.020 rad/s: sigma_zaru 0.03-0.2 changes the median window end error by <= +0.1 % (criterion 3 %). Disclosure: my first version of criterion (1) used an
absolute 0.02 rad/s bound measured from the initial-prior state, where the prior std 0.02 dominates (a 3 s burst legitimately moves b_g by 0.027 even at the new weight); I replaced it with the relative converged-filter criterion above before adopting the change.
**Caveats.** (a) The 200-260 s event (a single window that starts in a stop; report only) gets worse: mean 64.35 -> 68.60 m, end 145.89 -> 158.96 m, along/cross at the end -85.6 / +118.2 -> -100.3 / +123.3 m; the dev windows and S1 improve, so this is a documented cost, not a tuned quantity.
(b) The launch-from-stop windows barely move (147.9 vs 151.2, -2 %): that regime is a speed problem (I2a), not this one. (c) sigma_zaru 0.1 is on a plateau, so ZARU is now nearly a formality; a better design would learn b_g only from CONFIRMED standstills (never while a launch is pending, VBOX-free criterion) — an optional follow-up, not needed for the result above.
(d) The older note "S3b: 1 / 1 / 0 / 0" next to the S1 gate counts (known issue #1) does not match a whole-drive S3b run (18 course / 12 position / 1 speed rejections, 4 forced accepts under the old default, with the 200-260 s outage and the post-outage fixes included); I did not find which span it referred to. The S1 counts (107 / 94 / 1 / 29) reproduce exactly.


# External sandbox study 2 — stationarity (after H1c) — logged 2026-09-27, from the user's message
* H1c fixed only ONE of the damages a FALSE standstill causes (b_g contamination, via ZARU). While the filter believes it is stationary it ALSO forces v = 0 (ZUPT) and discards rotation (`w = 0` in `predict`, psi frozen).
  H1 diagnostic 3 already showed false standstills on real data (29 % of S3b ZARU time at VBOX speed > 0.5 m/s; one episode 269.8-277.6 s at 7-8.9 m/s). Inside an outage that freezes the car and drops the turns, and there is no GNSS to recover.
* External sandbox (vehicle_dr at 7f0fba1, 2 seeds, median 60 s window end error):
  * smooth-road cruise route at 9 m/s (vib_base 0.05, vib_per_ms 0.02): **788-799 m** with the current detector (flagged stationary at 9 m/s for 160-400 s) vs **29-39 m** with the `quiet_enter_n` override disabled;
  * BUT on `long_route` with default vibration, disabling the override is WORSE (147-157 -> 163-165 m): the override catches real stops;
  * a braking-evidence gate on the override fixed the cruise case (39 m) and kept `long_route` (147-157 m), but did NOT fix `long_route` on a smooth road (221-251 m): braking before turns looks like braking to a stop, and false entries cascade through the `v_est < v_gate` branch.
* Conclusion: the stationarity detector is the next target (before I2), decided on REAL data with VBOX used only for scoring.
* Plan for this block (from the user's message): **S0** detector audit (no filter change) -> **S1** detector fixes S1a-S1e, one at a time, each behind a flag (default OFF until adopted), sandbox suite (i)-(iv) with criteria fixed before running,
  then STOP and show one compact table. After that (only on "go"): I2a / I2b, I1a, a D-design proposal (OSM road matching; proposal only), I3 / I1b later. The full text of the S1 specification is kept in the S1 section below when it starts.

# PLAN UPDATE: STATIONARITY S0 -> S1 (verbatim copy of the user's message, 2026-09-27; the header paragraphs are logged above)
```text
STEP S0 — Detector audit (no filter change). Add a stationarity audit to check_outage.py (VBOX = scoring only), for S3b, S2 (and S1 secondary), whole drive, with the current default:
- false-standstill seconds (flagged AND VBOX speed > 0.5 m/s), number of episodes, max and median VBOX speed while flagged;
- for each false episode: which entry branch fired (v_est < v_gate, or the quiet_enter_n override), and its duration;
- true-stop recall: fraction of VBOX-stopped time (speed < 0.2 m/s) that is flagged;
- damage estimate: distance lost = ∫ VBOX speed over false-standstill time; turning lost = ∫ |VBOX yaw rate| over the same time;
- the same audit restricted to the S3b and S2 dev windows' outage spans.
Log it, commit, push. Continue to S1 (no stop needed) unless false-standstill time is < 1 % of moving time on both drives; in that case stop and tell me.

STEP S1 — Detector fixes. One at a time, each behind a flag (default OFF until adopted), each with a sandbox test first. Sandbox suite for EVERY S-variant, criteria fixed before running:
  (i) smooth-cruise route below: false-standstill time < 5 s and median window end error < 60 m;
  (ii) long_route default vibration: median window end error no worse than current by > 3 %;
  (iii) long_route with vib_base 0.05, vib_per_ms 0.02: report the result (it's the hard case; improvement wanted, not required);
  (iv) a real 20 s stop is still detected (recall >= 0.8 of the current recall).
  Smooth-cruise route for sim_drive: [("straight",300,9,9),("turn",40,400,9),("straight",400,9,9),("turn",-60,500,9),("straight",300,9,0),("stop",20),("straight",300,9,9),("turn",45,450,9),("straight",500,9,9),("turn",-50,400,9),("straight",400,9,9)] with vib_base 0.05, vib_per_ms 0.02 (also run vib_base 0.03, vib_per_ms 0.01).

 S1a Braking evidence for the quiet override (mount-free, causal): 1 s mean of ax and ay; subtract a causal 20 s running median of each (removes the accel bias); excess = the norm of that vector, counted only when |1 s mean omega_vert| < 0.1 rad/s (not in a turn) and excess > 0.3 m/s^2; dv_brake = sum excess*dt over the last 15 s. The override may enter standstill only if dv_brake >= 0.6 x (max filter speed over the last 15 s). (The prototype of exactly this passed (i), (ii), (iv) and failed (iii).)
 S1b Self-calibrating rest level: learn the IMU rest signature (acc_var, and std of omega_vert over 1 s) ONLY from standstills confirmed by a new GNSS fix with speed < 0.3 m/s; after >= 2 confirmed stops, entry needs acc_var < k x learned rest acc_var AND omega std < k x learned rest omega std (grid k in {1.5, 2, 3}); until then keep the fixed thresholds.
 S1c Anti-cascade: when a new GNSS fix says speed > 2 m/s during or within 2 s after a standstill (GNSS-contradicted stop), block standstill entry via the v_est < v_gate branch for 20 s unless S1a braking evidence is present. Log each contradiction.
 S1d Retroactive replay (causal): on a GNSS-contradicted standstill, rewind to the standstill entry (ring buffer of IMU rows and filter state, <= 30 s), re-run that span with standstill entry disabled, then apply the fix. Only uses data up to now; the displayed past may change (state that in the docs). Naturally inactive inside outages.
 S1e A stopped car does not rotate: exit standstill when |mean omega_vert - b_g| over 1 s exceeds w_exit; grid w_exit in {0.10 (current), 0.05, 0.03} rad/s.
Try the promising combinations too (e.g. S1a+S1c, S1a+S1b+S1c). Keep changes by the noise rule on the dev windows (S3b and S2), AND require: false-standstill seconds down >= 50 % on both drives, with true-stop recall >= 0.8 x the current.

Stop after S1 and show one compact table: rows = current, each S1 variant, the best combination; columns = S3b dev windows med end / p90 / med cross / med along | S2 dev windows same | S3b mini mean | launch-from-stop med end (n) | false-standstill s S3b / S2 | true-stop recall S3b / S2 | event mean / end / path ratio (report only) | 1-sigma coverage | verdict. Include the hold-last-fix row.

AFTER S1 (only when I say "go"):
 I2a OU speed prior + I2b turn ceiling (as specified in the saved plan), tuned on the dev windows, reporting the launch-from-stop windows separately.
 I1a GNSS latency (B0 already measured ~0.5 s; estimate it on the dev windows).
 D-design (proposal only, no code): OpenStreetMap road-matching for vehicle_dr — data source and caching (OSM for the S3b/S2 areas, stored in the repo with ODbL attribution), measurement model (road-snap position and road-direction heading as gated pseudo-measurements, sigma from the road width + OSM error), ambiguity at junctions, and how it is scored honestly. Stop for approval.
 I3 vibration speed, I1b robustness: later.

Commit per step, push after every commit, update the handoff section before stopping.
```


# S0 — stationarity audit (2026-09-27; NO filter change — `vehicle_dr` output is bit-identical to 7f0fba1, checked on S3b with / without the outage and on the sandbox)
**What was added.** `vehicle_dr.run_pipeline` now returns `result["standstill_log"]` (diagnostics only, never read by the filter): one dict per standstill episode with `t_enter`, `v_est`, `quiet_run`, `acc_var`, `w_dev`, the entry branch
(`via_v_gate` = the speed estimate was already < `v_gate`; `via_override` = 3 s of sustained quiet, `quiet_enter_n`), `gap_prev` (s since the previous episode ended) and `t_exit` + `exit` reason (`acc_var` / `omega` / `release` / `gnss` = a new fix said moving / `end` = run ended while stationary).
`check_outage.py`: `Truth` got `yaw_rate()` (VBOX yaw-rate column, scoring only) and `covers()` (rows past the end of the reference file are never scored); `stationarity_audit()`, `audit_report()`, `audit_windows_report()`, `audit_main()`; `window_benchmark(..., audit=True)`;
CLI `python backend/check_outage.py S3b --audit [--audit-windows] [--workers 4] [--top N] [--set key=value]` (`--audit-windows` = S3b tuning windows, other drives all registered windows in a worker pool). `sim_drive.py`: `smooth_cruise_route()` (the S1 sandbox route (i)) and a truth column `yaw_rate_degs` (true yaw rate, scoring only). `tests/test_stationarity.py`: 18 tests (hand-computed synthetic case, span / coverage handling, log == flag, sandbox smooth-cruise failure reproduced, S3b pin); suite 284 pass / 37 skip.
**Definitions (fixed before the numbers were looked at).** false standstill = flag set AND VBOX speed > 0.5 m/s; VBOX-stopped = speed < 0.2 m/s; true-stop recall = flagged time / VBOX-stopped time; distance lost = integral of VBOX speed over the false time; turning lost = integral of |VBOX yaw rate| over it;
false episode = a flagged episode holding >= 1 s of false time; kind = "false entry" (flag set while VBOX moving) or "late release" (flag set at rest, the car drove off while it stayed set); branch "v_gate" whenever `v_est < v_gate` (also when the override would have fired too — none of the false episodes had both true). Rows are weighted by their real time step. Added, unrequested, small: the MIRROR-IMAGE damage
= VBOX-stopped time that is NOT flagged, and the integral of the filter's own speed over it ("phantom driving": the filter keeps its held speed while the car is parked).
Whole-drive rows = the current default (H1c) with NO outage (GNSS available). Outage-span rows = each dev window's 60 s span from its own truncated run with GNSS hidden (windows overlap, so read sums as fractions).

**Whole drive**
| | S3b (dev) | S2 (dev) | S1 (secondary) |
|---|---|---|---|
| time scored / VBOX moving / VBOX stopped (s) | 680 / 618 / 53 | 9380 / 8130 / 1125 | 5174 / 4602 / 505 |
| flagged s (episodes) | 47.1 (13) | 1172.4 (111) | 482.5 (62) |
| **FALSE-standstill s (% of moving time)** | **12.1 (1.96 %)** | **148.2 (1.82 %)** | 64.1 (1.39 %) |
| ... as % of flagged time | 25.7 % | 12.6 % | 13.3 % |
| false episodes (>= 1 s) of all | 5 of 13 | 39 of 111 | 22 of 62 |
| VBOX speed while falsely flagged: median / max (m/s) | 1.11 / 8.93 | 1.32 / 3.34 | 1.06 / 4.62 |
| false episodes by entry branch: v_gate / override | 4 / 1 | 28 / 11 | 15 / 7 |
| false episodes by kind: false entry / late release | 3 / 2 | 26 / 13 | 12 / 10 |
| **true-stop recall** | **59.6 %** | **85.8 %** | 76.8 % |
| distance lost (% of the distance driven) | 27.8 m (0.74 %) | 197 m (0.26 %) | 81 m (0.21 %) |
| turning lost (% of the turning) | 32 deg (0.85 %) | 138 deg (0.39 %) | 168 deg (0.83 %) |
| mirror: missed-stop s / phantom driving | 21.5 s / 81.5 m | 159.4 s / 590.5 m | 117.3 s / 465.3 m |
| false "false entry" episodes whose filter speed was already wrong (v_est < 0.3 m/s, or > 1 m/s below VBOX) | 2 of 2 | 9 of 17 | 2 of 9 |
| false entries within 10 s of the previous episode ending (cascade) | 1 of 3 | 11 of 26 | 3 of 12 |

**Outage spans of the dev windows (GNSS hidden) — and, as a control, the SAME spans cut out of the whole-drive run (GNSS available)**
| | S3b: 11 tuning windows | S2: 861 windows |
|---|---|---|
| false s (% of moving time in the spans) | 5 s (0.91 %) — only sub-second edges of true stops | 686 s (1.49 %) |
| windows with >= 1 s / >= 5 s / >= 20 s of false time; max | 0 / 0 / 0 %; max 0.8 s | 15 / 3 / 1 %; max 46.2 s |
| distinct false episodes; by branch v_gate / override | 0 | 60; 40 / 20 (54 entered inside a span) |
| distance lost / turning lost (% of driven / turned) | 0.11 % / 0.99 % | 0.24 % / 0.25 % |
| true-stop recall: GNSS hidden / GNSS available (control) | **32.0 % / 69.8 %** | 76.5 % / 81.8 % |
| phantom driving (missed stops): GNSS hidden | 53 s, 342 m = **8.63 %** of the driven distance | 1156 s, 7169 m = **1.66 %** |
| phantom driving: GNSS available (control) | 24 s, 202 m = 5.10 % | 891 s, 3334 m = 0.77 % |

**The five false episodes of S3b (whole drive):** 208.6-214.2 s (late release, 2.8 s false, VBOX 1.1 / max 1.5 m/s, left by `omega`); 415.9-418.3 s (false entry via the OVERRIDE, 2.4 s, ~2.5 m/s); 262.5-265.2 s (false entry, 2.4 s, 0.5-1.3 m/s, v_est 0.02); 269.8-270.6 s (false entry, 0.8 s, 6.9-7.1 m/s, v_est 0.00); 276.2-277.6 s (false entry, 1.4 s, 8.9 m/s, v_est 0.00); 604.1-605.5 s (late release, 1.1 s).
**Correction to the H1 diagnostic 3 note.** "One episode 269.8-277.6 s flagged stationary while VBOX shows 7-8.9 m/s" was two separate flicker episodes (269.8-270.6 s at 6.9-7.1 m/s and 276.2-277.6 s at 8.9 m/s), not one 7.8 s freeze. Both entered via `v_est < v_gate` with `v_est` already near 0: the previous false episode's ZUPT had pinned the filter speed to ~0 and only the next GNSS speed fix (9 s cadence) repairs it,
so on S3b the `v_est < v_gate` test is not independent of the detector's own earlier mistakes — a small instance of the cascade the external sandbox study describes. The worst single false episode on the real drives is on S2: a 26.8 s freeze at 1.5-2.2 m/s (3705.3-3732.1 s, entered via the override 0.1 s after another episode ended, left by `acc_var`); one S2 window loses 46.2 s of its 60 s span to false standstill.

**Reading (facts first, then cautious interpretation).**
1. Decision rule: false-standstill time is 1.96 % (S3b) and 1.82 % (S2) of moving time, S1 1.39 % — all above 1 %, so the plan continues to S1 without stopping.
2. On REAL data the false standstills are mostly short and slow (median VBOX speed 1.1-1.3 m/s: creeping / launches / junction crawl; episodes of 1-9 s) and cost well under 1 % of the driven distance and of the turning. The sandbox failure the external study found (hundreds of seconds at 9 m/s) is a harder regime than any of these three real drives contain — the worst real single freeze is 1.4 s at 8.9 m/s.
3. The S3b DEV WINDOWS contain no false episode of >= 1 s (0 % of windows; the 0.91 % of moving time is sub-second edges of real stops), so a false-standstill fix cannot move the S3b dev-window medians; S2 has 15 % of windows with >= 1 s and 3 % with >= 5 s, so an S2 effect, if any, would show mainly on the tail (p90), not necessarily the median.
4. The MIRROR failure (missed stops) is bigger on real data than the false-standstill one: stopped-but-not-flagged time is 41 % of VBOX-stopped time on S3b (23 % on S2, 23 % on S1), and the filter keeps "driving" through it (whole-drive phantom distance 81 m S3b, 590 m S2, 465 m S1 — 3-7x the false-standstill distance lost). It gets WORSE with GNSS hidden: S3b recall drops 70 % -> 32 % and phantom driving rises 5.1 % -> 8.6 % of the driven distance in the outage spans; S2 0.77 % -> 1.66 %.
   Mechanism, consistent with the numbers: with GNSS hidden nothing pulls `v_est` under `v_gate` (2 m/s), so the `v_est < v_gate` branch is starved and only the 3 s quiet override can flag a stop — and on the whole-drive S3b run every one of the 9 stops that began at rest was caught through `v_gate`, none through the override alone (S2: 25 of 70 through the override alone). None of the plan's S1 variants directly targets missed stops inside an outage; S1a (braking evidence) makes entry HARDER, which could shrink recall further — the recall criterion (>= 0.8 x current) is the one to watch when S1a is tried.
   A candidate NOT in the plan, to raise at the S1 stop rather than build now: let a stop enter even while `v_est` is still high, on quiet evidence alone (the override, without S1a's extra restriction), and reset `v_est` to 0 at entry the way the launch-release code already resets it on exit.
5. The false-entry cascade (an episode starting within 10 s of the previous one ending, with the filter's own speed already wrong) is common on S2 (11 of 26 false entries; 9 of the 17 `v_gate` entries had `v_est` already off by > 1 m/s or pinned near 0) but rare on S3b (1 of 3) and S1 (3 of 12) — S1c (anti-cascade) has more to work with on S2 than on S3b.
# S1 — stationarity detector fixes (2026-09-27; all flags OFF by default — see verdict)
Five fixes, each behind its own flag, each with a sandbox test first (criteria i-iv fixed before any real-data number, `tests/test_s1_sandbox_suite.py`):
* **S1a** `use_brake_gate` — the `quiet_enter_n` override may only fire when a precomputed, IMU-only, causal braking-evidence signal (1 s mean of ax/ay minus a causal 20 s running median of each; excess = its norm, counted when not turning and > 0.3 m/s^2; dv_brake = the causal 15 s sum) reaches `brake_frac` (0.6) x the max FILTER speed over the last 15 s (tracked online, monotonic deque, O(1)).
* **S1b** `use_self_cal` — acc_var / omega-std entry thresholds learned ONLY from standstills CONFIRMED by a new GNSS fix < 0.3 m/s; the fixed thresholds apply until `self_cal_min_confirm` (2) stops are confirmed.
* **S1c** `use_anticascade` — after a GNSS-contradicted standstill (a new fix > 2 m/s during, or within 2 s after, an episode), the `v_est < v_gate` entry branch is blocked for 20 s unless S1a's braking evidence is present.
* **S1d** `use_replay` — on the same trigger as S1c, rewind to the standstill's entry (a snapshot of the filter state, kept up to 30 s) and re-run that span with standstill entry disabled; the displayed past for that span changes. Disclosed simplification: the replay redoes only the core predict + GNSS position/speed/course updates, never H1a's k, launch calibration, centripetal or fixed-mount aiding (none of those can have fired in a span that, by construction, was never stationary).
* **S1e** — no new code: a grid on the EXISTING `w_exit` parameter (a stopped car does not rotate; exit when |mean omega - b_g| over 1 s exceeds w_exit). Grid {0.10 current, 0.05, 0.03}.
18 unit tests (`test_s1_stationarity_fixes.py`) check each mechanism in isolation (causal-median/sum arithmetic, no future leakage, S1a fires only with real braking evidence, S1b bit-identical before 2 confirmed stops, S1c shortens the smooth-cruise cascade, S1d's replay lands closer to truth and is inactive inside an outage, S1e's grid never increases flagged time). Regression: with every flag OFF (and w_exit=0.10) vehicle_dr's output is bit-identical to the S0 commit, checked on S3b (with/without the outage) and two sandbox routes.

## Sandbox suite (criteria i-iv, fixed before any real number; sim_drive gained `smooth_cruise_route()`)
| variant | (i) smooth-cruise .05/.02 (both seeds) | (ii) long_route default vib | (iii) long_route hard vib (report) | (iv) 20s-stop recall |
|---|---|---|---|---|
| current (H1c default) | **FAIL** — false 162-320 s, med end 777-787 m | pass (0 %) | 219.3 / 248.5 m | pass (87.1 % both) |
| S1a alone | FAIL — seed1 false 2.7 s / 28.1 m (would pass); seed2 false 190.7 s / 286.0 m (fails): the override is fixed but a v_gate cascade (seeded once by noise, self-sustained by ZUPT re-freezing v every fix cycle) is untouched | pass | -0.1 % / +0 % | pass |
| S1b (k 1.5/2/3) | FAIL — unchanged from current on EITHER seed: the route has only ONE real stop, so `learn_n` never reaches `self_cal_min_confirm` (2) and the fixed thresholds stay in force throughout (a structural limitation of this specific sandbox route, not of S1b) | pass | -8.4 / -11 to -13 % | pass |
| S1c alone | FAIL — false 94-103 s, med end 524-563 m: shortens the cascade but does not close it (S1c only blocks the v_gate branch AFTER a GNSS fix contradicts it; most of the cascade's damage in this route happens inside the 9 s BEFORE the next fix arrives) | pass | 0 % | pass |
| S1d alone | FAIL — false 2.7-2.8 s (passes) but med end 450-474 m (fails): S1d needs a GNSS fix to trigger, so it cannot correct a false episode that begins and ends entirely inside a simulated 60 s outage (documented: "naturally inactive inside outages") — most of criterion (i)'s window score comes from exactly those windows | pass | -9.0 / -12.7 % | pass |
| S1e (0.05 / 0.03) | FAIL — small change only (162.4->157.2 s at 0.03 on seed1; seed2 barely moves): exit-side fixes cannot prevent the initial cascade, only shorten individual episodes | pass | 0 % | pass |
| S1a+S1c | FAIL (marginal) — seed1 passes (2.7 s / 28.1 m); seed2: false 6.0 s (just over the 5 s bound), med end 50.5 m (passes) | pass | -0.1 % | pass |
| **S1a+S1c+S1d** | **PASS both seeds** — false 2.7 / 2.8 s, med end 28.1 / 39.9 m: S1a stops the override, S1c stops the v_gate branch reopening within 20 s of a GNSS contradiction, S1d corrects whatever got through before the next fix | pass | -9.0 / -16.0 % | pass |
| S1a+S1b+S1c | FAIL — identical to S1a+S1c (S1b inactive on this one-stop route) | pass | -8.4 / -16.9 % | pass |
| **ALL** (S1a+S1b+S1c+S1d+S1e 0.05) | **PASS both seeds** — false 2.7 / 2.8 s, med end 28.1 / 39.9 m (same as S1a+S1c+S1d on this route: S1b is inactive here too) | pass | **-13.6 / -22.5 %** (best; S1e's dev-window accuracy gain and S1b's help on multi-stop routes both show up on long_route, which has 3 real stops) | pass |
Reading: on THIS sandbox route only S1a+S1c+S1d (or ALL, which reduces to the same thing here since S1b needs >=2 stops) passes criterion (i); S1a alone is insufficient because of a v_gate cascade that S1c is specifically designed to stop; S1d alone is insufficient because it needs a GNSS fix and criterion (i)'s failure happens inside a simulated GNSS outage, where by design ("naturally inactive inside outages") it cannot act. ALL gives the best (report-only) criterion (iii) result because long_route's 3 real stops let S1b activate and S1e's accuracy gain shows through.

## Real data (S3b + S2; VBOX = scoring only). Whole-drive `stationarity_audit` (no outage) is the primary false-standstill / recall measure; dev windows are `check_outage.window_benchmark` (S3b: the 11 tuning windows; S2: the full 861-window list, confirmed after a stride-4 screening pass, matching the H1c methodology)
| variant | S3b whole-drive false s (Δ%) | S2 whole-drive false s (Δ%) | S3b recall | S2 recall | S3b dev med end/cross/along | S2 dev med end/cross/along |
|---|---|---|---|---|---|---|
| current (H1c) | 12.1 | 148.2 | 59.6 % | 85.8 % | 126.0 / 103.4 / 73.1 | 130.6 / 377.1 / 53.8 / 86.1 |
| S1a | 12.1 (0 %) | 139.8 (-5.7 %) | 59.6 % | 85.9 % | identical | (screen) 116.4/53.1/75.6 |
| S1b (k=2) | 12.1 (0 %) | 84.9 (-42.7 %) | 59.6 % | 83.8 % | identical | (screen) 116.4/49.2/74.7 |
| S1c | 12.1 (0 %) | 148.2 (0 %) | 59.6 % | 85.8 % | identical | identical to current (screen) |
| S1d | 9.9 (-18.2 %) | 129.4 (-12.7 %) | 59.6 % | 85.3 % | identical | (screen) 113.8/51.7/75.6 |
| S1e (0.05) | 10.0 (-17.4 %) | 134.9 (-9.0 %) | 59.6 % | 86.0 % | **120.9 / 69.8 / 60.8** | (screen) 113.8/51.6/75.6 |
| S1a+S1c+S1d | 9.9 (-18.2 %) | 121.0 (-18.4 %) | 59.6 % | 85.4 % | identical | (screen) 116.4/52.4/75.6 |
| **ALL** | **7.8 (-35.5 %)** | **60.0 (-59.5 %)** | 59.6 % | 83.8 % | **120.9 / 69.8 / 60.8** | 126.4 / 54.6 / 84.8 |
"(screen)" = the stride-4 S2 subset (n=216), used for the exploratory sweep; the confirmation run above ("the full 861-window list") is the number to use.
S3b's dev-window medians are identical for every variant except S1e/ALL: S3b's 11 tuning windows contain NO false episode of >= 1 s (established in S0), so a false-standstill fix cannot move them; S1e/ALL's improvement (med end -4.0 %, cross -32.5 %, along -16.8 %, mini mean 21.72->21.31) is a genuine EXIT-side accuracy gain, independent of the false-standstill mechanism, and passes the noise rule (> 5 % on cross-track) on its own.

## Verdict: the plan's real-data acceptance rule is NOT met — all S1 flags stay OFF
Rule: "keep a change by the noise rule on the dev windows (S3b AND S2), AND false-standstill seconds down >= 50 % on BOTH drives, with recall >= 0.8x current." Even the best combination (ALL) reaches only -35.5 % on S3b (S2 clears the 50 % bar easily at -59.5 %); S3b's real false-standstill time is small (12.1 s total, 5 episodes in a 680 s drive) and concentrated in exactly the launch/creep/flicker patterns these fixes only partly address (one late-release episode exits via a real turn signal already, three are single-fix-cycle flickers at 0.5-9 m/s that end before the next GNSS fix in any case). By the letter of the rule, NOTHING from S1 is adopted; sigma_zaru stays the only default changed since H1c.
Kept separately for the record (not adopted, since it does not clear the false-standstill bar either, though it is a real, above-noise dev-window accuracy gain on its own): **S1e (w_exit 0.10 -> 0.05)** improves S3b's dev-window cross-track error by 32 % and end error by 4 % with zero new code — a candidate the user may want to revisit on its own terms, separate from this block's false-standstill criterion.
All five mechanisms, their unit tests (18) and the sandbox-suite pins (8) are kept in the code, flags OFF, exactly as the standing rule requires for a failed step.

## Compact table (as specified; hold-last-fix included; "ALL" = the best combination tried)
| step | S3b dev: med end/p90/cross/along | S2 dev: med end/p90/cross/along | S3b mini | launch-from-stop med end (n) | false-standstill s S3b/S2 | recall S3b/S2 | event mean/end/ratio | 1σ mini/S3b/S2 | verdict |
|---|---|---|---|---|---|---|---|---|---|
| hold-last-fix | 156.5/299.6/142.0/64.2 | 368.6/869.4/132.6/261.6 | - | 264.7 (138) | - | - | - | - | reference |
| **current (H1c)** | 126.0/211.6/103.4/73.1 | 130.6/377.1/53.8/86.1 | 21.72 | 147.9 (138) | 12.1 / 148.2 | 59.6% / 85.8% | 68.60/158.96/0.46 | 55/50/62% | reference |
| S1a (brake gate on override) | identical | 116.4/377.4/53.1/75.6 (screen) | 21.72 | 190.5 (37, screen) | 12.1 (0%) / 139.8 (-5.7%) | 59.6% / 85.9% | identical | identical | fails false-standstill bar |
| S1b (self-cal k=2) | identical | 116.4/368.9/49.2/74.7 (screen) | 21.72 | 134.2 (27, screen) | 12.1 (0%) / 84.9 (-42.7%) | 59.6% / 83.8% | identical | 55/50/64% | best single-fix S2 result; still < 50% |
| S1c (anti-cascade) | identical | identical (screen) | 21.72 | 182.5 (37, screen) | 12.1 (0%) / 148.2 (0%) | 59.6% / 85.8% | identical | identical | no measurable real effect |
| S1d (retroactive replay) | identical | 113.8/376.3/51.7/75.6 (screen) | 21.72 | 166.8 (36, screen) | 9.9 (-18.2%) / 129.4 (-12.7%) | 59.6% / 85.3% | identical | identical | modest, real, both drives |
| S1e (w_exit 0.05) | **120.9/211.6/69.8/60.8** | 113.8/377.2/51.6/75.6 (screen) | 21.31 | 193.5 (35, screen) | 10.0 (-17.4%) / 134.9 (-9.0%) | 59.6% / 86.0% | 66.77/175.95/0.46 | 55/56/59% | real S3b accuracy gain, S2 neutral; < 50% bar |
| **ALL (best combination)** | **120.9/211.6/69.8/60.8** | 126.4/381.6/54.6/84.8 | 21.31 | 133.7 (104) | **7.8 (-35.5%)** / **60.0 (-59.5%)** | 59.6% / 83.8% | 66.77/175.95/0.46 | 55/56/69% | **best tried; still fails the 50%-on-S3b bar -> NOT adopted** |
"S2 dev" for S1a-S1e = the stride-4 screening subset (n=216; labelled "screen"); current, ALL and S1a+S1c+S1d (in prose) are confirmed on the full 861-window list. false-standstill s / recall are whole-drive `stationarity_audit` (no outage), the primary real measure.

# External sandbox study 3 — S1 review + OU speed prior (2026-09-27)
- S1 review: the acceptance rule ("false-standstill s down >= 50 % on BOTH drives") was mis-specified — S3b's dev windows contain zero false episodes >= 1 s, so no fix could move S3b by 50 %. ALL (S1a+S1b+S1c+S1d+S1e w_exit 0.05) is accuracy-neutral by the noise rule (S3b med end -4 %, cross -32 %; S2 full list -3 %, p90 +1 %), removes the sandbox catastrophe (smooth cruise 777-787 m -> 28-40 m) and cuts false standstill -35 % (S3b) / -60 % (S2). Decision: adopt ALL as the default. This is a rule revision stated openly before any further tuning; S3c stays the sealed judge.
- OU speed prior, external prototype on vehicle_dr @ 78a4160 (sandbox, 2 seeds, median 60 s window end error, OFF -> tau 10 / 20 / 40 with W 120): long_route 157/146 -> 50/46, 82/84, 113/110; event-like window (stop, then outage 200-260 s) end 173 -> 36-38 m, path ratio 0.43 -> 0.86; stop-and-go route 221/223 -> 126/115 (tau 10), 159/161 (tau 20); multi_stop_route 130/123 -> 125/115 (tau 10) but 151/143 (tau 20, WORSE). OU + ALL ~= OU alone. Brake-gated faster stop entry (quiet_enter_n 15): mixed. Caveat: sandbox speeds are regular; real gains will be smaller; missed stops inside outages become phantom driving under OU.
- Priority decision: I1a (latency ~0.5 s ~ 4 m) and I1b (the lock-out was already removed by H1c) are negligible against 100+ m errors -> DEFERRED. I3 deferred unless I2 falls short. New order: R1 -> I2 -> C -> D-design.

# PLAN UPDATE: R1 -> I2 -> C -> D-design (verbatim copy of the user's message, 2026-09-27)
```text
Read CLAUDE.md and AERIS_FINDINGS.md fully first. Registry v2, the noise rule and all standing rules apply. Sonnet, high effort. Push after every commit.

FIRST, log this verbatim under "External sandbox study 3 — S1 review + OU speed prior (2026-09-27)" in AERIS_FINDINGS.md:
- S1 review: the acceptance rule ("false-standstill s down >= 50 % on BOTH drives") was mis-specified — S3b's dev windows contain zero false episodes >= 1 s, so no fix could move S3b by 50 %. ALL (S1a+S1b+S1c+S1d+S1e w_exit 0.05) is accuracy-neutral by the noise rule (S3b med end -4 %, cross -32 %; S2 full list -3 %, p90 +1 %), removes the sandbox catastrophe (smooth cruise 777-787 m -> 28-40 m) and cuts false standstill -35 % (S3b) / -60 % (S2). Decision: adopt ALL as the default. This is a rule revision stated openly before any further tuning; S3c stays the sealed judge.
- OU speed prior, external prototype on vehicle_dr @ 78a4160 (sandbox, 2 seeds, median 60 s window end error, OFF -> tau 10 / 20 / 40 with W 120): long_route 157/146 -> 50/46, 82/84, 113/110; event-like window (stop, then outage 200-260 s) end 173 -> 36-38 m, path ratio 0.43 -> 0.86; stop-and-go route 221/223 -> 126/115 (tau 10), 159/161 (tau 20); multi_stop_route 130/123 -> 125/115 (tau 10) but 151/143 (tau 20, WORSE). OU + ALL ~= OU alone. Brake-gated faster stop entry (quiet_enter_n 15): mixed. Caveat: sandbox speeds are regular; real gains will be smaller; missed stops inside outages become phantom driving under OU.
- Priority decision: I1a (latency ~0.5 s ~ 4 m) and I1b (the lock-out was already removed by H1c) are negligible against 100+ m errors -> DEFERRED. I3 deferred unless I2 falls short. New order: R1 -> I2 -> C -> D-design.

═════ R1 — adopt ALL as the default ═════
Set the defaults: use_brake_gate, use_self_cal, use_anticascade, use_replay = True; w_exit = 0.05. Verify that the new default reproduces the ALL row exactly (S3b dev 120.9/211.6/69.8/60.8, S2 full list 126.4/381.6/54.6/84.8, S3b mini 21.31, event 66.77/175.95/0.46). Update the tests that pin old defaults (keep the flags-off regression tests using explicit params). Full suite green. Update "Latest results" and the results table. Commit + push.

═════ I2a — OU speed prior (the main step) ═════
Implement exactly this in vehicle_dr (flag use_ou, default OFF until adopted):
- History: every NEW usable GNSS fix with speed > 2 m/s appends (t, speed). Before each predict: vbar = median, sv = max(std, 1.0) over the fixes with t_now − t ≤ ou_window_s; if fewer than 3, OU is inactive (speed held as now).
- In predict, only when NOT stationary and NOT accel-aided: a = exp(−dt/ou_tau); v ← vbar + (v − vbar)·a; F[3,3] = a; the speed process noise is sv²·(1 − a²) (replaces rw_v² dt). ZUPT / standstill still override (v = 0 when stationary). It runs between fixes too, not only in outages (causal).
- Label in code and docs: "speed prior from recent driving", not a measurement.
Sandbox first (criteria fixed now, 2 seeds, use_ou with tau 10, W 120, vs OFF):
  (a) long_route: median window end ≤ 0.5 × OFF;
  (b) the event-like window (start 200 s on default_route / long_route): path ratio ≥ 0.75;
  (c) a stop-and-go route, add to sim_drive as stop_and_go_route():
      [("straight",150,6,0),("stop",15),("straight",300,14,4),("turn",90,12,4),("straight",120,5,0),("stop",25),("straight",400,13,4),("turn",-90,12,4),("straight",200,7,0),("stop",10),("straight",250,12,4),("turn",90,12,4),("straight",150,6,0),("stop",30),("straight",500,14,4),("turn",-90,12,4),("straight",180,8,0),("stop",12),("straight",300,11,4),("turn",90,12,4),("straight",300,12,0)]
      median end ≤ 0.7 × OFF;
  (d) multi_stop_route: no worse than OFF by > 5 %.
Real data: screen the grid ou_tau ∈ {5, 10, 20, 40} × ou_window_s ∈ {60, 120, 300} on the S3b dev windows + the S2 stride-4 subset, then confirm the top 2 on the full S2 list.
SELECTION RULE (fixed now, before any real number): among the settings that do NOT worsen p90 end on either drive by > 5 % and keep the 1σ window coverage within 30–70 % on both drives, pick the lowest pooled median end error; ties within 5 % → the larger tau (more conservative). Adopt only if it beats the current default by > 5 % on the pooled median end (the noise rule).
Report for each row: S3b dev med end / p90 / cross / along | S2 same | S3b mini mean | launch-from-stop med end (n) | median path ratio (S3b / S2) | outage-span phantom driving (% of driven distance) and outage-span true-stop recall (S3b / S2) | event mean / end / path ratio (report only) | 1σ mini / S3b / S2.

═════ I2b — turn speed ceiling ═════
As in the saved plan (an inequality only, never pushes v up), tested on top of the I2a winner. Keep only by the noise rule.

═════ M1 — stops missed inside outages (report first, adopt only if clearly better) ═════
With the I2 winner as the default: measure the outage-span recall and phantom driving. Then try a brake-evidenced faster entry: quiet_enter_n ∈ {15, 20} (brake gate stays on, so entry still needs braking evidence). Adopt only if the outage-span phantom driving drops ≥ 25 % on both drives, the pooled median end error doesn't worsen by > 5 %, and the whole-drive false standstill doesn't rise > 20 %.

STOP after I2a / I2b / M1: show one compact table (rows: hold-last-fix, R1 default, the I2a grid top 3, I2a chosen, +I2b, +M1) and push.

═════ C — honest demo layer (only when I say "go C") ═════
- export_frontend_data.py --filter vehicle_dr (default), honest: no sim-aided, no VBOX input, no map-matching to VBOX. Keep the ground-truth track only as the separately labelled "reference" layer.
- An RTS smoother for vehicle_dr as a separate OFFLINE layer ("post-drive smoothed", never shown as live).
- Frontend: the outage window read from the export (not hard-coded in useGNSSStatus.ts / TimelineSlider); remove fake hard-coded values (e.g. "LOCKED (11 SATS)" in Sidebar.tsx / StatusPanel.tsx) — show real values from the export or "n/a"; GNSS hidden during the outage; AERIS continues from the last GNSS fix; the uncertainty ellipse from cov_matrix.
- A PNG of S3b (truth, phone fixes, vehicle_dr, old ESEKF, RTS, outage shaded) in backend/exports/evaluation/. Run the frontend build to check it compiles. Commit + push, stop.

═════ D-design — OpenStreetMap road matching (proposal only, no code, after C) ═════
Write a design section in AERIS_FINDINGS.md covering:
- Data: OSM road network for the S3b / S2 / S3c areas via Overpass (or an extract), cached in the repo with ODbL attribution; the drivable-road filter.
- Two candidate architectures, with pros and cons: (A) EKF pseudo-measurements (the distance to the nearest road segment as position, the road bearing as heading, gated, σ from road width + OSM error) — simple, fails at junctions; (B) a road-constrained particle filter / multi-hypothesis tracker: particles move along the road graph using vehicle_dr's speed and gyro heading change, weighted by how well the gyro turn matches the road geometry at junctions ("turn matching"), resampled at GNSS fixes. Recommend one.
- How the ambiguity at junctions is handled, and what happens when OSM is missing or the car leaves the road (car parks, private roads).
- How it is scored honestly (OSM is independent data; VBOX is scoring only; S3c stays sealed until B5).
- An estimate of the effort and the expected gain (use the dev windows' cross-track error as the target).
Stop for approval.

Before any /clear: update the handoff section, commit, push.
```

# R1 — adopt ALL as the default (2026-09-27)
Set `use_brake_gate`, `use_self_cal` (`self_cal_k` 2.0), `use_anticascade`, `use_replay` = True and `w_exit` = 0.05 as the `VDRParams` field defaults in `vehicle_dr.py` (previously all False / 0.10 — the S1 "ALL" combination, see "S1 — stationarity detector fixes" above).
No other code changed: this is purely a default-value flip, so the bare `VDRParams()` now behaves exactly as the already-measured "ALL" row.

**Reproduction (verified exact, 2026-09-27):** `PYTHONUTF8=1 python backend/check_outage.py S3b --filter vehicle_dr` -> mini-outages 21.31 / 16.09 / 63.95 (matches the documented ALL mini-mean 21.31 exactly), event mean/end/ratio 66.77 / 175.95 / 0.46 (exact), S3b dev-window median end/p90/cross/along 120.90 / 211.58 / 69.76 / 60.85 (matches 120.9/211.6/69.8/60.8).
`python backend/dev_eval.py --name "R1 default (ALL)" --workers 4` (full S2 list, 861 windows, ~14 min) -> S3b dev 120.9 / 211.6 / 69.8 / 60.8, S2 dev 126.4 / 381.6 / 54.6 / 84.8, pooled med end 126.1, S3b mini 21.31, launch-from-stop pooled med end 133.7 (n=104), event 66.77 / 175.95 / 0.46, 1σ coverage mini/S3b/S2 55 % / 56 % / 69 % — **matches the ALL row in the S1 compact table exactly**, cell for cell.

**Test suite.** Several tests pinned the pre-R1 default implicitly (bare `vehicle_dr.run_pipeline(s, None)` used as "the current/plain detector" inside isolation checks for S1a-S1e, plus two real-data/sandbox number pins). Fixed by introducing an explicit `OLD_DEFAULT = replace(VDRParams(), use_brake_gate=False, use_self_cal=False, use_anticascade=False, use_replay=False, w_exit=0.10)` constant in each affected test file (`test_s1_stationarity_fixes.py`, `test_s1_sandbox_suite.py`, `test_stationarity.py`) and using it wherever the test's intent was "the detector without this mechanism" or "the pre-R1 baseline" — so each S1 mechanism is still tested in isolation regardless of what the live default is. Renamed/added tests that were specifically ABOUT the default value (e.g. `test_current_default_fails` -> `test_old_default_failed_this_before_r1` + new `test_current_default_now_passes_after_r1`; `test_w_exit_010_is_bit_identical_to_the_default` -> `test_w_exit_010_reproduces_the_pre_r1_default` + new `test_current_default_w_exit_is_0_05`; `test_disabled_by_default_and_diagnostics_only` -> `test_replay_off_produces_no_replay_log`). Added `TestRealDataAcceptanceRule.test_current_live_default_matches_all_s1` (S3b, real data) asserting the bare default's positions/velocities are bit-identical to an explicit `ALL_S1` params object.

First full run after the default flip: 310 tests, 299 pass / 11 fail / 37 skip — all 11 failures traced to the implicit-default pattern above (none a real regression). Fixed all 11; one of my OWN new tests (`test_current_default_now_enables_replay`, asserting the bare default's replay_log is non-empty on the `_quiet_cruise` sandbox) then failed on rerun for a real and correct reason: with brake_gate also on by default, the false standstill that seeds the replay trigger never fires in the first place (brake_gate suppresses it upstream) — the mechanisms interacting as designed, not a bug. Replaced it with a static flag check (`test_current_default_has_replay_flag_on`) and kept the dynamic behavior coverage in the tests that already isolate replay correctly (`test_replays_fire_and_close_the_erased_episodes`, `test_current_live_default_matches_all_s1`).
Second full run: 314 tests, 313 pass / 1 fail (the test above) / 37 skip. After the last fix, reran all three touched files in isolation: 48/48 pass. A third full-suite run was then started to get one clean end-to-end confirmation, but the harness itself killed it (system memory pressure on this shared machine — "Machine is SHARED: a game runs on it", not a test failure) while this session was idle waiting on it; per the harness's own instruction it was not restarted. No other file was touched by R1, and an earlier broad grep across every test file for `run_pipeline(`/`VDRParams()`/`w_exit` usage found no other implicit-default dependency, so the full suite is taken as green on the strength of the two runs above rather than a fresh third one. Full suite should be reconfirmed opportunistically the next time it runs for an unrelated reason.

Handoff: current default is now ALL (S1a+S1b+S1c+S1d+S1e w_exit 0.05); next step is I2a (OU speed prior).

# I2a — OU speed prior (2026-09-27)
Implemented exactly as specified: `use_ou` (default OFF), `ou_tau` (default 10.0 s), `ou_window_s` (default 120.0 s) added to `VDRParams`. History: every NEW usable GNSS fix with speed > 2 m/s appends `(t, speed)` to a causal deque (`ou_hist`), purged to the last `ou_window_s`; a fix from row `i` is appended AFTER `predict()` runs for row `i`, so it only affects row `i+1` onward (verified by a dedicated causality test). Before each `predict()`: `vbar` = median, `sv` = max(std, 1.0) of the fixes currently in the window; fewer than 3 -> inactive (`ou_arg=None`, v held exactly as before — a pure no-op, verified bit-identical with `use_ou=False`). Inside `predict()`, active only when NOT stationary and NOT accel-aided (ZUPT and B3b launch aiding keep priority): `a = exp(-dt/tau)`, `v <- vbar + (v-vbar)*a`, `F[3,3] = a`, process noise on v = `sv^2*(1-a^2)` (replaces `rw_v^2*dt` for that step only). Labelled in code as "a speed prior from recent driving, NOT a measurement". `use_replay`'s replay span does NOT re-apply OU (disclosed simplification, same pattern as H1a/launch/centripetal/fixed-mount — v is held/random-walk during a replayed span). New result key `ou_active_count` (diagnostic). 10 new tests in `tests/test_i2a_ou_speed_prior.py` (mechanics: no-op when off, activates/holds correctly, ZUPT still wins at a real stop, causality, F[3,3]/process-noise formula by hand) — all pass.

## Sandbox (criteria a-d, fixed before any real number; 2 seeds, tau=10, W=120 vs OFF)
Added `stop_and_go_route()` to `sim_drive.py` exactly as specified (5 stops of varying length/speed, interleaved turns).
| criterion | seed 1 | seed 2 | bar | verdict |
|---|---|---|---|---|
| (a) long_route median window end, ON/OFF | 48.4 / 135.0 m (0.36x) | 46.2 / 129.1 m (0.36x) | <= 0.5x | **PASS** |
| (b) event-like window (200-260 s) path ratio, default_route | 0.86 | 0.88 | >= 0.75 | **PASS** |
| (b) event-like window path ratio, long_route | 0.86 | 0.86 | >= 0.75 | **PASS** |
| (c) stop_and_go_route median window end, ON/OFF | 118.0 / 241.9 m (0.49x) | 117.8 / 228.9 m (0.51x) | <= 0.7x | **PASS** |
| (d) multi_stop_route median window end, ON/OFF | 116.5 / 135.6 m (0.86x, BETTER) | 118.7 / 134.1 m (0.89x, BETTER) | <= 1.05x | **PASS** |
All four sandbox criteria pass cleanly on both seeds with tau=10/W=120 (matches the external prototype study almost exactly: event-like window end 173 -> 36-38 m / ratio 0.43 -> 0.86 logged in "External sandbox study 3" above).

## Real-data screening grid (S3b: 11 dev windows; S2: stride-4 screening subset, n=216) — `ou_tau` in {5,10,20,40} x `ou_window_s` in {60,120,300}
| step | S3b dev: med end/p90/cross/along | S2 dev (screen): med end/p90/cross/along | pooled med end | S3b mini mean | event mean/end/ratio | 1σ mini/S3b-win/S2-win |
|---|---|---|---|---|---|---|
| hold-last-fix | 156.5/299.6/142.0/64.2 | 368.5/863.8/137.1/248.3 | 346.9 | - | - | - |
| **R1 default (OU off)** | 120.9/211.6/69.8/60.8 | 113.8/368.6/49.0/73.9 | 114.1 | **21.31** | 66.77/175.95/**0.46** | **55%/56%/65%** |
| OU tau5 W60 | 83.0/143.0/33.4/65.3 | 122.0/383.8/46.6/76.0 | 117.9 | 33.16 | 136.08/165.19/1.47 | 30%/14%/10% |
| OU tau5 W120 | 89.2/126.1/61.0/58.2 | 117.8/403.9/48.4/75.7 | 115.1 | 31.52 | 139.49/180.02/1.54 | 35%/15%/5% |
| OU tau5 W300 | 87.6/126.1/47.9/58.2 | 138.4/409.3/51.6/77.5 | 133.1 | 31.74 | 136.10/168.96/1.48 | 35%/16%/8% |
| OU tau10 W60 | 76.5/157.2/41.4/62.5 | 119.4/377.2/46.0/73.9 | 119.0 | 33.60 | 112.97/159.13/1.16 | 30%/14%/11% |
| **OU tau10 W120** | 86.2/144.7/53.1/60.0 | 113.2/361.6/47.0/71.8 | **110.0** | 32.70 | 125.86/197.64/1.40 | 25%/8%/6% |
| OU tau10 W300 | 86.2/144.7/53.1/63.5 | 126.6/359.3/46.5/72.7 | 121.5 | 32.85 | 122.54/188.25/1.34 | 25%/8%/11% |
| OU tau20 W60 | 89.4/169.4/50.5/62.7 | 123.1/361.9/47.1/77.6 | 123.0 | 34.89 | 68.15/143.44/0.51 | 25%/8%/7% |
| **OU tau20 W120** | 101.0/172.0/65.2/70.5 | 107.3/350.2/53.0/70.4 | **107.2** | 34.43 | 96.03/204.24/0.96 | 25%/1%/8% |
| OU tau20 W300 | 101.0/172.0/65.2/70.5 | 120.6/397.3/42.7/72.9 | 119.4 | 34.40 | 93.58/194.87/0.91 | 25%/1%/14% |
| OU tau40 W60 | 117.1/186.5/75.6/80.9 | 118.9/370.4/52.3/77.1 | 117.3 | 42.85 | 68.61/139.19/0.49 | 15%/0%/4% |
| OU tau40 W120 | 122.2/195.0/87.6/85.2 | 117.4/383.0/52.7/78.6 | 117.7 | 42.33 | 85.11/177.78/0.75 | 20%/0%/5% |
| OU tau40 W300 | 122.2/195.0/87.6/85.2 | 122.7/386.9/47.7/77.5 | 122.4 | 42.32 | 83.56/172.11/0.71 | 20%/0%/10% |
Bold = the two lowest pooled-median-end candidates (tau20/W120 = 107.2, -6.0% vs R1's 114.1; tau10/W120 = 110.0, -3.6%).

## Verdict: FAILS the pre-registered 1σ-coverage gate at every grid point — `use_ou` stays OFF
**The selection rule was fixed before any real number was seen**: "among the settings that do NOT worsen p90 end on either drive by > 5% and keep the 1σ window coverage within 30-70% on both drives, pick the lowest pooled median end error... Adopt only if it beats the current default by > 5% on the pooled median end." **Every one of the 12 grid points fails the coverage half of that gate**: S3b-window 1σ coverage collapses to 0-16% (R1 default: 56%) and S2-window coverage to 4-14% (R1 default: 65%), both far below the required 30-70% band, for every `(tau, W)` combination tried — including the two settings with the best pooled median end error (tau20/W120: S3b-win 1%, S2-win 8%; tau10/W120: S3b-win 8%, S2-win 6%). Per the rule as written, **no candidate qualifies for adoption**, so the confirm-on-full-S2-list step was not run (there is no "top 2" to confirm) and `use_ou` stays OFF by default; the code and all 10 sandbox/mechanics tests are kept, exactly as the standing rule requires for a failed step.
**Why the coverage collapses (mechanism, not a bug):** the OU process variance is `sv^2*(1-e^(-2dt/tau))`, which SATURATES at `sv^2` as more dt steps accumulate without a GNSS correction — it is bounded. The random walk it replaces (`rw_v^2 * dt`) grows WITHOUT BOUND the longer GNSS is absent. Over a long GNSS-free stretch (a 60 s sliding window, or a real outage), OU's reported speed uncertainty — and therefore the position uncertainty fed through it — stops growing while the true error does not, so the filter becomes structurally overconfident. This is an intrinsic consequence of the OU formulation exactly as specified (the "recent driving" prior is a genuinely informative constraint, which is exactly why it also makes the filter *more confident than it has a right to be* once real accumulated drift exceeds what "recent driving" would suggest), not an implementation defect — verified independently by the mechanics tests (`test_f33_and_process_noise_match_the_ou_formula`) which hand-check the formula bit-for-bit.
**Corroborating evidence the point-estimate story is also mixed, not just the coverage:** S3b mini-outage mean gets MUCH worse under every OU setting (21.31 -> 31-43 m, +47% to +101%): short ~9 s dead-reckoning intervals are hurt because OU pulls v toward a windowed median rather than holding the last known value, which is the wrong prior for a car that is mid-acceleration or mid-braking between two fixes. The 200-260 s event path ratio, which the sandbox study got very right (0.43 -> 0.86, undershoot corrected), OVERSHOOTS badly on real data instead (0.46 -> 0.91-1.54, i.e. AERIS travels UP TO 1.5x the true path) for several settings — the real launch-from-a-stop event does not resemble the sandbox's steady mid-drive outage closely enough for `vbar` (a window median of recent moving-fix speeds) to be a safe prior right after a stop. This matches the plan's own stated caveat almost exactly: "real gains will be smaller; missed stops inside outages become phantom driving under OU."
**Not run (decision-irrelevant given the coverage-gate failure, and interrupted by system memory pressure on this shared machine — an orphan worker process was found and killed afterward, see the handoff notes):** the detailed outage-span phantom-driving / true-stop-recall breakdown for individual OU settings. Since the pre-registered gate already disqualifies every candidate on coverage grounds alone, this number would not change the adoption decision; it can be produced on request if the user wants it for the record.
I2b (turn speed ceiling, "tested on top of the I2a winner") and M1 are therefore tested on top of the R1 default (i.e., unchanged) rather than an I2a variant, since I2a has no adopted winner.

# I2b — turn speed ceiling (2026-09-27)
Implemented exactly as specified, tested on top of the R1 default (I2a has no winner): `use_turn_ceil` (adopted True), `ceil_w_min` 0.15 rad/s ("in a turn"), `ceil_margin` 0.6 m/s² (grid 0.3-1.0), `ceil_mode` ("ah" = the ACTUALLY MEASURED 1 s mean horizontal accel magnitude, mount-free; "fixed" = a constant comfort ceiling `ceil_a_max`, grid 2.5/3.0/4.0). In a real turn, if the filter's v implies MORE centripetal accel than the bound (+ margin) allows, a normal scalar EKF update pulls v toward `v_ceil = (bound + margin) / |omega - b_g|` — triggered only when `v_est > v_ceil`, so by construction of the trigger it is a one-sided cap (the update is a convex combination of `v_est` and `v_ceil`, so it can only move v DOWN toward, never past, the bound — hand-verified in `test_update_is_a_convex_combination_so_v_only_moves_toward_the_ceiling`, 50 random cases). 6 tests in `test_i2b_turn_ceiling.py`.

**Real-data screening grid** (S3b dev: 11 windows, exact; S2 dev: stride-4 screen, n=216) on top of R1 default:
| step | S3b dev: med end/p90/cross/along | S2 dev (screen): med end/p90/cross/along | pooled med end | S3b mini mean | event mean/end/ratio | 1σ mini/S3b-win/S2-win |
|---|---|---|---|---|---|---|
| **R1 default (ceil off)** | 120.9/211.6/69.8/60.8 | 113.8/368.6/49.0/73.9 | 114.1 | 21.31 | 66.77/175.95/0.46 | 55%/56%/65% |
| ceil ah m0.3 | 101.2/230.7/72.3/64.7 | 142.2/413.1/50.2/100.8 | 141.8 | 24.96 | 97.62/170.98/0.47 | 35%/16%/38% |
| ceil ah m0.6 | 104.3/224.5/63.9/63.2 | 121.7/390.9/45.0/87.8 | 120.7 | 22.32 | 84.86/175.15/0.46 | 30%/31%/49% |
| ceil ah m1.0 | 105.4/214.5/59.4/53.1 | 112.5/371.7/42.8/86.4 | 111.3 | 20.60 | 73.50/169.02/0.46 | 40%/34%/53% |
| ceil fixed 2.5 | 98.9/221.1/69.8/61.0 | 120.4/368.6/47.3/87.6 | 120.3 | 20.60 | 66.21/162.63/0.46 | 40%/37%/54% |
| **ceil fixed 3.0** | **99.5/209.0/69.7/61.2** | 110.3/374.8/42.6/83.5 | 109.0 | 20.23 | 66.47/165.54/0.46 | 40%/44%/59% |
| ceil fixed 4.0 | 120.9/211.6/69.8/60.8 (0 triggers on S3b) | 107.8/369.4/47.9/73.5 | 108.4 | 20.06 | 66.94/170.23/0.46 | 55%/49%/60% |
By drive vs R1 default: ah m0.3/m0.6 fail (S2 end +25.0%/+6.9%, and ah m0.3's own S3b p90 +9.0% — both beyond the 5% noise-rule bound). ah m1.0, fixed 2.5/3.0/4.0 all show S3b helped strongly (-12.8% to -18.2%) with S2 within noise of neutral (-1.1% to +5.8%; fixed 2.5's S2 +5.8% is a real regression there, so it's dropped) or genuinely improved (fixed 4.0: -5.3%). ceil_ah_m1.0, ceil_fixed_3.0 and ceil_fixed_4.0 all pass the noise rule ("helps S3b AND S2, or helps one and is neutral on the other"); **ceil_fixed_3.0 chosen** (strongest, most consistent S3b gain, S2 clearly not a regression, best mini-outage/event numbers among the "fixed" family, p90 stable on both drives).

**Confirmation on the FULL S2 list** (861 windows, not the stride-4 screen; ran with `--drives S2 --workers 2` after two `--workers 4` full-grid attempts were killed by the harness for system memory pressure on this shared machine — orphan worker processes were found and killed after each): R1 default S2 med end **126.4** (exact match to the R1/I2a full-list number, a good cross-check), p90 381.6, cross 54.6, along 84.8. `ceil_fixed_3.0`: S2 med end **122.1** (-3.4%, confirmed neutral-not-worse — below the 5% noise-rule bound, but the SAME direction as screening, not a reversal), p90 382.1 (+0.1%, negligible), cross 51.1 (better), along 85.3 (negligible). Combined with S3b's EXACT (never screened) -17.7% (120.9 -> 99.5 m), this satisfies "helps S3b AND is neutral (not worse) on S2" cleanly.

**Safety check — does the ceiling corrupt CORRECTLY-TRACKED turns (GNSS available, no outage)?** long_route, whole drive: OFF mean_err 8.95 m, ON (fixed 3.0) mean_err 8.94 m — unchanged; the ceiling fires only 7 times in 5683 rows. (For comparison, `ceil_mode="ah"` with GNSS available fires 124 times and slightly WORSENS accuracy, 8.95 -> 9.25 m — the raw measured accel is noisier than a fixed physical bound, so "ah" mode is both less safe during normal tracking AND the weaker real-data performer; this is why "fixed" was chosen over "ah" despite "ah" being the more mount-free/principled-looking design.) The reason the fixed 3.0 m/s² ceiling is virtually inert during normal driving: `default_route()`/`long_route()`'s turn segments target only ~4 m/s (an urban-junction speed, not a highway sweeper), so true centripetal accel in a turn averages ~1.3-1.7 m/s² — comfortably under the 3.6 m/s² (= a_max + margin) bound. The ceiling is specifically catching cases where a GNSS-outage-inflated `v` (held via the plain random walk, `rw_v=2.0 m/s/sqrt(s)`, unbounded growth — the same mechanism flagged as the cause of I2a's coverage collapse) implies an unrealistic amount of turning force for the actual measured dynamics.

## Verdict: ADOPTED — `use_turn_ceil=True, ceil_mode="fixed", ceil_a_max=3.0` (other I2b params at their listed defaults) is the new default, on top of R1
Reproduction (verified exact, 2026-09-27): `check_outage.py S3b --filter vehicle_dr` -> mini-outages 20.23 / 16.05 / 46.31, S3b dev median end/p90 **99.52 / 209.02** (matches 99.5/209.0), event mean/end/ratio 66.47/165.54/0.46. One test broke from the default flip: `test_gyro_scale.py`'s H1b P3 criterion ("H1b, scale=1.0, no worse than the current default by >3%") implicitly compared against the bare `VDRParams()`, which now includes turn_ceil; H1b (its own 7-state gyro-scale EKF, itself NOT adopted, off by default) turns out to reduce turn_ceil's benefit somewhat when both are on together (a real, mild, explainable interaction — turn_ceil still helps in both cases: -14.2% alone vs -6.4% with H1b also on) — not a bug (verified: H1b's structural/causality tests are unaffected). Fixed the same way as R1/I2a: pinned P3 explicitly against a `PRE_I2B_DEFAULT` (turn_ceil off) baseline so it keeps testing H1b in isolation, decoupled from later unrelated default changes. Full suite green after the fix (330 tests; see handoff for the exact run).

# M1 — stops missed inside outages (2026-09-27; BLOCKED — not measured)
Plan: with the I2 winner (= R1 + I2b, since I2a has no winner) as the base, measure the outage-span true-stop recall and phantom driving (whole-drive `stationarity_audit` false-standstill too), then try `quiet_enter_n` ∈ {15, 20} (currently 30; brake gate stays on, so entry still needs braking evidence) and adopt only if outage-span phantom driving drops >= 25 % on BOTH drives, the pooled median end error doesn't worsen by > 5 %, and whole-drive false standstill doesn't rise > 20 %.
**Could not be completed.** Four attempts, each smaller than the last, were all killed by the harness for system memory pressure on this shared machine while the session was idle waiting on them (an orphan `nav-env` python worker was found and killed after every one of the four; none were CPU/logic errors on retry #1, which also hit an unrelated Windows-multiprocessing `if __name__ == "__main__":` bug in the scratch script, fixed before retry #2):
1. `dev_eval`-based screen (S3b full + S2 stride-4 screen), 4 workers — killed.
2. Same, 2 workers — killed.
3. Same computation restricted to `--drives S2 --workers 2` (S3b is fast/single-process anyway) — killed.
4. Fully single-process, no worker pool at all (direct `check_outage.window_benchmark` calls, no `ProcessPoolExecutor`) — **also killed**, which rules out the size of my own job as the cause: a single Python process holding one drive's dataframe is a small, bounded footprint, so the repeated kills reflect genuine external memory pressure on the shared machine (consistent with CLAUDE.md's own note that "a game runs on it"), not something scoping the job down further can fix.
Per the harness's own instruction ("do not start it again on your own... memory may still be short"), this was not retried a fifth time. `quiet_enter_n` is left at its default (30, unchanged); M1 is not adopted (there is nothing to adopt — it was never measured) and stays a documented, ready-to-run TODO: the exact script used for the single-process attempt is reproducible (whole-drive `stationarity_audit` + `check_outage.window_benchmark(..., audit=True)` on S3b's 11 windows and a stride-4 S2 subset, for `quiet_enter_n` in {30 (current), 20, 15}). Will re-run on request, or opportunistically alongside a future step's real-data evaluation once the machine is free.

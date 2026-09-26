# AERIS findings log

# START HERE — handoff for a fresh session (state after E0, 242 tests pass / 37 skipped; vehicle_dr defaults UNCHANGED since 22ec79f)

**E0 (evaluation upgrade) is DONE and reported; the user reviews it before anything else.** The full plan E0 → D is saved verbatim below under "PLAN: E0 → D" — read it, plus the
"DRIVE REGISTRY" and "PRE-REGISTRATION" sections right after it. **Next step: I1a (GNSS latency), then I1b (robustness), then I2, I3 — only after the user says to continue**
(the plan stops after E0 and again after I3, where the table below must be shown). I4-I6, B4, B5, C, D wait for "go next".
Per-step protocol (standing rules): sandbox test with a numeric pass criterion first -> real-data metrics -> row in the plan table below -> full suite passes -> commit + push;
a failed step stays in the code behind a flag set to OFF, with the reason logged.

## Rules (CLAUDE.md + standing rules)
* Branch `fix/heading-spin`; never touch `main`; **push after every commit** (`git push origin fix/heading-spin`); never `git stash pop`; one change at a time.
* HARD RULE: nothing shown as AERIS may use VBOX (`V-*.csv`) speed/heading/path as an input (scoring and diagnostics only). No snapping to truth.
* `backend/ins_ekf.py` (ESEKF) stays untouched as the comparison baseline. Venv: `nav-env` (`nav-env/Scripts/python.exe`); dataset `./IO-VNBD`. Untracked files
  `anurag_branch_full.zip`, `branch_diff_stat.txt` are not ours — do not commit them.
* Conventions inside vehicle_dr: psi is ENU, radians, counter-clockwise from East; the phone course field is a BEARING (degrees clockwise from North):
  `psi = pi/2 - radians(bearing)`, wrapped (`bearing_to_psi`, unit-tested).
* Tuning data = S3b mini-outages (intervals between consecutive NEW phone fixes ending <= 200 s, 20 of them) and, from E0 on, the S3b sliding 60 s windows that END before 200 s
  (11 windows, starts 30-130). Report mean AND median AND max (windows: median / mean / p90), plus leave-one-out for tuned parameters. S1 and S3c are never tuned on; the 200-260 s
  event is never tuned on (reported only). **Drive registry:** S3b tuning; S2/S4 training for I3 only; S3c final validation (B5, untouched, guarded by `--unseal`); S1 previously inspected (secondary); S3a reserve.
* Step protocol: (1) sandbox test with a numeric pass criterion, (2) real S3b metrics (mini-outages + tuning windows), (3) row appended to the results table, (4) full test suite, (5) commit + push. A step that fails its
  pass criterion keeps its code behind a feature flag set to OFF (sandbox tests stay), the reason is logged, and work continues.
* Windows console: pipe output only with `PYTHONUTF8=1` (a `≈` in a print raises UnicodeEncodeError under cp1252).
* Selection rule used for tuning (fixed in advance, `backend/tune_vehicle_dr.py`): lowest mean mini-outage error among grid points whose 1-sigma coverage is in [30, 50] %
  (target ~39 %); if none qualifies, closest to 39 %.

## Files
| file | what |
|---|---|
| `backend/vehicle_dr.py` | THE new filter: 6-state [E, N, psi, v, b_g, b_a] EKF; `run_pipeline(s_df, None, outage_window, params, t_end)`; `VDRParams`; `bearing_to_psi`; `evaluate_launch`; `calibrate_fixed_mount` |
| `backend/check_outage.py` | scoring: `python backend/check_outage.py [drive] [--filter esekf or vehicle_dr] [--fixes-only] [--mini-only] [--windows auto/tuning/all/off] [--per-window] [--unseal]` — 200-260 s outage report, **E0 along/cross + speed + path-ratio block**, mini-outage section (hold / const-v baselines) and, for vehicle_dr on S3b, the **sliding 60 s tuning windows** (`window_benchmark`, `score_track`, `Truth`, `summarize_windows` are importable for tuning scripts). Reserved drives S3c/S3a/S2/S4 need `--unseal`. |
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

**OFF (default False; code + sandbox tests kept):** `use_centripetal` (B3c, failed on S3b), `use_fixed_mount` (B3d, no benefit on S1), **`use_gyro_scale` (H1a) and `use_gyro_state` (H1b): correct on the sandbox, no benefit on real data because the real gyro scale is ~1.0**. Accel-integrated speed (`aided_max_s > 0`) is off because it hurt on S3b.
H1 knobs: `gs_window_s` 300, `gs_min_pairs` 5, `gs_k_min/max` 0.7 / 1.4, `gs_min_speed` 3, `gs_min_dcourse_deg` 20, `gs_max_pair_s` 15, `gs_max_x_rad` 2.8, `gs_latency_s` 0, `gs_fit` theilsen, `gs_gate_on` course, `gs_deadband` 0; `p0_sg` 0.10, `rw_sg` 1e-4.
New result keys: `gyro_scale_k / _log / _pairs` (H1a), `gyro_state_log` (H1b), `gyro_bias` (b_g per row, diagnostics).

| group | defaults |
|---|---|
| process noise | sigma_gyro 0.010 rad/s, turn_noise 0.50, rw_v 2.00 m/s/sqrt(s), rw_bg 1e-4, rw_ba 1e-3, rw_pos 0.10, rw_v_aided 1.0 |
| GNSS | gnss_min_sigma 3.0 m, sigma_gnss_speed 0.3 m/s, sigma_gnss_course_deg 6.0, min_course_speed 3.0 m/s, min_satellites 6, gate_enabled True, max_consecutive_pos_rejects 3 |
| standstill | win 10 samples, acc_var_enter 0.10 / exit 0.30, w_enter 0.05 / exit 0.10 rad/s, v_gate 2.0 m/s, launch_sigma_v 1.5, gnss_moving_speed 2.0, sigma_zupt 0.05, sigma_zaru 0.01 |
| launch (ON) | use_launch True, n_before 8, n_after 20, min_rest 10, R_min 0.8, min_accel 0.4 m/s^2, turn_comp True, w_max_comp 0.8, comp_max 1.0, release_mean_thr 0.6 (x3 samples), quiet_enter_n 30, sigma_v_after 0.6, sigma_ba 0.2, aided_w_max 0.10, aided_max_s 0.0 |
| centripetal (OFF) | use_centripetal False, cent_w_min 0.15, cent_steady 0.10, cent_every 5, cent_v_min 1.0, sigma_cent 1.0 (untuned default; best S3b grid point was 4.0 = nearly off), cent_res 0.6, cent_bg_coupling False |
| fixed mount (OFF) | use_fixed_mount False, mount_cal_t 200 s, gate: both criteria corr > 0.8 and within 30 deg, sigma_lat 0.8, sigma_ba_rest 0.15 |
| initial P (std) | pos 5 m, psi pi, v 5 m/s, b_g 0.02, b_a 0.3; psi_init_sigma 6 deg |

Sanity check that the state is as documented: `PYTHONUTF8=1 python backend/check_outage.py S3b --filter vehicle_dr` must give mini-outages 21.93 / 17.11 / 64.85 (n = 20, coverage 50 %), outage mean 64.35 m, end 145.89 m
(reproduced 2026-09-26 before E0 and again after it), and the E0 reference: tuning windows (n = 11) mean error median / mean 80.97 / 84.11, end error median / p90 161.47 / 214.23, path ratio median 0.96;
event along / cross at end -85.58 / +118.15 m, path ratio 0.46. Runtime: one full vehicle_dr run of S3b = 0.10 s measured (15 us/row); all 345 S3c windows would take roughly 2 min (estimate, not measured).

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
| **B3b replay only (CURRENT DEFAULT)** | **21.93 / 17.11 / 64.85** | 22.12 | 64.35 / 145.89 | 75.5 | 104.9 | 50 % | n/a | pass, marginal (-0.53 m; 2 launches in the tuning window) |
| B3c centripetal speed (best S3b grid point) | 22.12 / 17.64 / 62.28 | 23.75 | 72.22 / 163.16 | 115.9 | 159.5 | 45 % | n/a | fail, OFF |
| B3d fixed-mount aiding (S3b gate inactive; S1 active, phi -65.5 deg) | = B3b | 22.12 | 64.35 / 145.89 | 75.5 | 104.9 | 50 % | off 43.89 / on 52.66 | no benefit, OFF |

S1 (validation, nothing tuned on it), 523 intervals outside 200-260 s: B3d off 43.89 / 20.05 / 620 (coverage 30 %); B3d on 52.66 / 20.09 / 1097 (20 %); const-v 26.67 / 22.78 / 136.

Current default outage (S3b, reported not tuned): mean 64.35, end 145.89, max 145.89, path 104.9 m (truth 225.7), displacement 75.5 m (truth 154.0), |dyaw| 288 deg (truth 676),
truth inside 1-sigma 20.3 %, sigma at 260 s = 268 m, gap last fix -> AERIS at 200 s = 4.26 m, pre-outage (20-200 s) mean 10.76 m vs raw phone GNSS 7.08 m.

## Plan results table (E0 → I3; S3b only; append a row per step; show this table to the user after I3)
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
   the event stays report-only. 11 windows overlap heavily (~2.7 independent 60 s stretches): a thin tuning signal.
1. **S1 heavy error tail from a hard-gate lock-out (highest priority).** vehicle_dr's S1 median 20.05 m beats const-v (22.78) but the mean 43.89 does not (26.67): 11.1 % of intervals > 100 m (const-v 0.8 %), 4 % > 200 m,
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

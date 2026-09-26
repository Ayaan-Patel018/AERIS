# AERIS findings log

# START HERE — handoff for a fresh session (state as of commit 22ec79f, 213 tests pass / 37 skipped)

**Next step: E0.** E0 was designated by the user at the end of the previous session; its definition is NOT recorded in this log or in that
session's transcript. Ask the user what E0 is before doing anything else — do not guess. Work already queued in this log that E0 may refer to:
the improvement candidates B3e–B3i (user must say "go ideas"), B4 (final tuning + ablation + S3b PNG plot), B5 (validation on an untouched drive), the
`--filter` flag for `export_frontend_data.py`, and the original Step 3 (dashboard regeneration + frontend hard-coded values) which the user has NOT yet released.

## Rules (CLAUDE.md + standing rules)
* Branch `fix/heading-spin`; never touch `main`; **push after every commit** (`git push origin fix/heading-spin`); never `git stash pop`; one change at a time.
* HARD RULE: nothing shown as AERIS may use VBOX (`V-*.csv`) speed/heading/path as an input (scoring and diagnostics only). No snapping to truth.
* `backend/ins_ekf.py` (ESEKF) stays untouched as the comparison baseline. Venv: `nav-env` (`nav-env/Scripts/python.exe`); dataset `./IO-VNBD`. Untracked files
  `anurag_branch_full.zip`, `branch_diff_stat.txt` are not ours — do not commit them.
* Conventions inside vehicle_dr: psi is ENU, radians, counter-clockwise from East; the phone course field is a BEARING (degrees clockwise from North):
  `psi = pi/2 - radians(bearing)`, wrapped (`bearing_to_psi`, unit-tested).
* Tuning data = S3b mini-outages (intervals between consecutive NEW phone fixes ending <= 200 s, 20 of them) ONLY. Report mean AND median AND max, plus
  leave-one-interval-out (LOO) for tuned parameters. S1 is never tuned on; the 200-260 s outage is never tuned on (reported only).
* Step protocol: (1) sandbox test passes, (2) real S3b mini-outage metric, (3) row appended to the results table, (4) commit + push. A step that fails its pass
  criterion is reverted (the feature flag defaults to OFF; code and sandbox tests stay), the reason is logged, and work continues.
* Selection rule used for tuning (fixed in advance, `backend/tune_vehicle_dr.py`): lowest mean mini-outage error among grid points whose 1-sigma coverage is in [30, 50] %
  (target ~39 %); if none qualifies, closest to 39 %.

## Files
| file | what |
|---|---|
| `backend/vehicle_dr.py` | THE new filter: 6-state [E, N, psi, v, b_g, b_a] EKF; `run_pipeline(s_df, None, outage_window, params, t_end)`; `VDRParams`; `bearing_to_psi`; `evaluate_launch`; `calibrate_fixed_mount` |
| `backend/check_outage.py` | scoring: `python backend/check_outage.py [drive] [--filter esekf or vehicle_dr] [--fixes-only] [--mini-only]` (200-260 s outage report + mini-outage section with hold / const-v baselines) |
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

**OFF (default False; code + sandbox tests kept):** `use_centripetal` (B3c, failed on S3b), `use_fixed_mount` (B3d, no benefit on S1). Accel-integrated speed (`aided_max_s > 0`) is off because it hurt on S3b.

| group | defaults |
|---|---|
| process noise | sigma_gyro 0.010 rad/s, turn_noise 0.50, rw_v 2.00 m/s/sqrt(s), rw_bg 1e-4, rw_ba 1e-3, rw_pos 0.10, rw_v_aided 1.0 |
| GNSS | gnss_min_sigma 3.0 m, sigma_gnss_speed 0.3 m/s, sigma_gnss_course_deg 6.0, min_course_speed 3.0 m/s, min_satellites 6, gate_enabled True, max_consecutive_pos_rejects 3 |
| standstill | win 10 samples, acc_var_enter 0.10 / exit 0.30, w_enter 0.05 / exit 0.10 rad/s, v_gate 2.0 m/s, launch_sigma_v 1.5, gnss_moving_speed 2.0, sigma_zupt 0.05, sigma_zaru 0.01 |
| launch (ON) | use_launch True, n_before 8, n_after 20, min_rest 10, R_min 0.8, min_accel 0.4 m/s^2, turn_comp True, w_max_comp 0.8, comp_max 1.0, release_mean_thr 0.6 (x3 samples), quiet_enter_n 30, sigma_v_after 0.6, sigma_ba 0.2, aided_w_max 0.10, aided_max_s 0.0 |
| centripetal (OFF) | use_centripetal False, cent_w_min 0.15, cent_steady 0.10, cent_every 5, cent_v_min 1.0, sigma_cent 1.0 (untuned default; best S3b grid point was 4.0 = nearly off), cent_res 0.6, cent_bg_coupling False |
| fixed mount (OFF) | use_fixed_mount False, mount_cal_t 200 s, gate: both criteria corr > 0.8 and within 30 deg, sigma_lat 0.8, sigma_ba_rest 0.15 |
| initial P (std) | pos 5 m, psi pi, v 5 m/s, b_g 0.02, b_a 0.3; psi_init_sigma 6 deg |

Sanity check that the state is as documented: `python backend/check_outage.py S3b --filter vehicle_dr` must give mini-outages 21.93 / 17.11 / 64.85 (n = 20, coverage 50 %) and outage mean 64.35 m, end 145.89 m.

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

## Known issues (open)
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
* Untouched same-driver drives with S+V pairs (never loaded by any experiment so far): **S2 (156 min), S3a (41 min), S3c (62 min), S4 (158 min)** under
  `IO-VNBD/Synchronised V abd S datasets/Categorised IOVNB Dataset/S (Driver A)/<drive>/S-<drive>.csv` and `V-<drive>.csv`. `check_outage.load_drive("<drive>")` handles them. Recommended: use one (S3c or S3a) as the fresh validation drive for B5.
  Before scoring a new drive, redo the B0 time-alignment check (phone-GNSS vs VBOX error per fix, lag scan; loader uses the phone wall-clock column and `sv_time_offset()` for scoring).
* **S1 is no longer pristine**: it was used for the A1/A2 diagnostics, the launch log (50 releases, 31 accepted), the mount-stability scan, the B3d validation and the tail characterisation.
* Other drives exist (M, Vf, Vta, Vtb, Vw, Y) — not investigated.
* Real-data facts: phone GNSS fix every ~9 s (values held between fixes); speed column already m/s; vertical gyro = CSV "Pitch" column (A2); gravity columns are ~(0, 0, 9.806) so the phone is treated as flat;
  ESEKF's real dead-reckoning is 3-13x worse than const-v (its 10-12 m "tracking" comes from 10 Hz interpolated GNSS, i.e. non-causal).
* Candidate ideas still open (user must say "go ideas"): B3e stochastic cloning (between-fix displacement), B3f gyro scale factor (A2 slopes 1.29 S3b vs 0.94 S1), B3g learned vibration speed, B3h magnetometer heading aid, B3i robust GNSS.
* After the ideas: B4 = final tuning on S3b mini-outages (with LOO), report the S3b 200-260 s outage ONCE + ablation table + PNG; B5 = validation once with NO retuning (mini-outages + 200-260 s outage).

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

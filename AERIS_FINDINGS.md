# AERIS findings log

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

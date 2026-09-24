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

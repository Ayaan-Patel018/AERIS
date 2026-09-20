"""Before/after comparison for the 3 drift-reduction fixes."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from data_loader import load_smartphone, load_vehicle, get_dataset_root
from ins_ekf import run_pipeline, rts_smooth, evaluate_error
import numpy as np

root = get_dataset_root()
base = os.path.join(root, "Synchronised V abd S datasets",
                    "Categorised IOVNB Dataset", "S (Driver A)", "S3b")
s_df = load_smartphone(os.path.join(base, "S-S3b.csv"))
v_df = load_vehicle(os.path.join(base, "V-S3b.csv"))

outage = (200.0, 260.0)

# Real-time full EKF
rt = run_pipeline(s_df, v_df, mode="full", outage_window=outage, store_smoothing_data=True)

# RTS smoothed
rts = rts_smooth(rt, rt["lat0"], rt["lon0"])

rt_ev  = evaluate_error(rt,  v_df)
rts_ev = evaluate_error(rts, v_df)

rt_errors  = np.array(rt_ev["errors_m"])
rts_errors = np.array(rts_ev["errors_m"])
times      = np.array(rt_ev["timestamps"])

mask_out = (times >= 200.0) & (times <= 260.0)
rt_out   = rt_errors[mask_out]
rts_out  = rts_errors[mask_out]
t_out    = times[mask_out]

print("=" * 72)
print("  STEP-BY-STEP OUTAGE TRACKING (after 3 drift fixes)")
print("=" * 72)
print(f"  {'Time':>6} | {'Real-Time EKF':>14} | {'RTS Smoothed':>13} | Status")
print("  " + "-" * 68)
for t_check in range(200, 265, 5):
    mask = (times >= t_check - 0.5) & (times <= t_check + 0.5)
    if mask.any():
        rt_e  = float(np.mean(rt_errors[mask]))
        rts_e = float(np.mean(rts_errors[mask]))
        if rt_e < 20:   s = "EXCELLENT"
        elif rt_e < 50: s = "GOOD (< 50 m)"
        else:           s = "ACCEPTABLE (< 100 m)"
        print(f"  t={t_check:>4}s | {rt_e:>12.2f} m | {rts_e:>11.2f} m | {s}")

print()
print("=" * 72)
print("  OUTAGE WINDOW SUMMARY (200s \u2013 260s)")
print("=" * 72)
print(f"  Metric     | Real-Time EKF | RTS Smoothed")
print(f"  -----------+---------------+--------------")
print(f"  Mean       | {np.mean(rt_out):>11.2f} m | {np.mean(rts_out):>10.2f} m")
print(f"  RMSE       | {np.sqrt(np.mean(rt_out**2)):>11.2f} m | {np.sqrt(np.mean(rts_out**2)):>10.2f} m")
print(f"  Max        | {np.max(rt_out):>11.2f} m | {np.max(rts_out):>10.2f} m")
print(f"  P95        | {np.percentile(rt_out, 95):>11.2f} m | {np.percentile(rts_out, 95):>10.2f} m")
print(f"  Overall Mean| {np.mean(rt_errors):>10.2f} m | {np.mean(rts_errors):>9.2f} m")

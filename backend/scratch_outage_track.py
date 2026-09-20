"""Outage tracking diagnostic — prints step-by-step AERIS error during 60s GNSS blackout."""
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

# Run full real-time pipeline
rt_result = run_pipeline(s_df, v_df, mode="full", outage_window=outage, store_smoothing_data=True)

# Run RTS smoother
rts_result = rts_smooth(rt_result, rt_result["lat0"], rt_result["lon0"])

# Evaluate both
rt_ev  = evaluate_error(rt_result,  v_df)
rts_ev = evaluate_error(rts_result, v_df)

rt_errors  = np.array(rt_ev["errors_m"])
rts_errors = np.array(rts_ev["errors_m"])
times      = np.array(rt_ev["timestamps"])

print("=" * 72)
print("  AERIS TRACKING ACCURACY — 60s GNSS OUTAGE (t=200s to t=260s)")
print("=" * 72)
print(f"  {'Time':>6} | {'Real-Time EKF':>14} | {'RTS Smoothed':>13} | {'Status'}")
print("  " + "-" * 68)

first_rt = None
for t_check in range(200, 265, 5):
    mask = (times >= t_check - 0.5) & (times <= t_check + 0.5)
    if mask.any():
        rt_e  = float(np.mean(rt_errors[mask]))
        rts_e = float(np.mean(rts_errors[mask]))
        if first_rt is None:
            first_rt = rt_e
        if rt_e < 20:
            status = "EXCELLENT"
        elif rt_e < 50:
            status = "GOOD (< 50 m)"
        elif rt_e < 100:
            status = "ACCEPTABLE (< 100 m)"
        else:
            status = "DEGRADED"
        print(f"  t={t_check:>4}s | {rt_e:>12.2f} m | {rts_e:>11.2f} m | {status}")

print()
mask_out = (times >= 200.0) & (times <= 260.0)
rt_out   = rt_errors[mask_out]
rts_out  = rts_errors[mask_out]

print("=" * 72)
print("  OUTAGE WINDOW STATISTICS")
print("=" * 72)
print(f"  Metric            | Real-Time EKF | RTS Smoothed")
print(f"  ------------------+---------------+--------------")
print(f"  Mean error        | {np.mean(rt_out):>11.2f} m | {np.mean(rts_out):>10.2f} m")
print(f"  RMSE              | {np.sqrt(np.mean(rt_out**2)):>11.2f} m | {np.sqrt(np.mean(rts_out**2)):>10.2f} m")
print(f"  Max error         | {np.max(rt_out):>11.2f} m | {np.max(rts_out):>10.2f} m")
print(f"  P50 error         | {np.percentile(rt_out, 50):>11.2f} m | {np.percentile(rts_out, 50):>10.2f} m")
print(f"  P95 error         | {np.percentile(rt_out, 95):>11.2f} m | {np.percentile(rts_out, 95):>10.2f} m")
print(f"  Steps (no GNSS)   | {mask_out.sum():>8} steps |  (10 Hz, {mask_out.sum()/10:.0f}s)")
print()

# Compare to baseline (no fusion)
pure_ins = run_pipeline(s_df, v_df, mode="ins_only", outage_window=outage)
pure_ev  = evaluate_error(pure_ins, v_df)
pure_out = np.array(pure_ev["errors_m"])[(times >= 200.0) & (times <= 260.0)]
print("=" * 72)
print("  IMPROVEMENT vs PURE STRAPDOWN INS (no fusion)")
print("=" * 72)
print(f"  Pure INS outage mean : {np.mean(pure_out):>10.2f} m")
print(f"  AERIS RT  outage mean: {np.mean(rt_out):>10.2f} m  ({100*(1-np.mean(rt_out)/np.mean(pure_out)):.1f}% better)")
print(f"  AERIS RTS outage mean: {np.mean(rts_out):>10.2f} m  ({100*(1-np.mean(rts_out)/np.mean(pure_out)):.1f}% better)")

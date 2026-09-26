"""
check_alignment.py — B0 time-alignment check (phone GNSS vs VBOX), reusable for any drive.

For every usable NEW phone fix: distance between the phone position and the VBOX position at the aligned time
(phone time + sv_time_offset), plus a lag scan (VBOX looked up at t + off + shift). A healthy drive has a flat error
over time (no step / trend) and a best shift near -0.5 s (the known GNSS latency bias, ~4 m at 8 m/s).
Scoring-side only — nothing here reaches a filter. Reserved drives need --unseal (same guard as check_outage.py).

    python backend/check_alignment.py S3b S1 S2
    python backend/check_alignment.py S3c --unseal        # B5 only
"""
import argparse
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import check_outage as co
import window_plan
from ins_ekf import latlon_to_enu


def check(drive, unseal=False, seg_s=600.0, shifts=np.arange(-2.0, 6.01, 0.25)):
    co.guard_drive(drive, unseal)
    s, v, off = co.load_drive(drive)
    lat0, lon0 = co.origin(s)
    rows = window_plan.usable_fix_rows(s)
    t = s["timestamp_s"].values[rows]
    p = np.array([latlon_to_enu(la, lo, lat0, lon0)[:2] for la, lo in zip(s["gps_lat"].values[rows], s["gps_lon"].values[rows])])
    spd = s["gps_speed_ms"].values[rows]
    v_end = float(v.dropna(subset=["gps_lat", "gps_lon"])["timestamp_s"].values[-1]) - off
    ok = (t <= v_end - 5.0) & (t >= 0.0)                                # truth must exist (VBOX ends before the phone)
    t, p, spd = t[ok], p[ok], spd[ok]
    err0 = np.linalg.norm(p - co.Truth.from_vehicle(v, lat0, lon0, off).pos(t), axis=1)
    res = []
    for sh in shifts:
        tr = co.Truth.from_vehicle(v, lat0, lon0, off + sh)
        res.append(np.linalg.norm(p - tr.pos(t), axis=1).mean())
    res = np.array(res)
    best = shifts[int(np.argmin(res))]
    print(f"=== {drive}: S/V offset {off:.3f} s, {len(t)} usable fixes (t <= {t[-1]:.0f} s) ===")
    print(f"phone GNSS vs VBOX at the aligned time: mean {err0.mean():.2f} m, median {np.median(err0):.2f} m, p90 {np.percentile(err0, 90):.2f} m, max {err0.max():.1f} m")
    print(f"lag scan: best shift {best:+.2f} s -> mean {res.min():.2f} m (at 0 s: {res[np.argmin(np.abs(shifts))]:.2f} m)")
    edges = np.arange(0.0, t[-1] + seg_s, seg_s)
    segs = []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (t >= a) & (t < b)
        if m.sum() >= 5:
            sh_best = shifts[int(np.argmin([np.linalg.norm(p[m] - co.Truth.from_vehicle(v, lat0, lon0, off + sh).pos(t[m]), axis=1).mean()
                                            for sh in shifts]))]
            segs.append((a, b, int(m.sum()), err0[m].mean(), sh_best))
    print("per segment (start-end s: n, mean error m, best shift s): " +
          "; ".join(f"{a:.0f}-{b:.0f}: {n}, {e:.1f}, {sh:+.2f}" for a, b, n, e, sh in segs))
    return dict(drive=drive, off=off, n=len(t), mean=float(err0.mean()), median=float(np.median(err0)), best_shift=float(best),
                mean_at_best=float(res.min()), segments=segs)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("drives", nargs="+")
    ap.add_argument("--unseal", action="store_true")
    a = ap.parse_args()
    for d in a.drives:
        check(d, a.unseal)
        print()

"""
check_outage.py — honest outage check for AERIS.

Runs a filter with v_df=None (VBOX is never an input) and a GNSS outage of
200–260 s, then scores the result against V-<drive>.csv (truth looked up at the
wall-clock-aligned V time, see data_loader.sv_time_offset).

Two sections:
  1. the 200–260 s outage (position error, path/displacement, yaw, 1σ, ...)
  2. MINI-OUTAGES: for every interval between consecutive NEW phone fixes, the
     error just before the next fix arrives, i.e. pure dead reckoning over ~9 s.
     This is the metric filters are tuned on (never the 200–260 s window).

Usage:
    python backend/check_outage.py                       # S3b, esekf
    python backend/check_outage.py S1 --mini-only
    python backend/check_outage.py S3b --fixes-only      # esekf fed GNSS only on new-fix rows
    python backend/check_outage.py S3b --filter vehicle_dr
"""
import argparse
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from data_loader import load_smartphone, load_vehicle, get_dataset_root, sv_time_offset
from ins_ekf import latlon_to_enu

OUTAGE = (200.0, 260.0)
FILTERS = ("esekf", "vehicle_dr")


def load_drive(drive):
    base = os.path.join(get_dataset_root(), "Synchronised V abd S datasets",
                        "Categorised IOVNB Dataset", "S (Driver A)", drive)
    s_df = load_smartphone(os.path.join(base, f"S-{drive}.csv"))
    v_df = load_vehicle(os.path.join(base, f"V-{drive}.csv"))   # scoring only
    return s_df, v_df, sv_time_offset(s_df, v_df)


def new_fix_rows(s_df):
    """Row indices where the phone delivered a NEW fix (lat/lon changed; row 0 counts)."""
    lat, lon = s_df["gps_lat"].values, s_df["gps_lon"].values
    fix = np.r_[True, (np.diff(lat) != 0) | (np.diff(lon) != 0)] & np.isfinite(lat) & np.isfinite(lon)
    return np.where(fix)[0]


def mask_non_fix_rows(s_df):
    """Copy of s_df in which every row that is NOT a new fix reports 0 satellites, so a
    pipeline that classifies GNSS by satellite count sees GNSS only on new-fix rows.
    Data-only: lets the unmodified ESEKF be scored as a true dead-reckoner."""
    m = s_df.copy()
    keep = np.zeros(len(m), dtype=bool)
    keep[new_fix_rows(s_df)] = True
    m.loc[~keep, "gps_satellites"] = 0.0
    return m


def run_filter(name, s_df, outage_window):
    if name == "esekf":
        from ins_ekf import run_pipeline
        return run_pipeline(s_df, None, mode="full", outage_window=outage_window)
    if name == "vehicle_dr":
        from vehicle_dr import run_pipeline as run_vdr
        return run_vdr(s_df, None, outage_window=outage_window)
    raise ValueError(name)


def _path_len(xy):
    return float(np.sum(np.linalg.norm(np.diff(xy, axis=0), axis=1))) if len(xy) > 1 else 0.0


def _truth_fn(v_df, lat0, lon0, off):
    ref = v_df.dropna(subset=["gps_lat", "gps_lon"])
    ref_enu = np.array([latlon_to_enu(la, lo, lat0, lon0)[:2]
                        for la, lo in zip(ref["gps_lat"], ref["gps_lon"])])
    rt = ref["timestamp_s"].values

    def truth(t):
        t = np.asarray(t, dtype=float) + off
        return np.column_stack([np.interp(t, rt, ref_enu[:, 0]), np.interp(t, rt, ref_enu[:, 1])])
    return truth, ref, ref_enu, rt


def _inside_1sigma(cov_row, e):
    cxx, cyy, cxy = cov_row
    P = np.array([[cxx, cxy], [cxy, cyy]])
    try:
        return float(e @ np.linalg.solve(P, e)) <= 1.0
    except np.linalg.LinAlgError:
        return False


def outage_report(res, s_df, v_df, off, drive):
    lat0, lon0 = res["lat0"], res["lon0"]
    t = np.array(res["timestamps"])
    est = np.array([latlon_to_enu(la, lo, lat0, lon0)[:2] for la, lo in res["positions"]])
    truth_fn, ref, ref_enu, rt = _truth_fn(v_df, lat0, lon0, off)
    err_vec = est - truth_fn(t)
    err = np.linalg.norm(err_vec, axis=1)

    m_out = (t >= OUTAGE[0]) & (t <= OUTAGE[1])
    m_pre = (t >= 20.0) & (t < OUTAGE[0])

    # Outage path/displacement: AERIS vs truth
    e_out = est[m_out]
    rmask = (rt >= OUTAGE[0] + off) & (rt <= OUTAGE[1] + off)
    r_out = ref_enu[rmask]
    aeris_path, true_path = _path_len(e_out), _path_len(r_out)
    aeris_disp = float(np.linalg.norm(e_out[-1] - e_out[0]))
    true_disp = float(np.linalg.norm(r_out[-1] - r_out[0]))

    # Total |Δyaw| during outage (AERIS vs truth heading)
    hdg = np.array(res["headings"])[m_out]
    dyaw = np.sum(np.abs((np.diff(hdg) + 180.0) % 360.0 - 180.0))
    v_hdg = ref["gps_heading_deg"].values[rmask]
    v_hdg = v_hdg[np.isfinite(v_hdg)]
    true_dyaw = np.sum(np.abs((np.diff(v_hdg) + 180.0) % 360.0 - 180.0))

    # Truth inside the reported 1σ ellipse (Mahalanobis distance ≤ 1)
    cov = np.array(res["cov_matrix"])[m_out]
    inside = sum(_inside_1sigma(c, e) for c, e in zip(cov, err_vec[m_out]))
    pct_1sig = 100.0 * inside / max(m_out.sum(), 1)
    sig_end = float(np.sqrt(cov[-1][0] + cov[-1][1]))

    # Gap between last raw phone GNSS fix before outage and AERIS at 200 s
    raw = s_df[(s_df["timestamp_s"] < OUTAGE[0])].dropna(subset=["gps_lat", "gps_lon"])
    raw = raw[(raw["gps_lat"].diff() != 0) | (raw["gps_lon"].diff() != 0)]
    last = raw.iloc[-1]
    last_enu = latlon_to_enu(last["gps_lat"], last["gps_lon"], lat0, lon0)[:2]
    i200 = int(np.argmin(np.abs(t - OUTAGE[0])))
    gap = float(np.linalg.norm(est[i200] - last_enu))

    # Reference floor: raw phone GNSS fixes vs truth, 20–200 s
    rp = raw[raw["timestamp_s"] >= 20.0]
    rp_enu = np.array([latlon_to_enu(la, lo, lat0, lon0)[:2]
                       for la, lo in zip(rp["gps_lat"], rp["gps_lon"])])
    gnss_pre = float(np.linalg.norm(rp_enu - truth_fn(rp["timestamp_s"].values), axis=1).mean())

    print(f"=== check_outage: {drive}  (v_df=None, outage {OUTAGE[0]:.0f}-{OUTAGE[1]:.0f} s) ===")
    print(f"outage mean error        : {err[m_out].mean():8.2f} m")
    print(f"outage end error (260 s) : {err[m_out][-1]:8.2f} m")
    print(f"outage max error         : {err[m_out].max():8.2f} m")
    print(f"AERIS path / truth path  : {aeris_path:8.1f} m / {true_path:.1f} m")
    print(f"AERIS disp / truth disp  : {aeris_disp:8.1f} m / {true_disp:.1f} m")
    print(f"total |dyaw| in outage   : {dyaw:8.1f} deg  (truth {true_dyaw:.1f} deg)")
    print(f"pre-outage mean (20-200s): {err[m_pre].mean():8.2f} m  (max {err[m_pre].max():.2f} m)")
    print(f"  (raw phone GNSS 20-200s: {gnss_pre:8.2f} m — reference floor)")
    print(f"truth inside 1-sigma    : {pct_1sig:8.1f} %  (sigma at 260 s = {sig_end:.1f} m)")
    print(f"gap last GNSS fix->AERIS : {gap:8.2f} m  (fix at t={last['timestamp_s']:.1f} s, AERIS at t={t[i200]:.1f} s)")


def mini_outage(res, s_df, v_df, off, t_max=None, skip=None):
    """
    Per-interval dead-reckoning error. For consecutive NEW phone fixes a -> b the
    AERIS position on the last row BEFORE fix b is compared with the truth at that
    instant. That is pure dead reckoning since fix a only if the filter used no
    GNSS between the fixes (vehicle_dr by construction; esekf with --fixes-only).

    t_max: keep intervals whose next fix is at or before t_max (None = all).
    skip:  (t0, t1) — drop intervals overlapping this window (the real outage).
    Also scores two trivial phone-only baselines from the same fix a:
      hold  = stay at fix a;   cv = fix a + its GNSS speed along its GNSS course.
    """
    lat0, lon0 = res["lat0"], res["lon0"]
    t_res = np.array(res["timestamps"])
    est = np.array([latlon_to_enu(la, lo, lat0, lon0)[:2] for la, lo in res["positions"]])
    cov = np.array(res["cov_matrix"])
    truth_fn = _truth_fn(v_df, lat0, lon0, off)[0]
    ts = s_df["timestamp_s"].values
    fixes = new_fix_rows(s_df)
    spd = s_df["gps_speed_ms"].values
    crs = np.deg2rad(s_df["gps_heading_deg"].values)

    rows = []
    for a, b in zip(fixes[:-1], fixes[1:]):
        if b - 1 < 2:
            continue
        if t_max is not None and ts[b] > t_max:
            break
        if skip is not None and not (ts[b] < skip[0] or ts[a] > skip[1]):
            continue
        j = (b - 1) - 1                      # result index of row b-1 (results start at row 1)
        if j >= len(t_res) or abs(t_res[j] - ts[b - 1]) > 1e-6:
            continue
        tb = ts[b - 1]
        tr = truth_fn([tb])[0]
        pa = latlon_to_enu(s_df["gps_lat"].iloc[a], s_df["gps_lon"].iloc[a], lat0, lon0)[:2]
        dtt = tb - ts[a]
        v = spd[a] if np.isfinite(spd[a]) and np.isfinite(crs[a]) and spd[a] > 1.0 else 0.0
        p_cv = pa + v * dtt * np.array([np.sin(crs[a]), np.cos(crs[a])]) if v > 0 else pa
        e_vec = est[j] - tr
        rows.append(dict(
            t_a=ts[a], t_b=ts[b], dur=dtt,
            moving=bool(spd[a] > 2.0 and spd[b] > 2.0),
            aeris=float(np.linalg.norm(e_vec)),
            hold=float(np.linalg.norm(pa - tr)),
            cv=float(np.linalg.norm(p_cv - tr)),
            inside=_inside_1sigma(cov[j], e_vec),
            sig=float(np.sqrt(cov[j][0] + cov[j][1])),
        ))
    return rows


def _stats(x):
    x = np.asarray(x, dtype=float)
    return f"{x.mean():8.2f} {np.median(x):8.2f} {x.max():8.2f}" if len(x) else "     n/a      n/a      n/a"


def mini_report(rows, label, scope):
    print(f"--- mini-outages ({scope}): AERIS error just before each next NEW fix — pure DR since the previous fix ---")
    if not rows:
        print("   no intervals"); return {}
    mv = [r for r in rows if r["moving"]]
    dur = np.array([r["dur"] for r in rows])
    print(f"intervals: {len(rows)} (moving both ends > 2 m/s: {len(mv)}), duration mean {dur.mean():.1f} s, "
          f"median {np.median(dur):.1f} s, > 15 s: {(dur > 15).sum()}")
    print(f"{'':32s}      mean   median      max   (m)")
    for name, key in [(label, "aeris"), ("baseline: hold last fix", "hold"), ("baseline: last fix + const-v", "cv")]:
        print(f"{name:32s} {_stats([r[key] for r in rows])}   all")
        print(f"{'':32s} {_stats([r[key] for r in mv])}   moving")
    ins = 100.0 * np.mean([r["inside"] for r in rows])
    print(f"truth inside AERIS 1-sigma ellipse: {ins:.1f} %  (all intervals; consistent filter ≈ 39 %; "
          f"mean reported sigma {np.mean([r['sig'] for r in rows]):.1f} m)")
    return dict(n=len(rows), mean=float(np.mean([r["aeris"] for r in rows])),
                median=float(np.median([r["aeris"] for r in rows])), max=float(np.max([r["aeris"] for r in rows])),
                moving_mean=float(np.mean([r["aeris"] for r in mv])) if mv else float("nan"), inside=ins)


def main(drive="S3b", filt="esekf", fixes_only=False, mini_only=False):
    s_df, v_df, off = load_drive(drive)
    s_in = mask_non_fix_rows(s_df) if fixes_only else s_df
    res = run_filter(filt, s_in, OUTAGE)
    label = f"{filt}{' (GNSS on new-fix rows only)' if fixes_only else ''}"
    if not mini_only:
        outage_report(res, s_df, v_df, off, drive)
        print()
    # S3b: tune/score on intervals before the outage; other drives: every interval outside the outage window
    if drive == "S3b":
        rows = mini_outage(res, s_df, v_df, off, t_max=OUTAGE[0])
        mini_report(rows, label, "S3b, intervals ending <= 200 s")
    else:
        rows = mini_outage(res, s_df, v_df, off, skip=OUTAGE)
        mini_report(rows, label, f"{drive}, all intervals outside the {OUTAGE[0]:.0f}-{OUTAGE[1]:.0f} s outage")
    return res, rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("drive", nargs="?", default="S3b")
    ap.add_argument("--filter", choices=FILTERS, default="esekf")
    ap.add_argument("--fixes-only", action="store_true",
                    help="feed GNSS only on new-fix rows (data masking; lets the ESEKF be scored as a dead-reckoner)")
    ap.add_argument("--mini-only", action="store_true", help="skip the 200-260 s outage section")
    a = ap.parse_args()
    main(a.drive, a.filter, a.fixes_only, a.mini_only)

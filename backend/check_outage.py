"""
check_outage.py — honest outage check for AERIS.

Runs the full pipeline with v_df=None (VBOX is never an input) and a GNSS
outage of 200–260 s, then scores the result against V-<drive>.csv.

Usage:
    python backend/check_outage.py          # S3b
    python backend/check_outage.py S1
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from data_loader import load_smartphone, load_vehicle, get_dataset_root, sv_time_offset
from ins_ekf import run_pipeline, latlon_to_enu

OUTAGE = (200.0, 260.0)


def _path_len(xy):
    return float(np.sum(np.linalg.norm(np.diff(xy, axis=0), axis=1))) if len(xy) > 1 else 0.0


def main(drive="S3b"):
    base = os.path.join(get_dataset_root(), "Synchronised V abd S datasets",
                        "Categorised IOVNB Dataset", "S (Driver A)", drive)
    s_df = load_smartphone(os.path.join(base, f"S-{drive}.csv"))
    v_df = load_vehicle(os.path.join(base, f"V-{drive}.csv"))   # scoring only
    off = sv_time_offset(s_df, v_df)   # S time + off = V time (wall-clock start offset; scoring only)

    res = run_pipeline(s_df, None, mode="full", outage_window=OUTAGE)
    lat0, lon0 = res["lat0"], res["lon0"]

    t = np.array(res["timestamps"])
    pos = np.array(res["positions"])
    est = np.array([latlon_to_enu(la, lo, lat0, lon0)[:2] for la, lo in pos])

    ref = v_df.dropna(subset=["gps_lat", "gps_lon"])
    ref_enu = np.array([latlon_to_enu(la, lo, lat0, lon0)[:2]
                        for la, lo in zip(ref["gps_lat"], ref["gps_lon"])])
    rt = ref["timestamp_s"].values
    truth = np.column_stack([np.interp(t + off, rt, ref_enu[:, 0]),
                             np.interp(t + off, rt, ref_enu[:, 1])])
    err_vec = est - truth
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
    inside = 0
    for (cxx, cyy, cxy), e in zip(cov, err_vec[m_out]):
        P = np.array([[cxx, cxy], [cxy, cyy]])
        try:
            d2 = float(e @ np.linalg.solve(P, e))
        except np.linalg.LinAlgError:
            d2 = np.inf
        inside += d2 <= 1.0
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
    rp_truth = np.column_stack([np.interp(rp["timestamp_s"] + off, rt, ref_enu[:, 0]),
                                np.interp(rp["timestamp_s"] + off, rt, ref_enu[:, 1])])
    gnss_pre = float(np.linalg.norm(rp_enu - rp_truth, axis=1).mean())

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
    return res


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "S3b")

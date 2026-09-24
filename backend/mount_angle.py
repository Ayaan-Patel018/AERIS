"""
mount_angle.py — phone horizontal frame -> vehicle forward direction (angle phi).

CALIBRATION PHASE, phone data only (VBOX is never read here). Only rows with
timestamp_s <= t_cal_max (default 200 s) are used, so a live system could run this
once early in the drive and then hold phi fixed.

Definitions (phone x/y = the horizontal plane; the gravity columns are ~(0,0,g)):
    a_h   = [linear_accel_x, linear_accel_y]
    a_fwd = a_h . [cos phi,  sin phi]        a_lat = a_h . [-sin phi, cos phi]
    phi is the angle of the vehicle's forward axis measured from phone +x toward +y.

Two independent criteria, each a grid search over phi in 1 deg steps:
  (i)  integral of a_fwd over each interval between consecutive NEW phone fixes
       correlated with the phone-GNSS speed change over that interval
       (speed at fix b minus speed at fix a). Maximum correlation -> phi.
  (ii) a_lat correlated with v * omega_vert in turns (|omega_vert| > 0.1 rad/s,
       v > 3 m/s). v = phone GNSS speed linearly interpolated between fixes and
       accel/gyro smoothed over 0.5 s — acceptable ONLY because this is an
       offline calibration, never used inside a real-time filter.
       omega_vert = gyro . g_hat with the A2 axis mapping, counter-clockwise +.
       A left turn gives a_lat > 0 when +lateral points left, so the maximum
       gives the lateral axis and forward = lateral - 90 deg.

Usage:  python backend/mount_angle.py [S3b S1 ...]
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

SPIKE_ACC = 15.0      # m/s^2  samples beyond this are sensor spikes -> 0
SPIKE_GYRO = 5.0      # rad/s
PHIS = np.deg2rad(np.arange(-180.0, 180.0, 1.0))


def _new_fix_rows(s_df):
    lat, lon = s_df["gps_lat"].values, s_df["gps_lon"].values
    fix = np.r_[True, (np.diff(lat) != 0) | (np.diff(lon) != 0)] & np.isfinite(lat) & np.isfinite(lon)
    return np.where(fix)[0]


def _wrap_deg(a):
    return (a + 180.0) % 360.0 - 180.0


def _smooth(x, n=5):
    return np.convolve(x, np.ones(n) / n, mode="same")


def _circ_plateau(phis_deg, corr, drop=0.05):
    """Width (deg) of the contiguous circular range around the peak with corr >= peak - drop."""
    k = int(np.argmax(corr)); ok = corr >= corr[k] - drop; n = len(corr)
    lo = hi = k
    while ok[(lo - 1) % n] and (k - lo) < n // 2: lo -= 1
    while ok[(hi + 1) % n] and (hi - k) < n // 2: hi += 1
    return hi - lo + 1


def _corr_curve(cols, y):
    """corr( c0*u0(phi) + c1*u1(phi), y ) for every phi; cols is (n, 2) of the two accel components."""
    out = np.full(len(PHIS), np.nan)
    for i, ph in enumerate(PHIS):
        x = cols @ np.array([np.cos(ph), np.sin(ph)])
        if np.std(x) > 0 and np.std(y) > 0:
            out[i] = np.corrcoef(x, y)[0, 1]
    return out


def estimate_mount_angle(s_df, t_cal_max=200.0):
    ts = s_df["timestamp_s"].values
    n = len(ts)
    ax = s_df["linear_accel_x"].values.astype(float).copy()
    ay = s_df["linear_accel_y"].values.astype(float).copy()
    ax[~np.isfinite(ax) | (np.abs(ax) > SPIKE_ACC)] = 0.0
    ay[~np.isfinite(ay) | (np.abs(ay) > SPIKE_ACC)] = 0.0
    spd = s_df["gps_speed_ms"].values.astype(float)
    dt = np.r_[np.diff(ts), 0.1]
    dt[(dt <= 0) | (dt > 1.0)] = 0.1
    fixes = _new_fix_rows(s_df)
    fixes_cal = fixes[ts[fixes] <= t_cal_max]

    # ── (i) integral of a_fwd over fix intervals vs GNSS speed change ─────────
    Ix, Iy, dv = [], [], []
    for a, b in zip(fixes_cal[:-1], fixes_cal[1:]):
        if ts[b] - ts[a] > 15.0 or not (np.isfinite(spd[a]) and np.isfinite(spd[b])):
            continue
        Ix.append(np.sum(ax[a:b] * dt[a:b])); Iy.append(np.sum(ay[a:b] * dt[a:b])); dv.append(spd[b] - spd[a])
    I = np.column_stack([Ix, Iy]); dv = np.array(dv)
    c_i = _corr_curve(I, dv) if len(dv) >= 4 else np.full(len(PHIS), np.nan)

    # ── (ii) a_lat vs v * omega_vert in turns ────────────────────────────────
    G = s_df[["gravity_x", "gravity_y", "gravity_z"]].values.astype(float)
    gn = np.linalg.norm(G, axis=1, keepdims=True)
    ghat = np.where(gn > 1.0, G / np.where(gn > 1.0, gn, 1.0), np.array([0.0, 0.0, 1.0]))
    W = s_df[["gyro_roll_rads", "gyro_pitch_rads", "gyro_yaw_rads"]].values.astype(float).copy()
    W[~np.isfinite(W) | (np.abs(W) > SPIKE_GYRO)] = 0.0
    wv = np.sum(W * ghat, axis=1)
    fx = fixes[np.isfinite(spd[fixes])]
    v = np.interp(ts, ts[fx], spd[fx])
    ws, axs, ays = _smooth(wv), _smooth(ax), _smooth(ay)
    m = (ts <= t_cal_max) & (v > 3.0) & (np.abs(ws) > 0.1)
    y = (v * ws)[m]
    A = np.column_stack([axs[m], ays[m]])
    # a_lat = a_h . [-sin phi, cos phi]  ==  a_h . [cos(phi+90), sin(phi+90)]  -> curve over the LATERAL angle
    c_lat = _corr_curve(A, y) if m.sum() >= 50 else np.full(len(PHIS), np.nan)
    c_ii = np.roll(c_lat, -90)      # index by forward angle phi = lateral angle - 90 deg

    phis_deg = np.rad2deg(PHIS)
    out = dict(t_cal_max=t_cal_max, phis_deg=phis_deg, corr_i=c_i, corr_ii=c_ii,
               n_i=int(len(dv)), n_ii=int(m.sum()))
    for key, c in (("i", c_i), ("ii", c_ii)):
        if np.all(np.isnan(c)):
            out[f"phi_{key}"] = float("nan"); out[f"peak_{key}"] = float("nan"); out[f"width_{key}"] = float("nan")
        else:
            k = int(np.nanargmax(c))
            out[f"phi_{key}"] = float(phis_deg[k]); out[f"peak_{key}"] = float(c[k])
            out[f"width_{key}"] = _circ_plateau(phis_deg, np.nan_to_num(c, nan=-1.0))
    # scale sanity for (ii): slope of v*omega on a_lat at the best phi
    if not np.isnan(out["phi_ii"]):
        ph = np.deg2rad(out["phi_ii"])
        a_lat = A @ np.array([-np.sin(ph), np.cos(ph)])
        out["slope_ii"] = float(np.polyfit(y, a_lat, 1)[0])
    if not np.isnan(out["phi_i"]):
        ph = np.deg2rad(out["phi_i"])
        out["slope_i"] = float(np.polyfit(dv, I @ np.array([np.cos(ph), np.sin(ph)]), 1)[0])
    if not (np.isnan(out["phi_i"]) or np.isnan(out["phi_ii"])):
        out["diff_deg"] = float(_wrap_deg(out["phi_i"] - out["phi_ii"]))
    return out


def window_scan(s_df, win=30.0, tmax=None, min_samples=30):
    """Criterion (ii) per time window: is the mounting angle constant over the drive?
    Returns rows (t0, n, phi_deg, local_corr, slope). A constant mount gives the same phi in
    every well-fitting window (high corr); a moving phone gives good fits at different phi."""
    ts = s_df["timestamp_s"].values
    tmax = ts[-1] if tmax is None else tmax
    ax = s_df["linear_accel_x"].values.astype(float).copy(); ay = s_df["linear_accel_y"].values.astype(float).copy()
    ax[~np.isfinite(ax) | (np.abs(ax) > SPIKE_ACC)] = 0.0; ay[~np.isfinite(ay) | (np.abs(ay) > SPIKE_ACC)] = 0.0
    w = s_df["gyro_yaw_rads"].values.astype(float).copy(); w[~np.isfinite(w) | (np.abs(w) > SPIKE_GYRO)] = 0.0
    spd = s_df["gps_speed_ms"].values.astype(float)
    fx = _new_fix_rows(s_df); fx = fx[np.isfinite(spd[fx])]
    v = np.interp(ts, ts[fx], spd[fx])
    axs, ays, ws = _smooth(ax), _smooth(ay), _smooth(w)
    rows = []
    for a in np.arange(0.0, tmax, win):
        m = (ts >= a) & (ts < a + win) & (v > 2.5) & (np.abs(ws) > 0.1)
        if m.sum() < min_samples:
            continue
        A, y = np.column_stack([axs[m], ays[m]]), (v * ws)[m]
        c = np.roll(_corr_curve(A, y), -90)
        k = int(np.nanargmax(c)); ph = PHIS[k]
        slope = float(np.polyfit(y, A @ np.array([-np.sin(ph), np.cos(ph)]), 1)[0])
        rows.append((float(a), int(m.sum()), float(np.rad2deg(ph)), float(c[k]), slope))
    return rows


def format_windows(name, rows, good=0.8):
    lines = [f"--- {name}: mounting angle per window (criterion ii) ---", "  window        n     phi    corr   slope"]
    for a, n, p, c, sl in rows:
        lines.append(f"  {a:6.0f}+      {n:4d} {p:+7.1f}   {c:+.2f}   {sl:+.2f}{'' if c > good else '   (weak fit)'}")
    ph = [p for _, _, p, c, _ in rows if c > good]
    if ph:
        z = np.exp(1j * np.deg2rad(ph)); mean = np.rad2deg(np.angle(z.mean())); R = abs(z.mean())
        lines.append(f"  well-fitting windows (corr > {good}): {len(ph)}/{len(rows)}; circular mean phi {mean:+.1f} deg, "
                     f"resultant length {R:.2f} (1.0 = all identical, ~0 = uniformly spread)")
    return "\n".join(lines)


def format_report(name, r):
    lines = [f"--- {name}: calibration on t <= {r['t_cal_max']:.0f} s ---"]
    lines.append(f"  (i)  integral(a_fwd) vs GNSS speed change : n={r['n_i']:4d} intervals   "
                 f"phi = {r['phi_i']:+7.1f} deg   corr = {r['peak_i']:+.3f}   "
                 f"plateau(corr >= peak-0.05) = {r['width_i']} deg   slope = {r.get('slope_i', float('nan')):+.2f}")
    lines.append(f"  (ii) a_lat vs v*omega_vert in turns      : n={r['n_ii']:4d} samples     "
                 f"phi = {r['phi_ii']:+7.1f} deg   corr = {r['peak_ii']:+.3f}   "
                 f"plateau(corr >= peak-0.05) = {r['width_ii']} deg   slope = {r.get('slope_ii', float('nan')):+.2f}")
    if "diff_deg" in r:
        lines.append(f"  disagreement (i) - (ii) = {r['diff_deg']:+.1f} deg")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    from data_loader import load_smartphone, get_dataset_root
    ap = argparse.ArgumentParser()
    ap.add_argument("drives", nargs="*", default=["S3b", "S1"])
    ap.add_argument("--windows", type=float, default=0.0, help="also print the per-window scan with this window length (s)")
    ap.add_argument("--tmax", type=float, default=None, help="end of the window scan (s); default = whole drive")
    a = ap.parse_args()
    for d in a.drives:
        base = os.path.join(get_dataset_root(), "Synchronised V abd S datasets",
                            "Categorised IOVNB Dataset", "S (Driver A)", d)
        s = load_smartphone(os.path.join(base, f"S-{d}.csv"))
        print(format_report(d, estimate_mount_angle(s, 200.0)))
        if a.windows > 0:
            print(format_windows(d, window_scan(s, a.windows, a.tmax)))

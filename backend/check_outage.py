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

E0 additions (the older output above is unchanged):
  3. along-/cross-track split, speed diagnostics and path ratio of the 200–260 s outage
  4. SLIDING 60 s OUTAGES (vehicle_dr only): a simulated 60 s GNSS outage every 10 s wherever the drive allows
     (window plan in window_plan.py), scored against the truth with along/cross, path ratio and speed error, next to
     the constant-velocity and hold baselines. Default on S3b = the tuning set (windows that END before 200 s).
Reserved drives (S3c final validation, S3a reserve, S4 training) are not scored without --unseal.

Usage:
    python backend/check_outage.py                       # S3b, esekf
    python backend/check_outage.py S1 --mini-only
    python backend/check_outage.py S3b --fixes-only      # esekf fed GNSS only on new-fix rows
    python backend/check_outage.py S3b --filter vehicle_dr                  # + the S3b tuning windows
    python backend/check_outage.py S1 --filter vehicle_dr --windows all     # secondary report (slow: one run per window)
Windows console: set PYTHONUTF8=1 when piping the output.
"""
import argparse
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from data_loader import load_smartphone, load_vehicle, get_dataset_root, sv_time_offset
from ins_ekf import latlon_to_enu
import window_plan

OUTAGE = (200.0, 260.0)
FILTERS = ("esekf", "vehicle_dr")
WINDOW_S = window_plan.LENGTH_S
LAUNCH_LOOKBACK_S = 10.0     # a window "starts within 10 s after an IMU standstill" if the standstill flag was set in [start - 10 s, start]
RESERVED = {"S3c": "final validation drive (B5)", "S3a": "reserve drive",
            "S4": "I3 training drive (never scored)"}       # registry v2: S2 became a development drive


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


# ══ E0 — along/cross split, speed diagnostics, sliding 60 s outages ═══════════════════════════════════════════════
def guard_drive(drive, unseal=False):
    """Reserved drives are not scored before their planned use (drive registry in AERIS_FINDINGS.md)."""
    if drive in RESERVED and not unseal:
        raise SystemExit(f"{drive} is the {RESERVED[drive]}: it is not scored before its planned use "
                         f"(drive registry in AERIS_FINDINGS.md). Re-run with --unseal only when that step is due.")


def origin(s_df):
    """Local-frame origin = first row with a finite position (the rule vehicle_dr.run_pipeline uses)."""
    lat, lon = s_df["gps_lat"].values.astype(float), s_df["gps_lon"].values.astype(float)
    k = int(np.flatnonzero(np.isfinite(lat) & np.isfinite(lon))[0])
    return float(lat[k]), float(lon[k])


class Truth:
    """Reference (VBOX) track in the filter's local ENU frame, on the phone clock (V time = phone time + off).
    SCORING ONLY — nothing here is ever passed to a filter.
    direction(t) = unit vector of travel = position(t + 0.5 s) - position(t - 0.5 s), normalised; while the car is
    (nearly) stopped (< 0.3 m in that second) the last moving direction is carried forward, so along/cross stay defined.
    Limitation: within 0.5 s of the first/last reference sample the chord is one-sided (np.interp clamps), which is
    slightly biased on a curve (0.25 m at R = 50 m, 10 m/s). Windows end well inside the reference file, so it is not hit."""
    DIR_HALF_S = 0.5
    MIN_MOVE_M = 0.3

    def __init__(self, rt, xy, speed, off=0.0, yaw_rate=None):
        self.rt, self.xy, self.off = np.asarray(rt, float), np.asarray(xy, float), float(off)
        sp = np.asarray(speed, float)
        ok = np.isfinite(sp)
        self.spd = np.interp(self.rt, self.rt[ok], sp[ok]) if ok.any() else np.zeros(len(self.rt))
        yw = np.asarray(yaw_rate, float) if yaw_rate is not None else np.full(len(self.rt), np.nan)     # rad/s (S0 audit; NaN = not available)
        oky = np.isfinite(yw)
        self.yaw = np.interp(self.rt, self.rt[oky], yw[oky]) if oky.any() else np.full(len(self.rt), np.nan)
        self._dir = self._directions()

    @classmethod
    def from_vehicle(cls, v_df, lat0, lon0, off):
        _, ref, ref_enu, rt = _truth_fn(v_df, lat0, lon0, off)
        yaw = np.radians(ref["yaw_rate_degs"].values.astype(float)) if "yaw_rate_degs" in ref else None
        return cls(rt, ref_enu, ref["gps_speed_ms"].values, off, yaw)

    def covers(self, t):
        """True where the phone time t maps inside the reference file (np.interp clamps outside it: such rows must not be scored)."""
        tv = np.asarray(t, dtype=float) + self.off
        return (tv >= self.rt[0]) & (tv <= self.rt[-1])

    def yaw_rate(self, t):
        """Reference yaw rate (rad/s, signed) at phone time t; NaN when the reference has no yaw-rate column."""
        return np.interp(np.asarray(t, dtype=float) + self.off, self.rt, self.yaw)

    def pos(self, t):
        t = np.asarray(t, dtype=float) + self.off
        return np.column_stack([np.interp(t, self.rt, self.xy[:, 0]), np.interp(t, self.rt, self.xy[:, 1])])

    def speed(self, t):
        return np.interp(np.asarray(t, dtype=float) + self.off, self.rt, self.spd)

    def _directions(self):
        h = self.DIR_HALF_S
        p1 = np.column_stack([np.interp(self.rt + h, self.rt, self.xy[:, i]) for i in (0, 1)])
        p0 = np.column_stack([np.interp(self.rt - h, self.rt, self.xy[:, i]) for i in (0, 1)])
        d = p1 - p0
        n = np.linalg.norm(d, axis=1)
        ok = n > self.MIN_MOVE_M
        unit = d / np.maximum(n, 1e-9)[:, None]
        if not ok.any():
            return np.full_like(unit, np.nan)
        idx = np.maximum.accumulate(np.where(ok, np.arange(len(n)), -1))
        idx = np.where(idx < 0, np.flatnonzero(ok)[0], idx)          # before the first movement: the first direction
        return unit[idx]

    def direction(self, t):
        tv = np.asarray(t, dtype=float) + self.off
        j = np.clip(np.searchsorted(self.rt, tv), 1, len(self.rt) - 1)
        j = np.where(np.abs(self.rt[j] - tv) < np.abs(self.rt[j - 1] - tv), j, j - 1)
        return self._dir[j]


def score_track(truth, t, est, v_est=None, cov=None):
    """
    Score an estimated track (ENU metres, one row per epoch t) against the truth on the same epochs.
      along  = (est - truth) . direction of travel   (+ = AERIS ahead of the truth)
      cross  = (est - truth) . left normal           (+ = AERIS to the left of the truth)
    so along^2 + cross^2 = error^2 at every epoch. path_ratio = path(est) / path(truth), both on the epoch grid.
    v_est (m/s) adds speed diagnostics against the reference speed; cov ([cxx, cyy, cxy] rows) adds the 1-sigma coverage.
    """
    t, est = np.asarray(t, float), np.asarray(est, float)
    tp = truth.pos(t)
    e = est - tp
    err = np.linalg.norm(e, axis=1)
    d = truth.direction(t)
    nl = np.column_stack([-d[:, 1], d[:, 0]])
    along, cross = np.sum(e * d, axis=1), np.sum(e * nl, axis=1)
    p_est, p_true = _path_len(est), _path_len(tp)
    out = dict(n=len(t), mean_err=float(err.mean()), end_err=float(err[-1]), max_err=float(err.max()),
               mean_abs_along=float(np.nanmean(np.abs(along))), mean_abs_cross=float(np.nanmean(np.abs(cross))),
               along_end=float(along[-1]), cross_end=float(cross[-1]),
               abs_along_end=float(abs(along[-1])), abs_cross_end=float(abs(cross[-1])),
               path_est=p_est, path_true=p_true, path_ratio=(p_est / p_true) if p_true > 1.0 else float("nan"))
    if v_est is not None:
        v_est = np.asarray(v_est, float)
        vt = truth.speed(t)
        k30 = int(np.argmin(np.abs(t - (t[0] + 30.0))))
        out.update(mean_abs_dv=float(np.mean(np.abs(v_est - vt))), dv_end=float(v_est[-1] - vt[-1]),
                   v_est_30=float(v_est[k30]), v_true_30=float(vt[k30]),
                   v_est_end=float(v_est[-1]), v_true_end=float(vt[-1]))
    if cov is not None:
        ins = [_inside_1sigma(c, ee) for c, ee in zip(np.asarray(cov, float), e)]
        out.update(inside=100.0 * float(np.mean(ins)), inside_end=100.0 * float(ins[-1]))
    return out


def _res_enu(res, mask=None):
    pos = np.asarray(res["positions"], dtype=float)
    if mask is not None:
        pos = pos[mask]
    return np.array([latlon_to_enu(la, lo, res["lat0"], res["lon0"])[:2] for la, lo in pos])


def outage_e0_report(res, truth, window=OUTAGE):
    """Along/cross split, speed diagnostics and path ratio of the (single) outage window in `res`."""
    t = np.array(res["timestamps"])
    m = (t >= window[0]) & (t <= window[1])
    sc = score_track(truth, t[m], _res_enu(res, m), np.array(res["velocities"])[m], np.array(res["cov_matrix"])[m])
    print(f"--- E0: outage {window[0]:.0f}-{window[1]:.0f} s — along / cross split, speed, path ratio "
          f"(+along = AERIS ahead of truth, +cross = AERIS left of truth) ---")
    print(f"mean |along| / mean |cross|  : {sc['mean_abs_along']:8.2f} / {sc['mean_abs_cross']:.2f} m   (mean error {sc['mean_err']:.2f} m)")
    print(f"at the end of the outage     : along {sc['along_end']:+8.2f} m, cross {sc['cross_end']:+.2f} m   (end error {sc['end_err']:.2f} m)")
    print(f"path ratio AERIS / truth     : {sc['path_ratio']:8.2f}     ({sc['path_est']:.1f} m / {sc['path_true']:.1f} m, both on the AERIS 10 Hz grid)")
    print(f"speed, filter v vs VBOX speed: mean |dv| {sc['mean_abs_dv']:.2f} m/s;  +30 s: {sc['v_est_30']:.2f} vs {sc['v_true_30']:.2f};  "
          f"+60 s: {sc['v_est_end']:.2f} vs {sc['v_true_end']:.2f} m/s")
    return sc


def baseline_tracks(s_df, fix_rows, start, t, lat0, lon0):
    """Phone-only baselines for an outage that starts at `start`: they use the last usable NEW fix strictly before it.
    hold = stay at that fix;  cv = that fix + its GNSS speed along its GNSS course (speed <= 1 m/s counts as 0)."""
    ts = s_df["timestamp_s"].values
    a = int(fix_rows[np.searchsorted(ts[fix_rows], start, side="left") - 1])
    pa = np.asarray(latlon_to_enu(s_df["gps_lat"].iloc[a], s_df["gps_lon"].iloc[a], lat0, lon0)[:2], dtype=float)
    spd, brg = float(s_df["gps_speed_ms"].iloc[a]), float(s_df["gps_heading_deg"].iloc[a])
    v = spd if np.isfinite(spd) and np.isfinite(brg) and spd > 1.0 else 0.0
    c = np.deg2rad(brg) if np.isfinite(brg) else 0.0
    cv = pa + v * (np.asarray(t) - ts[a])[:, None] * np.array([np.sin(c), np.cos(c)])
    return cv, np.full(len(t), v), np.tile(pa, (len(t), 1))


def window_benchmark(s_df, truth, starts, params=None, length=WINDOW_S, run_kw=None, audit=False):
    """
    Simulate a `length` s GNSS outage starting at each t in `starts` (vehicle_dr; GNSS hidden on [start, start+length]) and
    score the outage rows. The filter is causal, so each run is truncated at the window end (exactness is unit-tested).
    Returns one dict per window: start, and score_track() dicts for 'vdr', 'cv' (const-velocity) and 'hold' baselines.
    audit=True adds row["audit"] = stationarity_audit() restricted to the outage span [start, start + length] (S0).
    """
    import vehicle_dr
    lat0, lon0 = origin(s_df)
    ts = s_df["timestamp_s"].values
    fix_rows = window_plan.usable_fix_rows(s_df)
    out = []
    for s0 in starts:
        s1 = s0 + length
        sub = s_df[ts <= s1 + 1.0]
        sub.attrs = s_df.attrs
        res = vehicle_dr.run_pipeline(sub, None, outage_window=(s0, s1), params=params, t_end=s1, **(run_kw or {}))
        assert (res["lat0"], res["lon0"]) == (lat0, lon0)
        t = np.array(res["timestamps"])
        m = (t >= s0) & (t <= s1)
        tw = t[m]
        cv, vcv, hold = baseline_tracks(s_df, fix_rows, s0, tw, lat0, lon0)
        st = np.asarray(res["stationary"], dtype=bool)               # IMU-only standstill flag of the filter (causal)
        stopped_recently = bool(np.any(st[(t >= s0 - LAUNCH_LOOKBACK_S) & (t <= s0)]))
        out.append(dict(start=float(s0), n=int(m.sum()), stopped_recently=stopped_recently,
                        vdr=score_track(truth, tw, _res_enu(res, m), np.array(res["velocities"])[m], np.array(res["cov_matrix"])[m]),
                        cv=score_track(truth, tw, cv, vcv), hold=score_track(truth, tw, hold, np.zeros(len(tw))),
                        gate_counts=res.get("gate_counts")))
        if audit:
            out[-1]["audit"] = stationarity_audit(res, truth, span=(s0, s1))
    return out


WINDOW_METRICS = [("mean_err", "mean error (m)"), ("end_err", "end error (m)"),
                  ("abs_along_end", "|along| at end (m)"), ("abs_cross_end", "|cross| at end (m)"),
                  ("along_end", "along at end, signed (m)"), ("cross_end", "cross at end, signed (m)"),
                  ("path_ratio", "path ratio AERIS/truth"), ("mean_abs_dv", "mean |speed error| (m/s)"),
                  ("inside", "truth inside 1-sigma (%)")]


def summarize_windows(rows, who):
    """{metric: (median, mean, p90)} over windows; p90 = numpy linear-interpolated 90th percentile; NaNs dropped."""
    out = {}
    for key, _ in WINDOW_METRICS:
        x = np.array([r[who].get(key, np.nan) for r in rows], dtype=float)
        x = x[np.isfinite(x)]
        out[key] = (float(np.median(x)), float(x.mean()), float(np.percentile(x, 90))) if len(x) else (np.nan,) * 3
    return out


def window_report(rows, scope, label="vehicle_dr", per_window=None):
    print(f"--- sliding {WINDOW_S:.0f} s outages ({scope}): {len(rows)} windows, GNSS hidden on [start, start+{WINDOW_S:.0f} s] ---")
    if not rows:
        print("   no windows"); return {}
    who = [("vdr", label), ("cv", "const-v baseline"), ("hold", "hold-last-fix")]
    summ = {k: summarize_windows(rows, k) for k, _ in who}
    print(f"{'':27s}" + "".join(f"{name:^27s}" for _, name in who))
    print(f"{'(median / mean / p90)':27s}" + "".join(f"{'median':>9s}{'mean':>9s}{'p90':>9s}" for _ in who))
    for key, name in WINDOW_METRICS:
        cells = ""
        for k, _ in who:
            med, mean, p90 = summ[k][key]
            cells += ("".join(f"{v:9.2f}" for v in (med, mean, p90)) if np.isfinite(med) else f"{'-':>9s}{'-':>9s}{'-':>9s}")
        print(f"{name:27s}{cells}")
    if per_window is None:
        per_window = len(rows) <= 20
    if per_window:
        print(f"{'start':>7s} | {label:^43s} | {'const-v baseline':^19s}")
        print(f"{'(s)':>7s} | {'mean':>7s}{'end':>8s}{'along':>8s}{'cross':>8s}{'ratio':>7s}{'in1s%':>6s} | {'mean':>9s}{'end':>9s}")
        for r in rows:
            v, c = r["vdr"], r["cv"]
            print(f"{r['start']:7.0f} | {v['mean_err']:7.1f}{v['end_err']:8.1f}{v['along_end']:+8.1f}{v['cross_end']:+8.1f}"
                  f"{v['path_ratio']:7.2f}{v.get('inside', float('nan')):6.0f} | {c['mean_err']:9.1f}{c['end_err']:9.1f}")
    return summ


# ══ S0 — stationarity audit (VBOX = SCORING ONLY) ═════════════════════════════════════════════════════════════════
MOVE_MPS = 0.5            # VBOX speed above this = moving; a flagged standstill at this speed is a FALSE standstill
STOP_MPS = 0.2            # VBOX speed below this = truly stopped
FALSE_EP_MIN_S = 1.0      # a flagged episode is a "false episode" if it holds at least this many seconds of false standstill
AUDIT_SUMS = ("time", "moving", "stopped", "flagged", "false", "stopped_flagged", "dist_lost", "turn_lost", "path", "turn_total", "missed", "missed_dist")


def stationarity_audit(res, truth, span=None):
    """
    Audit the vehicle_dr IMU-only standstill flag against the reference (VBOX) motion. Rows are weighted by their real time step;
    only rows inside the reference file (and inside `span` = (t0, t1), e.g. an outage window) count. Definitions:
      false standstill  = flag set AND reference speed > MOVE_MPS            (the filter freezes v and drops the turn rate)
      true-stop recall  = flagged time / time with reference speed < STOP_MPS
      distance lost     = integral of the reference speed over the false-standstill time
      turning lost      = integral of |reference yaw rate| over the same time (rad)
      missed stop       = reference stopped (speed < STOP_MPS) but NOT flagged: the filter keeps its speed and "drives" on the spot;
                          missed distance = integral of the filter's own speed over that time (the mirror-image damage)
    Each standstill episode (res["standstill_log"]) is scored on its own: entry branch (v_gate = the speed estimate was already
    below v_gate; override = only the sustained-quiet `quiet_enter_n` branch could have fired), exit reason, false seconds,
    reference speed at entry, and kind = "false entry" (entered while the reference was moving) or "late release" (entered at rest,
    the car then moved on while the flag stayed set).
    """
    t = np.asarray(res["timestamps"], float)
    flag = np.asarray(res["stationary"], bool)
    dt = np.r_[np.median(np.diff(t)) if len(t) > 1 else 0.1, np.diff(t)]
    use = truth.covers(t)
    if span is not None:
        use &= (t >= span[0]) & (t <= span[1])
    v = truth.speed(t)
    w = np.abs(truth.yaw_rate(t))
    w = np.where(np.isfinite(w), w, 0.0)
    moving, stopped = v > MOVE_MPS, v < STOP_MPS
    false = flag & moving
    missed = stopped & ~flag
    v_filter = np.abs(np.asarray(res["velocities"], float))

    def sec(m):
        return float(dt[m & use].sum())

    out = dict(time=sec(np.ones(len(t), bool)), moving=sec(moving), stopped=sec(stopped), flagged=sec(flag), false=sec(false),
               stopped_flagged=sec(flag & stopped), dist_lost=float((v * dt)[false & use].sum()), turn_lost=float((w * dt)[false & use].sum()),
               path=float((v * dt)[moving & use].sum()), turn_total=float((w * dt)[moving & use].sum()),
               missed=sec(missed), missed_dist=float((v_filter * dt)[missed & use].sum()),
               holes=int(np.sum((dt > 1.0) & use)),
               false_v_med=float(np.median(v[false & use])) if (false & use).any() else float("nan"),
               false_v_max=float(v[false & use].max()) if (false & use).any() else float("nan"),
               flag_v_med=float(np.median(v[flag & use])) if (flag & use).any() else float("nan"),
               flag_v_max=float(v[flag & use].max()) if (flag & use).any() else float("nan"))
    eps = []
    for e in res.get("standstill_log", []):
        te = e["t_exit"]
        r = (t >= e["t_enter"]) & ((t <= te) if e.get("exit") == "end" else (t < te)) & use
        if not r.any():
            continue
        f = r & moving
        v_in = float(truth.speed([e["t_enter"]])[0]) if truth.covers([e["t_enter"]])[0] else float("nan")
        eps.append(dict(t_enter=e["t_enter"], t_exit=te, dur=float(dt[r].sum()), false_s=float(dt[f].sum()),
                        branch="v_gate" if e["via_v_gate"] else ("override" if e["via_override"] else "?"),
                        both=bool(e["via_v_gate"] and e["via_override"]), exit=e.get("exit", "?"), v_est=e["v_est"], gap_prev=e["gap_prev"],
                        v_entry=v_in, kind="false entry" if v_in > MOVE_MPS else "late release",
                        v_mean=float(np.average(v[f], weights=dt[f])) if f.any() else float("nan"), v_max=float(v[f].max()) if f.any() else float("nan"),
                        dist_lost=float((v * dt)[f].sum()), turn_lost=float((w * dt)[f].sum()),
                        in_span=span is None or span[0] <= e["t_enter"] <= span[1]))
    out["episodes"] = eps
    out["n_episodes"] = len(eps)
    out["n_false"] = sum(1 for e in eps if e["false_s"] >= FALSE_EP_MIN_S)
    return out


def _audit_lines(a, label):
    mv = max(a["moving"], 1e-9)
    print(f"--- stationarity audit ({label}) — VBOX used for scoring only; false = flagged AND VBOX speed > {MOVE_MPS} m/s ---")
    print(f"time scored {a['time']:.0f} s (VBOX moving {a['moving']:.0f} s, stopped < {STOP_MPS} m/s {a['stopped']:.0f} s); "
          f"flagged {a['flagged']:.1f} s in {a['n_episodes']} episodes{' (data holes: %d)' % a['holes'] if a.get('holes') else ''}")
    print(f"FALSE-standstill time      : {a['false']:8.1f} s = {100 * a['false'] / mv:5.2f} % of moving time, {100 * a['false'] / max(a['flagged'], 1e-9):4.1f} % of flagged time; "
          f"{a['n_false']} false episodes (>= {FALSE_EP_MIN_S:.0f} s of false time) of {a['n_episodes']}")
    print(f"VBOX speed while falsely flagged: median {a['false_v_med']:.2f} / max {a['false_v_max']:.2f} m/s;   while flagged (all): median {a['flag_v_med']:.2f} / max {a['flag_v_max']:.2f} m/s")
    print(f"true-stop recall           : {100 * a['stopped_flagged'] / max(a['stopped'], 1e-9):5.1f} %  ({a['stopped_flagged']:.1f} of {a['stopped']:.1f} s of VBOX-stopped time is flagged)")
    print(f"damage while falsely frozen: distance lost {a['dist_lost']:.1f} m ({100 * a['dist_lost'] / max(a['path'], 1e-9):.2f} % of the {a['path']:.0f} m driven), "
          f"turning lost {np.degrees(a['turn_lost']):.0f} deg ({100 * a['turn_lost'] / max(a['turn_total'], 1e-9):.2f} % of {np.degrees(a['turn_total']):.0f} deg turned)")
    print(f"mirror image (missed stops): {a['missed']:.1f} s of VBOX-stopped time NOT flagged; the filter's own speed integrates to {a['missed_dist']:.1f} m of phantom driving during it")


def audit_report(a, label, top=12):
    """Print the whole-run audit: totals, entry-branch split of the false episodes, and the `top` worst false episodes."""
    _audit_lines(a, label)
    fe = sorted([e for e in a["episodes"] if e["false_s"] >= FALSE_EP_MIN_S], key=lambda e: -e["false_s"])
    for br in ("v_gate", "override"):
        sel = [e for e in fe if e["branch"] == br]
        print(f"  false episodes entered via {br:8s}: {len(sel):3d}  ({sum(e['false_s'] for e in sel):7.1f} s false, {sum(e['dist_lost'] for e in sel):7.0f} m lost"
              f"{', %d of them with both branches true' % sum(e['both'] for e in sel) if br == 'v_gate' else ''})")
    for kd in ("false entry", "late release"):
        sel = [e for e in fe if e["kind"] == kd]
        print(f"  false episodes, {kd:12s}: {len(sel):3d}  ({sum(e['false_s'] for e in sel):7.1f} s false)   "
              f"[false entry = flag set while VBOX moving; late release = flag set at rest, the car then drove off while it stayed set]")
    if fe:
        print(f"  worst {min(top, len(fe))} false episodes (t_enter-t_exit s, dur, false s, kind, branch, exit, VBOX v at entry / mean / max m/s, v_est at entry, gap to previous episode s, m lost, deg lost):")
        for e in fe[:top]:
            print(f"    {e['t_enter']:8.1f}-{e['t_exit']:8.1f}  {e['dur']:5.1f}  {e['false_s']:5.1f}  {e['kind']:12s} {e['branch']:8s}{'*' if e['both'] else ' '} {e['exit']:8s}"
                  f" {e['v_entry']:5.2f} / {e['v_mean']:5.2f} / {e['v_max']:5.2f}  v_est {e['v_est']:5.2f}  gap {min(e['gap_prev'], 9999):7.1f}  {e['dist_lost']:6.1f} m  {np.degrees(e['turn_lost']):6.1f} deg")
        print("    (* = both entry branches were true; attributed to v_gate because that branch alone would have sufficed)")


def audit_windows_report(rows, label):
    """Aggregate the per-window audits (window_benchmark(..., audit=True)) over the outage spans; windows overlap, so the sums count
    each stretch of driving several times — read them as fractions, not as absolute seconds."""
    aud = [r["audit"] for r in rows]
    tot = {k: sum(a[k] for a in aud) for k in AUDIT_SUMS}
    tot.update(holes=sum(a["holes"] for a in aud))
    allv = [(e, a) for a in aud for e in a["episodes"]]
    fs = np.array([a["false"] for a in aud])
    mv = max(tot["moving"], 1e-9)
    print(f"--- stationarity audit ({label}): outage spans of {len(rows)} windows (60 s each; GNSS hidden, windows overlap) ---")
    print(f"time in spans {tot['time']:.0f} s (VBOX moving {tot['moving']:.0f} s, stopped {tot['stopped']:.0f} s); flagged {tot['flagged']:.0f} s")
    print(f"FALSE-standstill time      : {tot['false']:.0f} s = {100 * tot['false'] / mv:5.2f} % of moving time in the spans, {100 * tot['false'] / max(tot['flagged'], 1e-9):4.1f} % of flagged time")
    print(f"per window (false s in the 60 s span): median {np.median(fs):.1f}, p90 {np.percentile(fs, 90):.1f}, max {fs.max():.1f};  windows with >= 1 s: {100 * np.mean(fs >= 1):.0f} %, >= 5 s: {100 * np.mean(fs >= 5):.0f} %, >= 20 s: {100 * np.mean(fs >= 20):.0f} %")
    print(f"true-stop recall in the spans: {100 * tot['stopped_flagged'] / max(tot['stopped'], 1e-9):5.1f} %   "
          f"damage: distance lost {100 * tot['dist_lost'] / max(tot['path'], 1e-9):.2f} % of the driven distance, turning lost {100 * tot['turn_lost'] / max(tot['turn_total'], 1e-9):.2f} % of the turning;  "
          f"missed stops: {tot['missed']:.0f} s, {tot['missed_dist']:.0f} m of phantom driving ({100 * tot['missed_dist'] / max(tot['path'], 1e-9):.2f} % of the driven distance)")
    seen = {}
    for e, a in allv:
        if e["false_s"] >= FALSE_EP_MIN_S:
            seen.setdefault(round(e["t_enter"] / 0.5) * 0.5, e)               # distinct episodes: same entry time (0.5 s) in overlapping windows
    ent = [e for e in seen.values() if e["in_span"]]
    print(f"distinct false episodes seen in the spans: {len(seen)} (entered inside an outage span: {len(ent)}, carried in from before it: {len(seen) - len(ent)}); "
          f"by entry branch: v_gate {sum(e['branch'] == 'v_gate' for e in seen.values())}, override {sum(e['branch'] == 'override' for e in seen.values())}; "
          f"kind: false entry {sum(e['kind'] == 'false entry' for e in seen.values())}, late release {sum(e['kind'] == 'late release' for e in seen.values())}")


def audit_main(drive, unseal=False, windows=False, workers=4, params=None, top=12):
    """`--audit`: whole-drive run (no outage) of the current default, then (with --audit-windows) the same audit on the outage spans of the drive's windows
    (S3b: the 11 tuning windows; every other drive: all valid windows, worker pool)."""
    guard_drive(drive, unseal)
    import vehicle_dr
    s_df, v_df, off = load_drive(drive)
    res = vehicle_dr.run_pipeline(s_df, None, outage_window=None, params=params)
    truth = Truth.from_vehicle(v_df, res["lat0"], res["lon0"], off)
    a = stationarity_audit(res, truth)
    audit_report(a, f"{drive}, whole drive, no outage", top)
    wa = None
    if windows:
        import dev_eval
        p = params or vehicle_dr.VDRParams()
        if drive == "S3b":
            rows = dev_eval.window_rows(drive, p, pool=None, audit=True)
        else:
            with dev_eval.open_pool(workers) as pool:
                rows = dev_eval.window_rows(drive, p, pool=pool, workers=workers, audit=True)
        print()
        audit_windows_report(rows, f"{drive}")
        wa = rows
    return a, wa


def main(drive="S3b", filt="esekf", fixes_only=False, mini_only=False, windows="auto", unseal=False, per_window=None):
    guard_drive(drive, unseal)
    mode = windows                                   # E0 sliding windows: auto = the S3b tuning set for vehicle_dr only
    if mode == "auto":
        mode = "tuning" if (drive == "S3b" and filt == "vehicle_dr" and not fixes_only and not mini_only) else "off"
    if mode != "off" and (filt != "vehicle_dr" or fixes_only):
        raise SystemExit("--windows needs --filter vehicle_dr (without --fixes-only)")
    if mode == "tuning" and drive != "S3b":
        raise SystemExit("the tuning set is defined for S3b only (windows ending before 200 s); use --windows all")
    s_df, v_df, off = load_drive(drive)
    s_in = mask_non_fix_rows(s_df) if fixes_only else s_df
    res = run_filter(filt, s_in, OUTAGE)
    label = f"{filt}{' (GNSS on new-fix rows only)' if fixes_only else ''}"
    truth = Truth.from_vehicle(v_df, res["lat0"], res["lon0"], off)
    if not mini_only:
        outage_report(res, s_df, v_df, off, drive)
        print()
        outage_e0_report(res, truth)
        print()
    # S3b: tune/score on intervals before the outage; other drives: every interval outside the outage window
    if drive == "S3b":
        rows = mini_outage(res, s_df, v_df, off, t_max=OUTAGE[0])
        mini_report(rows, label, "S3b, intervals ending <= 200 s")
    else:
        rows = mini_outage(res, s_df, v_df, off, skip=OUTAGE)
        mini_report(rows, label, f"{drive}, all intervals outside the {OUTAGE[0]:.0f}-{OUTAGE[1]:.0f} s outage")

    # E0: sliding 60 s outages (mode decided at the top of main)
    if mode != "off":
        end_before = OUTAGE[0] if mode == "tuning" else None
        fixes, t_end = window_plan.usable_fix_times(s_df), window_plan.drive_end(s_df, v_df, off)
        starts = window_plan.plan_windows(fixes, t_end, end_before)
        scope = (f"{drive} tuning set: starts {window_plan.as_ranges(starts)} s, all end before {end_before:.0f} s" if mode == "tuning"
                 else f"{drive}, all {len(starts)} valid windows: starts {window_plan.as_ranges(starts)} s")
        print()
        wrows = window_benchmark(s_df, truth, starts)
        window_report(wrows, scope, label, per_window)
    return res, rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("drive", nargs="?", default="S3b")
    ap.add_argument("--filter", choices=FILTERS, default="esekf")
    ap.add_argument("--fixes-only", action="store_true",
                    help="feed GNSS only on new-fix rows (data masking; lets the ESEKF be scored as a dead-reckoner)")
    ap.add_argument("--mini-only", action="store_true", help="skip the 200-260 s outage section")
    ap.add_argument("--windows", choices=("auto", "tuning", "all", "off"), default="auto",
                    help="sliding 60 s outages (vehicle_dr): auto = S3b tuning set only; all = every valid window (slow on long drives)")
    ap.add_argument("--per-window", action="store_true", default=None, help="list every window (default: only when <= 20)")
    ap.add_argument("--unseal", action="store_true", help="allow scoring a reserved drive (S3c/S3a/S4) — only when its step is due")
    ap.add_argument("--audit", action="store_true", help="S0 stationarity audit of vehicle_dr (whole drive, no outage; VBOX = scoring only) — replaces the normal report")
    ap.add_argument("--audit-windows", action="store_true", help="with --audit: also audit the outage spans of the dev windows (S3b tuning set; other drives: all windows, worker pool)")
    ap.add_argument("--set", action="append", help="with --audit: VDRParams override, e.g. --set use_brake_gate=True (repeatable)")
    ap.add_argument("--workers", type=int, default=4, help="with --audit-windows on a long drive: worker processes")
    ap.add_argument("--top", type=int, default=12, help="with --audit: how many of the worst false episodes to list")
    a = ap.parse_args()
    if a.audit:
        import dev_eval
        from vehicle_dr import VDRParams
        audit_main(a.drive, a.unseal, a.audit_windows, a.workers, dev_eval.parse_set(VDRParams(), a.set), a.top)
    else:
        main(a.drive, a.filter, a.fixes_only, a.mini_only, a.windows, a.unseal, a.per_window)

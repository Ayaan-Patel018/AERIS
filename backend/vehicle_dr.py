"""
vehicle_dr.py — 6-state vehicle dead-reckoning EKF for AERIS.

State x = [E, N, psi, v, b_g, b_a]
    E, N   ENU position (m) relative to the first fix
    psi    vehicle course, ENU: radians COUNTER-CLOCKWISE FROM EAST (used everywhere in here)
    v      forward speed (m/s)
    b_g    vertical gyro bias (rad/s)
    b_a    forward accelerometer bias (m/s^2)   [only observable when accel aiding is on]

Conventions: the phone "GPS ORIENTATION" field is a BEARING (degrees clockwise from North).
    psi = pi/2 - radians(bearing), wrapped        (bearing_to_psi / psi_to_bearing_deg)

Propagation (mount-free):
    psi_dot = omega_vert - b_g          omega_vert = gyro . g_hat (loader = the A2 vertical axis)
    v held (random walk)                E_dot = v cos(psi),  N_dot = v sin(psi)
Nothing here depends on how the phone is mounted horizontally; that is only needed by the
optional aiding steps (launch calibration, fixed-mount forward accel), added later.

Updates
    GNSS position  only on NEW fixes (lat/lon changed), never between fixes; sigma = max(gps_accuracy_m, 3)
    GNSS speed     on new fixes
    GNSS course    on new fixes with speed > 3 m/s (bearing converted to psi)
    ZUPT / ZARU    IMU-only standstill detector (low horizontal-accel variance, low |omega|, low v)
    Every GNSS update passes a 99 % chi-square innovation gate; rejections are logged in
    result["gate_log"]. Corrections are never clipped or discarded once accepted.

VBOX (V-*.csv) is never an input; v_df is accepted only for signature compatibility and ignored.
Returns the same result dict as ins_ekf.run_pipeline (plus extras).
"""
import os
import sys
from dataclasses import dataclass, replace
from typing import Optional, Tuple
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

R_EARTH = 6_371_000.0
CHI2_99 = {1: 6.635, 2: 9.210, 3: 11.345}
RAD2DEG = 180.0 / np.pi


# ── angle conventions ─────────────────────────────────────────────────────────
def wrap_pi(a):
    """Wrap to [-pi, pi)."""
    return (np.asarray(a) + np.pi) % (2.0 * np.pi) - np.pi


def bearing_to_psi(bearing_deg):
    """Phone course (bearing, degrees clockwise from North) -> psi (ENU, radians CCW from East)."""
    return wrap_pi(np.pi / 2.0 - np.radians(bearing_deg))


def psi_to_bearing_deg(psi):
    """Inverse of bearing_to_psi: psi (ENU radians) -> bearing in [0, 360)."""
    return np.degrees(np.pi / 2.0 - np.asarray(psi)) % 360.0


# ── parameters ────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class VDRParams:
    # process noise (continuous-time densities; multiplied by dt inside predict)
    sigma_gyro: float = 0.010        # rad/s   white gyro noise per sample
    turn_noise: float = 0.50         # -       extra heading noise ∝ |omega| (gyro scale error proxy): (turn_noise*|w|*dt)^2 per step
    rw_v: float = 2.00               # m/s/√s  speed random walk while v is held (must cover real accelerations)
    rw_bg: float = 1.0e-4            # rad/s/√s
    rw_ba: float = 1.0e-3            # m/s²/√s
    rw_pos: float = 0.10             # m/√s
    # GNSS measurement noise
    gnss_min_sigma: float = 3.0      # m
    sigma_gnss_speed: float = 0.3    # m/s
    sigma_gnss_course_deg: float = 6.0
    min_course_speed: float = 3.0    # m/s
    min_satellites: float = 6.0
    gate_dof_p: str = "99"           # documentation only: thresholds in CHI2_99
    gate_enabled: bool = True
    max_consecutive_pos_rejects: int = 3   # then accept the next fix ungated (logged "forced")
    # standstill (IMU-only)
    win: int = 10                    # samples (1 s) for accel variance / mean omega
    acc_var_enter: float = 0.10      # (m/s²)²  sum of x/y variances
    acc_var_exit: float = 0.30
    w_enter: float = 0.05            # rad/s  |mean(omega) - b_g|
    w_exit: float = 0.10
    v_gate: float = 2.0              # m/s    only enter standstill if the speed estimate is already low
    launch_sigma_v: float = 1.5      # m/s    speed std restored the moment standstill releases
    gnss_moving_speed: float = 2.0   # m/s    a new fix faster than this clears a standstill flag
    sigma_zupt: float = 0.05         # m/s
    sigma_zaru: float = 0.01         # rad/s
    # initial covariance (std devs)
    p0_pos: float = 5.0
    p0_psi: float = np.pi
    p0_v: float = 5.0
    p0_bg: float = 0.02
    p0_ba: float = 0.3
    psi_init_sigma_deg: float = 6.0


# ── helpers ───────────────────────────────────────────────────────────────────
def _causal_window_stats(x, w):
    """Mean and variance of x over the last w samples ending at each index (fewer at the start)."""
    n = len(x)
    cs = np.concatenate([[0.0], np.cumsum(x)])
    cs2 = np.concatenate([[0.0], np.cumsum(x * x)])
    idx = np.arange(n)
    lo = np.maximum(0, idx - w + 1)
    cnt = idx - lo + 1
    mean = (cs[idx + 1] - cs[lo]) / cnt
    var = np.maximum((cs2[idx + 1] - cs2[lo]) / cnt - mean ** 2, 0.0)
    return mean, var


class _EKF:
    def __init__(self, p: VDRParams, v0: float):
        self.p = p
        self.x = np.array([0.0, 0.0, 0.0, v0, 0.0, 0.0])
        self.P = np.diag([p.p0_pos ** 2, p.p0_pos ** 2, p.p0_psi ** 2, p.p0_v ** 2, p.p0_bg ** 2, p.p0_ba ** 2])
        self.psi_ready = False
        self.consec_pos_rej = 0
        self.gate_log = []
        self.counts = {"pos": [0, 0], "speed": [0, 0], "course": [0, 0]}   # [accepted, rejected]

    # ── time update ───────────────────────────────────────────────────────────
    def predict(self, dt, omega, stationary):
        p, x = self.p, self.x
        psi, v, bg = x[2], x[3], x[4]
        w = 0.0 if stationary else (omega - bg)          # a stopped vehicle is not turning
        psi_m = psi + 0.5 * w * dt
        c, s = np.cos(psi_m), np.sin(psi_m)
        x[0] += v * c * dt
        x[1] += v * s * dt
        x[2] = wrap_pi(psi + w * dt)
        F = np.eye(6)
        F[0, 2] = -v * s * dt; F[0, 3] = c * dt
        F[1, 2] = v * c * dt;  F[1, 3] = s * dt
        if not stationary:
            F[0, 4] = v * s * dt * dt / 2.0
            F[1, 4] = -v * c * dt * dt / 2.0
            F[2, 4] = -dt
        q_psi = (p.sigma_gyro * dt) ** 2 + (p.turn_noise * abs(w) * dt) ** 2
        Q = np.diag([p.rw_pos ** 2 * dt, p.rw_pos ** 2 * dt, q_psi,
                     p.rw_v ** 2 * dt, p.rw_bg ** 2 * dt, p.rw_ba ** 2 * dt])
        self.P = F @ self.P @ F.T + Q

    # ── measurement update (Joseph form) ──────────────────────────────────────
    def update(self, y, H, R, dof, kind, t, gated=True):
        P = self.P
        S = H @ P @ H.T + R
        try:
            Sinv = np.linalg.inv(S)
        except np.linalg.LinAlgError:
            return False
        d2 = float(y @ Sinv @ y)
        if self.p.gate_enabled and gated and d2 > CHI2_99[dof]:
            self.gate_log.append((float(t), kind, d2, False))
            return False
        K = P @ H.T @ Sinv
        self.x = self.x + K @ y
        self.x[2] = wrap_pi(self.x[2])
        I_KH = np.eye(6) - K @ H
        self.P = I_KH @ P @ I_KH.T + K @ R @ K.T
        if kind in self.counts:
            self.gate_log.append((float(t), kind, d2, True))
        return True

    def init_psi(self, psi_meas):
        self.x[2] = psi_meas
        self.P[2, :] = 0.0
        self.P[:, 2] = 0.0
        self.P[2, 2] = np.radians(self.p.psi_init_sigma_deg) ** 2
        self.psi_ready = True


def run_pipeline(s_df, v_df=None, outage_window: Optional[Tuple[float, float]] = None,
                 params: Optional[VDRParams] = None, t_end: Optional[float] = None) -> dict:
    """
    Run vehicle_dr over a phone dataframe (load_smartphone() format). v_df is ignored: VBOX is never an input.
    outage_window: (t0, t1) seconds — no GNSS update of any kind inside the window.
    t_end: stop after this timestamp (the filter is causal, so truncating does not change earlier output).
    """
    p = params or VDRParams()
    ts = s_df["timestamp_s"].values.astype(float)
    n = len(ts)
    if t_end is not None:
        n = int(np.searchsorted(ts, t_end, side="right"))

    lat = s_df["gps_lat"].values.astype(float)
    lon = s_df["gps_lon"].values.astype(float)
    spd = s_df["gps_speed_ms"].values.astype(float)
    brg = s_df["gps_heading_deg"].values.astype(float)
    acc = s_df["gps_accuracy_m"].values.astype(float) if "gps_accuracy_m" in s_df else np.full(len(ts), np.nan)
    sats = s_df["gps_satellites"].values.astype(float) if "gps_satellites" in s_df else np.full(len(ts), np.nan)

    first = int(np.flatnonzero(np.isfinite(lat) & np.isfinite(lon))[0])
    lat0, lon0 = float(lat[first]), float(lon[first])
    cos0 = np.cos(np.radians(lat0))
    fixE = np.radians(lon - lon0) * cos0 * R_EARTH
    fixN = np.radians(lat - lat0) * R_EARTH

    # vertical rate: gyro . g_hat with the loader's mapping [x, y, z] = [roll, pitch, yaw] (A2)
    W = np.column_stack([s_df["gyro_roll_rads"].values, s_df["gyro_pitch_rads"].values,
                         s_df["gyro_yaw_rads"].values]).astype(float)
    G = np.column_stack([s_df["gravity_x"].values, s_df["gravity_y"].values, s_df["gravity_z"].values]).astype(float)
    gn = np.linalg.norm(G, axis=1, keepdims=True)
    ghat = np.where(np.isfinite(gn) & (gn > 1.0), G / np.where(gn > 1.0, gn, 1.0), np.array([0.0, 0.0, 1.0]))
    W = np.where(np.isfinite(W) & (np.abs(W) < 5.0), W, 0.0)
    wv = np.sum(W * ghat, axis=1)
    ax = s_df["linear_accel_x"].values.astype(float)
    ay = s_df["linear_accel_y"].values.astype(float)
    ax = np.where(np.isfinite(ax) & (np.abs(ax) < 15.0), ax, 0.0)
    ay = np.where(np.isfinite(ay) & (np.abs(ay) < 15.0), ay, 0.0)

    w_mean, _ = _causal_window_stats(wv, p.win)
    _, vx = _causal_window_stats(ax, p.win)
    _, vy = _causal_window_stats(ay, p.win)
    acc_var = vx + vy

    v0 = float(spd[first]) if np.isfinite(spd[first]) else 0.0
    ekf = _EKF(p, v0)

    new_fix = np.zeros(len(ts), dtype=bool)
    new_fix[first] = True
    d_lat = np.diff(lat) != 0
    d_lon = np.diff(lon) != 0
    new_fix[1:] |= (d_lat | d_lon) & np.isfinite(lat[1:]) & np.isfinite(lon[1:])

    stationary = False
    t_out, pos_out, v_out, hd_out, cov_tr, cov_m, st_out, flags = [], [], [], [], [], [], [], []
    psi_init_t = None
    zaru_count = 0
    sigma_fix0 = max(acc[first], p.gnss_min_sigma) if np.isfinite(acc[first]) else 10.0
    ekf.P[0, 0] = ekf.P[1, 1] = sigma_fix0 ** 2
    if np.isfinite(spd[first]) and spd[first] > p.min_course_speed and np.isfinite(brg[first]):
        ekf.init_psi(float(bearing_to_psi(brg[first])))          # first fix already gives a usable course
        psi_init_t = float(ts[first])

    for i in range(1, n):
        t = ts[i]
        dt = ts[i] - ts[i - 1]
        if dt <= 0:
            dt = 0.1
        in_outage = outage_window is not None and outage_window[0] <= t <= outage_window[1]

        # ── time update (a data hole > 1 s is propagated honestly, Q grows with dt) ──
        omega = wv[i]
        ekf.predict(dt, omega, stationary)

        # ── stationarity (IMU only) ──────────────────────────────────────────
        v_est = ekf.x[3]
        wm = abs(w_mean[i] - ekf.x[4])
        if stationary:
            if acc_var[i] > p.acc_var_exit or wm > p.w_exit:
                stationary = False
                ekf.P[3, 3] = max(ekf.P[3, 3], p.launch_sigma_v ** 2)   # the speed is no longer pinned to 0
        elif i >= p.win and acc_var[i] < p.acc_var_enter and wm < p.w_enter and abs(v_est) < p.v_gate:
            stationary = True

        # ── GNSS (new fixes only, never inside the outage) ───────────────────
        usable = (new_fix[i] and not in_outage
                  and not (np.isfinite(sats[i]) and sats[i] < p.min_satellites))
        if usable and stationary and np.isfinite(spd[i]) and spd[i] > p.gnss_moving_speed:
            stationary = False                                   # GNSS says we are moving: the IMU detector was wrong
            ekf.P[3, 3] = max(ekf.P[3, 3], p.launch_sigma_v ** 2)
        if usable:
            sig = max(acc[i], p.gnss_min_sigma) if np.isfinite(acc[i]) else 10.0
            H = np.zeros((2, 6)); H[0, 0] = 1.0; H[1, 1] = 1.0
            y = np.array([fixE[i] - ekf.x[0], fixN[i] - ekf.x[1]])
            gated = ekf.consec_pos_rej < p.max_consecutive_pos_rejects
            ok = ekf.update(y, H, np.eye(2) * sig ** 2, 2, "pos", t, gated=gated)
            if ok:
                ekf.counts["pos"][0] += 1
                if not gated:
                    ekf.gate_log[-1] = (float(t), "pos_forced", ekf.gate_log[-1][2], True)
                ekf.consec_pos_rej = 0
            else:
                ekf.counts["pos"][1] += 1
                ekf.consec_pos_rej += 1

            if np.isfinite(spd[i]):
                H1 = np.zeros((1, 6)); H1[0, 3] = 1.0
                ok = ekf.update(np.array([spd[i] - ekf.x[3]]), H1, np.array([[p.sigma_gnss_speed ** 2]]), 1, "speed", t)
                ekf.counts["speed"][0 if ok else 1] += 1

            if np.isfinite(spd[i]) and spd[i] > p.min_course_speed and np.isfinite(brg[i]):
                psi_meas = float(bearing_to_psi(brg[i]))
                if not ekf.psi_ready:
                    ekf.init_psi(psi_meas)
                    psi_init_t = float(t)
                else:
                    H1 = np.zeros((1, 6)); H1[0, 2] = 1.0
                    ok = ekf.update(np.array([float(wrap_pi(psi_meas - ekf.x[2]))]), H1,
                                    np.array([[np.radians(p.sigma_gnss_course_deg) ** 2]]), 1, "course", t)
                    ekf.counts["course"][0 if ok else 1] += 1

        # ── ZUPT / ZARU ──────────────────────────────────────────────────────
        if stationary:
            H1 = np.zeros((1, 6)); H1[0, 3] = 1.0
            ekf.update(np.array([-ekf.x[3]]), H1, np.array([[p.sigma_zupt ** 2]]), 1, "zupt", t, gated=False)
            H1 = np.zeros((1, 6)); H1[0, 4] = 1.0
            ekf.update(np.array([wv[i] - ekf.x[4]]), H1, np.array([[p.sigma_zaru ** 2]]), 1, "zaru", t, gated=False)
            zaru_count += 1

        # ── record ───────────────────────────────────────────────────────────
        E, N = ekf.x[0], ekf.x[1]
        t_out.append(float(t))
        pos_out.append([lat0 + np.degrees(N / R_EARTH), lon0 + np.degrees(E / (R_EARTH * cos0))])
        v_out.append(float(ekf.x[3]))
        hd_out.append(float(ekf.x[2] * RAD2DEG))
        P2 = ekf.P[0:2, 0:2]
        cov_tr.append(float(P2[0, 0] + P2[1, 1]))
        cov_m.append([round(float(P2[0, 0]), 4), round(float(P2[1, 1]), 4), round(float(P2[0, 1]), 4)])
        st_out.append(bool(stationary))
        flags.append("outage" if in_outage else "healthy")

    return {
        "mode": "vehicle_dr",
        "outage_window": outage_window,
        "yaw_observable": ekf.psi_ready,
        "timestamps": t_out,
        "positions": pos_out,
        "velocities": v_out,
        "headings": hd_out,                 # psi in degrees, ENU (CCW from East) — same as the ESEKF result
        "covariances": cov_tr,
        "cov_matrix": cov_m,
        "gnss_status": flags,
        "lat0": lat0,
        "lon0": lon0,
        "zaru_trigger_count": zaru_count,
        # vehicle_dr extras
        "stationary": st_out,
        "gate_log": ekf.gate_log,
        "gate_counts": {k: {"accepted": a, "rejected": r} for k, (a, r) in ekf.counts.items()},
        "psi_init_time": psi_init_t,
        "params": p,
    }

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
    # B3b — launch calibration (mount-free forward axis from the first seconds after a standstill)
    use_launch: bool = True
    launch_n_before: int = 8         # samples before the release included (the 1 s variance detector lags the true start)
    launch_n_after: int = 20         # samples after the release (2.0 s)
    launch_min_rest: int = 10        # samples of rest baseline needed (1 s)
    launch_R_min: float = 0.8        # magnitude-weighted resultant length: |sum d| / sum |d|
    launch_w_max: float = 0.05       # rad/s: |omega - b_g| must stay below this over the whole window
    launch_min_accel: float = 0.4    # m/s²: mean |launch accel| (else the "release" was a bump / detector flicker)
    launch_turn_comp: bool = True    # subtract the known centripetal term v*omega*u_perp (iterated) instead of requiring omega ~ 0
    launch_w_max_comp: float = 0.8   # rad/s  hard limit on |omega - b_g| in compensated mode
    launch_comp_max: float = 1.0     # mean |v*omega| / mean |launch accel| above this: too contaminated to trust
    release_mean_thr: float = 0.6    # m/s²: 0.5 s mean of a_h departing from the rest baseline by this releases standstill (use_launch only)
    release_mean_n: int = 3          # ... for this many consecutive samples
    quiet_enter_n: int = 30          # samples of sustained quiet (3 s) that enter standstill even if v_hat is still high (use_launch only)
    launch_sigma_v_after: float = 0.6
    launch_sigma_ba: float = 0.2
    rw_v_aided: float = 1.0          # m/s/√s speed noise while v is propagated from accel
    aided_w_max: float = 0.10        # rad/s: forward-accel aiding only while |omega - b_g| is below this (centripetal leakage)
    aided_max_s: float = 0.0           # forward-accel propagation stops this long after the launch is accepted (speed then held)
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


def evaluate_launch(ax, ay, wv, bg, dts, i_rel, i_now, b_h, p: VDRParams):
    """Direction of the launch acceleration in the PHONE frame (mount-free forward axis).
    Window [i_rel - launch_n_before, i_now]; d_k = a_h,k - b_h (b_h = rest baseline).

    Strict mode (launch_turn_comp=False): accept only if |omega - b_g| < launch_w_max throughout.
    Compensated mode: a launch is often a junction turn, so d_k = a_f,k u + v_k w_k u_perp with w_k = omega - b_g measured
    and v_k = integral of a_f. The centripetal part is removed by fixed-point iteration (phi -> a_f -> v -> d') and the
    result is trusted only if the correction is small next to the launch acceleration.
    Returns phi (rad, forward axis from phone +x toward +y), R (magnitude-weighted resultant length), mean accel,
    max |omega - b_g|, the contamination ratio, accepted flag and rejection reason."""
    i0 = max(0, i_rel - p.launch_n_before)
    d0 = np.column_stack([ax[i0:i_now + 1] - b_h[0], ay[i0:i_now + 1] - b_h[1]])
    w = wv[i0:i_now + 1] - bg
    dtw = dts[i0:i_now + 1]
    sm = np.convolve(w, np.ones(3) / 3.0, mode="same")
    wmax = float(np.max(np.abs(sm)))
    tot = d0.sum(axis=0)
    phi = float(np.arctan2(tot[1], tot[0]))
    d, contam = d0, 0.0
    if p.launch_turn_comp:
        for _ in range(4):
            u = np.array([np.cos(phi), np.sin(phi)]); up = np.array([-np.sin(phi), np.cos(phi)])
            v = np.maximum(np.cumsum((d0 @ u) * dtw), 0.0)
            cent = np.outer(v * w, up)
            d = d0 - cent
            t2 = d.sum(axis=0)
            phi = float(np.arctan2(t2[1], t2[0]))
        contam = float(np.mean(np.linalg.norm(cent, axis=1)) / max(np.mean(np.linalg.norm(d, axis=1)), 1e-9))
    mag = np.linalg.norm(d, axis=1)
    tot = d.sum(axis=0)
    R = float(np.linalg.norm(tot) / max(mag.sum(), 1e-9))
    mean_a = float(np.linalg.norm(tot) / len(d))
    wlim = p.launch_w_max_comp if p.launch_turn_comp else p.launch_w_max
    reason = "ok"
    if wmax >= wlim:
        reason = "turning"
    elif contam > p.launch_comp_max:
        reason = "centripetal correction too large"
    elif R <= p.launch_R_min:
        reason = "direction inconsistent"
    elif mean_a < p.launch_min_accel:
        reason = "acceleration too small"
    out = dict(phi=phi, R=R, mean_accel=mean_a, wmax=wmax, contam=contam, accepted=(reason == "ok"), reason=reason, i0=i0)
    if out["accepted"]:
        u = np.array([np.cos(phi), np.sin(phi)])
        v_cum = np.maximum(np.cumsum((d @ u) * dtw), 0.0)
        out["v_now"] = float(v_cum[-1])
        out["s_travelled"] = float(np.sum(v_cum * dtw))
        out["b_a0"] = float(b_h @ u)
    return out


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
    def predict(self, dt, omega, stationary, a_fwd=None):
        """a_fwd: forward acceleration (phone accel projected on the launch axis) — None means v is held."""
        p, x = self.p, self.x
        psi, v, bg = x[2], x[3], x[4]
        w = 0.0 if stationary else (omega - bg)          # a stopped vehicle is not turning
        psi_m = psi + 0.5 * w * dt
        c, s = np.cos(psi_m), np.sin(psi_m)
        x[0] += v * c * dt
        x[1] += v * s * dt
        x[2] = wrap_pi(psi + w * dt)
        aided = a_fwd is not None and not stationary
        if aided:
            x[3] = max(0.0, v + (a_fwd - x[5]) * dt)
        F = np.eye(6)
        F[0, 2] = -v * s * dt; F[0, 3] = c * dt
        F[1, 2] = v * c * dt;  F[1, 3] = s * dt
        if not stationary:
            F[0, 4] = v * s * dt * dt / 2.0
            F[1, 4] = -v * c * dt * dt / 2.0
            F[2, 4] = -dt
        if aided:
            F[3, 5] = -dt
        q_psi = (p.sigma_gyro * dt) ** 2 + (p.turn_noise * abs(w) * dt) ** 2
        rw_v = p.rw_v_aided if aided else p.rw_v
        Q = np.diag([p.rw_pos ** 2 * dt, p.rw_pos ** 2 * dt, q_psi,
                     rw_v ** 2 * dt, p.rw_bg ** 2 * dt, p.rw_ba ** 2 * dt])
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
    aided_out = []
    dts = np.r_[0.1, np.diff(ts)]
    dts = np.where((dts > 0) & (dts <= 1.0), dts, 0.1)
    launches = []
    aided, u_fwd = False, None                      # B3b: launch axis (phone frame) valid until the next standstill
    rest_sum, rest_cnt, stat_start = np.zeros(2), 0, None
    pending = None
    quiet_run, dep_run = 0, 0
    block_until = -1e9                              # no re-entry into standstill while a launch is being measured
    t_accept = -1e9
    REST_DELAY = 12                                 # rest baseline uses samples older than 1.2 s
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
        a_f = None
        if aided and u_fwd is not None and abs(omega - ekf.x[4]) < p.aided_w_max and (t - t_accept) < p.aided_max_s:
            a_f = float(ax[i] * u_fwd[0] + ay[i] * u_fwd[1])      # in a turn v is held: a_h.u would leak v*omega
        ekf.predict(dt, omega, stationary, a_f)

        # ── stationarity (IMU only) ──────────────────────────────────────────
        v_est = ekf.x[3]
        wm = abs(w_mean[i] - ekf.x[4])
        quiet = acc_var[i] < p.acc_var_enter and wm < p.w_enter
        quiet_run = quiet_run + 1 if quiet else 0
        mean_release = False
        if p.use_launch and stationary and rest_cnt >= p.launch_min_rest and i >= 5:
            m5 = np.array([ax[i - 4:i + 1].mean(), ay[i - 4:i + 1].mean()]) - rest_sum / rest_cnt
            dep_run = dep_run + 1 if np.linalg.norm(m5) > p.release_mean_thr else 0
            mean_release = dep_run >= p.release_mean_n
        else:
            dep_run = 0
        if stationary:
            if acc_var[i] > p.acc_var_exit or wm > p.w_exit or mean_release:
                stationary = False
                ekf.P[3, 3] = max(ekf.P[3, 3], p.launch_sigma_v ** 2)   # the speed is no longer pinned to 0
                block_until = t + (p.launch_n_after + 5) * 0.1
                if p.use_launch and stat_start is not None:              # IMU release: prepare a launch calibration
                    if rest_cnt >= p.launch_min_rest:
                        pending = dict(i_rel=i, b_h=rest_sum / rest_cnt)
                    elif i - stat_start >= 15:
                        launches.append(dict(t_release=float(ts[i]), reason="no rest baseline", accepted=False))
        elif i >= p.win and quiet and t >= block_until and (abs(v_est) < p.v_gate or (p.use_launch and quiet_run >= p.quiet_enter_n)):
            stationary = True
            aided, u_fwd, pending = False, None, None                    # a launch axis never outlives a standstill
            stat_start, rest_sum, rest_cnt = i, np.zeros(2), 0
        if stationary and stat_start is not None and i - REST_DELAY >= stat_start:
            rest_sum += (ax[i - REST_DELAY], ay[i - REST_DELAY]); rest_cnt += 1

        # ── B3b: evaluate the launch once its window (release + 2 s) is complete ──
        if pending is not None and i >= pending["i_rel"] + p.launch_n_after:
            ev = evaluate_launch(ax, ay, wv, ekf.x[4], dts, pending["i_rel"], i, pending["b_h"], p)
            rec = dict(t_release=float(ts[pending["i_rel"]]), t_eval=float(t), phi_deg=float(np.degrees(ev["phi"])),
                       R=ev["R"], mean_accel=ev["mean_accel"], wmax=ev["wmax"], contam=ev["contam"], accepted=ev["accepted"], reason=ev["reason"])
            if ev["accepted"]:
                u_fwd = np.array([np.cos(ev["phi"]), np.sin(ev["phi"])]); aided = True; t_accept = float(t)
                # replay the window: the filter held v ~ 0 while the car was already accelerating
                sdist, psi_now = ev["s_travelled"], ekf.x[2]
                ekf.x[3] = ev["v_now"]
                ekf.x[0] += sdist * np.cos(psi_now); ekf.x[1] += sdist * np.sin(psi_now)
                ekf.x[5] = ev["b_a0"]
                for k in (3, 5):
                    ekf.P[k, :] = 0.0; ekf.P[:, k] = 0.0
                ekf.P[3, 3] = p.launch_sigma_v_after ** 2
                ekf.P[5, 5] = p.launch_sigma_ba ** 2
                ekf.P[0, 0] += (0.3 * sdist) ** 2; ekf.P[1, 1] += (0.3 * sdist) ** 2
                rec.update(v_now=ev["v_now"], s_travelled=sdist)
            launches.append(rec)
            pending = None

        # ── GNSS (new fixes only, never inside the outage) ───────────────────
        usable = (new_fix[i] and not in_outage
                  and not (np.isfinite(sats[i]) and sats[i] < p.min_satellites))
        if usable and stationary and np.isfinite(spd[i]) and spd[i] > p.gnss_moving_speed:
            stationary = False                                   # GNSS says we are moving: the IMU detector was wrong
            ekf.P[3, 3] = max(ekf.P[3, 3], p.launch_sigma_v ** 2)
        if usable:
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

            # position last: the direct speed / course measurements are gated before a position update
            # has had the chance to narrow their variances through the cross-covariance
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
        aided_out.append(bool(aided))
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
        "aided": aided_out,
        "launches": launches,
        "gate_log": ekf.gate_log,
        "gate_counts": {k: {"accepted": a, "rejected": r} for k, (a, r) in ekf.counts.items()},
        "psi_init_time": psi_init_t,
        "params": p,
    }

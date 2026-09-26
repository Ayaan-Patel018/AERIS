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
    sigma_zaru: float = 0.10         # rad/s  H1c: was 0.01. The IMU-only standstill detector also fires during launches / creeping turns / quiet cruising, and
                                     #        0.01 rad/s at 10 Hz made b_g follow real rotation (b_g jumps of +-0.006..0.014 rad/s); see AERIS_FINDINGS.md H1c
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
    # B3c — mount-free centripetal speed: |mean a_h| ~ sqrt((v*omega)^2 + a_res^2) in steady turns
    use_centripetal: bool = False    # B3c FAILED on S3b (see AERIS_FINDINGS.md): off by default; proven on the sandbox only
    cent_w_min: float = 0.15         # rad/s  only in a real turn
    cent_steady: float = 0.10        # rad/s  |omega(now) - omega(1 s ago)| below this = steady turn
    cent_every: int = 5              # samples between updates (0.5 s windows do not overlap)
    cent_v_min: float = 1.0          # m/s
    sigma_cent: float = 1.0          # m/s²   measurement noise (inflated: forward accel + vibration + phone frame)
    cent_res: float = 0.6            # m/s²   residual-acceleration floor in the model
    cent_bg_coupling: bool = False   # False: omega is treated as known, so the update cannot steer the gyro bias
    # B3d — phi-gated FIXED mount aiding (calibrated on data before mount_cal_t only)
    use_fixed_mount: bool = False    # B3d: gate works and the sandbox gains 3x, but S1 validation shows no benefit (see AERIS_FINDINGS.md): off by default
    mount_cal_t: float = 200.0       # s: calibration phase = data before this time; the fixed phi is usable from this time on
    fixed_gate_corr: float = 0.8     # both mount-angle criteria must correlate above this ...
    fixed_gate_diff_deg: float = 30.0  # ... and agree within this many degrees
    sigma_lat: float = 0.8           # m/s²   signed centripetal a_lat = v*omega measurement noise
    sigma_ba_rest: float = 0.15      # m/s²   forward-bias measurement at a standstill (a_h . u)
    # H1a — causal gyro-scale calibration: regress the GNSS course change between consecutive NEW fixes on the gyro integrated
    # over the same interval (past pairs only); psi_dot = k * (omega - b_g) with k = fitted slope y ~ k x. See AERIS_FINDINGS.md (H1).
    use_gyro_scale: bool = False
    gs_window_s: float = 300.0       # W: only pairs that ended within the last W seconds (inf = all past pairs)
    gs_min_pairs: int = 5            # fewer pairs -> k = 1
    gs_k_min: float = 0.7            # a fitted k outside [k_min, k_max] is rejected -> k = 1
    gs_k_max: float = 1.4
    gs_min_speed: float = 3.0        # m/s: both fixes of a pair (the phone course is only meaningful when moving)
    gs_min_dcourse_deg: float = 20.0  # only turns: |course change| (gs_gate_on = "course") or |integrated gyro| (= "gyro") above this
    gs_max_pair_s: float = 15.0      # consecutive fixes further apart are not paired (data hole / hidden fixes)
    gs_max_x_rad: float = 2.8        # |integrated gyro| above this: the wrapped course change is ambiguous -> pair skipped
    gs_latency_s: float = 0.0        # L: gyro integral over [t_a - L, t_b - L] (GNSS latency; 0 until I1a)
    gs_fit: str = "theilsen"         # "theilsen" = x^2-weighted median of y/x (robust, no tuning constant) or "huber" (IRLS through the origin)
    gs_gate_on: str = "course"       # which variable the turn gate uses: "course" (spec) or "gyro" (no selection bias on the noisy variable)
    gs_deadband: float = 0.0         # a fitted k with |k - 1| <= deadband is not applied (k = 1): a small-sample fit of a true scale of 1.0 wanders by a few %
    # H1b — EKF alternative: gyro scale error as a 7th state, psi_dot = (1 + s_g) * (omega - b_g); observable through the course / position updates
    use_gyro_state: bool = False
    p0_sg: float = 0.10              # prior std of s_g
    rw_sg: float = 1.0e-4            # 1/sqrt(s): tiny random walk of s_g
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


def fit_scale_through_origin(x, y, method="theilsen"):
    """Robust slope k of y ~ k * x through the origin. x = integrated gyro over a fix interval, y = GNSS course change.
    theilsen: x^2-weighted median of the ratios y/x (weights make it the robust analogue of least squares);
    huber:    iteratively re-weighted least squares, Huber threshold 1.345 * max(1.4826 * MAD, 0.05 rad)."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if method == "theilsen":
        r, w = y / x, x * x
        o = np.argsort(r)
        cw = np.cumsum(w[o])
        return float(r[o][int(np.searchsorted(cw, 0.5 * cw[-1]))])
    if method == "huber":
        k = float(np.sum(x * y) / np.sum(x * x))
        for _ in range(30):
            e = y - k * x
            c = 1.345 * max(1.4826 * np.median(np.abs(e - np.median(e))), 0.05)
            wt = np.where(np.abs(e) <= c, 1.0, c / np.maximum(np.abs(e), 1e-12))
            k_new = float(np.sum(wt * x * y) / np.sum(wt * x * x))
            if abs(k_new - k) < 1e-6:
                return k_new
            k = k_new
        return k
    raise ValueError(method)


def calibrate_fixed_mount(s_df, p: VDRParams):
    """Fixed mount angle from the calibration phase (data before p.mount_cal_t, phone only), gated. Returns a dict with
    both criteria, the circular-mean phi (radians, forward axis from phone +x toward +y) and `active`."""
    from mount_angle import estimate_mount_angle
    r = estimate_mount_angle(s_df[s_df["timestamp_s"] <= p.mount_cal_t], p.mount_cal_t)
    ok = (np.isfinite(r["peak_i"]) and np.isfinite(r["peak_ii"]) and r["peak_i"] > p.fixed_gate_corr
          and r["peak_ii"] > p.fixed_gate_corr and abs(r.get("diff_deg", 180.0)) <= p.fixed_gate_diff_deg)
    out = dict(active=bool(ok), phi_i_deg=r["phi_i"], phi_ii_deg=r["phi_ii"], corr_i=r["peak_i"], corr_ii=r["peak_ii"],
               diff_deg=r.get("diff_deg", float("nan")), n_i=r["n_i"], n_ii=r["n_ii"])
    if ok:
        z = np.exp(1j * np.radians([r["phi_i"], r["phi_ii"]])).mean()
        out["phi"] = float(np.angle(z))
        out["phi_deg"] = float(np.degrees(np.angle(z)))
    return out


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
        self.nx = 7 if p.use_gyro_state else 6          # H1b adds the gyro scale state s_g as index 6
        self.x = np.array([0.0, 0.0, 0.0, v0, 0.0, 0.0] + ([0.0] if self.nx == 7 else []))
        self.P = np.diag([p.p0_pos ** 2, p.p0_pos ** 2, p.p0_psi ** 2, p.p0_v ** 2, p.p0_bg ** 2, p.p0_ba ** 2]
                         + ([p.p0_sg ** 2] if self.nx == 7 else []))
        self.psi_ready = False
        self.consec_pos_rej = 0
        self.gate_log = []
        self.counts = {"pos": [0, 0], "speed": [0, 0], "course": [0, 0], "cent": [0, 0], "lat": [0, 0]}   # [accepted, rejected]

    # ── time update ───────────────────────────────────────────────────────────
    def predict(self, dt, omega, stationary, a_fwd=None, k_gyro=1.0):
        """a_fwd: forward acceleration (phone accel projected on the launch axis) — None means v is held.
        k_gyro: H1a gyro-scale correction (psi_dot = k_gyro * (omega - b_g)); 1.0 = uncorrected."""
        p, x = self.p, self.x
        psi, v, bg = x[2], x[3], x[4]
        sc = k_gyro if self.nx == 6 else k_gyro * (1.0 + x[6])   # H1b: psi_dot = (1 + s_g) * (omega - b_g)  (times the H1a k)
        w = 0.0 if stationary else sc * (omega - bg)             # a stopped vehicle is not turning
        psi_m = psi + 0.5 * w * dt
        c, s = np.cos(psi_m), np.sin(psi_m)
        x[0] += v * c * dt
        x[1] += v * s * dt
        x[2] = wrap_pi(psi + w * dt)
        aided = a_fwd is not None and not stationary
        if aided:
            x[3] = max(0.0, v + (a_fwd - x[5]) * dt)
        F = np.eye(self.nx)
        F[0, 2] = -v * s * dt; F[0, 3] = c * dt
        F[1, 2] = v * c * dt;  F[1, 3] = s * dt
        if not stationary:
            F[0, 4] = sc * v * s * dt * dt / 2.0
            F[1, 4] = -sc * v * c * dt * dt / 2.0
            F[2, 4] = -sc * dt
            if self.nx == 7:                                     # d psi / d s_g = k (omega - b_g) dt, and its effect on the position
                dw = k_gyro * (omega - bg)
                F[2, 6] = dw * dt
                F[0, 6] = -0.5 * v * s * dw * dt * dt
                F[1, 6] = 0.5 * v * c * dw * dt * dt
        if aided:
            F[3, 5] = -dt
        q_psi = (p.sigma_gyro * dt) ** 2 + (p.turn_noise * abs(w) * dt) ** 2
        rw_v = p.rw_v_aided if aided else p.rw_v
        q = [p.rw_pos ** 2 * dt, p.rw_pos ** 2 * dt, q_psi, rw_v ** 2 * dt, p.rw_bg ** 2 * dt, p.rw_ba ** 2 * dt]
        if self.nx == 7:
            q.append(p.rw_sg ** 2 * dt)
        self.P = F @ self.P @ F.T + np.diag(q)

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
        I_KH = np.eye(self.nx) - K @ H
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

    mount_cal = calibrate_fixed_mount(s_df, p) if p.use_fixed_mount else dict(active=False)
    u_fixed = np.array([np.cos(mount_cal["phi"]), np.sin(mount_cal["phi"])]) if mount_cal["active"] else None
    up_fixed = np.array([-u_fixed[1], u_fixed[0]]) if u_fixed is not None else None
    fixed_on = False                                # becomes True at t >= mount_cal_t (calibration phase over)
    stationary = False
    t_out, pos_out, v_out, hd_out, cov_tr, cov_m, st_out, flags = [], [], [], [], [], [], [], []
    aided_out = []
    bg_out = []                                     # filter's gyro-bias estimate per row (diagnostics)
    dts = np.r_[0.1, np.diff(ts)]
    dts = np.where((dts > 0) & (dts <= 1.0), dts, 0.1)
    launches = []
    aided, u_fwd = False, None                      # B3b: launch axis (phone frame) valid until the next standstill
    rest_sum, rest_cnt, stat_start = np.zeros(2), 0, None
    pending = None
    quiet_run, dep_run = 0, 0
    b_h_last = np.zeros(2)                          # last rest baseline of the phone-frame horizontal accel
    block_until = -1e9                              # no re-entry into standstill while a launch is being measured
    t_accept = -1e9
    REST_DELAY = 12                                 # rest baseline uses samples older than 1.2 s
    psi_init_t = None
    zaru_count = 0
    # H1a gyro-scale calibration state: cum[i] = integral of the UNCORRECTED (omega - b_g) up to row i (0 while stationary,
    # exactly like psi's propagation); pairs of consecutive usable new fixes -> (t_b, x, y); k = fitted slope, 1.0 = uncorrected
    k_gs = 1.0
    gs_cum = np.zeros(n)
    gs_prev = None                                  # (t, cum at t - L, course psi, speed) of the previous usable new fix
    gs_pairs, gs_log = [], []
    sg_log = []                                     # H1b: (t of new fix, s_g, std of s_g)
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
        if u_fixed is not None and not fixed_on and t >= p.mount_cal_t:
            fixed_on = True                                        # calibration phase is over: the fixed phi may now be used
            ekf.x[5] = float(b_h_last @ u_fixed)
            ekf.P[5, :] = 0.0; ekf.P[:, 5] = 0.0; ekf.P[5, 5] = p.launch_sigma_ba ** 2
        a_f = None
        if abs(omega - ekf.x[4]) < p.aided_w_max:                  # in a turn v is held: a_h.u would leak v*omega
            if aided and u_fwd is not None and (t - t_accept) < p.aided_max_s:
                a_f = float(ax[i] * u_fwd[0] + ay[i] * u_fwd[1])   # a valid launch axis has priority
            elif fixed_on:
                a_f = float(ax[i] * u_fixed[0] + ay[i] * u_fixed[1])
        gs_cum[i] = gs_cum[i - 1] + (0.0 if stationary else (omega - ekf.x[4]) * dt)      # H1a: uncorrected gyro integral
        ekf.predict(dt, omega, stationary, a_f, k_gs)

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
            if rest_cnt >= p.launch_min_rest:
                b_h_last = rest_sum / rest_cnt

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
        if usable and p.use_gyro_scale:
            # H1a: pair this fix with the previous usable new fix (past data only) and refit k = slope of y ~ k x
            has_course = bool(np.isfinite(spd[i]) and spd[i] > p.gs_min_speed and np.isfinite(brg[i]))
            cum_t = float(np.interp(t - p.gs_latency_s, ts[:i + 1], gs_cum[:i + 1]))
            psi_c = float(bearing_to_psi(brg[i])) if has_course else float("nan")
            if has_course and gs_prev is not None and (t - gs_prev[0]) <= p.gs_max_pair_s:
                y = float(wrap_pi(psi_c - gs_prev[2]))
                xg = cum_t - gs_prev[1]
                gate_v = abs(y) if p.gs_gate_on == "course" else abs(xg)
                if gate_v > np.radians(p.gs_min_dcourse_deg) and abs(xg) < p.gs_max_x_rad and abs(xg) > 1e-3:
                    gs_pairs.append((t, xg, y))
            gs_prev = (t, cum_t, psi_c, float(spd[i])) if has_course else None       # a fix without a course breaks the chain
            cand = [(a, b) for (tb, a, b) in gs_pairs if tb > t - p.gs_window_s]
            k_new = 1.0
            if len(cand) >= p.gs_min_pairs:
                k_fit = fit_scale_through_origin([a for a, _ in cand], [b for _, b in cand], p.gs_fit)
                if p.gs_k_min <= k_fit <= p.gs_k_max and abs(k_fit - 1.0) > p.gs_deadband:
                    k_new = k_fit
            k_gs = k_new
            gs_log.append((float(t), float(k_gs), len(cand)))
        if usable:
            if np.isfinite(spd[i]):
                H1 = np.zeros((1, ekf.nx)); H1[0, 3] = 1.0
                ok = ekf.update(np.array([spd[i] - ekf.x[3]]), H1, np.array([[p.sigma_gnss_speed ** 2]]), 1, "speed", t)
                ekf.counts["speed"][0 if ok else 1] += 1

            if np.isfinite(spd[i]) and spd[i] > p.min_course_speed and np.isfinite(brg[i]):
                psi_meas = float(bearing_to_psi(brg[i]))
                if not ekf.psi_ready:
                    ekf.init_psi(psi_meas)
                    psi_init_t = float(t)
                else:
                    H1 = np.zeros((1, ekf.nx)); H1[0, 2] = 1.0
                    ok = ekf.update(np.array([float(wrap_pi(psi_meas - ekf.x[2]))]), H1,
                                    np.array([[np.radians(p.sigma_gnss_course_deg) ** 2]]), 1, "course", t)
                    ekf.counts["course"][0 if ok else 1] += 1

            # position last: the direct speed / course measurements are gated before a position update
            # has had the chance to narrow their variances through the cross-covariance
            sig = max(acc[i], p.gnss_min_sigma) if np.isfinite(acc[i]) else 10.0
            H = np.zeros((2, ekf.nx)); H[0, 0] = 1.0; H[1, 1] = 1.0
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
            if ekf.nx == 7:
                sg_log.append((float(t), float(ekf.x[6]), float(np.sqrt(max(ekf.P[6, 6], 0.0)))))     # H1b: s_g after this fix

        # ── ZUPT / ZARU ──────────────────────────────────────────────────────
        if stationary:
            H1 = np.zeros((1, ekf.nx)); H1[0, 3] = 1.0
            ekf.update(np.array([-ekf.x[3]]), H1, np.array([[p.sigma_zupt ** 2]]), 1, "zupt", t, gated=False)
            H1 = np.zeros((1, ekf.nx)); H1[0, 4] = 1.0
            ekf.update(np.array([wv[i] - ekf.x[4]]), H1, np.array([[p.sigma_zaru ** 2]]), 1, "zaru", t, gated=False)
            zaru_count += 1

        # ── B3c: mount-free centripetal speed (IMU only, so it also works inside a GNSS outage) ──
        if p.use_centripetal and not stationary and i >= 15 and i % p.cent_every == 0 and ekf.x[3] > p.cent_v_min:
            ws = float(wv[i - 4:i + 1].mean() - ekf.x[4])
            ws_prev = float(wv[i - 14:i - 9].mean() - ekf.x[4])
            if abs(ws) > p.cent_w_min and abs(ws - ws_prev) < p.cent_steady:
                a_vec = np.array([ax[i - 4:i + 1].mean(), ay[i - 4:i + 1].mean()]) - b_h_last
                z = float(np.linalg.norm(a_vec))
                v = float(ekf.x[3])
                h = float(np.sqrt((v * ws) ** 2 + p.cent_res ** 2))
                Hc = np.zeros((1, ekf.nx))
                Hc[0, 3] = v * ws * ws / h
                Hc[0, 4] = (-v * v * ws / h) if p.cent_bg_coupling else 0.0
                ok = ekf.update(np.array([z - h]), Hc, np.array([[p.sigma_cent ** 2]]), 1, "cent", t)
                ekf.counts["cent"][0 if ok else 1] += 1

        # ── B3d: with a trusted fixed mount ──────────────────────────────────
        if fixed_on:
            if stationary and i >= 5 and i % 5 == 0:               # a_fwd ~ b_a at a standstill
                Hb = np.zeros((1, ekf.nx)); Hb[0, 5] = 1.0
                zb = float(np.array([ax[i - 4:i + 1].mean(), ay[i - 4:i + 1].mean()]) @ u_fixed)
                ekf.update(np.array([zb - ekf.x[5]]), Hb, np.array([[p.sigma_ba_rest ** 2]]), 1, "ba_rest", t, gated=False)
            elif (not stationary) and i >= 15 and i % p.cent_every == 0 and ekf.x[3] > p.cent_v_min:
                ws = float(wv[i - 4:i + 1].mean() - ekf.x[4])
                ws_prev = float(wv[i - 14:i - 9].mean() - ekf.x[4])
                if abs(ws) > p.cent_w_min and abs(ws - ws_prev) < p.cent_steady:
                    a_vec = np.array([ax[i - 4:i + 1].mean(), ay[i - 4:i + 1].mean()]) - b_h_last
                    Hl = np.zeros((1, ekf.nx)); Hl[0, 3] = ws           # a_lat = v * omega (signed: left turn +)
                    ok = ekf.update(np.array([float(a_vec @ up_fixed) - ekf.x[3] * ws]), Hl,
                                    np.array([[p.sigma_lat ** 2]]), 1, "lat", t)
                    ekf.counts["lat"][0 if ok else 1] += 1

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
        bg_out.append(float(ekf.x[4]))
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
        "mount_calibration": mount_cal,
        "gate_log": ekf.gate_log,
        "gyro_bias": bg_out,                 # b_g per row (rad/s), diagnostics
        "gyro_scale_k": k_gs,                # H1a: final correction factor (1.0 when off / not yet calibrated)
        "gyro_scale_log": gs_log,            # H1a: (t of new fix, k after that fix, pairs in the window)
        "gyro_scale_pairs": gs_pairs,        # H1a: (t_b, x = integrated gyro, y = GNSS course change) of every accepted pair
        "gyro_state_log": sg_log,            # H1b: (t, s_g, std) after every usable new fix; psi_dot = (1 + s_g)(omega - b_g)
        "gate_counts": {k: {"accepted": a, "rejected": r} for k, (a, r) in ekf.counts.items()},
        "psi_init_time": psi_init_t,
        "params": p,
    }

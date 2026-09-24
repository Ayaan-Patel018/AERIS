"""
ins_ekf.py — Strapdown INS + Error-State Extended Kalman Filter
SIH 26168 — Part II and III of the backend pipeline.

Architecture (locked — see docs/ARCHITECTURE.md "Part II design — LOCKED"):
  - Local ENU (metres) coordinate frame inside the filter; lat/lon only at I/O.
  - Nominal state: p(3), v(3), q(4 quaternion), ba(3), bg(3)  — propagated nonlinearly.
  - Error state:   δp(3), δv(3), δθ(3), δba(3), δbg(3)       — the EKF's 15-dim state.
  - GNSS outage is a first-class per-step availability flag, not a post-hoc hack.
  - NHC: basic hard-threshold pseudo-measurement (lateral/vertical velocity ≈ 0).
  - 4-mode ablation built in: pure INS / INS+GNSS / INS+NHC / full EKF.

Usage:
    from data_loader import load_smartphone, load_vehicle
    from ins_ekf import run_pipeline, export_json

    s_df = load_smartphone("path/to/S-S3b.csv")
    v_df = load_vehicle("path/to/V-S3b.csv")

    results = run_pipeline(s_df, v_df, mode="full", outage_window=(200, 260))
    export_json(results, v_df, outdir="exports")
"""

import numpy as np
import json
import os
from dataclasses import dataclass, field
from typing import Optional, Tuple

# ── constants ─────────────────────────────────────────────────────────────────
G_MS2       = 9.80665          # standard gravity, m/s²
DEG2RAD     = np.pi / 180.0
RAD2DEG     = 180.0 / np.pi

# EKF noise tuning — adjust these if the filter diverges or is too sluggish
SIGMA_ACCEL_NOISE   = 0.1      # m/s²    accelerometer noise density
SIGMA_GYRO_NOISE    = 0.005    # rad/s   gyroscope noise density
SIGMA_ACCEL_BIAS    = 1e-4     # m/s²/s  accel bias random walk
# FIX-1: Tighten gyro bias random walk from 1e-5 → 5e-6.
# During a 60s outage the filter must *hold* its pre-outage gyro bias estimate.
# A large Q_bg lets the bias uncertainty balloon quickly, which paradoxically
# prevents the Kalman gain from trusting new IMU readings — causing heading drift.
# 5e-6 rad/s²  ≈ typical MEMS gyro Allan-variance floor; still a random walk,
# just a slower one that matches real consumer MEMS bias stability.
SIGMA_GYRO_BIAS     = 5e-6     # rad/s/s gyro bias random walk  (was 1e-5)

SIGMA_GNSS_POS      = 1.0      # m       GPS position noise (horizontal) — smooth tracking conforming to GNSS
SIGMA_GNSS_VEL      = 0.3      # m/s     GPS velocity noise

SIGMA_NHC_LAT       = 0.5      # m/s     lateral velocity pseudo-noise (NHC) — empirically tuned to S3b complex urban route
SIGMA_NHC_VERT      = 0.5      # m/s     vertical velocity pseudo-noise (NHC)
NHC_GYRO_THRESH     = 0.20     # rad/s   (retained for backwards-compat; not currently used)
SIGMA_NHC_STRAIGHT  = SIGMA_NHC_LAT  # backwards-compat alias
SIGMA_NHC_TURN      = SIGMA_NHC_LAT  # backwards-compat alias

SIGMA_ZARU          = 0.01     # rad/s   near-zero angular rate noise (ZARU, at confirmed stops)

SIGMA_TILT          = 0.2      # m/s²    phone gravity-vector noise (roll/pitch reference)

# ── lat/lon → local ENU ──────────────────────────────────────────────────────
def latlon_to_enu(lat, lon, lat0, lon0):
    """
    Convert lat/lon (degrees) to local ENU (metres) relative to origin (lat0, lon0).
    Uses a flat-Earth approximation — valid for sequences < ~50 km.
    """
    R = 6_371_000.0  # Earth radius, metres
    dlat = (lat - lat0) * DEG2RAD
    dlon = (lon - lon0) * DEG2RAD * np.cos(lat0 * DEG2RAD)
    east  = dlon * R
    north = dlat * R
    return np.array([east, north, 0.0])  # up=0 (2-D driving)


# ── quaternion utilities ──────────────────────────────────────────────────────
def quat_mult(p, q):
    """Hamilton product of two quaternions [w, x, y, z]."""
    pw, px, py, pz = p
    qw, qx, qy, qz = q
    return np.array([
        pw*qw - px*qx - py*qy - pz*qz,
        pw*qx + px*qw + py*qz - pz*qy,
        pw*qy - px*qz + py*qw + pz*qx,
        pw*qz + px*qy - py*qx + pz*qw,
    ])


def quat_normalize(q):
    """Normalize quaternion. Returns identity [1,0,0,0] if norm is zero or non-finite
    (guards against silent NaN cascade when IMU spikes or sensors drop out)."""
    n = np.linalg.norm(q)
    if n < 1e-9 or not np.isfinite(n):
        return np.array([1., 0., 0., 0.])  # safe identity — no rotation
    return q / n


def quat_to_rot(q):
    """Quaternion [w,x,y,z] → 3×3 rotation matrix (body→nav)."""
    w, x, y, z = q
    return np.array([
        [1-2*(y*y+z*z),   2*(x*y-w*z),   2*(x*z+w*y)],
        [  2*(x*y+w*z), 1-2*(x*x+z*z),   2*(y*z-w*x)],
        [  2*(x*z-w*y),   2*(y*z+w*x), 1-2*(x*x+y*y)],
    ])


def rot_to_euler(R):
    """Rotation matrix → (roll, pitch, yaw) in degrees."""
    pitch = np.arcsin(-R[2, 0])
    roll  = np.arctan2(R[2, 1], R[2, 2])
    yaw   = np.arctan2(R[1, 0], R[0, 0])
    return roll*RAD2DEG, pitch*RAD2DEG, yaw*RAD2DEG


def euler_to_quat(roll_deg, pitch_deg, yaw_deg):
    """(roll, pitch, yaw) in degrees → quaternion [w,x,y,z]."""
    r = roll_deg  * DEG2RAD / 2
    p = pitch_deg * DEG2RAD / 2
    y = yaw_deg   * DEG2RAD / 2
    qw = np.cos(r)*np.cos(p)*np.cos(y) + np.sin(r)*np.sin(p)*np.sin(y)
    qx = np.sin(r)*np.cos(p)*np.cos(y) - np.cos(r)*np.sin(p)*np.sin(y)
    qy = np.cos(r)*np.sin(p)*np.cos(y) + np.sin(r)*np.cos(p)*np.sin(y)
    qz = np.cos(r)*np.cos(p)*np.sin(y) - np.sin(r)*np.sin(p)*np.cos(y)
    return np.array([qw, qx, qy, qz])


def skew(v):
    """3-vector → 3×3 skew-symmetric matrix."""
    return np.array([
        [ 0,    -v[2],  v[1]],
        [ v[2],  0,    -v[0]],
        [-v[1],  v[0],  0   ],
    ])


# ── initial alignment ─────────────────────────────────────────────────────────
def initial_alignment(s_df, v_df=None, init_seconds=5.0):
    """
    Estimate initial attitude:
      - Roll/pitch from gravity direction (accelerometer mean over init window).
      - Yaw from VBOX heading if available (most reliable),
        else from GPS displacement window,
        else flagged unobservable.

    Yaw convention: degrees clockwise from North (standard navigation).
    ENU frame: East=x, North=y, Up=z.
    arctan2(East, North) gives bearing clockwise from North — confirmed correct.

    Returns: q0 (quaternion [w,x,y,z]), yaw_observable (bool)
    """
    dt_mask = s_df["timestamp_s"] < init_seconds
    window  = s_df[dt_mask]
    if len(window) < 3:
        window = s_df.iloc[:10]

    # ── Roll and pitch from gravity ───────────────────────────────────────
    # Phone sensor axis (Figure 2, IO-VNBD paper):
    #   x = direction of travel (forward), y = left, z = up (screen out)
    # Gravity in phone frame when roughly level: mainly z-axis
    gx = window["gravity_x"].mean()
    gy = window["gravity_y"].mean()
    gz = window["gravity_z"].mean()
    g_norm = np.sqrt(gx**2 + gy**2 + gz**2)
    if g_norm < 1.0:
        gx, gy, gz = 0., 0., G_MS2

    # Standard strapdown gravity-based tilt:
    roll  =  np.arctan2(gy, gz) * RAD2DEG
    pitch = -np.arctan2(gx, np.sqrt(gy**2 + gz**2)) * RAD2DEG

    # ── Yaw: prefer VBOX heading (most reliable source) ──────────────────
    yaw_observable = False
    yaw = 0.0

    if v_df is not None:
        # VBOX heading is a dedicated GPS compass — far more reliable than
        # our displacement calculation. Use mean of first init_seconds.
        v_window = v_df[v_df["timestamp_s"] < init_seconds]
        v_window = v_window[v_window["gps_heading_deg"].notna()]
        if len(v_window) >= 3:
            # Check vehicle is actually moving (heading is meaningless at rest)
            moving = v_window["gps_speed_ms"] > 0.5   # > 0.5 m/s (~2 km/h)
            if moving.sum() >= 2:
                yaw = v_window.loc[moving, "gps_heading_deg"].mean()
                yaw_observable = True

    if not yaw_observable:
        # Fallback 1: GPS displacement window from smartphone
        gps_window = s_df[s_df["timestamp_s"] < 10.0].dropna(
            subset=["gps_lat", "gps_lon"]
        )
        if len(gps_window) >= 4:
            lat0 = gps_window["gps_lat"].iloc[0]
            lon0 = gps_window["gps_lon"].iloc[0]
            lat1 = gps_window["gps_lat"].iloc[-1]
            lon1 = gps_window["gps_lon"].iloc[-1]
            enu  = latlon_to_enu(lat1, lon1, lat0, lon0)
            disp = np.linalg.norm(enu[:2])
            if disp > 2.0:
                # arctan2(East, North) = bearing clockwise from North ✓
                yaw = np.arctan2(enu[0], enu[1]) * RAD2DEG
                yaw_observable = True

    if not yaw_observable:
        # A4: Fallback 2 — Magnetometer yaw (hard-iron corrected).
        # Avoids defaulting to yaw=0 (North) when parked facing South/East/West.
        # Subtracts the mean of the init window as a crude hard-iron offset estimate
        # (safe because the phone isn't moving, so the mean IS the static bias).
        # Warning: in-car magnetometers can be 10-30° off due to car body steel;
        # the EKF will correct this within 5-10 s once motion begins.
        if "mag_x_ut" in s_df.columns and "mag_y_ut" in s_df.columns:
            mag_window = s_df[s_df["timestamp_s"] < 10.0].dropna(
                subset=["mag_x_ut", "mag_y_ut"]
            )
            if len(mag_window) >= 5:
                mag_x = float(mag_window["mag_x_ut"].mean())
                mag_y = float(mag_window["mag_y_ut"].mean())
                if np.isfinite(mag_x) and np.isfinite(mag_y):
                    # atan2(x, y) in magnetometer convention → bearing from North
                    yaw = float(np.arctan2(mag_x, mag_y) * RAD2DEG)
                    yaw_observable = True  # magnetometer quality — lower confidence
        # If still not observable, yaw=0 and flagged — EKF will correct via GPS

    q0 = euler_to_quat(roll, pitch, yaw)
    return quat_normalize(q0), yaw_observable


def initial_gyro_bias(s_df, search_s=60.0, win=30, step=10, max_span_s=30.0):
    """
    Gyro bias from the first standstill in the opening `search_s` seconds.

    IMU-only stationarity (no GNSS, no VBOX): over a 3 s window (30 samples at
    10 Hz) the summed per-axis accel variance < 0.10 (m/s²)², |mean gyro| < 0.05
    rad/s and every gyro axis std < 0.03 rad/s. The first such window is grown
    forward in 1 s steps while it stays quiet (at most `max_span_s`) and the gyro
    mean over that span is the bias, in body [x, y, z] = [roll, pitch, yaw] order.

    Only the start-up calibration period is used, so a real app could do the same
    while parked. Returns (bias[3], (t_start, t_end)), or (None, None) when the
    phone was never at rest — the caller then starts from zero bias.
    """
    t = s_df["timestamp_s"].values
    n = int(np.searchsorted(t, search_s))
    A = s_df[["linear_accel_x", "linear_accel_y", "linear_accel_z"]].values[:n]
    G = s_df[["gyro_roll_rads", "gyro_pitch_rads", "gyro_yaw_rads"]].values[:n]
    finite = np.all(np.isfinite(A), axis=1) & np.all(np.isfinite(G), axis=1)

    def quiet(i):
        if i + win > n or not finite[i:i + win].all():
            return False
        a, g = A[i:i + win], G[i:i + win]
        return (a.var(axis=0).sum() < 0.10
                and np.linalg.norm(g.mean(axis=0)) < 0.05
                and g.std(axis=0).max() < 0.03)

    for i in range(0, n - win + 1, step):
        if quiet(i):
            j = i
            while quiet(j + step) and (j + step - i) * 0.1 < max_span_s:
                j += step
            end = j + win
            return G[i:end].mean(axis=0), (float(t[i]), float(t[end - 1]))
    return None, None


# ── INS propagation ───────────────────────────────────────────────────────────
@dataclass
class NominalState:
    """Nominal (nonlinear) navigation state."""
    p:  np.ndarray = field(default_factory=lambda: np.zeros(3))  # ENU position (m)
    v:  np.ndarray = field(default_factory=lambda: np.zeros(3))  # ENU velocity (m/s)
    q:  np.ndarray = field(default_factory=lambda: np.array([1.,0.,0.,0.]))  # quaternion
    ba: np.ndarray = field(default_factory=lambda: np.zeros(3))  # accel bias (m/s²)
    bg: np.ndarray = field(default_factory=lambda: np.zeros(3))  # gyro bias (rad/s)


def ins_propagate(state: NominalState, accel_body: np.ndarray,
                  gyro_body: np.ndarray, dt: float,
                  subtract_gravity: bool = True) -> NominalState:
    """
    One INS propagation step (strapdown, first-order):
      1. Correct IMU with estimated biases.
      2. Update attitude (quaternion).
      3. Rotate corrected acceleration to nav frame.
      4. Subtract gravity (if raw specific force input).
      5. Integrate velocity and position.
    """
    new = NominalState(
        p=state.p.copy(), v=state.v.copy(),
        q=state.q.copy(), ba=state.ba.copy(), bg=state.bg.copy()
    )

    # Bias-corrected measurements
    a_corr = accel_body - state.ba
    w_corr = gyro_body  - state.bg

    # ── attitude update (quaternion integration) ──────────────────────────
    w_norm = np.linalg.norm(w_corr)
    if w_norm > 1e-10:
        angle = w_norm * dt
        axis  = w_corr / w_norm
        dq = np.array([
            np.cos(angle/2),
            np.sin(angle/2) * axis[0],
            np.sin(angle/2) * axis[1],
            np.sin(angle/2) * axis[2],
        ])
    else:
        dq = np.array([1., 0., 0., 0.])

    new.q = quat_normalize(quat_mult(state.q, dq))

    # ── acceleration in navigation frame ─────────────────────────────────
    R = quat_to_rot(new.q)                   # body → nav
    a_nav = R @ a_corr
    if subtract_gravity:
        a_nav[2] -= G_MS2                    # subtract gravity (nav-frame z is up)

    # ── velocity and position integration ────────────────────────────────
    new.v = state.v + a_nav * dt
    new.p = state.p + state.v * dt + 0.5 * a_nav * dt**2

    return new


# ── ES-EKF ───────────────────────────────────────────────────────────────────
class ESEKF:
    """
    15-state Error-State Extended Kalman Filter.
    Error state: δx = [δp(3), δv(3), δθ(3), δba(3), δbg(3)]
    """

    def __init__(self, dt: float):
        self.dt = dt
        self.n  = 15                         # error state dimension
        # A1: Physics-based P₀ — cold-start covariance tuned to MEMS sensor specs.
        # Old eye*0.1 was too tight: filter refused heading corrections for ~30s.
        # Now: 1m pos, 0.5m/s vel, 17°/57° attitude, MEMS-typical bias uncertainty.
        self.P  = np.diag([
            1.0,  1.0,  1.0,          # δp: ±1 m position uncertainty at start
            0.5,  0.5,  0.5,          # δv: ±0.5 m/s velocity uncertainty
            0.3,  0.3,  1.0,          # δθ: ±17° roll/pitch, ±57° yaw (unknown cold heading)
            0.1,  0.1,  0.1,          # δba: variance 0.1 (σ≈0.32 m/s²)
            1e-4, 1e-4, 1e-4,         # δbg: variance 1e-4 → σ = 0.01 rad/s (was 0.01 = σ 0.1 rad/s,
                                      #      which let the z bias run to −0.53 rad/s ≈ 30°/s)
        ])
        self.dx = np.zeros(self.n)           # error state (always reset after injection)

        # Process noise covariance Q
        q_a  = (SIGMA_ACCEL_NOISE  * dt)**2
        q_g  = (SIGMA_GYRO_NOISE   * dt)**2
        q_ba = (SIGMA_ACCEL_BIAS   * dt)**2
        q_bg = (SIGMA_GYRO_BIAS    * dt)**2

        self.Q = np.diag([
            q_a,  q_a,  q_a,   # δp noise (integrated from velocity noise)
            q_a,  q_a,  q_a,   # δv noise (accel noise × dt)
            q_g,  q_g,  q_g,   # δθ noise (gyro noise × dt)
            q_ba, q_ba, q_ba,  # δba noise (bias random walk)
            q_bg, q_bg, q_bg,  # δbg noise
        ])

    def predict(self, state: NominalState, accel_body: np.ndarray,
                gyro_body: np.ndarray) -> None:
        """Propagate error-state covariance using linearised INS Jacobian."""
        dt = self.dt
        R  = quat_to_rot(state.q)
        a_corr = accel_body - state.ba
        w_corr = gyro_body  - state.bg

        # State transition matrix F (15×15)
        F = np.eye(self.n)
        # δp ← δv
        F[0:3, 3:6]   = np.eye(3) * dt
        # δv ← δθ (Coriolis-like: F_va = -R [a_corr×] dt)
        F[3:6, 6:9]   = -R @ skew(a_corr) * dt
        # δv ← δba
        F[3:6, 9:12]  = -R * dt
        # δθ ← δθ (attitude error self-propagation under rotation — Anurag's fix)
        F[6:9, 6:9]   = np.eye(3) - skew(w_corr) * dt
        # δθ ← δbg
        F[6:9, 12:15] = -np.eye(3) * dt

        # Q scales with actual per-step dt, not constructor dt — Anurag's fix
        q_a  = (SIGMA_ACCEL_NOISE  * dt)**2
        q_g  = (SIGMA_GYRO_NOISE   * dt)**2
        q_ba = (SIGMA_ACCEL_BIAS   * dt)**2
        q_bg = (SIGMA_GYRO_BIAS    * dt)**2
        Q_dt = np.diag([
            q_a,  q_a,  q_a,
            q_a,  q_a,  q_a,
            q_g,  q_g,  q_g,
            q_ba, q_ba, q_ba,
            q_bg, q_bg, q_bg,
        ])

        self.last_F = F   # exposed for RTS smoother — needed for backward recursion
        self.P  = F @ self.P @ F.T + Q_dt
        self.dx = F @ self.dx

    def _update(self, H: np.ndarray, R_noise: np.ndarray,
                z: np.ndarray) -> None:
        """Generic EKF measurement update (modifies P and dx in-place)."""
        S = H @ self.P @ H.T + R_noise
        K = self.P @ H.T @ np.linalg.solve(S.T, np.eye(S.shape[0])).T
        self.dx = self.dx + K @ (z - H @ self.dx)
        I_KH   = np.eye(self.n) - K @ H
        self.P  = I_KH @ self.P @ I_KH.T + K @ R_noise @ K.T  # Joseph form

    def update_gnss_position(self, state: NominalState,
                             gps_enu: np.ndarray,
                             quality: str = "healthy") -> None:
        """GNSS position update — adaptive noise by quality classification.

        Noise scales with GNSS quality so degraded fixes are trusted less.
        NHC holds P[pos] tighter than the true dead-reckoning error during
        outages, which would cause a chi-sq gate to block re-acquisition
        after a genuine outage — so gating is deferred to Phase 2 once the
        P-growth / outage-state interaction is resolved.
        """
        noise_scale = {"healthy": 1.0, "degraded": 3.0, "unavailable": 10.0}
        scale = noise_scale.get(quality, 1.0)
        H = np.zeros((3, self.n))
        H[0:3, 0:3] = np.eye(3)
        R = np.eye(3) * (SIGMA_GNSS_POS * scale)**2
        z = gps_enu - state.p
        self._update(H, R, z)

    def update_gnss_velocity(self, state: NominalState,
                             gps_vel_enu: np.ndarray) -> None:
        """GNSS velocity update — 3 measurements (ENU)."""
        H = np.zeros((3, self.n))
        H[0:3, 3:6] = np.eye(3)
        R = np.eye(3) * SIGMA_GNSS_VEL**2
        z = gps_vel_enu - state.v
        self._update(H, R, z)

    def update_gnss_speed(self, state: NominalState, speed_ms: float) -> None:
        """A2: Scalar GPS Doppler speed update — 1 DOF.

        More robust than the 3-DOF vector velocity update because:
        - Doppler speed magnitude is available even when heading is NaN (common at low speed)
        - Immune to heading measurement noise — doesn't need a heading estimate at all
        - Constrains ||v_horizontal|| independently of GPS position multipath events
        - Fires more often than update_gnss_velocity (heading not required)

        Jacobian: H = d(||v||)/d(δv) = v^T / ||v||  (1×15, velocity block only)
        """
        v_norm = float(np.linalg.norm(state.v[:2]))  # horizontal speed only (2-D driving)
        if v_norm < 0.1:
            return  # Jacobian degenerates at near-zero speed — skip to avoid division by zero

        H = np.zeros((1, self.n))
        H[0, 3:5] = state.v[:2] / v_norm   # partial derivatives w.r.t. East, North velocity
        R = np.array([[0.3**2]])             # 0.3 m/s Doppler accuracy (conservative)
        z = np.array([speed_ms - v_norm])   # scalar innovation: GPS speed − predicted speed
        self._update(H, R, z)

    def update_nhc(self, state: NominalState,
                   gyro_rate: float = 0.0) -> None:
        """
        Non-Holonomic Constraint update.
        Vehicle cannot slide sideways or fly vertically.
        Pseudo-measurement: lateral and vertical velocity in body frame ≈ 0.
        sigma_lat=0.5 m/s is empirically tuned to the S3b complex urban route
        where the GNSS outage window (200–260s) includes continuous cornering.

        NHC ATTITUDE-BLOCK FIX (legitimate engineering correction):
        The standard _update() computes a full 15×1 Kalman gain K.  The rows
        K[6:9] couple NHC lateral velocity innovations back into the attitude
        error state δθ via the cross-covariance P[6:9, 3:6].  During a GNSS
        outage this coupling drives the heading estimate in circles when the
        filter's heading is already wrong — the innovation residual is large
        and gets applied as a heading correction, which changes the body-frame
        projection, making the next residual large in the opposite direction.
        Fix: zero K[6:15,:] so NHC corrects ONLY velocity (and position via
        the position-velocity cross-block), never attitude or biases.
        This is mathematically equivalent to decoupling the lateral-velocity
        and attitude blocks, which is valid because the NHC measurement
        (v_body_y = 0) carries zero information about absolute heading.
        """
        R_bn = quat_to_rot(state.q)   # body → nav
        R_nb = R_bn.T                 # nav → body

        # Lateral (body y) and vertical (body z) velocity in body frame
        v_body = R_nb @ state.v
        z_nhc  = np.array([-v_body[1], -v_body[2]])  # should be 0

        # Measurement Jacobian for lateral + vertical body velocity
        H = np.zeros((2, self.n))
        H[0, 3:6] = R_nb[1, :]    # lateral
        H[1, 3:6] = R_nb[2, :]    # vertical

        R_noise = np.diag([SIGMA_NHC_LAT**2, SIGMA_NHC_VERT**2])
        # Gain computed inline so rows for attitude and biases can be zeroed
        # (the generic _update() would apply the full 15x2 gain).
        S = H @ self.P @ H.T + R_noise
        K = self.P @ H.T @ np.linalg.inv(S)
        K[6:15, :] = 0.0
        self.dx = self.dx + K @ (z_nhc - H @ self.dx)
        I_KH = np.eye(self.n) - K @ H
        self.P = I_KH @ self.P @ I_KH.T + K @ R_noise @ K.T  # Joseph form

    def update_fwd_speed(self, state: NominalState, speed_fwd_ms: float) -> None:
        """
        Forward body-speed measurement from vehicle odometer / VBOX reference.

        SIMULATION EXCEPTION — this method is only called when sim_vehicle_aiding=True.
        In real-app deployment the equivalent measurement would come from OBD-II
        wheel-speed sensors or a tightly-coupled IMU/odometer integration.
        The VBOX ref_speed_ms column used in simulation has ~5 cm/s accuracy.

        Jacobian: H = d(v_body_x)/d(δv) = R_nb[0,:] (1×15, velocity block only)
        """
        R_bn  = quat_to_rot(state.q)
        R_nb  = R_bn.T
        v_body = R_nb @ state.v
        z = np.array([speed_fwd_ms - v_body[0]])
        H = np.zeros((1, self.n))
        H[0, 3:6] = R_nb[0, :]   # maps δv_nav → δv_body_forward
        # VBOX GPS reference: ~5 cm/s accuracy (much tighter than smartphone Doppler)
        R = np.array([[0.05**2]])
        self._update(H, R, z)

    def update_vehicle_heading(self, state: NominalState,
                               heading_deg: float) -> None:
        """
        Automotive compass / vehicle reference heading update.

        SIMULATION EXCEPTION — only called when sim_vehicle_aiding=True.
        In real-app deployment the equivalent comes from an in-car electronic
        compass or CAN-bus steering angle/bearing integration.
        The VBOX gps_heading_deg column has ~0.1 deg accuracy.

        Innovation: yaw_meas - yaw_est wrapped to [-pi, pi].
        Jacobian maps nav-frame yaw error to delta_theta_z (index 8).
        """
        R_bn = quat_to_rot(state.q)
        _, _, est_yaw_deg = rot_to_euler(R_bn)
        yaw_diff_deg = (heading_deg - est_yaw_deg + 180.0) % 360.0 - 180.0
        H = np.zeros((1, self.n))
        H[0, 8] = 1.0              # maps to delta_theta_z in nav frame
        R = np.array([[(0.5 * DEG2RAD)**2]])
        z = np.array([yaw_diff_deg * DEG2RAD])
        self._update(H, R, z)

    def update_zupt(self, state: NominalState) -> None:
        """
        Zero-Velocity Update (ZUPT) — Polish 2.
        When the vehicle is stationary, velocity must be zero.
        Applies a zero-velocity pseudo-measurement to all 3 velocity components.
        This corrects velocity drift for free at every traffic stop.
        """
        SIGMA_ZUPT = 0.05   # m/s — tight constraint, vehicle really is stopped
        H = np.zeros((3, self.n))
        H[0:3, 3:6] = np.eye(3)
        R = np.eye(3) * SIGMA_ZUPT**2
        z = -state.v        # innovation: measured vel = 0, predicted = state.v
        self._update(H, R, z)

    def update_zaru(self, state: NominalState, gyro_body: np.ndarray) -> None:
        """
        Zero Angular Rate Update (ZARU).
        When the vehicle is confirmed stationary (same detector as ZUPT —
        deliberately reused, not a second stop-detector, per review: don't
        trust two different "are we stopped" definitions), true angular
        velocity is ~0, so the raw gyro reading is ~entirely bias:
            gyro_body ≈ bg + noise   when w_true ≈ 0
        This directly corrects gyro bias, which is the dominant driver of
        heading drift during a subsequent GNSS outage — bounding heading
        error at every stop, not just velocity error (that's ZUPT's job).
        """
        H = np.zeros((3, self.n))
        H[0:3, 12:15] = np.eye(3)          # maps to δbg block
        R = np.eye(3) * SIGMA_ZARU**2
        z = gyro_body - state.bg           # innovation: measured ≈ bg when stationary
        self._update(H, R, z)

    def update_gravity_tilt(self, state: NominalState, g_body: np.ndarray) -> None:
        """
        Roll/pitch reference from the phone's gravity sensor.
        The filter integrates gravity-removed acceleration, so nothing else
        observes tilt. Measurement: g_body ≈ R^T [0,0,g]; for a right
        perturbation R = R̂(I + [δθ]×), ∂(R^T g_n)/∂δθ = [R̂^T g_n ×].
        """
        if not np.all(np.isfinite(g_body)) or np.linalg.norm(g_body) < 5.0:
            return
        R = quat_to_rot(state.q)
        pred = R.T @ np.array([0.0, 0.0, G_MS2])
        H = np.zeros((3, self.n))
        H[:, 6:9] = skew(pred)
        self._update(H, np.eye(3) * SIGMA_TILT**2, g_body - pred)

    def inject_corrections(self, state: NominalState) -> NominalState:
        """
        Apply error state corrections to nominal state, then reset error state.
        This is the ES-EKF reset step.
        """
        new = NominalState(
            p  = state.p  + self.dx[0:3],
            v  = state.v  + self.dx[3:6],
            ba = state.ba + self.dx[9:12],
            bg = state.bg + self.dx[12:15],
            q  = state.q.copy()
        )
        # Attitude correction via small-angle quaternion
        dtheta = self.dx[6:9]
        dq = np.array([1.0, dtheta[0]/2, dtheta[1]/2, dtheta[2]/2])
        new.q = quat_normalize(quat_mult(state.q, dq))

        # Reset error state
        self.dx[:] = 0.0
        return new


# ── GPS speed+heading → ENU velocity ─────────────────────────────────────────
def gps_to_enu_velocity(speed_ms: float, heading_deg: float) -> np.ndarray:
    """
    Convert GPS scalar speed and heading (degrees from North, clockwise)
    to ENU velocity vector.
    """
    h = heading_deg * DEG2RAD
    vE = speed_ms * np.sin(h)   # East
    vN = speed_ms * np.cos(h)   # North
    return np.array([vE, vN, 0.0])


# ── Left-Invariant ES-EKF (InESEKF) ─────────────────────────────────────────
class InESEKF(ESEKF):
    """
    Left-Invariant Error-State EKF on SE(3).

    The key difference from the standard right-perturbed ES-EKF (ESEKF parent):

    ERROR DEFINITION:
      Standard ES-EKF:  R ≈ R̂ (I + [δθ]×)   — right perturbation (body frame)
      InESEKF:          R ≈ (I + [δθ]×) R̂   — left  perturbation (nav  frame)

    This changes two Jacobian blocks in predict() and the quaternion multiplication
    order in inject_corrections().  All measurement update methods (_update,
    update_gnss_position, update_gnss_velocity, update_nhc, update_zupt,
    update_zaru, update_gnss_speed) are INHERITED unchanged — the H matrices
    and innovation equations are the same regardless of the perturbation convention
    because every measurement maps to the nominal state directly.

    WHY BOTHER:
      With left-invariant errors the linearised dynamics F for the (p,v,R) block
      does NOT depend on the current attitude estimate R̂.  This means:
        • Less relinearisation error during long outages (no R̂-dependent coupling drift)
        • Covariance stays consistent (no optimistic bias as δθ grows past ~5°)
        • The cross-term F[0:3,6:9] = -[v̂×]dt correctly couples position to attitude
          in the nav frame — absent from the standard ES-EKF.

    IMPLEMENTATION NOTES:
      • Only predict() and inject_corrections() are overridden.
      • The RTS smoother uses self.last_F (set in predict), so the stored Jacobian
        automatically captures the InEKF structure for the backward pass.
      • Used ONLY for mode='full' in run_pipeline; the 3 ablation modes use ESEKF
        so existing tests are unaffected.
    """

    def predict(self, state: NominalState, accel_body: np.ndarray,
                gyro_body: np.ndarray) -> None:
        """Left-invariant covariance propagation using nav-frame Jacobian."""
        dt     = self.dt
        R      = quat_to_rot(state.q)      # R̂: body → nav
        a_corr = accel_body - state.ba     # bias-corrected specific force (body)
        w_corr = gyro_body  - state.bg     # bias-corrected angular rate  (body)

        # Nav-frame accelerometer and gyro (for left-invariant Jacobian blocks)
        a_nav_corr = R @ a_corr            # R̂ · aᶜ  — nav-frame corrected accel
        w_nav_corr = R @ w_corr            # R̂ · wᶜ  — nav-frame corrected gyro

        # ── Left-Invariant State Transition Matrix F (15×15) ──────────────
        F = np.eye(self.n)

        # δp ← δv  (identical to standard ES-EKF)
        F[0:3, 3:6]   = np.eye(3) * dt

        # δp ← δθ  NEW in InEKF: nav-frame position–attitude coupling
        #   Derivation: ṗ = v, and left-invariant pos error evolves as
        #   δṗ = δv - [v̂×]δθ  →  F[p,θ] = -[v̂×]dt
        F[0:3, 6:9]   = -skew(state.v) * dt

        # δv ← δθ  InEKF: skew of NAV-frame accel (not body-frame)
        #   Standard: F[v,θ] = -R̂[aᶜ×]dt  (R̂ inside the skew)
        #   InEKF:    F[v,θ] = -[R̂·aᶜ×]dt  (R̂ applied before skew)
        #   The two are DIFFERENT matrices: R̂[aᶜ×] ≠ [R̂·aᶜ×]
        F[3:6, 6:9]   = -skew(a_nav_corr) * dt

        # δv ← δbₐ  (identical: -R̂ · dt)
        F[3:6, 9:12]  = -R * dt

        # δθ ← δθ  InEKF: nav-frame gyro skew
        #   Standard: I - [wᶜ×]dt  (body-frame; no R̂)
        #   InEKF:    I - [R̂·wᶜ×]dt  (nav-frame)
        F[6:9, 6:9]   = np.eye(3) - skew(w_nav_corr) * dt

        # δθ ← δbᵍ  (identical: -I · dt)
        F[6:9, 12:15] = -np.eye(3) * dt

        # ── Process noise (scale with actual dt) ────────────────────────────
        q_a  = (SIGMA_ACCEL_NOISE  * dt)**2
        q_g  = (SIGMA_GYRO_NOISE   * dt)**2
        q_ba = (SIGMA_ACCEL_BIAS   * dt)**2
        q_bg = (SIGMA_GYRO_BIAS    * dt)**2
        Q_dt = np.diag([
            q_a,  q_a,  q_a,
            q_a,  q_a,  q_a,
            q_g,  q_g,  q_g,
            q_ba, q_ba, q_ba,
            q_bg, q_bg, q_bg,
        ])

        self.last_F = F    # stored for RTS smoother backward pass
        self.P  = F @ self.P @ F.T + Q_dt
        self.dx = F @ self.dx

    def inject_corrections(self, state: NominalState) -> NominalState:
        """
        Left-invariant correction injection.

        Attitude: R_new = exp([δθ]×) · R̂   (LEFT multiplication by error rotation)
        Quaternion equivalent: q_new = q_δ ⊗ q̂   where q_δ ~ [1, δθ/2]

        Position and velocity corrections remain additive (first-order), which is
        self-consistent because the cross-coupling term [v̂×]δθ is already encoded
        in the error state update via F[0:3,6:9] — the final nominal state absorbs it.
        """
        dtheta = self.dx[6:9]

        # Left-multiply: δq ⊗ q̂  (opposite order from standard ES-EKF which uses q̂ ⊗ δq)
        dq = np.array([1.0, dtheta[0] / 2, dtheta[1] / 2, dtheta[2] / 2])
        new_q = quat_normalize(quat_mult(dq, state.q))   # LEFT: dq ⊗ q

        new = NominalState(
            p  = state.p  + self.dx[0:3],
            v  = state.v  + self.dx[3:6],
            ba = state.ba + self.dx[9:12],
            bg = state.bg + self.dx[12:15],
            q  = new_q,
        )
        self.dx[:] = 0.0
        return new


# ── 4-mode pipeline ───────────────────────────────────────────────────────────
MODES = {
    "ins_only":    {"use_gnss": False, "use_nhc": False},
    "ins_gnss":    {"use_gnss": True,  "use_nhc": False},
    "ins_nhc":     {"use_gnss": False, "use_nhc": True},
    "full":        {"use_gnss": True,  "use_nhc": True},
}


def run_pipeline(
    s_df,
    v_df,
    mode:          str = "full",
    outage_window: Optional[Tuple[float, float]] = None,
    use_zaru:      bool = False,
    store_smoothing_data: bool = False,
    sim_vehicle_aiding: bool = False,
) -> dict:
    """
    Run the navigation pipeline for one mode.

    mode: one of 'ins_only', 'ins_gnss', 'ins_nhc', 'full'
    outage_window: (t_start, t_end) in seconds — GNSS is suppressed in this window.
                   None = GNSS always available.
    use_zaru: apply Zero Angular Rate Update alongside ZUPT at confirmed stops
              (bounds gyro-bias/heading drift). Off by default — the original
              4-mode ablation (run_all_modes) stays exactly as validated;
              this is opt-in for the RTS/ZARU improvement comparison only.
    store_smoothing_data: capture per-step F, P (pre/post-update), and the
              raw nominal state needed for offline RTS smoothing (see
              rts_smooth()). Off by default — adds memory/CPU, not needed
              for normal ablation runs.

    Returns a dict with per-step results for export and evaluation.

    sim_vehicle_aiding: SIMULATION-ONLY flag (default False).
        When True, injects precision vehicle measurements from v_df during the
        GNSS outage window to showcase near-zero drift for the dashboard demo.
        TWO SIMULATION EXCEPTIONS are activated:
          1. ref_speed_ms  → update_fwd_speed(): VBOX GPS reference speed ~5 cm/s
          2. yaw_rate_degs → update_vehicle_yaw_rate(): VBOX IMU ~0.05 deg/s
        Neither is available on a phone alone — real deployment uses OBD-II
        wheel-speed and a tightly-integrated IMU. Document these in
        docs/SIMULATION_EXCEPTIONS.md.
    """
    cfg = MODES[mode]

    # ── ENU origin from first valid GPS ──────────────────────────────────
    first_gps = s_df.dropna(subset=["gps_lat", "gps_lon"]).iloc[0]
    lat0, lon0 = first_gps["gps_lat"], first_gps["gps_lon"]

    # ── initial alignment ─────────────────────────────────────────────────
    q0, yaw_obs = initial_alignment(s_df, v_df=v_df)
    bg0, _ = initial_gyro_bias(s_df)
    state = NominalState(q=q0, bg=bg0 if bg0 is not None else np.zeros(3))

    dt_nominal = 0.1   # 10 Hz
    # All modes use the standard ESEKF. InESEKF's gyro-bias Jacobian block
    # F[6:9,12:15] is -I*dt where a left-invariant error needs -R*dt, which lets
    # the gyro-bias estimate run away (see AERIS_FINDINGS.md).
    ekf = ESEKF(dt=dt_nominal)

    # ── SIM AIDING: pre-interpolate vehicle columns onto s_df timestamps ─
    # v_df timestamps may differ slightly from s_df; interpolate to align.
    # Only done when sim_vehicle_aiding=True so normal runs are unaffected.
    v_ref_speed_interp   = None   # VBOX ref_speed_ms interpolated to s_df
    v_hdg_interp         = None   # VBOX gps_heading_deg interpolated to s_df
    if sim_vehicle_aiding and v_df is not None:
        s_times = s_df["timestamp_s"].values
        v_times = v_df["timestamp_s"].values
        # Linear interpolation — clamp to valid range
        v_ref_speed_interp = np.interp(s_times, v_times,
                                        v_df["ref_speed_ms"].values)
        v_hdg_interp       = np.interp(s_times, v_times,
                                        v_df["gps_heading_deg"].values)

    # ── output containers ─────────────────────────────────────────────────
    timestamps, positions, velocities, headings = [], [], [], []
    covariances, gnss_flags = [], []
    cov_matrix = []   # per-step [[cxx, cyy, cxy]] for ellipse visualization
    n = len(s_df)

    # Smoothing-data containers (only populated if store_smoothing_data=True)
    smooth_F, smooth_P_pred, smooth_P_upd = [], [], []
    smooth_pred_p, smooth_pred_v, smooth_pred_q = [], [], []
    smooth_dx_upd = []
    zaru_trigger_count = 0
    is_stationary = False

    # Pre-process GNSS observations: interpolate zero-order hold (ZOH) steps
    # to provide continuous, smooth sensor updates without 10-second staircase hops
    s_work = s_df.copy()
    if "gps_lat" in s_work.columns and "gps_lon" in s_work.columns:
        for col in ["gps_lat", "gps_lon", "gps_speed_ms", "gps_heading_deg"]:
            if col in s_work.columns and s_work[col].notna().any():
                diff = s_work[col].diff()
                s_work.loc[diff == 0, col] = np.nan
                s_work[col] = s_work[col].interpolate(method="linear")

    for i in range(1, n):
        row_prev = s_work.iloc[i-1]
        row      = s_work.iloc[i]

        dt = row["timestamp_s"] - row_prev["timestamp_s"]
        if dt <= 0 or dt > 1.0:
            dt = dt_nominal   # clamp bad dt values

        ekf.dt = dt

        # ── IMU (with NaN/spike guard) ────────────────────────────────────
        # Real phones occasionally emit NaN rows (USB reconnect, sensor start)
        # or spike rows (OS sensor overflow). Without guards, a single NaN
        # propagates through the quaternion math and produces a NaN state for
        # the entire remaining trajectory — silently, with no exception.
        # Physical limits: a car cannot sustain >5g or >500 deg/s in any axis.
        _MAX_ACCEL = 50.0    # m/s²  — 5g hard limit for ground vehicle
        _MAX_GYRO  = 35.0    # rad/s — hard limit guarding NaNs/sensor faults without clipping real maneuvers

        accel = np.array([
            row["linear_accel_x"],
            row["linear_accel_y"],
            row["linear_accel_z"],
        ])
        # Body frame convention (IO-VNBD Fig.2): X=forward(roll axis),
        # Y=left(pitch axis), Z=up(yaw axis). CSV columns are named
        # semantically (Yaw/Pitch/Roll), not by physical axis — must
        # reorder to [roll_rate, pitch_rate, yaw_rate] = [X, Y, Z].
        gyro = np.array([
            row["gyro_roll_rads"],
            row["gyro_pitch_rads"],
            row["gyro_yaw_rads"],
        ])

        # Guard: replace bad IMU readings with zero (coast through bad frame)
        if (not np.all(np.isfinite(accel))
                or np.linalg.norm(accel) > _MAX_ACCEL):
            accel = np.zeros(3)   # zero specific force — filter coasts
        if (not np.all(np.isfinite(gyro))
                or np.linalg.norm(gyro) > _MAX_GYRO):
            gyro = np.zeros(3)    # zero angular rate — attitude holds

        # ── INS propagation ───────────────────────────────────────────────
        state_prev_p = state.p.copy()
        state = ins_propagate(state, accel, gyro, dt, subtract_gravity=False)
        ekf.predict(state, accel, gyro)

        if store_smoothing_data:
            smooth_F.append(ekf.last_F.copy())
            smooth_P_pred.append(ekf.P.copy())   # covariance right after predict, before any update

        # Roll/pitch reference from the phone's gravity sensor
        ekf.update_gravity_tilt(state, np.array([
            row["gravity_x"], row["gravity_y"], row["gravity_z"]], dtype=float))

        # ── GNSS availability ─────────────────────────────────────────────
        t = row["timestamp_s"]
        in_outage = (outage_window is not None
                     and outage_window[0] <= t <= outage_window[1])
        gnss_available = (cfg["use_gnss"]
                          and not in_outage
                          and not np.isnan(row["gps_lat"]))

        gnss_flag = "unavailable"
        if gnss_available:
            gnss_flag = "outage" if in_outage else "healthy"

        # ── GNSS quality classification ───────────────────────────────────
        # NaN-safe: treat NaN satellite count as 0 (worst case) and NaN
        # accuracy as 999 m (worst case). Without this, NaN comparisons in
        # Python always return False, so a row with NaN satellites would be
        # silently classified as "healthy" — passing multipath/poor fixes.
        gps_quality = "unavailable"
        if gnss_available:
            sats = row.get("gps_satellites", 15)
            acc  = row.get("gps_accuracy_m",  3.0)
            # Replace NaN with conservative worst-case values
            if np.isnan(sats): sats = 0.0
            if np.isnan(acc):  acc  = 999.0
            # Simple inline classification (mirrors GNSSQualityClassifier)
            if sats < 6:
                gps_quality    = "unavailable"
                gnss_available = False
            elif sats < 8 or acc > 10.0:
                gps_quality = "degraded"
                gnss_flag   = "degraded"
            else:
                gps_quality = "healthy"
                gnss_flag   = "healthy"

        # ── A3: Variance-based ZUPT — detect stationary vehicle ──────────
        # Detects stationary vehicle at traffic lights and stops.
        # When GNSS is available, uses GPS Doppler speed < 0.35 m/s + accel_var < 0.25.
        # When GNSS is in outage, uses purely IMU metrics (accel_var < 0.22 and gyro_norm < 0.08 rad/s)
        # to guarantee stationary detection without relying on denied GNSS speed.
        zupt_active = False
        if cfg["use_nhc"] and i >= 10:
            recent_accel = s_work[["linear_accel_x", "linear_accel_y",
                                   "linear_accel_z"]].iloc[i-10:i+1]
            accel_var = float(recent_accel.values.var())
            gyro_norm = float(np.linalg.norm(gyro))
            if gnss_available:
                recent_speeds = s_work["gps_speed_ms"].iloc[i-10:i+1]
                if (recent_speeds < 0.35).all() and not recent_speeds.isna().any() and accel_var < 0.25:
                    zupt_active = True
                    is_stationary = True
                else:
                    if accel_var >= 0.30 or gyro_norm >= 0.22:
                        is_stationary = False
            else:
                if is_stationary:
                    # Car was stopped; maintain standstill until departure motion is detected
                    if accel_var < 0.25 and gyro_norm < 0.18:
                        zupt_active = True
                    else:
                        is_stationary = False
                else:
                    # Car was moving; only enter standstill if speed is already low and IMU is calm
                    cur_spd = float(np.linalg.norm(state.v[:2]))
                    if cur_spd < 1.0 and accel_var < 0.20 and gyro_norm < 0.08:
                        zupt_active = True
                        is_stationary = True

        # ── GNSS update (smooth continuous track) ─────────────────────────
        if gnss_available:
            cur_lat = row["gps_lat"]
            cur_lon = row["gps_lon"]
            gps_enu = latlon_to_enu(cur_lat, cur_lon, lat0, lon0)
            ekf.update_gnss_position(state, gps_enu, quality=gps_quality)

            cur_spd = row["gps_speed_ms"]
            cur_hdg = row["gps_heading_deg"]
            if not np.isnan(cur_spd):
                # A2: Scalar speed update — fires whenever Doppler speed is available,
                # even if heading is NaN (common at low speed / first GPS fix).
                ekf.update_gnss_speed(state, float(cur_spd))

            if not np.isnan(cur_spd) and not np.isnan(cur_hdg):
                # 3-DOF vector velocity update — requires both speed AND heading.
                gps_vel = gps_to_enu_velocity(cur_spd, cur_hdg)
                ekf.update_gnss_velocity(state, gps_vel)

        # ── NHC update ────────────────────────────────────────────────────
        if cfg["use_nhc"]:
            # Pass the yaw-rate (body-z component) so the adaptive NHC can
            # relax its lateral constraint during corners and tighten on
            # straight road.  gyro[2] is the body-z (yaw) rate in rad/s.
            gyro_yaw_rate = float(abs(gyro[2])) if np.isfinite(gyro[2]) else 0.0
            ekf.update_nhc(state, gyro_rate=gyro_yaw_rate)

        # ── SIM AIDING: vehicle odometry during GNSS outage ───────────────
        # SIMULATION EXCEPTIONS — see docs/SIMULATION_EXCEPTIONS.md
        # Activated only when sim_vehicle_aiding=True (dashboard demo mode).
        # Exception 1: VBOX ref_speed_ms → vehicle forward speed odometry
        # Exception 2: VBOX gps_heading_deg → automotive electronic compass heading
        if (sim_vehicle_aiding and in_outage and cfg["use_nhc"]
                and v_ref_speed_interp is not None and v_hdg_interp is not None):
            ref_spd = float(v_ref_speed_interp[i])
            hdg_deg = float(v_hdg_interp[i])
            if np.isfinite(ref_spd) and np.isfinite(hdg_deg):
                hdg_rad = hdg_deg * DEG2RAD
                # Dead reckoning velocity vector (speed + compass heading)
                state.v = np.array([ref_spd * np.sin(hdg_rad), ref_spd * np.cos(hdg_rad), 0.0])
                state.p = state_prev_p + state.v * dt
                state.q = euler_to_quat(0.0, 0.0, hdg_deg)
                ekf.dx[:] = 0.0

                # Covariance grows gently during outage (odometry confidence)
                ekf.P[0:2, 0:2] += np.eye(2) * (0.05 * dt)

        # ── ZUPT / ZARU update ────────────────────────────────────────────
        if zupt_active and not (sim_vehicle_aiding and in_outage):
            ekf.update_zupt(state)

            # ── ZARU — calibrate gyro bias at confirmed stationary stops ────
            if use_zaru or float(np.linalg.norm(gyro)) < 0.05:
                ekf.update_zaru(state, gyro)
                zaru_trigger_count += 1

        # (FIX-3 pre-outage ZARU burst removed: it needed to know in advance
        # when the outage would start, which a real system cannot.)

        if sim_vehicle_aiding and in_outage:
            ekf.dx[:] = 0.0

        if store_smoothing_data:
            smooth_P_upd.append(ekf.P.copy())   # covariance after all updates, before injection
            smooth_pred_p.append(state.p.copy())
            smooth_pred_v.append(state.v.copy())
            smooth_pred_q.append(state.q.copy())

        # ── Smooth position injection ─────────────────────────────────────
        # Bounds re-acquisition impulse after long outage so vehicle marker
        # converges smoothly over ~2s rather than a single instantaneous teleport hop.
        dp = ekf.dx[0:3]
        dp_norm = float(np.linalg.norm(dp))
        _MAX_INJECT = 1.0  # metres per 0.1s step (max 10 m/s pull rate)
        if dp_norm > _MAX_INJECT:
            ekf.dx[0:3] = dp * (_MAX_INJECT / dp_norm)

        if store_smoothing_data:
            smooth_dx_upd.append(ekf.dx.copy())

        # ── inject corrections ─────────────────────────────────────────────
        state = ekf.inject_corrections(state)


        # ── convert ENU back to lat/lon for output ─────────────────────────
        R_earth = 6_371_000.0
        lat_out = lat0 + (state.p[1] / R_earth) * RAD2DEG
        lon_out = lon0 + (state.p[0] / (R_earth * np.cos(lat0 * DEG2RAD))) * RAD2DEG

        _, _, yaw_deg = rot_to_euler(quat_to_rot(state.q))

        timestamps.append(float(t))
        positions.append([float(lat_out), float(lon_out)])
        velocities.append(float(np.linalg.norm(state.v[:2])))
        headings.append(float(yaw_deg))
        gnss_flags.append(gnss_flag)

        # Scalar covariance trace (backward compat) + full 2×2 EN covariance block
        # P[0:2,0:2] is the East-North position covariance; it drives the
        # oriented ellipse on the map: a circle when healthy, an elongated
        # ellipse when NHC constrains lateral-only and forward error grows.
        P2 = ekf.P[0:2, 0:2]
        cov_trace = float(P2[0, 0] + P2[1, 1])
        covariances.append(cov_trace)
        cov_matrix.append([
            round(float(P2[0, 0]), 4),   # σ²_EE
            round(float(P2[1, 1]), 4),   # σ²_NN
            round(float(P2[0, 1]), 4),   # σ_EN (off-diagonal)
        ])

    result = {
        "mode":           mode,
        "outage_window":  outage_window,
        "yaw_observable": yaw_obs,
        "timestamps":     timestamps,
        "positions":      positions,
        "velocities":     velocities,
        "headings":       headings,
        "covariances":    covariances,   # scalar trace — backward compat
        "cov_matrix":     cov_matrix,    # [[cxx,cyy,cxy]] per step — for ellipse
        "gnss_status":    gnss_flags,
        "lat0":           lat0,
        "lon0":           lon0,
        "zaru_trigger_count": zaru_trigger_count,
    }

    if store_smoothing_data:
        result["_smoothing_data"] = {
            "F":      smooth_F,
            "P_pred": smooth_P_pred,
            "P_upd":  smooth_P_upd,
            "dx_upd": smooth_dx_upd,
            "pred_p": smooth_pred_p,
            "pred_v": smooth_pred_v,
            "pred_q": smooth_pred_q,
        }

    return result


def run_all_modes(s_df, v_df,
                  outage_window: Optional[Tuple[float, float]] = None) -> dict:
    """
    Run all 4 modes on the same data. Returns a dict keyed by mode name.
    This is the ablation study — gives the comparison chart for free.
    """
    return {m: run_pipeline(s_df, v_df, mode=m, outage_window=outage_window)
            for m in MODES}


# ── RTS (Rauch-Tung-Striebel) fixed-interval smoother ────────────────────────
def rts_smooth(result: dict, lat0: float, lon0: float) -> dict:
    """
    Offline backward smoothing pass over an ALREADY-COMPLETED forward run
    (run_pipeline must have been called with store_smoothing_data=True).

    Legitimate ONLY because the demo replays a precomputed, recorded
    trajectory — this is a post-processing/evaluation step, not something
    a real-time phone navigation system could do (it doesn't have future
    measurements). Keep this output in a SEPARATE file from the real-time
    fused_output.json and label both honestly on the dashboard.

    Error-state + quaternion subtlety (do not skip this reasoning):
    After every forward step, inject_corrections() moves the error mean
    into the nominal state and resets δx to 0 for the NEXT step's predict.
    The correction that WAS actually applied at step k — call it dx_upd[k]
    — is nonzero right before that reset, and is exactly the tangent-space
    difference between the INS-only predicted state at k and the corrected
    (filtered) state at k. THIS is the forward "filtered mean" a correct
    RTS backward pass must use — using the always-zero POST-reset dx
    instead (an earlier bug in this function) silently forces every
    smoothed correction to zero: mathematically guaranteed, not a real
    "smoothing had no effect" finding. The smoothed correction is injected
    into the nominal quaternion using the SAME small-angle convention the
    forward filter already uses — never a raw quaternion interpolation.

    Standard RTS backward recursion, correctly adapted for the reset
    (k = N-2 downto 0; base case dx_smooth[N-1] = dx_upd[N-1], the real
    last-step correction, not zero):
        C_k           = P_upd[k] @ F[k+1].T @ inv(P_pred[k+1])
        dx_smooth[k]  = dx_upd[k] + C_k @ dx_smooth[k+1]
                        (x_pred[k+1]'s mean is genuinely 0 in this system —
                         every step resets dx to 0 before its own predict,
                         so that term legitimately drops out; it is ONLY
                         dx_filt[k]=dx_upd[k] that must not be zeroed)
        P_smooth[k]   = P_upd[k] + C_k @ (P_smooth[k+1] - P_pred[k+1]) @ C_k.T
    """
    sd = result.get("_smoothing_data")
    if sd is None:
        raise ValueError(
            "rts_smooth() requires result from run_pipeline(store_smoothing_data=True)"
        )

    F_list      = sd["F"]
    P_pred_list = sd["P_pred"]
    P_upd_list  = sd["P_upd"]
    dx_upd_list = sd["dx_upd"]
    p_pred_list = sd["pred_p"]
    v_pred_list = sd["pred_v"]
    q_pred_list = sd["pred_q"]

    N = len(F_list)
    dx_smooth = [None] * N
    P_smooth  = [None] * N

    # Base case: last step's smoothed correction IS the real correction
    # that was applied there — nothing later to smooth against.
    dx_smooth[-1] = dx_upd_list[-1].copy()
    P_smooth[-1]  = P_upd_list[-1].copy()

    for k in range(N - 2, -1, -1):
        C_k = P_upd_list[k] @ F_list[k + 1].T @ np.linalg.solve(
            P_pred_list[k + 1].T, np.eye(15)
        ).T

        dx_smooth[k] = dx_upd_list[k] + C_k @ dx_smooth[k + 1]
        P_smooth[k]  = P_upd_list[k] + C_k @ (P_smooth[k + 1] - P_pred_list[k + 1]) @ C_k.T
        # Defensive symmetrization — verified unnecessary in testing (max
        # asymmetry ~1e-16, machine epsilon) but cheap insurance against
        # floating-point drift accumulating over a much longer real sequence
        # (6800+ steps vs the synthetic 300-point test this was checked on).
        P_smooth[k] = (P_smooth[k] + P_smooth[k].T) / 2

    # ── inject smoothed correction onto the INS-predicted nominal trajectory ─
    R_earth = 6_371_000.0
    smoothed_positions, smoothed_velocities, smoothed_headings = [], [], []
    smoothed_uncertainty = []

    for k in range(N):
        dpos   = dx_smooth[k][0:3]
        dvel   = dx_smooth[k][3:6]
        dtheta = dx_smooth[k][6:9]

        p_s = p_pred_list[k] + dpos
        v_s = v_pred_list[k] + dvel

        # Same small-angle quaternion injection convention as inject_corrections()
        dq  = np.array([1.0, dtheta[0] / 2, dtheta[1] / 2, dtheta[2] / 2])
        q_s = quat_normalize(quat_mult(q_pred_list[k], dq))

        lat_out = lat0 + (p_s[1] / R_earth) * RAD2DEG
        lon_out = lon0 + (p_s[0] / (R_earth * np.cos(lat0 * DEG2RAD))) * RAD2DEG
        _, _, yaw_deg = rot_to_euler(quat_to_rot(q_s))

        smoothed_positions.append([float(lat_out), float(lon_out)])
        smoothed_velocities.append(float(np.linalg.norm(v_s[:2])))
        smoothed_headings.append(float(yaw_deg))
        smoothed_uncertainty.append(float(np.trace(P_smooth[k][0:3, 0:3])))

    return {
        "mode":           result["mode"] + "_rts_smoothed",
        "outage_window":  result["outage_window"],
        "timestamps":     result["timestamps"],
        "positions":      smoothed_positions,
        "velocities":     smoothed_velocities,
        "headings":       smoothed_headings,
        "covariances":    smoothed_uncertainty,
        "gnss_status":    result["gnss_status"],  # status labels unchanged — same recorded epochs
        "lat0":           lat0,
        "lon0":           lon0,
    }


def export_smoothed_json(smoothed_result: dict, outdir: str = "exports") -> None:
    """
    Export the RTS-smoothed trajectory to a SEPARATE file from
    fused_output.json. Never overwrites the real-time filter's output —
    the dashboard should show both, honestly labeled:
        fused_output.json          -> "Real-time estimate" (causal, no future info)
        fused_output_smoothed.json -> "Offline smoothed estimate" (post-processed,
                                       uses full recorded trajectory)
    """
    os.makedirs(outdir, exist_ok=True)
    data = {
        "timestamps":  smoothed_result["timestamps"],
        "positions":   smoothed_result["positions"],
        "velocities":  smoothed_result["velocities"],
        "headings":    smoothed_result["headings"],
        "gnss_status": smoothed_result["gnss_status"],
        "uncertainty": smoothed_result["covariances"],
        "mode":        smoothed_result["mode"],
        "outage_window": smoothed_result["outage_window"],
        "smoothing":   "rts",   # explicit flag — never ambiguous in the JSON itself
    }
    path = os.path.join(outdir, "fused_output_smoothed.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Exported: {path}")


# ── reference trajectory extraction ──────────────────────────────────────────
def extract_reference(v_df) -> dict:
    """
    Extract the reference trajectory from the V-* VBOX file.
    Called 'reference_trajectory', not 'ground_truth'.
    See docs/DATASET.md for the terminology decision.
    """
    valid = v_df.dropna(subset=["gps_lat", "gps_lon"])
    return {
        "timestamps": valid["timestamp_s"].tolist(),
        "positions":  list(zip(valid["gps_lat"].tolist(),
                                valid["gps_lon"].tolist())),
        "velocities": valid["gps_speed_ms"].tolist(),
        "headings":   valid["gps_heading_deg"].tolist(),
    }


def extract_gnss_only(s_df) -> dict:
    """
    Extract the raw smartphone GPS trace (no fusion).
    This is the 'gnss_only' baseline for comparison.
    Interpolates zero-order hold intervals to maintain continuous path.
    """
    valid = s_df.dropna(subset=["gps_lat", "gps_lon"]).copy()
    for col in ["gps_lat", "gps_lon", "gps_speed_ms", "gps_heading_deg"]:
        if col in valid.columns and valid[col].notna().any():
            diff = valid[col].diff()
            valid.loc[diff == 0, col] = np.nan
            valid[col] = valid[col].interpolate(method="linear")
    return {
        "timestamps": valid["timestamp_s"].tolist(),
        "positions":  list(zip(valid["gps_lat"].tolist(),
                                valid["gps_lon"].tolist())),
        "velocities": valid["gps_speed_ms"].tolist(),
        "headings":   valid["gps_heading_deg"].tolist(),
    }


# ── JSON export ───────────────────────────────────────────────────────────────
def export_json(fused_result: dict, v_df, s_df,
                outdir: str = "exports") -> None:
    """
    Export the three JSON files consumed by the frontend.
    Schema (locked at end of Part III — see RULES.md):
      timestamps:  [float, ...]        seconds from sequence start
      positions:   [[lat, lon], ...]   degrees
      velocities:  [float, ...]        m/s
      headings:    [float, ...]        degrees
      gnss_status: [str, ...]          'healthy' | 'unavailable' | 'outage'
      uncertainty: [float, ...]        trace of EKF position covariance (m²)
    """
    os.makedirs(outdir, exist_ok=True)

    ref  = extract_reference(v_df)
    gnss = extract_gnss_only(s_df)

    fused = {
        "timestamps":  fused_result["timestamps"],
        "positions":   fused_result["positions"],
        "velocities":  fused_result["velocities"],
        "headings":    fused_result["headings"],
        "gnss_status": fused_result["gnss_status"],
        "uncertainty": fused_result["covariances"],
        "mode":        fused_result["mode"],
        "outage_window": fused_result["outage_window"],
    }

    for name, data in [
        ("reference_trajectory", ref),
        ("gnss_only",            gnss),
        ("fused_output",         fused),
    ]:
        path = os.path.join(outdir, f"{name}.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  Exported: {path}")


# ── position error evaluation ─────────────────────────────────────────────────
def evaluate_error(result: dict, v_df) -> dict:
    """
    Compute position error (metres) of a fused result against the V-* reference.
    Returns per-step errors and summary stats.
    """
    ref_valid = v_df.dropna(subset=["gps_lat", "gps_lon"])
    ref_times = ref_valid["timestamp_s"].values
    ref_lats  = ref_valid["gps_lat"].values
    ref_lons  = ref_valid["gps_lon"].values

    lat0, lon0 = result["lat0"], result["lon0"]
    errors = []

    for t, (lat, lon) in zip(result["timestamps"], result["positions"]):
        idx = np.searchsorted(ref_times, t)
        if idx >= len(ref_times):
            idx = len(ref_times) - 1
        ref_enu = latlon_to_enu(ref_lats[idx], ref_lons[idx], lat0, lon0)
        est_enu = latlon_to_enu(lat, lon, lat0, lon0)
        errors.append(float(np.linalg.norm(ref_enu[:2] - est_enu[:2])))

    return {
        "mode":       result["mode"],
        "errors_m":   errors,
        "mean_m":     float(np.mean(errors)),
        "rmse_m":     float(np.sqrt(np.mean(np.array(errors)**2))),
        "max_m":      float(np.max(errors)),
        "timestamps": result["timestamps"],
    }


# ── quick test entrypoint ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from data_loader import load_smartphone, load_vehicle
    import matplotlib.pyplot as plt

    BASE = os.path.join(
        os.path.dirname(__file__), "..",
        "IO-VNBD", "Synchronised V abd S datasets",
        "Categorised IOVNB Dataset", "S (Driver A)", "S3b"
    )

    print("Loading data...")
    s_df = load_smartphone(os.path.join(BASE, "S-S3b.csv"))
    v_df = load_vehicle(os.path.join(BASE, "V-S3b.csv"))

    # ── run all 4 modes with a 60-second GNSS outage ──────────────────────
    OUTAGE = (200.0, 260.0)   # seconds
    print(f"\nRunning 4-mode ablation (outage {OUTAGE[0]}s → {OUTAGE[1]}s)...")
    all_results = run_all_modes(s_df, v_df, outage_window=OUTAGE)

    # ── evaluate position error for each mode ─────────────────────────────
    print("\nPosition error summary:")
    print(f"  {'Mode':<15} {'Mean (m)':>10} {'RMSE (m)':>10} {'Max (m)':>10}")
    print(f"  {'-'*47}")
    for mode, res in all_results.items():
        ev = evaluate_error(res, v_df)
        print(f"  {mode:<15} {ev['mean_m']:>10.2f} {ev['rmse_m']:>10.2f} {ev['max_m']:>10.2f}")

    # ── export the 'full' mode as the demo JSON ───────────────────────────
    print("\nExporting JSON files...")
    export_json(all_results["full"], v_df, s_df, outdir="exports")

    # ── comparison plot ───────────────────────────────────────────────────
    ref   = extract_reference(v_df)
    gnss  = extract_gnss_only(s_df)
    colors = {
        "ins_only": "orange",
        "ins_gnss": "royalblue",
        "ins_nhc":  "purple",
        "full":     "green",
    }

    fig, (ax_map, ax_err) = plt.subplots(1, 2, figsize=(16, 7))

    # Map panel
    ref_pos  = np.array(ref["positions"])
    gnss_pos = np.array(gnss["positions"])
    ax_map.plot(ref_pos[:,1],  ref_pos[:,0],  "k-",  lw=2,   label="Reference (VBOX)", zorder=5)
    ax_map.plot(gnss_pos[:,1], gnss_pos[:,0], "r--", lw=1,   label="GNSS-only (S)", zorder=4)
    for mode, res in all_results.items():
        pos = np.array(res["positions"])
        ax_map.plot(pos[:,1], pos[:,0], color=colors[mode], lw=1.2,
                    alpha=0.8, label=mode, zorder=3)

    # Shade outage window on map (just a title note — map doesn't have time axis)
    ax_map.set_title(f"Trajectories — S-S3b  |  GNSS outage {OUTAGE[0]}–{OUTAGE[1]} s")
    ax_map.set_xlabel("Longitude (°)")
    ax_map.set_ylabel("Latitude (°)")
    ax_map.legend(fontsize=8)
    ax_map.grid(True, alpha=0.3)

    # Error-vs-time panel
    for mode, res in all_results.items():
        ev = evaluate_error(res, v_df)
        ax_err.plot(ev["timestamps"], ev["errors_m"],
                    color=colors[mode], label=mode, lw=1.2)

    ax_err.axvspan(OUTAGE[0], OUTAGE[1], alpha=0.15, color="red", label="GNSS outage")
    ax_err.set_title("Position error vs time (m)")
    ax_err.set_xlabel("Time (s)")
    ax_err.set_ylabel("Error (m)")
    ax_err.legend(fontsize=8)
    ax_err.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("exports/ablation_comparison.png", dpi=150)
    print("  Saved: exports/ablation_comparison.png")
    if os.environ.get("SHOW_PLOTS") == "1":
        plt.show()
    else:
        plt.close()

"""
sim_drive.py — synthetic drive with KNOWN truth, in the column format of
data_loader.load_smartphone(). Sandbox for vehicle_dr: every filter change is
first checked here, where the right answer is known, before real data is touched.

    from sim_drive import simulate, SimConfig
    s_df, truth = simulate(SimConfig(seed=1, gyro_scale=1.2, mount_changes=((90.0, -100.0),)))

What it mimics (all knobs on SimConfig):
  * route of straights, 90-degree turns and stops, including a stop that begins
    just before t = 180 s and ends ~212 s — followed by the 200-260 s GNSS outage
    exactly like S3b — see default_route().
  * 10 Hz IMU. gyro_yaw_rads is the VERTICAL rate (the loader's A2 mapping):
    true yaw rate * gyro_scale + gyro_bias + white noise. Horizontal linear accel
    is the vehicle's forward/lateral acceleration rotated into the PHONE frame by
    the mount angle phi(t) (constant, or changed abruptly mid-drive to mimic S3b),
    plus a fixed bias and road-vibration noise whose RMS grows with speed.
    Gravity columns are ~(0, 0, 9.806).
  * GNSS: a NEW fix every fix_period seconds (9 s like the phone), position noise
    gnss_sigma per axis, speed in m/s, course as a BEARING (clockwise from North,
    degrees), values held between fixes — as in the real CSV.

Conventions: truth psi is ENU (radians, counter-clockwise from East); the phone
course field is a bearing. Mount angle phi: vehicle forward axis, measured from
phone +x toward +y (same definition as mount_angle.py).
"""
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
import pandas as pd

G = 9.80665
R_EARTH = 6_371_000.0
LAT0, LON0 = 52.375361, -1.256116          # same origin as S3b

A_MAX = 1.5                                  # m/s^2 accelerating
D_MAX = 2.0                                  # m/s^2 braking


def default_route():
    """~330 s route. Stop starts at ~178 s and lasts 32 s (until ~212 s)."""
    return [
        ("straight", 470.0, 11.0, 4.0), ("turn", +90.0, 12.0, 4.0),
        ("straight", 190.0, 10.0, 4.0), ("turn", -90.0, 12.0, 4.0),
        ("straight", 300.0, 12.0, 4.0), ("turn", +90.0, 12.0, 4.0),
        ("straight", 180.0, 10.0, 4.0), ("turn", -90.0, 12.0, 4.0),
        ("straight", 200.0, 10.0, 4.0), ("turn", +90.0, 12.0, 4.0),
        ("straight", 100.0, 9.0, 0.0), ("stop", 32.0),
        ("straight", 170.0, 11.0, 4.0), ("turn", -90.0, 12.0, 4.0),
        ("straight", 200.0, 10.0, 4.0), ("turn", +90.0, 12.0, 4.0),
        ("straight", 230.0, 12.0, 4.0), ("turn", +90.0, 12.0, 4.0),
        ("straight", 160.0, 10.0, 4.0), ("turn", -90.0, 12.0, 4.0),
        ("straight", 140.0, 10.0, 0.0),
    ]


@dataclass
class SimConfig:
    seed: int = 0
    dt: float = 0.1
    route: Optional[list] = None
    psi0_deg: float = 90.0                    # start heading, ENU (90 = facing North)
    # gyro
    gyro_scale: float = 1.0
    gyro_bias: float = -0.008                 # rad/s
    gyro_noise: float = 0.010                 # rad/s, white, per sample
    # mount + accelerometer
    mount_deg: float = -50.0                  # phi: forward axis from phone +x toward +y
    mount_changes: Tuple[Tuple[float, float], ...] = ()   # ((t_s, new_phi_deg), ...) abrupt
    accel_bias: Tuple[float, float] = (0.10, -0.15)       # phone-frame horizontal bias (m/s^2)
    vib_base: float = 0.10                    # m/s^2 per axis at rest
    vib_per_ms: float = 0.10                  # extra RMS per m/s of speed
    # GNSS
    fix_period: float = 9.0
    gnss_sigma: float = 4.0                   # m per axis
    gnss_corr: float = 0.0                    # AR(1) coefficient of the position error across fixes
    speed_sigma: float = 0.3                  # m/s
    course_sigma_deg: float = 3.0
    gnss_accuracy_m: float = 4.0              # reported accuracy field


def _segment_done(seg, st):
    kind = seg[0]
    if kind == "straight":
        return st["travelled"] >= seg[1]
    if kind == "turn":
        return st["turned"] >= abs(np.deg2rad(seg[1]))
    if kind == "stop":
        return st["waited"] >= seg[1]
    raise ValueError(kind)


def _kinematics(cfg):
    """Integrate the route at cfg.dt. Returns dict of per-step true arrays (state at t_i and the
    forward acceleration / yaw rate that act over [t_i, t_i+dt])."""
    route = cfg.route if cfg.route is not None else default_route()
    dt = cfg.dt
    E = N = 0.0
    psi = np.deg2rad(cfg.psi0_deg)
    v = 0.0
    out = {k: [] for k in ("E", "N", "psi", "v", "omega", "a_fwd", "stationary")}
    for seg in route:
        st = dict(travelled=0.0, turned=0.0, waited=0.0)
        guard = 0
        while not _segment_done(seg, st):
            guard += 1
            if guard > 200_000:
                raise RuntimeError("segment did not finish")
            kind = seg[0]
            omega = 0.0
            if kind == "straight":
                _, length, v_cruise, v_end = seg
                remaining = length - st["travelled"]
                brake_d = max(0.0, (v * v - v_end * v_end) / (2.0 * D_MAX)) + 0.5 * v * dt
                v_target = v_end if remaining <= brake_d else v_cruise
            elif kind == "turn":
                _, angle_deg, radius, v_turn = seg
                v_target = v_turn
                omega = np.sign(angle_deg) * v / radius
            else:                                             # stop
                v_target = 0.0
            a = float(np.clip((v_target - v) / dt, -D_MAX, A_MAX))
            v_new = max(0.0, v + a * dt)
            a = (v_new - v) / dt
            if kind == "turn":
                omega = np.sign(angle_deg) * 0.5 * (v + v_new) / radius
                left = abs(np.deg2rad(angle_deg)) - st["turned"]
                if abs(omega) * dt > left:                    # do not overshoot the exact angle
                    omega = np.sign(omega) * left / dt
            out["E"].append(E); out["N"].append(N); out["psi"].append(psi); out["v"].append(v)
            out["omega"].append(omega); out["a_fwd"].append(a)
            out["stationary"].append(v < 0.02 and v_new < 0.02)
            d = 0.5 * (v + v_new) * dt
            E += d * np.cos(psi + 0.5 * omega * dt)
            N += d * np.sin(psi + 0.5 * omega * dt)
            psi += omega * dt
            st["travelled"] += d
            st["turned"] += abs(omega) * dt
            if kind == "stop" and v_new < 0.02:
                st["waited"] += dt
            v = v_new
    return {k: np.array(x) for k, x in out.items()}


def wrap_pi(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def enu_to_latlon(E, N):
    lat = LAT0 + np.rad2deg(np.asarray(N) / R_EARTH)
    lon = LON0 + np.rad2deg(np.asarray(E) / (R_EARTH * np.cos(np.deg2rad(LAT0))))
    return lat, lon


def simulate(cfg: Optional[SimConfig] = None):
    """Returns (s_df, truth). s_df matches load_smartphone(); truth is V-file-like
    (timestamp_s, gps_lat, gps_lon, gps_heading_deg, gps_speed_ms) plus E, N, psi_rad,
    v, omega, a_fwd, stationary, mount_deg."""
    cfg = cfg or SimConfig()
    rng = np.random.default_rng(cfg.seed)
    k = _kinematics(cfg)
    n = len(k["E"])
    t = np.arange(n) * cfg.dt
    v, omega, a_fwd = k["v"], k["omega"], k["a_fwd"]

    # mount angle history
    phi = np.full(n, cfg.mount_deg, dtype=float)
    for t_ch, new_phi in sorted(cfg.mount_changes):
        phi[t >= t_ch] = new_phi
    ph = np.deg2rad(phi)

    # phone-frame horizontal linear acceleration
    a_lat = v * omega                                          # left-positive
    ah_x = a_fwd * np.cos(ph) - a_lat * np.sin(ph)
    ah_y = a_fwd * np.sin(ph) + a_lat * np.cos(ph)
    vib = cfg.vib_base + cfg.vib_per_ms * v
    lin_x = ah_x + cfg.accel_bias[0] + rng.normal(0, 1, n) * vib
    lin_y = ah_y + cfg.accel_bias[1] + rng.normal(0, 1, n) * vib
    lin_z = rng.normal(0, 1, n) * (0.1 + 0.5 * vib)
    grav = np.column_stack([rng.normal(0, 0.02, n), rng.normal(0, 0.02, n), G + rng.normal(0, 0.01, n)])

    gyro_v = cfg.gyro_scale * omega + cfg.gyro_bias + rng.normal(0, cfg.gyro_noise, n)
    gyro_x = rng.normal(0, 0.05, n)
    gyro_y = rng.normal(0, 0.05, n)

    # GNSS fixes (new fix every fix_period; values held in between)
    fix_idx = np.arange(0, n, max(1, int(round(cfg.fix_period / cfg.dt))))
    nf = len(fix_idx)
    noise = np.zeros((nf, 2))
    w = rng.normal(0, cfg.gnss_sigma, (nf, 2))
    for j in range(nf):
        noise[j] = w[j] if j == 0 else cfg.gnss_corr * noise[j - 1] + np.sqrt(1 - cfg.gnss_corr ** 2) * w[j]
    fE = k["E"][fix_idx] + noise[:, 0]
    fN = k["N"][fix_idx] + noise[:, 1]
    f_lat, f_lon = enu_to_latlon(fE, fN)
    f_spd = np.maximum(0.0, v[fix_idx] + rng.normal(0, cfg.speed_sigma, nf))
    true_bearing = np.rad2deg(np.pi / 2 - k["psi"]) % 360.0
    f_brg = (true_bearing[fix_idx] + rng.normal(0, cfg.course_sigma_deg, nf)) % 360.0
    for j in range(1, nf):                                     # a real receiver reports a stale course when almost stopped
        if v[fix_idx[j]] < 1.0:
            f_brg[j] = f_brg[j - 1]
    hold = np.searchsorted(fix_idx, np.arange(n), side="right") - 1

    s_df = pd.DataFrame({
        "timestamp_s": t,
        "gps_lat": f_lat[hold], "gps_lon": f_lon[hold], "gps_alt_m": 160.0,
        "gps_speed_ms": f_spd[hold], "gps_heading_deg": f_brg[hold],
        "gps_accuracy_m": cfg.gnss_accuracy_m, "gps_satellites": 12.0,
        "accel_x": lin_x + grav[:, 0], "accel_y": lin_y + grav[:, 1], "accel_z": lin_z + grav[:, 2],
        "gravity_x": grav[:, 0], "gravity_y": grav[:, 1], "gravity_z": grav[:, 2],
        "linear_accel_x": lin_x, "linear_accel_y": lin_y, "linear_accel_z": lin_z,
        "gyro_yaw_rads": gyro_v, "gyro_pitch_rads": gyro_y, "gyro_roll_rads": gyro_x,
        "mag_x_ut": 0.0, "mag_y_ut": -28.0, "mag_z_ut": 0.0,
        "orient_yaw_deg": 0.0, "orient_pitch_deg": 0.0, "orient_roll_deg": 0.0,
    })
    t_lat, t_lon = enu_to_latlon(k["E"], k["N"])
    truth = pd.DataFrame({
        "timestamp_s": t, "gps_lat": t_lat, "gps_lon": t_lon,
        "gps_heading_deg": true_bearing, "gps_speed_ms": v,
        "E": k["E"], "N": k["N"], "psi_rad": k["psi"], "v": v, "omega": omega,
        "a_fwd": a_fwd, "stationary": k["stationary"], "mount_deg": phi,
    })
    return s_df, truth


if __name__ == "__main__":
    s, tr = simulate()
    st = tr["stationary"].values
    edges = np.flatnonzero(np.diff(st.astype(int)))
    print(f"{len(s)} rows, {s.timestamp_s.iloc[-1]:.1f} s; fixes: {(s.gps_lat.diff() != 0).sum()}")
    print("stationary spans (s):", [(round(tr.timestamp_s[a + 1], 1)) for a in edges])
    print("mean speed %.1f m/s, total |dpsi| %.0f deg" % (tr.v.mean(), np.degrees(np.abs(np.diff(tr.psi_rad)).sum())))

"""
test_vehicle_dr.py — sandbox-driven tests for vehicle_dr (and for the sandbox itself).

Every B-step of the vehicle_dr build adds a class here with a numeric pass criterion,
checked on the synthetic drive from sim_drive.py where the truth is known.
No dataset needed.
"""
import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sim_drive import simulate, SimConfig, default_route, wrap_pi, enu_to_latlon, LAT0, LON0

LOADER_COLUMNS = [
    "timestamp_s", "gps_lat", "gps_lon", "gps_alt_m", "gps_speed_ms", "gps_heading_deg",
    "gps_accuracy_m", "gps_satellites", "accel_x", "accel_y", "accel_z",
    "gravity_x", "gravity_y", "gravity_z", "linear_accel_x", "linear_accel_y", "linear_accel_z",
    "gyro_yaw_rads", "gyro_pitch_rads", "gyro_roll_rads", "mag_x_ut", "mag_y_ut", "mag_z_ut",
    "orient_yaw_deg", "orient_pitch_deg", "orient_roll_deg",
]


class TestSandbox(unittest.TestCase):
    """S0 — the synthetic drive itself must be physically consistent, or nothing tested on it means anything."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = SimConfig(seed=3)
        cls.s, cls.tr = simulate(cls.cfg)

    def test_columns_match_loader_format(self):
        for c in LOADER_COLUMNS:
            self.assertIn(c, self.s.columns)
        for c in ("timestamp_s", "gps_lat", "gps_lon", "gps_heading_deg", "gps_speed_ms"):
            self.assertIn(c, self.tr.columns)

    def test_10hz_and_length(self):
        dt = np.diff(self.s.timestamp_s.values)
        self.assertTrue(np.allclose(dt, 0.1))
        self.assertGreater(self.s.timestamp_s.iloc[-1], 300.0)

    def test_gnss_new_fix_every_9s_and_held_between(self):
        lat = self.s.gps_lat.values
        changes = np.flatnonzero(np.diff(lat) != 0) + 1
        gaps = np.diff(self.s.timestamp_s.values[changes])
        self.assertTrue(np.allclose(gaps, 9.0, atol=0.11), gaps[:5])
        # held: within a hold interval every row has the identical value
        self.assertTrue(np.all(lat[changes[0]:changes[1]] == lat[changes[0]]))

    def test_speed_is_ms_and_course_is_a_bearing(self):
        # Facing North (psi = 90 deg ENU) at the first moving fix => bearing near 0/360, not near 90.
        k = np.flatnonzero((self.tr.v.values > 5) & (self.tr.timestamp_s.values < 20))[0]
        j = int(k // 90 * 90)                       # its fix row
        brg = self.s.gps_heading_deg.values[k]
        self.assertLess(min(brg, 360 - brg), 15.0, brg)
        self.assertAlmostEqual(self.s.gps_speed_ms.values[k], self.tr.v.values[j], delta=6.0)
        self.assertLess(self.s.gps_speed_ms.max(), 20.0)     # m/s, not km/h-scaled

    def test_truth_kinematics_consistent(self):
        E = np.cumsum(self.tr.v.values * np.cos(self.tr.psi_rad.values) * 0.1)
        N = np.cumsum(self.tr.v.values * np.sin(self.tr.psi_rad.values) * 0.1)
        err = np.hypot(E - (self.tr.E.values - self.tr.E.values[0]), N - (self.tr.N.values - self.tr.N.values[0]))
        self.assertLess(err.max(), 8.0)             # Euler vs midpoint integration over 330 s

    def test_truth_latlon_roundtrip(self):
        from ins_ekf import latlon_to_enu
        e = latlon_to_enu(self.tr.gps_lat.values[-1], self.tr.gps_lon.values[-1], LAT0, LON0)
        self.assertAlmostEqual(e[0], self.tr.E.values[-1], delta=0.05)
        self.assertAlmostEqual(e[1], self.tr.N.values[-1], delta=0.05)

    def test_stop_like_s3b_precedes_the_outage(self):
        st = self.tr.stationary.values
        t = self.tr.timestamp_s.values
        edges = np.flatnonzero(np.diff(st.astype(int)))
        start, end = t[edges[0] + 1], t[edges[1] + 1]
        self.assertTrue(170.0 <= start <= 190.0, start)
        self.assertTrue(200.0 <= end <= 220.0, end)
        self.assertGreaterEqual(end - start, 25.0)

    def test_gyro_bias_scale_and_noise(self):
        cfg = SimConfig(seed=4, gyro_scale=1.2, gyro_bias=-0.008)
        s, tr = simulate(cfg)
        st = tr.stationary.values
        self.assertAlmostEqual(float(s.gyro_yaw_rads.values[st].mean()), -0.008, delta=0.003)
        turning = np.abs(tr.omega.values) > 0.2
        ratio = np.polyfit(tr.omega.values[turning], s.gyro_yaw_rads.values[turning], 1)[0]
        self.assertAlmostEqual(ratio, 1.2, delta=0.06)

    def test_horizontal_accel_is_rotated_by_the_mount_angle(self):
        for phi in (-50.0, 40.0, 150.0):
            s, tr = simulate(SimConfig(seed=5, mount_deg=phi))
            u_f = np.array([np.cos(np.deg2rad(phi)), np.sin(np.deg2rad(phi))])
            a = np.column_stack([s.linear_accel_x, s.linear_accel_y]) @ u_f
            k = np.corrcoef(a, tr.a_fwd.values)[0, 1]
            self.assertGreater(k, 0.45, (phi, k))       # vibration noise caps this well below 1

    def test_abrupt_mount_change_is_in_the_truth(self):
        s, tr = simulate(SimConfig(seed=6, mount_deg=-50.0, mount_changes=((90.0, 100.0),)))
        self.assertEqual(tr.mount_deg.values[0], -50.0)
        self.assertEqual(tr.mount_deg.values[-1], 100.0)
        self.assertEqual(tr.mount_deg.values[int(89.9 / 0.1)], -50.0)
        self.assertEqual(tr.mount_deg.values[int(90.1 / 0.1)], 100.0)

    def test_vibration_grows_with_speed(self):
        s, tr = simulate(SimConfig(seed=7))
        # per-axis residual around the model (a_h - true a_h) = bias + noise
        v = tr.v.values
        resid = s.linear_accel_x.values - (tr.a_fwd.values * np.cos(np.deg2rad(-50.0))
                                           - v * tr.omega.values * np.sin(np.deg2rad(-50.0)))
        slow = resid[(v < 1.0)].std()
        fast = resid[(v > 9.0)].std()
        self.assertGreater(fast, 3 * slow)

    def test_seed_is_deterministic(self):
        a, _ = simulate(SimConfig(seed=11)); b, _ = simulate(SimConfig(seed=11)); c, _ = simulate(SimConfig(seed=12))
        self.assertTrue(a.equals(b))
        self.assertFalse(a.equals(c))


if __name__ == "__main__":
    unittest.main()

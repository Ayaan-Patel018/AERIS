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
from sim_drive import simulate, SimConfig, default_route, multi_stop_route, wrap_pi, enu_to_latlon, LAT0, LON0

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



# ─────────────────────────────────────────────────────────────────────────────
# B3a — vehicle_dr core
# ─────────────────────────────────────────────────────────────────────────────
import vehicle_dr
import check_outage
from vehicle_dr import bearing_to_psi, psi_to_bearing_deg, wrap_pi as vdr_wrap


class TestAngleConventions(unittest.TestCase):
    """Phone course is a BEARING (deg, clockwise from North); vehicle_dr's psi is ENU (rad, CCW from East)."""

    def test_cardinal_directions(self):
        self.assertAlmostEqual(float(bearing_to_psi(0.0)), np.pi / 2)        # North
        self.assertAlmostEqual(float(bearing_to_psi(90.0)), 0.0)             # East
        self.assertAlmostEqual(float(bearing_to_psi(180.0)), -np.pi / 2)     # South
        west = float(bearing_to_psi(270.0))                                  # West: +/- pi
        self.assertAlmostEqual(abs(west), np.pi)

    def test_northeast_is_45_degrees_ccw_from_east(self):
        self.assertAlmostEqual(float(bearing_to_psi(45.0)), np.pi / 4)

    def test_direction_vectors_agree(self):
        # bearing b points along (E, N) = (sin b, cos b); psi points along (cos psi, sin psi)
        for b in (0, 30, 90, 135, 200, 270, 359):
            psi = float(bearing_to_psi(b))
            self.assertAlmostEqual(np.cos(psi), np.sin(np.radians(b)), places=9)
            self.assertAlmostEqual(np.sin(psi), np.cos(np.radians(b)), places=9)

    def test_round_trip_and_wrapping(self):
        for b in (-370.0, -90.0, 0.0, 1.0, 359.9, 360.0, 725.0):
            back = float(psi_to_bearing_deg(bearing_to_psi(b)))
            self.assertAlmostEqual((back - b + 180.0) % 360.0 - 180.0, 0.0, places=6)
        self.assertTrue(-np.pi <= float(bearing_to_psi(123.0)) < np.pi)

    def test_wrap_pi(self):
        self.assertAlmostEqual(float(vdr_wrap(3 * np.pi / 2)), -np.pi / 2)
        self.assertAlmostEqual(float(vdr_wrap(-3 * np.pi / 2)), np.pi / 2)
        self.assertAlmostEqual(float(vdr_wrap(0.3)), 0.3)

    def test_sandbox_course_field_round_trips_to_truth_psi(self):
        s, tr = simulate(SimConfig(seed=2, course_sigma_deg=0.0))
        k = int(np.flatnonzero(tr.v.values > 5)[0])
        fix = int(k // 90 * 90)
        psi_from_phone = float(bearing_to_psi(s.gps_heading_deg.values[k]))
        self.assertAlmostEqual(float(vdr_wrap(psi_from_phone - tr.psi_rad.values[fix])), 0.0, places=6)


def _mini(res, s, tr, t_max=200.0):
    rows = check_outage.mini_outage(res, s, tr, 0.0, t_max=t_max)
    err = np.array([r["aeris"] for r in rows]); cv = np.array([r["cv"] for r in rows])
    ins = np.array([r["inside"] for r in rows], dtype=float)
    return rows, err, cv, ins


class TestVehicleDRCore(unittest.TestCase):
    """B3a. Sandbox pass criteria: beats the last-fix + constant-velocity baseline; honest uncertainty; ZUPT works;
    causal; never uses V-data; GNSS never used inside the outage."""
    SEEDS = (0, 1, 2, 3)

    @classmethod
    def setUpClass(cls):
        cls.runs = {}
        for sd in cls.SEEDS:
            s, tr = simulate(SimConfig(seed=sd))
            cls.runs[sd] = (s, tr, vehicle_dr.run_pipeline(s, None, outage_window=(200.0, 260.0)))

    def test_result_dict_has_the_run_pipeline_keys(self):
        res = self.runs[0][2]
        for k in ("mode", "outage_window", "yaw_observable", "timestamps", "positions", "velocities", "headings",
                  "covariances", "cov_matrix", "gnss_status", "lat0", "lon0", "zaru_trigger_count"):
            self.assertIn(k, res)
        n = len(res["timestamps"])
        self.assertEqual(n, len(self.runs[0][0]) - 1)
        for k in ("positions", "velocities", "headings", "covariances", "cov_matrix", "gnss_status"):
            self.assertEqual(len(res[k]), n)
        self.assertTrue(np.all(np.isfinite(np.array(res["positions"]))))

    def test_beats_const_velocity_baseline_on_every_seed(self):
        for sd in self.SEEDS:
            s, tr, res = self.runs[sd]
            _, err, cv, _ = _mini(res, s, tr)
            self.assertLess(err.mean(), cv.mean(), (sd, err.mean(), cv.mean()))

    def test_one_sigma_coverage_is_honest(self):
        # S3b-tuned noise on the calmer sandbox slightly over-covers (~64 %); the window guards against 0 % / 100 %.
        cov = np.mean([100 * _mini(r[2], r[0], r[1])[3].mean() for r in self.runs.values()])
        self.assertTrue(25.0 <= cov <= 70.0, cov)

    def test_heading_tracks_truth_between_fixes(self):
        s, tr, res = self.runs[0]
        psi = np.radians(np.array(res["headings"]))
        k = np.arange(1, len(psi) + 1)
        err = np.degrees(np.abs(vdr_wrap(psi - tr.psi_rad.values[k])))
        moving = (tr.v.values[k] > 3.0) & (tr.timestamp_s.values[k] < 200.0)
        self.assertLess(np.median(err[moving]), 6.0)

    def test_standstill_pins_speed_to_zero_and_position_holds(self):
        s, tr, res = self.runs[0]
        t = np.array(res["timestamps"]); v = np.array(res["velocities"])
        stop = (tr.timestamp_s.values >= 185.0) & (tr.timestamp_s.values <= 205.0)
        idx = np.flatnonzero(stop) - 1
        self.assertLess(np.abs(v[idx]).max(), 0.3)
        self.assertTrue(np.all(np.array(res["stationary"])[idx]))

    def test_gate_rejects_few_fixes_and_logs_them(self):
        res = self.runs[1][2]
        c = res["gate_counts"]["pos"]
        self.assertLess(c["rejected"], 0.2 * (c["accepted"] + c["rejected"]))
        self.assertIsInstance(res["gate_log"], list)
        for t, kind, d2, ok in res["gate_log"]:
            self.assertIsInstance(ok, bool)

    def test_no_gnss_inside_the_outage_window(self):
        res = self.runs[0][2]
        for t, kind, d2, ok in res["gate_log"]:
            if kind in ("pos", "pos_forced", "speed", "course"):
                self.assertFalse(200.0 <= t <= 260.0, (t, kind))

    def test_is_causal(self):
        s, tr, full = self.runs[0]
        part = vehicle_dr.run_pipeline(s, None, outage_window=(200.0, 260.0), t_end=120.0)
        n = len(part["timestamps"])
        self.assertTrue(np.allclose(np.array(part["positions"]), np.array(full["positions"])[:n]))
        self.assertTrue(np.allclose(part["headings"], full["headings"][:n]))

    def test_vbox_argument_is_ignored(self):
        s, tr, full = self.runs[0]
        garbage = tr.copy(); garbage["gps_lat"] += 1.0; garbage["gps_heading_deg"] = 12.3
        other = vehicle_dr.run_pipeline(s, garbage, outage_window=(200.0, 260.0))
        self.assertTrue(np.allclose(np.array(other["positions"]), np.array(full["positions"])))

    def test_psi_initialised_from_first_course_fix(self):
        for sd in self.SEEDS:
            res = self.runs[sd][2]
            self.assertTrue(res["yaw_observable"])
            self.assertLessEqual(res["psi_init_time"], 9.0)


# ─────────────────────────────────────────────────────────────────────────────
# B3b — launch calibration (mount-free forward axis)
# ─────────────────────────────────────────────────────────────────────────────
from dataclasses import replace as _replace


def _stop_spans(tr):
    st = tr.stationary.values.astype(int)
    e = np.flatnonzero(np.diff(np.r_[0, st, 0]))
    t = tr.timestamp_s.values
    return [(t[a], t[min(b, len(t) - 1)]) for a, b in zip(e[::2], e[1::2])]


def _launch_errors(res, tr):
    """(truth mount - estimated phi) in degrees for every accepted launch, using the mount at the release time."""
    out = []
    for L in res["launches"]:
        if L.get("accepted"):
            k = min(int(round(L["t_release"] / 0.1)), len(tr) - 1)
            out.append(float(np.degrees(vdr_wrap(np.radians(L["phi_deg"] - tr.mount_deg.values[k])))))
    return out


class TestLaunchCalibration(unittest.TestCase):
    """B3b. Sandbox pass criteria: phi recovered within 10 deg on straight and turning launches, also after an abrupt
    mount change; launches are logged; the step does not make the multi-stop route worse."""

    @staticmethod
    def _cfg(turn, change, seed=1):
        base = SimConfig(seed=seed, mount_deg=-50.0, v0=0.0, route=multi_stop_route(turn))
        if not change:
            return base
        _, tr0 = simulate(base)
        sp = _stop_spans(tr0)
        return _replace(base, mount_changes=(((sp[1][0] + sp[1][1]) / 2.0, 100.0),))   # phone moved DURING the 2nd stop

    def _run(self, turn, change, **kw):
        s, tr = simulate(self._cfg(turn, change))
        res = vehicle_dr.run_pipeline(s, None, params=_replace(vehicle_dr.VDRParams(), **kw))
        return s, tr, res

    def test_straight_launches_recover_phi_within_10_deg(self):
        s, tr, res = self._run(False, False)
        errs = _launch_errors(res, tr)
        self.assertGreaterEqual(len(errs), 4, res["launches"])
        self.assertLess(max(abs(e) for e in errs), 10.0, errs)

    def test_turning_launches_recover_phi_within_10_deg(self):
        s, tr, res = self._run(True, False)
        errs = _launch_errors(res, tr)
        self.assertGreaterEqual(len(errs), 4, res["launches"])
        self.assertLess(max(abs(e) for e in errs), 10.0, errs)

    def test_phi_recovered_after_an_abrupt_mount_change(self):
        for turn in (False, True):
            s, tr, res = self._run(turn, True)
            errs = _launch_errors(res, tr)
            self.assertGreaterEqual(len(errs), 4)
            self.assertLess(max(abs(e) for e in errs), 10.0, (turn, errs))
            phis = [L["phi_deg"] for L in res["launches"] if L.get("accepted")]
            self.assertTrue(min(abs(vdr_wrap(np.radians(q - 100.0))) for q in phis[2:]) < np.radians(10.0))

    def test_strict_mode_refuses_a_turning_launch(self):
        s, tr, res = self._run(True, False, launch_turn_comp=False)
        self.assertEqual(len(_launch_errors(res, tr)), 0)
        self.assertTrue(any(L.get("reason") == "turning" for L in res["launches"]))

    def test_every_launch_is_logged_with_its_evidence(self):
        s, tr, res = self._run(False, False)
        self.assertGreaterEqual(len(res["launches"]), 4)
        for L in res["launches"]:
            self.assertIn("t_release", L); self.assertIn("accepted", L)
            if "phi_deg" in L:
                for k in ("R", "mean_accel", "wmax", "contam", "reason"):
                    self.assertIn(k, L)

    def test_no_launch_is_invented_without_a_standstill(self):
        s, tr = simulate(SimConfig(seed=2, v0=8.0, route=[("straight", 400.0, 10.0, 8.0)]))
        res = vehicle_dr.run_pipeline(s, None)
        self.assertEqual([L for L in res["launches"] if L.get("accepted")], [])

    def test_bumps_are_not_launches(self):
        # a stopped car whose phone is jostled: consistent-looking spikes must not be accepted as a launch
        s, tr = simulate(SimConfig(seed=3, v0=0.0, route=[("stop", 40.0)]))
        s = s.copy()
        s.loc[200:203, "linear_accel_x"] += 0.9      # 0.4 s bump
        res = vehicle_dr.run_pipeline(s, None)
        self.assertEqual([L for L in res["launches"] if L.get("accepted")], [])

    def test_does_not_make_the_multi_stop_route_worse(self):
        for turn in (False, True):
            s, tr = simulate(self._cfg(turn, False))
            base = vehicle_dr.run_pipeline(s, None, params=_replace(vehicle_dr.VDRParams(), use_launch=False))
            new = vehicle_dr.run_pipeline(s, None)
            m0 = np.mean([r["aeris"] for r in check_outage.mini_outage(base, s, tr, 0.0)])
            m1 = np.mean([r["aeris"] for r in check_outage.mini_outage(new, s, tr, 0.0)])
            self.assertLessEqual(m1, m0 + 0.5, (turn, m0, m1))

    def test_unlimited_accel_aiding_helps_when_the_mount_is_stable(self):
        # the machinery itself works: with a stable mount, integrating the forward accel beats holding the speed
        s, tr = simulate(self._cfg(False, False))
        held = vehicle_dr.run_pipeline(s, None, params=_replace(vehicle_dr.VDRParams(), use_launch=False))
        aided = vehicle_dr.run_pipeline(s, None, params=_replace(vehicle_dr.VDRParams(), aided_max_s=float("inf")))
        m0 = np.mean([r["aeris"] for r in check_outage.mini_outage(held, s, tr, 0.0)])
        m1 = np.mean([r["aeris"] for r in check_outage.mini_outage(aided, s, tr, 0.0)])
        self.assertLess(m1, m0)


class TestLaunchEvaluator(unittest.TestCase):
    def test_pure_turn_contamination_is_removed(self):
        # launch straight at 1.5 m/s^2 along phone axis 30 deg while turning at 0.4 rad/s
        dt, n = 0.1, 30
        phi = np.radians(30.0)
        t = np.arange(n) * dt
        a_f = np.full(n, 1.5); v = np.cumsum(a_f * dt); w = np.full(n, 0.4)
        u = np.array([np.cos(phi), np.sin(phi)]); up = np.array([-np.sin(phi), np.cos(phi)])
        d = np.outer(a_f, u) + np.outer(v * w, up)
        ax, ay = d[:, 0], d[:, 1]
        p = vehicle_dr.VDRParams()
        ev = vehicle_dr.evaluate_launch(ax, ay, w, 0.0, np.full(n, dt), 8, n - 1, np.zeros(2), p)
        self.assertTrue(ev["accepted"], ev)
        self.assertLess(abs(np.degrees(vdr_wrap(ev["phi"] - phi))), 3.0)
        naive = np.arctan2(d.sum(0)[1], d.sum(0)[0])          # what an uncompensated mean would give
        self.assertGreater(abs(np.degrees(vdr_wrap(naive - phi))), abs(np.degrees(vdr_wrap(ev["phi"] - phi))))

    def test_random_directions_are_rejected(self):
        rng = np.random.default_rng(0)
        n = 30
        d = rng.normal(0, 1.0, (n, 2))
        ev = vehicle_dr.evaluate_launch(d[:, 0], d[:, 1], np.zeros(n), 0.0, np.full(n, 0.1), 8, n - 1, np.zeros(2), vehicle_dr.VDRParams())
        self.assertFalse(ev["accepted"])


if __name__ == "__main__":
    unittest.main()

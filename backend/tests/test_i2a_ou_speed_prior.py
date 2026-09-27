"""
test_i2a_ou_speed_prior.py — I2a: the Ornstein-Uhlenbeck speed prior (`use_ou`, default OFF until adopted).

Sandbox pass criteria (i)-(iv), fixed before the real-data grid search (see AERIS_FINDINGS.md "I2a — OU speed
prior"), 2 seeds, tau=10 / W=120 vs OFF:
  (a) long_route: median sliding-60s-window end error <= 0.5 x OFF.
  (b) the event-like window (outage_window=(200,260) on default_route / long_route, like the S3b demo outage):
      path ratio (AERIS path / truth path) >= 0.75.
  (c) stop_and_go_route: median window end error <= 0.7 x OFF.
  (d) multi_stop_route: no worse than OFF by > 5 %.
Also checks the flag-off no-op guarantee and the basic mechanics (vbar/sv, F[3,3], causality, ZUPT priority).
"""
import os
import sys
import unittest
from dataclasses import replace
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import check_outage as co
import vehicle_dr
import window_plan as wp
from vehicle_dr import VDRParams
from sim_drive import simulate, SimConfig, default_route, long_route, multi_stop_route, stop_and_go_route

OFF = VDRParams()
ON_10_120 = replace(VDRParams(), use_ou=True, ou_tau=10.0, ou_window_s=120.0)


def _window_median_end(route, seed, params):
    s, tr = simulate(SimConfig(seed=seed, route=route))
    lat0, lon0 = co.origin(s)
    truth = co.Truth.from_vehicle(tr, lat0, lon0, 0.0)
    starts = wp.plan_windows(wp.usable_fix_times(s), wp.drive_end(s, tr, 0.0))
    rows = co.window_benchmark(s, truth, starts, params=params)
    return float(np.median([r["vdr"]["end_err"] for r in rows])), len(rows)


def _event_score(route, seed, params):
    s, tr = simulate(SimConfig(seed=seed, route=route))
    lat0, lon0 = co.origin(s)
    truth = co.Truth.from_vehicle(tr, lat0, lon0, 0.0)
    res = vehicle_dr.run_pipeline(s, None, outage_window=(200.0, 260.0), params=params, t_end=260.0)
    t = np.array(res["timestamps"]); m = (t >= 200.0) & (t <= 260.0)
    return co.score_track(truth, t[m], co._res_enu(res, m), np.array(res["velocities"])[m], np.array(res["cov_matrix"])[m])


class TestMechanics(unittest.TestCase):
    """Basic correctness of the OU mechanism, independent of the sandbox pass criteria."""

    def test_flag_off_is_a_pure_noop(self):
        s, _ = simulate(SimConfig(seed=1, route=long_route()))
        a = vehicle_dr.run_pipeline(s, None)                          # bare default: use_ou=False
        b = vehicle_dr.run_pipeline(s, None, params=OFF)
        self.assertEqual(a["positions"], b["positions"]); self.assertEqual(a["velocities"], b["velocities"])
        self.assertEqual(a["ou_active_count"], 0)

    def test_ou_activates_once_history_builds_up_and_holds_before_that(self):
        s, _ = simulate(SimConfig(seed=1, route=long_route()))
        res = vehicle_dr.run_pipeline(s, None, params=ON_10_120)
        self.assertGreater(res["ou_active_count"], 0)
        self.assertLess(res["ou_active_count"], len(res["velocities"]))   # not every row (stationary / no-history rows excluded)

    def test_fewer_than_three_fixes_means_inactive_speed_held_as_now(self):
        # a route with only a single fix ever reporting speed > 2 m/s in the whole run: OU can never activate.
        s, _ = simulate(SimConfig(seed=1, route=[("straight", 3000.0, 8.0, 8.0)], fix_period=9000.0))
        res = vehicle_dr.run_pipeline(s, None, params=ON_10_120)
        self.assertEqual(res["ou_active_count"], 0)

    def test_ou_does_not_override_zupt_at_a_real_stop(self):
        s, tr = simulate(SimConfig(seed=1, route=[("straight", 300.0, 9.0, 0.0), ("stop", 20.0), ("straight", 100.0, 9.0, 9.0)]))
        res = vehicle_dr.run_pipeline(s, None, params=ON_10_120)
        v = np.asarray(res["velocities"]); st = np.asarray(res["stationary"])
        self.assertTrue(np.all(np.abs(v[st]) < 0.5))                  # ZUPT still pins v ~ 0 while flagged stationary

    def test_causal_no_future_leakage(self):
        # changing the IMU/GNSS strictly AFTER row k must not change any output at or before row k.
        s, _ = simulate(SimConfig(seed=1, route=long_route()))
        k = len(s) // 2
        s2 = s.copy()
        s2.loc[k + 50:, "gps_speed_ms"] = s2.loc[k + 50:, "gps_speed_ms"] * 3.0 + 5.0
        a = vehicle_dr.run_pipeline(s, None, params=ON_10_120, t_end=float(s.timestamp_s.iloc[k]))
        b = vehicle_dr.run_pipeline(s2, None, params=ON_10_120, t_end=float(s.timestamp_s.iloc[k]))
        self.assertEqual(a["positions"], b["positions"]); self.assertEqual(a["velocities"], b["velocities"])

    def test_f33_and_process_noise_match_the_ou_formula(self):
        p = replace(VDRParams(), use_ou=True, ou_tau=10.0)
        e = vehicle_dr._EKF(p, 8.0)
        dt = 0.1
        vbar, sv = 12.0, 2.0
        v0 = float(e.x[3])
        e.predict(dt, 0.0, False, None, 1.0, (vbar, sv))
        a = np.exp(-dt / p.ou_tau)
        self.assertAlmostEqual(float(e.x[3]), vbar + (v0 - vbar) * a, places=9)
        self.assertTrue(e.last_ou_active)
        # process noise on v should be sv^2*(1-a^2), not the old rw_v^2*dt: check indirectly via P growth from a
        # clean P (P[3,3] should have grown by exactly sv^2*(1-a^2) since F[3,3]=a and P0[3,3] contributes a^2*P0)
        p0_v = p.p0_v ** 2
        self.assertAlmostEqual(float(e.P[3, 3]), a * a * p0_v + sv ** 2 * (1.0 - a * a), places=6)


class TestSandboxCriteria(unittest.TestCase):
    """(a)-(d), fixed before any real-data number (see AERIS_FINDINGS.md I2a), tau=10, W=120, 2 seeds."""

    def test_a_long_route_halves_median_end_error(self):
        for sd in (1, 2):
            off_m, _ = _window_median_end(long_route(), sd, OFF)
            on_m, _ = _window_median_end(long_route(), sd, ON_10_120)
            self.assertLessEqual(on_m, 0.5 * off_m, msg=f"seed {sd}: OFF {off_m:.1f} ON {on_m:.1f}")

    def test_b_event_like_window_path_ratio(self):
        for route in (default_route(), long_route()):
            for sd in (1, 2):
                sc = _event_score(route, sd, ON_10_120)
                self.assertGreaterEqual(sc["path_ratio"], 0.75, msg=f"seed {sd}: ratio {sc['path_ratio']:.2f}")

    def test_c_stop_and_go_route(self):
        for sd in (1, 2):
            off_m, _ = _window_median_end(stop_and_go_route(), sd, OFF)
            on_m, _ = _window_median_end(stop_and_go_route(), sd, ON_10_120)
            self.assertLessEqual(on_m, 0.7 * off_m, msg=f"seed {sd}: OFF {off_m:.1f} ON {on_m:.1f}")

    def test_d_multi_stop_route_not_worse_than_5_percent(self):
        for sd in (1, 2):
            off_m, _ = _window_median_end(multi_stop_route(), sd, OFF)
            on_m, _ = _window_median_end(multi_stop_route(), sd, ON_10_120)
            self.assertLessEqual(on_m, off_m * 1.05, msg=f"seed {sd}: OFF {off_m:.1f} ON {on_m:.1f}")


if __name__ == "__main__":
    unittest.main()

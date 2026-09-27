"""
test_i2b_turn_ceiling.py — I2b: the turn speed ceiling (`use_turn_ceil`), the fixed version of B3c.

Mount-free, INEQUALITY ONLY (never pushes v up): in a real turn (|omega - b_g| > ceil_w_min), if the filter's v
implies more centripetal accel (v * |omega - b_g|) than a bound (+ margin) allows, pull v DOWN toward the bound
via a normal scalar EKF update — triggered only when v_est > v_ceil, so the update is a one-sided cap in practice.
Two bound modes: "ah" = the ACTUALLY MEASURED 1 s mean horizontal accel magnitude (mount-free, adapts to the real
turn); "fixed" = a constant comfort ceiling `ceil_a_max`.

Real-data screening (S3b dev + S2 stride-4) and confirmation (S2 full list) found ceil_mode="fixed", ceil_a_max=3.0
clears the noise rule tested on top of the R1 default (I2a has no adopted winner, see AERIS_FINDINGS.md I2a):
S3b dev median end 120.9 -> 99.5 m (-17.7%, exact, S3b is never screened), S2 dev median end 126.4 -> 122.1 m
(-3.4%, confirmed on the FULL 861-window list -- neutral, not a regression), p90 stable on both drives
(S3b -1.2%, S2 +0.1%). A whole-drive GNSS-available check (no outage) shows the ceiling barely fires during
correctly-tracked driving (long_route: 7 of 5683 rows) and does not change its accuracy -- it is specifically
catching cases where a GNSS-outage-inflated v is unrealistic for the turn actually happening, not interfering
with normal tracking. Adopted as the new default: use_turn_ceil=True, ceil_mode="fixed", ceil_a_max=3.0 (on top
of R1). See AERIS_FINDINGS.md "I2b — turn speed ceiling".
"""
import os
import sys
import unittest
from dataclasses import replace
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import check_outage as co
import vehicle_dr
from vehicle_dr import VDRParams
from sim_drive import simulate, SimConfig, long_route

# Pre-I2b baseline (R1 default with the ceiling explicitly off) so these tests stay meaningful regardless of the
# live default -- same pattern as R1's OLD_DEFAULT / I2a's tests.
OLD_DEFAULT = replace(VDRParams(), use_turn_ceil=False)
FIXED_3 = replace(VDRParams(), use_turn_ceil=True, ceil_mode="fixed", ceil_a_max=3.0)


class TestMechanics(unittest.TestCase):
    def test_flag_off_is_a_pure_noop(self):
        s, _ = simulate(SimConfig(seed=1, route=long_route()))
        a = vehicle_dr.run_pipeline(s, None, params=OLD_DEFAULT)
        b = vehicle_dr.run_pipeline(s, None, params=replace(OLD_DEFAULT, use_turn_ceil=False))
        self.assertEqual(a["positions"], b["positions"]); self.assertEqual(a["velocities"], b["velocities"])
        self.assertEqual(a["gate_counts"]["turn_ceil"], {"accepted": 0, "rejected": 0})

    def test_update_is_a_convex_combination_so_v_only_moves_toward_the_ceiling(self):
        # direct EKF-level check: whatever the gain, a scalar update toward a LOWER measurement cannot raise v,
        # and cannot overshoot below the measurement either (K in (0,1) for P, R > 0).
        rng = np.random.default_rng(0)
        for _ in range(50):
            p = replace(VDRParams(), sigma_turn_ceil=float(rng.uniform(0.1, 2.0)))
            e = vehicle_dr._EKF(p, 0.0)
            v0 = float(rng.uniform(2.0, 20.0))
            e.x[3] = v0
            e.P[3, 3] = float(rng.uniform(0.5, 30.0))
            v_ceil = v0 - float(rng.uniform(0.1, v0))          # always below v0, like a real trigger
            H1 = np.zeros((1, e.nx)); H1[0, 3] = 1.0
            e.update(np.array([v_ceil - v0]), H1, np.array([[p.sigma_turn_ceil ** 2]]), 1, "turn_ceil", 0.0)
            self.assertLessEqual(float(e.x[3]), v0 + 1e-9)
            self.assertGreaterEqual(float(e.x[3]), v_ceil - 1e-9)

    def test_no_trigger_on_a_route_with_no_sharp_turns(self):
        # default_route()/long_route() turns are gentle (target ~4 m/s -> ~1.3-1.7 m/s^2 centripetal, well under
        # the 3.6 m/s^2 = ceil_a_max + ceil_margin bound), so a straight-only route should never trigger at all.
        s, _ = simulate(SimConfig(seed=1, route=[("straight", 3000.0, 10.0, 10.0)]))
        res = vehicle_dr.run_pipeline(s, None, params=FIXED_3)
        self.assertEqual(res["gate_counts"]["turn_ceil"]["accepted"], 0)

    def test_does_not_meaningfully_change_correctly_tracked_driving(self):
        # with GNSS available throughout (no outage), the ceiling should barely fire and not change accuracy --
        # it targets GNSS-outage-inflated speed estimates, not normal tracking.
        s, tr = simulate(SimConfig(seed=1, route=long_route()))
        lat0, lon0 = co.origin(s)
        truth = co.Truth.from_vehicle(tr, lat0, lon0, 0.0)
        off = vehicle_dr.run_pipeline(s, None, params=OLD_DEFAULT)
        on = vehicle_dr.run_pipeline(s, None, params=FIXED_3)
        t = np.array(on["timestamps"])
        sc_off = co.score_track(truth, t, co._res_enu(off), np.array(off["velocities"]), np.array(off["cov_matrix"]))
        sc_on = co.score_track(truth, t, co._res_enu(on), np.array(on["velocities"]), np.array(on["cov_matrix"]))
        self.assertLess(on["gate_counts"]["turn_ceil"]["accepted"], 20)             # rare
        self.assertLessEqual(sc_on["mean_err"], sc_off["mean_err"] * 1.05)          # not worse by more than 5%

    def test_fixed_mode_bound_is_independent_of_measured_accel(self):
        # ceil_mode="fixed" must not depend on ax/ay at all -- perturbing the IMU accel must not change its trigger
        # count (unlike ceil_mode="ah", which is defined BY the measured accel and should change).
        s, _ = simulate(SimConfig(seed=2, route=long_route(), vib_base=0.05, vib_per_ms=0.02))
        s2 = s.copy()
        s2["linear_accel_x"] = s2["linear_accel_x"] * 3.0
        s2["linear_accel_y"] = s2["linear_accel_y"] * 3.0
        fixed_a = vehicle_dr.run_pipeline(s, None, params=FIXED_3)["gate_counts"]["turn_ceil"]["accepted"]
        fixed_b = vehicle_dr.run_pipeline(s2, None, params=FIXED_3)["gate_counts"]["turn_ceil"]["accepted"]
        self.assertEqual(fixed_a, fixed_b)
        ah = replace(VDRParams(), use_turn_ceil=True, ceil_mode="ah", ceil_margin=1.0)
        ah_a = vehicle_dr.run_pipeline(s, None, params=ah)["gate_counts"]["turn_ceil"]["accepted"]
        ah_b = vehicle_dr.run_pipeline(s2, None, params=ah)["gate_counts"]["turn_ceil"]["accepted"]
        self.assertNotEqual(ah_a, ah_b)

    def test_never_stationary_or_accel_aided(self):
        # a parked car (all stop) must never trigger the ceiling (excluded by "not stationary").
        s, _ = simulate(SimConfig(seed=1, v0=0.0, route=[("stop", 60.0)]))
        res = vehicle_dr.run_pipeline(s, None, params=FIXED_3)
        self.assertEqual(res["gate_counts"]["turn_ceil"]["accepted"], 0)


if __name__ == "__main__":
    unittest.main()

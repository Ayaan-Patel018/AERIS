"""
test_s1_stationarity_fixes.py — S1: unit-level correctness of the five stationarity-detector fixes (S1a-S1e).

Each mechanism is behind its own flag, default OFF (verified bit-identical to the S0 commit when all are off,
in test_stationarity.py / TestStandstillLog and the vehicle_dr HEAD comparison logged in AERIS_FINDINGS.md).
This file checks the MECHANISMS in isolation (hand-checkable synthetic cases); the sandbox pass/fail criteria
(i)-(iv) for the adopted combination are in test_s1_sandbox_suite.py.
"""
import os
import sys
import unittest
from dataclasses import replace
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import vehicle_dr
from vehicle_dr import VDRParams, _causal_median, _causal_sum


class TestCausalMedian(unittest.TestCase):
    def test_matches_a_hand_computed_window(self):
        x = np.array([1.0, 5.0, 2.0, 8.0, 3.0, 9.0, 4.0])
        out = _causal_median(x, 3)
        # index 0: median([1]) = 1; index 1: median([1,5]) = 3; index 2: median([1,5,2]) = 2; index 3: median([5,2,8]) = 5; ...
        self.assertAlmostEqual(out[0], 1.0); self.assertAlmostEqual(out[1], 3.0); self.assertAlmostEqual(out[2], 2.0)
        self.assertAlmostEqual(out[3], np.median([5, 2, 8])); self.assertAlmostEqual(out[6], np.median([3, 9, 4]))

    def test_causal_never_uses_future_samples(self):
        x = np.arange(50.0)
        out = _causal_median(x, 5)
        x2 = x.copy(); x2[40:] = -1000.0                # change everything AFTER index 39
        out2 = _causal_median(x2, 5)
        self.assertTrue(np.array_equal(out[:40], out2[:40]))   # rows before the change are untouched

    def test_window_longer_than_the_array(self):
        x = np.array([2.0, 4.0, 6.0])
        out = _causal_median(x, 10)
        self.assertAlmostEqual(out[-1], 4.0)             # median of everything seen so far


class TestCausalSum(unittest.TestCase):
    def test_matches_a_hand_computed_window(self):
        x = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
        out = _causal_sum(x, 3)
        self.assertTrue(np.array_equal(out, [1.0, 2.0, 3.0, 3.0, 3.0]))


def _quiet_cruise(n=400, v=9.0, dt=0.1, fix_period_samples=90):
    """A synthetic run with NO IMU signal (all zero) at a constant GNSS-reported speed v: the ideal
    (zero-vibration) version of the smooth-cruise failure. Returns an s_df-like frame via sim_drive's format,
    reusing simulate() with the vibration essentially off so the effect is not seed-dependent."""
    from sim_drive import simulate, SimConfig
    route = [("straight", v * n * dt * 1.2, v, v)]
    return simulate(SimConfig(seed=0, route=route, v0=v, vib_base=0.0, vib_per_ms=0.0, gyro_noise=0.0,
                              accel_bias=(0.0, 0.0), gnss_sigma=0.5, speed_sigma=0.05, course_sigma_deg=0.5))


class TestS1aBrakeGate(unittest.TestCase):
    """S1a: the override may only fire when dv_brake reaches brake_frac x the max filter speed over the last
    brake_window_s. With NO braking (perfectly steady cruise, zero vibration) the override should never fire."""

    def test_override_never_fires_without_braking_evidence(self):
        s, _ = _quiet_cruise()
        base = vehicle_dr.run_pipeline(s, None)
        self.assertGreater(sum(base["stationary"]), 0)                       # the plain detector DOES flag this cruise
        gated = vehicle_dr.run_pipeline(s, None, params=replace(VDRParams(), use_brake_gate=True))
        overrides = [e for e in gated["standstill_log"] if e["via_override"] and not e["via_v_gate"]]
        self.assertEqual(overrides, [])                                      # no braking evidence anywhere -> none of them fire

    def test_a_real_deceleration_still_lets_the_override_fire(self):
        from sim_drive import simulate, SimConfig
        s, _ = simulate(SimConfig(seed=0, route=[("straight", 300.0, 9.0, 0.0), ("stop", 15.0)], v0=9.0,
                                  vib_base=0.0, vib_per_ms=0.0, gyro_noise=0.0, accel_bias=(0.0, 0.0)))
        res = vehicle_dr.run_pipeline(s, None, params=replace(VDRParams(), use_brake_gate=True))
        self.assertGreater(sum(res["stationary"]), 50)                       # the real stop is still caught

    def test_dv_brake_is_purely_from_the_imu_not_the_filter_state(self):
        # two different VDRParams that change the FILTER (turn_noise) must not change the precomputed dv_brake
        s, _ = _quiet_cruise()
        r1 = vehicle_dr.run_pipeline(s, None, params=replace(VDRParams(), use_brake_gate=True, turn_noise=0.5))
        r2 = vehicle_dr.run_pipeline(s, None, params=replace(VDRParams(), use_brake_gate=True, turn_noise=0.05))
        # same standstill flag either way, since with no braking evidence the override never fires regardless of turn_noise
        self.assertEqual(sum(r1["stationary"]), sum(r2["stationary"]))


class TestS1bSelfCalibration(unittest.TestCase):
    """S1b: entry thresholds are learned only from GNSS-confirmed standstills; the fixed thresholds apply until
    self_cal_min_confirm stops are confirmed."""

    def test_bit_identical_to_default_before_two_stops_are_confirmed(self):
        from sim_drive import simulate, SimConfig, default_route          # exactly one real stop
        s, _ = simulate(SimConfig(seed=1, route=default_route()))
        base = vehicle_dr.run_pipeline(s, None)
        s1b = vehicle_dr.run_pipeline(s, None, params=replace(VDRParams(), use_self_cal=True))
        self.assertTrue(np.array_equal(base["stationary"], s1b["stationary"]))   # never reaches min_confirm=2

    def test_learning_activates_after_two_confirmed_stops_and_changes_the_flag(self):
        from sim_drive import simulate, SimConfig, long_route             # three real stops
        s, _ = simulate(SimConfig(seed=1, route=long_route(), vib_base=0.05, vib_per_ms=0.02))
        base = vehicle_dr.run_pipeline(s, None)
        s1b = vehicle_dr.run_pipeline(s, None, params=replace(VDRParams(), use_self_cal=True, self_cal_k=2.0))
        self.assertFalse(np.array_equal(base["stationary"], s1b["stationary"]))
        self.assertLess(sum(s1b["stationary"]), sum(base["stationary"]))     # net effect here: fewer flagged rows

    def test_true_stops_are_still_confirmed_and_recovered(self):
        from sim_drive import simulate, SimConfig, long_route
        s, tr = simulate(SimConfig(seed=1, route=long_route(), vib_base=0.05, vib_per_ms=0.02))
        res = vehicle_dr.run_pipeline(s, None, params=replace(VDRParams(), use_self_cal=True))
        real_stop_rows = tr.stationary.values[1:]
        flagged = np.asarray(res["stationary"])
        recall = np.mean(flagged[real_stop_rows]) if real_stop_rows.any() else float("nan")
        self.assertGreater(recall, 0.5)


class TestS1cAntiCascade(unittest.TestCase):
    """S1c: after a GNSS-contradicted standstill, the v_est < v_gate entry branch is blocked for anticascade_block_s."""

    def test_a_cascading_v_gate_re_entry_is_blocked(self):
        # smooth_cruise_route, seed 2: S1a alone still lets one noise-triggered override through after the real
        # stop, which zeroes v_est and then self-sustains through the (S1a-immune) v_gate branch every fix cycle
        # (see AERIS_FINDINGS.md S1 for the trace). S1c must shorten this a lot.
        from sim_drive import simulate, SimConfig, smooth_cruise_route
        s, _ = simulate(SimConfig(seed=2, route=smooth_cruise_route(), vib_base=0.05, vib_per_ms=0.02))
        plain = vehicle_dr.run_pipeline(s, None, params=replace(VDRParams(), use_brake_gate=True))
        gated = vehicle_dr.run_pipeline(s, None, params=replace(VDRParams(), use_brake_gate=True, use_anticascade=True))
        self.assertLess(sum(gated["stationary"]), sum(plain["stationary"]) * 0.5)

    def test_no_effect_when_there_is_nothing_to_contradict(self):
        from sim_drive import simulate, SimConfig, default_route
        s, _ = simulate(SimConfig(seed=1, route=default_route()))
        base = vehicle_dr.run_pipeline(s, None)
        s1c = vehicle_dr.run_pipeline(s, None, params=replace(VDRParams(), use_anticascade=True))
        # default_route has no false standstill (see AERIS_FINDINGS.md S0 sandbox controls): nothing for S1c to block
        self.assertTrue(np.array_equal(base["stationary"], s1c["stationary"]))


class TestS1dRetroactiveReplay(unittest.TestCase):
    """S1d: on a GNSS-contradicted standstill, the displayed past for that span is corrected."""

    def test_replays_fire_and_close_the_erased_episodes(self):
        s, _ = _quiet_cruise(n=1500)
        res = vehicle_dr.run_pipeline(s, None, params=replace(VDRParams(), use_replay=True))
        self.assertGreater(len(res["replay_log"]), 0)
        for rl in res["replay_log"]:
            self.assertNotIn(rl["i_entry"], [e.get("i_entry") for e in res["standstill_log"]])

    def test_replayed_rows_are_closer_to_truth_than_frozen(self):
        s, tr = _quiet_cruise(n=1500)
        from ins_ekf import latlon_to_enu
        plain = vehicle_dr.run_pipeline(s, None)
        replayed = vehicle_dr.run_pipeline(s, None, params=replace(VDRParams(), use_replay=True))
        lat0, lon0 = plain["lat0"], plain["lon0"]

        def err_at(res, frac):
            k = int(len(res["positions"]) * frac)
            la, lo = res["positions"][k]
            e, n = latlon_to_enu(la, lo, lat0, lon0)[:2]
            te, tn = np.interp(res["timestamps"][k], tr.timestamp_s.values, tr.E.values), np.interp(res["timestamps"][k], tr.timestamp_s.values, tr.N.values)
            return float(np.hypot(e - te, n - tn))
        self.assertLess(err_at(replayed, 0.9), err_at(plain, 0.9))

    def test_inactive_inside_an_outage(self):
        s, _ = _quiet_cruise(n=1500)
        res = vehicle_dr.run_pipeline(s, None, params=replace(VDRParams(), use_replay=True), outage_window=(50.0, 110.0))
        self.assertTrue(all(rl["t"] < 50.0 or rl["t"] > 110.0 for rl in res["replay_log"]))

    def test_disabled_by_default_and_diagnostics_only(self):
        s, _ = _quiet_cruise()
        res = vehicle_dr.run_pipeline(s, None)
        self.assertEqual(res["replay_log"], [])


class TestS1eExitSensitivity(unittest.TestCase):
    """S1e is a grid over the EXISTING w_exit parameter; no new code. A tighter w_exit exits sooner or not at all
    (never later), and moving the current default (0.10) reproduces the pre-S1 filter exactly."""

    def test_w_exit_010_is_bit_identical_to_the_default(self):
        s, _ = self._sim()
        a = vehicle_dr.run_pipeline(s, None)
        b = vehicle_dr.run_pipeline(s, None, params=replace(VDRParams(), w_exit=0.10))
        self.assertTrue(np.array_equal(a["stationary"], b["stationary"]))

    def test_tighter_w_exit_never_increases_flagged_time(self):
        s, _ = self._sim()
        base = sum(vehicle_dr.run_pipeline(s, None)["stationary"])
        tight = sum(vehicle_dr.run_pipeline(s, None, params=replace(VDRParams(), w_exit=0.03))["stationary"])
        self.assertLessEqual(tight, base)

    @staticmethod
    def _sim():
        from sim_drive import simulate, SimConfig, long_route
        return simulate(SimConfig(seed=1, route=long_route(), vib_base=0.05, vib_per_ms=0.02))


if __name__ == "__main__":
    unittest.main()

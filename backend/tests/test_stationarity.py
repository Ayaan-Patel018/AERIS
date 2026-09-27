"""
test_stationarity.py — S0: the stationarity audit (check_outage.stationarity_audit) and the standstill log of vehicle_dr.

The audit compares vehicle_dr's IMU-only standstill flag with the reference (VBOX) motion — SCORING ONLY.
Expected numbers of the synthetic case are worked out by hand in the docstring of `_synthetic` (fixed before the code ran).
Sandbox part: the smooth-cruise route (S1 sandbox criterion i) reproduces the false-standstill failure with the S0 default.
One real-data pin (S3b, skipped when the dataset is absent): the numbers logged in AERIS_FINDINGS.md (S0).
"""
import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dataclasses import replace
import check_outage as co
import vehicle_dr
import window_plan as wp
from sim_drive import simulate, SimConfig, long_route, smooth_cruise_route
from vehicle_dr import VDRParams

# R1 (2026-09-27) adopted ALL (S1a/b/c/d + w_exit 0.05) as the bare VDRParams() default; the S0 audit numbers below
# were logged against the pre-R1 flags-off baseline, so they are pinned explicitly against it here.
OLD_DEFAULT = replace(VDRParams(), use_brake_gate=False, use_self_cal=False, use_anticascade=False,
                      use_replay=False, w_exit=0.10)


def _synthetic():
    """1200 rows on a 0.1 s grid (the filter's result rows start at row 1, so 1199 rows = 119.9 s are scored); the reference drives at 10 m/s
    (yaw rate 0.1 rad/s) except for a true stop in rows 400-599 (40-60 s).
    Filter flag episodes (row ranges, half open):  A [100,150)  5 s at 10 m/s          -> false entry, v_gate branch
                                                   B [420,580) 16 s at rest             -> a true stop
                                                   C [580,630) 2 s at rest + 3 s moving -> late release, override branch
    Hand-computed: scored 119.9 s; flagged 26.0 s; false 5 + 3 = 8.0 s; stopped 20.0 s of which flagged 16 + 2 = 18.0 (recall 0.90);
    distance lost 10 * 8 = 80 m; turning lost 0.1 * 8 = 0.8 rad; moving 99.9 s (path 999 m); missed stop = rows 400-419 = 2.0 s, at a filter speed of 3 m/s = 6 m."""
    n = 1200
    t = np.arange(n) * 0.1
    idx = np.arange(n)
    v = np.where((idx >= 400) & (idx < 600), 0.0, 10.0)
    yaw = np.where(v > 0, 0.1, 0.0)
    truth = co.Truth(t, np.column_stack([np.cumsum(v * 0.1), np.zeros(n)]), v, 0.0, yaw)
    flag = np.zeros(n, bool)
    log = []
    for a, b, gate, over, why in ((100, 150, True, False, "acc_var"), (420, 580, True, False, "omega"), (580, 630, False, True, "release")):
        flag[a:b] = True
        log.append(dict(t_enter=t[a], t_exit=t[b], via_v_gate=gate, via_override=over, exit=why, v_est=0.0, quiet_run=12, acc_var=0.01, w_dev=0.0, gap_prev=1e9))
    res = dict(timestamps=t[1:], stationary=flag[1:], velocities=np.full(n - 1, 3.0), standstill_log=log)
    return res, truth, t


class TestAuditArithmetic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res, cls.truth, cls.t = _synthetic()
        cls.a = co.stationarity_audit(cls.res, cls.truth)

    def test_totals_match_the_hand_computation(self):
        a = self.a
        for key, want in (("time", 119.9), ("moving", 99.9), ("stopped", 20.0), ("flagged", 26.0), ("false", 8.0), ("stopped_flagged", 18.0),
                          ("dist_lost", 80.0), ("turn_lost", 0.8), ("missed", 2.0), ("missed_dist", 6.0), ("path", 999.0)):
            self.assertAlmostEqual(a[key], want, places=6, msg=key)

    def test_recall_and_speed_statistics(self):
        a = self.a
        self.assertAlmostEqual(a["stopped_flagged"] / a["stopped"], 0.9, places=9)
        self.assertAlmostEqual(a["false_v_med"], 10.0); self.assertAlmostEqual(a["false_v_max"], 10.0)
        self.assertAlmostEqual(a["flag_v_max"], 10.0); self.assertAlmostEqual(a["flag_v_med"], 0.0)      # 16 s + 2 s of the 26 s flagged time are at rest

    def test_episodes_are_classified(self):
        eps = {round(e["t_enter"], 1): e for e in self.a["episodes"]}
        A, B, C = eps[10.0], eps[42.0], eps[58.0]
        self.assertEqual((A["kind"], A["branch"], A["exit"]), ("false entry", "v_gate", "acc_var"))
        self.assertAlmostEqual(A["false_s"], 5.0); self.assertAlmostEqual(A["dist_lost"], 50.0); self.assertAlmostEqual(A["v_entry"], 10.0)
        self.assertEqual(B["false_s"], 0.0); self.assertAlmostEqual(B["dur"], 16.0)
        self.assertEqual((C["kind"], C["branch"]), ("late release", "override"))
        self.assertAlmostEqual(C["false_s"], 3.0); self.assertAlmostEqual(C["dur"], 5.0); self.assertAlmostEqual(C["v_entry"], 0.0)
        self.assertEqual((self.a["n_episodes"], self.a["n_false"]), (3, 2))

    def test_episode_time_adds_up_to_the_flagged_time(self):
        self.assertAlmostEqual(sum(e["dur"] for e in self.a["episodes"]), self.a["flagged"], places=9)
        self.assertAlmostEqual(sum(e["false_s"] for e in self.a["episodes"]), self.a["false"], places=9)
        self.assertAlmostEqual(sum(e["dist_lost"] for e in self.a["episodes"]), self.a["dist_lost"], places=9)

    def test_both_branches_true_is_attributed_to_v_gate_and_marked(self):
        res, truth, t = _synthetic()
        res["standstill_log"][2].update(via_v_gate=True, via_override=True)
        eps = {round(e["t_enter"], 1): e for e in co.stationarity_audit(res, truth)["episodes"]}
        self.assertEqual((eps[58.0]["branch"], eps[58.0]["both"]), ("v_gate", True))

    def test_span_restricts_every_quantity(self):
        a = co.stationarity_audit(self.res, self.truth, span=(self.t[100], self.t[199]))       # rows 100-199 = 10 s, episode A only
        self.assertAlmostEqual(a["time"], 10.0); self.assertAlmostEqual(a["flagged"], 5.0); self.assertAlmostEqual(a["false"], 5.0)
        self.assertEqual((a["n_episodes"], a["n_false"]), (1, 1)); self.assertTrue(a["episodes"][0]["in_span"])
        self.assertAlmostEqual(a["dist_lost"], 50.0); self.assertAlmostEqual(a["stopped"], 0.0)

    def test_an_episode_carried_into_the_span_is_marked(self):
        a = co.stationarity_audit(self.res, self.truth, span=(self.t[110], self.t[199]))       # A began at row 100, before the span
        self.assertEqual(a["n_episodes"], 1); self.assertFalse(a["episodes"][0]["in_span"]); self.assertAlmostEqual(a["episodes"][0]["false_s"], 4.0)

    def test_rows_outside_the_reference_file_are_not_scored(self):
        res, _, t = _synthetic()
        tr = co.Truth(t[:600], np.column_stack([t[:600], np.zeros(600)]), np.full(600, 10.0), 0.0, np.zeros(600))    # reference ends at 59.9 s
        a = co.stationarity_audit(res, tr)
        self.assertAlmostEqual(a["time"], 59.9)                       # result rows 1-599 only; the rest would silently reuse the last reference value
        self.assertAlmostEqual(a["flagged"], 5.0 + 16.0 + 2.0)        # A (5 s), B (rows 420-579 = 16 s) and rows 580-599 of C (2 s)
        # the clock offset moves the covered range: reference time = phone time + 30 s, so only phone times up to 29.9 s are covered
        tr2 = co.Truth(t[:600], np.column_stack([t[:600], np.zeros(600)]), np.full(600, 10.0), 30.0, np.zeros(600))
        self.assertAlmostEqual(co.stationarity_audit(res, tr2)["time"], 29.9)

    def test_no_yaw_column_means_zero_turning_lost_not_a_crash(self):
        res, _, t = _synthetic()
        tr = co.Truth(t, np.column_stack([t, np.zeros(len(t))]), np.full(len(t), 10.0), 0.0)
        a = co.stationarity_audit(res, tr)
        self.assertEqual(a["turn_lost"], 0.0)

    def test_report_prints_without_error(self):
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            co.audit_report(self.a, "synthetic")
        out = buf.getvalue()
        self.assertIn("FALSE-standstill time", out); self.assertIn("true-stop recall", out); self.assertIn("late release", out)


class TestStandstillLog(unittest.TestCase):
    """The log added to vehicle_dr is diagnostics only: it must describe the `stationary` flag exactly and change nothing else."""
    @classmethod
    def setUpClass(cls):
        cls.s, cls.tr = simulate(SimConfig(seed=1, route=long_route()))
        cls.res = vehicle_dr.run_pipeline(cls.s, None, outage_window=(200.0, 260.0))

    def test_log_reproduces_the_flag_exactly(self):
        t = np.asarray(self.res["timestamps"]); flag = np.asarray(self.res["stationary"])
        rebuilt = np.zeros(len(t), bool)
        for e in self.res["standstill_log"]:
            rebuilt |= (t >= e["t_enter"]) & ((t <= e["t_exit"]) if e["exit"] == "end" else (t < e["t_exit"]))
        self.assertTrue(np.array_equal(rebuilt, flag))
        self.assertGreaterEqual(len(self.res["standstill_log"]), 3)   # long_route has three real stops

    def test_every_episode_has_a_branch_a_reason_and_is_ordered(self):
        prev = -1e9
        for e in self.res["standstill_log"]:
            self.assertTrue(e["via_v_gate"] or e["via_override"])
            self.assertIn(e["exit"], ("acc_var", "omega", "release", "gnss", "end"))
            self.assertGreaterEqual(e["t_enter"], prev); self.assertGreater(e["t_exit"], e["t_enter"]); prev = e["t_exit"]

    def test_truncated_run_closes_the_open_episode(self):
        t_stop = self.tr.timestamp_s[self.tr.stationary.values].iloc[100]                     # 10 s into the first real stop
        res = vehicle_dr.run_pipeline(self.s, None, t_end=float(t_stop))
        last = res["standstill_log"][-1]
        self.assertEqual(last["exit"], "end"); self.assertTrue(res["stationary"][-1])

    def test_gnss_contradiction_exit_is_logged_with_the_fix_speed(self):
        s = self.s.copy()
        s["linear_accel_x"] = s["linear_accel_x"] * 0.0 + 0.0; s["linear_accel_y"] = s["linear_accel_y"] * 0.0    # perfectly quiet phone: the detector flags the moving car
        s["gyro_yaw_rads"] = 0.0
        res = vehicle_dr.run_pipeline(s, None)
        g = [e for e in res["standstill_log"] if e["exit"] == "gnss"]
        self.assertTrue(g)
        self.assertTrue(all(e["gnss_speed"] > VDRParams().gnss_moving_speed for e in g))


class TestSmoothCruiseSandbox(unittest.TestCase):
    """The S1 sandbox case (i), with the S0 default (no S-variant exists yet): the failure the external study found is reproduced."""
    @classmethod
    def setUpClass(cls):
        cls.s, cls.tr = simulate(SimConfig(seed=1, route=smooth_cruise_route(), vib_base=0.05, vib_per_ms=0.02))
        cls.res = vehicle_dr.run_pipeline(cls.s, None, params=OLD_DEFAULT)
        lat0, lon0 = co.origin(cls.s)
        cls.truth = co.Truth.from_vehicle(cls.tr, lat0, lon0, 0.0)
        cls.a = co.stationarity_audit(cls.res, cls.truth)

    def test_route_has_one_20_s_stop_and_a_steady_9_ms_cruise(self):
        st = self.tr.stationary.values
        self.assertGreaterEqual(st.sum() * 0.1, 19.0)
        v = self.tr.v.values
        self.assertAlmostEqual(float(np.median(v[v > 5])), 9.0, delta=0.3)

    def test_default_detector_flags_the_moving_car_and_the_audit_sees_it(self):
        a = self.a
        self.assertGreater(a["false"], 60.0)                          # observed 162 s (39 % of the moving time); external study: flagged for 160-400 s
        self.assertGreater(a["false_v_med"], 5.0)                     # ... at cruising speed, not creeping
        self.assertGreater(a["dist_lost"], 300.0)
        self.assertGreater(a["stopped_flagged"] / a["stopped"], 0.6)  # the one real stop is still caught

    def test_audit_does_not_change_the_window_scores(self):
        starts = wp.plan_windows(wp.usable_fix_times(self.s), wp.drive_end(self.s, self.tr, 0.0))[::6]
        plain = co.window_benchmark(self.s, self.truth, starts)
        with_audit = co.window_benchmark(self.s, self.truth, starts, audit=True)
        for p, q in zip(plain, with_audit):
            self.assertEqual(p["vdr"]["end_err"], q["vdr"]["end_err"])
            self.assertIn("audit", q); self.assertNotIn("audit", p)
            self.assertLessEqual(q["audit"]["false"], q["audit"]["flagged"] + 1e-9)
            self.assertAlmostEqual(q["audit"]["time"], 60.0, delta=0.15)


class TestRealS3bPin(unittest.TestCase):
    """The S0 numbers logged in AERIS_FINDINGS.md (whole S3b, no outage, S0 default). Skipped when the dataset is not available."""
    def test_s3b_whole_drive(self):
        try:
            s, v, off = co.load_drive("S3b")
        except Exception as ex:                                        # dataset not present on this machine
            self.skipTest(f"S3b not available: {ex}")
        res = vehicle_dr.run_pipeline(s, None, params=OLD_DEFAULT)
        a = co.stationarity_audit(res, co.Truth.from_vehicle(v, res["lat0"], res["lon0"], off))
        self.assertEqual(a["n_episodes"], 13)
        self.assertAlmostEqual(a["flagged"], 47.1, delta=0.15)
        self.assertAlmostEqual(a["false"], 12.1, delta=0.15)
        self.assertEqual(a["n_false"], 5)


if __name__ == "__main__":
    unittest.main()

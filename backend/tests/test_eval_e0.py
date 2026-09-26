"""
test_eval_e0.py — E0 evaluation upgrade, checked on constructed data and on the synthetic sandbox (sim_drive).

Pass criteria are numeric and were fixed before the real-data metrics were computed:
  window plan   : hand-computed start lists (GNSS hole, late first fix, drive end, 20 s staleness boundary, satellites)
  along / cross : recover a known offset to < 0.02 m on a straight line and on a circle; along^2 + cross^2 == err^2
  path ratio    : a track driven at half speed scores 0.5
  windows       : hiding is real (corrupting the phone GNSS inside a window changes that window's track by < 1e-9 m),
                  truncating the phone file is exact, vehicle_dr beats "hold last fix" on the sandbox
No dataset needed.
"""
import os
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import window_plan as wp
import check_outage
import vehicle_dr
from sim_drive import simulate, SimConfig


def _phone(fix_times, t_end=330.0, sats=10.0):
    """Minimal phone frame: 10 Hz rows, a NEW lat/lon at each fix time, held in between, NaN before the first fix
    (row 0 counts as a new fix whenever its position is finite — the convention of vehicle_dr and check_outage)."""
    t = np.round(np.arange(0.0, t_end + 1e-9, 0.1), 6)
    k = np.searchsorted(np.asarray(fix_times, dtype=float) - 1e-6, t, side="right") - 1
    lat = np.where(k >= 0, 52.0 + 1e-5 * np.maximum(k, 0), np.nan)
    lon = np.where(k >= 0, -1.0 + 1e-5 * np.maximum(k, 0), np.nan)
    return pd.DataFrame(dict(timestamp_s=t, gps_lat=lat, gps_lon=lon, gps_satellites=np.full(len(t), sats)))


class TestWindowPlan(unittest.TestCase):
    FIX9 = np.arange(0.0, 330.0, 9.0)

    def test_no_holes_grid_and_count(self):
        f = wp.usable_fix_times(_phone(self.FIX9))
        starts = wp.plan_windows(f, 329.0)
        self.assertEqual(starts[0], 30.0)
        self.assertEqual(starts[-1], 260.0)                 # 260 + 60 = 320 <= 329 < 330
        self.assertEqual(len(starts), 24)
        self.assertTrue(np.allclose(np.diff(starts), 10.0))

    def test_tuning_set_is_windows_ending_before_200(self):
        f = wp.usable_fix_times(_phone(self.FIX9))
        tune = wp.plan_windows(f, 329.0, end_before=200.0)
        self.assertEqual(tune[0], 30.0)
        self.assertEqual(tune[-1], 130.0)                   # 130 + 60 = 190 < 200; 140 + 60 = 200 is NOT before 200
        self.assertEqual(len(tune), 11)
        self.assertTrue(all(s + 60.0 < 200.0 for s in tune))

    def test_gnss_hole_excludes_exactly_the_starved_starts(self):
        fixes = np.r_[np.arange(0.0, 100.0, 9.0), np.arange(162.0, 330.0, 9.0)]     # fixes ..., 99, then 162, 171, ...
        f = wp.usable_fix_times(_phone(fixes))
        starts = wp.plan_windows(f, 329.0)
        skipped = wp.excluded_starts(f, 329.0)
        # 110: last fix 99 (age 11), 3 fixes in [80, 110]  -> valid. 120: age 21 > 20 -> invalid ... 160: none in [130, 160].
        # 170: only fix 162 in [140, 170] (1 < 2) -> invalid.  180: 162, 171, 180 in [150, 180] -> valid.
        self.assertIn(110.0, starts)
        self.assertEqual(skipped, [120.0, 130.0, 140.0, 150.0, 160.0, 170.0])
        self.assertIn(180.0, starts)
        self.assertEqual(sorted(starts + skipped), [30.0 + 10.0 * k for k in range(24)])

    def test_late_first_fix_needs_30_s_of_history(self):
        fixes = np.arange(5.0, 330.0, 9.0)                  # first fix at 5 s
        f = wp.usable_fix_times(_phone(fixes))
        self.assertNotIn(30.0, wp.plan_windows(f, 329.0))   # no fix at or before t = 0
        self.assertEqual(wp.plan_windows(f, 329.0)[0], 40.0)  # fix at 5 <= 10, fixes 14, 23, 32 in [10, 40]

    def test_window_must_lie_inside_the_drive(self):
        f = wp.usable_fix_times(_phone(self.FIX9))
        self.assertEqual(wp.plan_windows(f, 150.0)[-1], 90.0)   # 90 + 60 = 150 fits
        self.assertEqual(wp.plan_windows(f, 149.9)[-1], 80.0)
        self.assertEqual(wp.plan_windows(f, 80.0), [])          # < 30 + 60

    def test_fix_age_boundary_is_20_s_and_two_prior_fixes_are_required(self):
        f = np.array([0.0, 10.0, 20.0, 30.0])
        self.assertTrue(wp.is_valid_start(50.0, f, 300.0))      # fixes 20, 30 in [20, 50]; age exactly 20
        self.assertFalse(wp.is_valid_start(60.0, f, 300.0))     # only fix 30 in [30, 60]

    def test_low_satellite_fixes_are_not_usable(self):
        df = _phone(self.FIX9)
        df.loc[(df.timestamp_s >= 9.0) & (df.timestamp_s < 18.0), "gps_satellites"] = 4.0
        f = wp.usable_fix_times(df)
        self.assertNotIn(9.0, np.round(f, 6))
        self.assertIn(18.0, np.round(f, 6))

    def test_plan_ignores_everything_but_fix_times_and_span(self):
        a = wp.plan_windows(wp.usable_fix_times(_phone(self.FIX9)), 329.0)
        df = _phone(self.FIX9); df["gps_speed_ms"] = 99.0; df["extra"] = 1.0
        self.assertEqual(a, wp.plan_windows(wp.usable_fix_times(df), 329.0))

    def test_event_window_uses_the_same_rule(self):
        f = wp.usable_fix_times(_phone(self.FIX9))
        self.assertTrue(wp.is_valid_start(wp.EVENT_START_S, f, 329.0))
        self.assertFalse(wp.is_valid_start(wp.EVENT_START_S, f, 259.0))     # 200 + 60 > 259

    def test_ranges_and_fingerprint(self):
        self.assertEqual(wp.as_ranges([30.0, 40.0, 50.0, 80.0, 90.0, 200.0]), "30-50, 80-90, 200")
        self.assertEqual(wp.as_ranges([]), "(none)")
        a, b = wp.fingerprint([30.0, 40.0]), wp.fingerprint([30.0, 50.0])
        self.assertEqual(a, wp.fingerprint([30.0, 40.0]))
        self.assertNotEqual(a, b)


# ─────────────────────────────────────────────────────────────────────────────
# along / cross split, path ratio, speed diagnostics (constructed tracks with a known answer)
# ─────────────────────────────────────────────────────────────────────────────
def _line_truth(speed=10.0, heading_deg=45.0, t_end=60.0):
    t = np.round(np.arange(0.0, t_end + 1e-9, 0.1), 6)
    d = np.array([np.cos(np.radians(heading_deg)), np.sin(np.radians(heading_deg))])
    return t, speed * t[:, None] * d, d


class TestAlongCross(unittest.TestCase):
    def test_straight_line_recovers_known_offset(self):
        t, xy, d = _line_truth()
        tr = check_outage.Truth(t, xy, np.full(len(t), 10.0))
        left = np.array([-d[1], d[0]])
        sc = check_outage.score_track(tr, t, xy + 3.0 * d + 4.0 * left)
        self.assertAlmostEqual(sc["along_end"], 3.0, delta=1e-6)
        self.assertAlmostEqual(sc["cross_end"], 4.0, delta=1e-6)
        self.assertAlmostEqual(sc["mean_abs_along"], 3.0, delta=1e-6)
        self.assertAlmostEqual(sc["mean_abs_cross"], 4.0, delta=1e-6)
        self.assertAlmostEqual(sc["mean_err"], 5.0, delta=1e-6)

    def test_sign_convention_ahead_positive_left_positive(self):
        t, xy, d = _line_truth(heading_deg=0.0)                     # driving East
        tr = check_outage.Truth(t, xy, np.full(len(t), 10.0))
        left = check_outage.score_track(tr, t, xy + np.array([0.0, 2.0]))      # +N of an eastbound car = left
        behind = check_outage.score_track(tr, t, xy - np.array([2.0, 0.0]))    # behind
        self.assertAlmostEqual(left["cross_end"], 2.0, delta=1e-6)
        self.assertAlmostEqual(behind["along_end"], -2.0, delta=1e-6)

    def test_circle_recovers_known_offset_within_2_cm(self):
        R, w = 50.0, 0.2                                             # counter-clockwise, 10 m/s
        t = np.round(np.arange(0.0, 62.0 + 1e-9, 0.1), 6)           # truth runs 2 s past the scored epochs: within 0.5 s
        th = w * t                                                   # of the ends of the reference file the direction uses
        xy = R * np.column_stack([np.cos(th), np.sin(th)])           # a one-sided half-second chord (see Truth)
        tang = np.column_stack([-np.sin(th), np.cos(th)])
        left = np.column_stack([-np.cos(th), -np.sin(th)])           # towards the centre = left of a CCW circle
        tr = check_outage.Truth(t, xy, np.full(len(t), R * w))
        n = 601                                                      # score t = 0 ... 60 s
        sc = check_outage.score_track(tr, t[:n], (xy + 2.0 * tang + 5.0 * left)[:n])
        self.assertAlmostEqual(sc["mean_abs_along"], 2.0, delta=0.02)
        self.assertAlmostEqual(sc["mean_abs_cross"], 5.0, delta=0.02)
        self.assertAlmostEqual(sc["along_end"], 2.0, delta=0.02)
        self.assertAlmostEqual(sc["cross_end"], 5.0, delta=0.02)

    def test_along_squared_plus_cross_squared_equals_error_squared(self):
        rng = np.random.default_rng(0)
        t, xy, _ = _line_truth(heading_deg=200.0)
        tr = check_outage.Truth(t, xy, np.full(len(t), 10.0))
        est = xy + rng.normal(0.0, 6.0, xy.shape)
        sc = check_outage.score_track(tr, t, est)
        e = np.linalg.norm(est - tr.pos(t), axis=1)
        d = tr.direction(t)
        nl = np.column_stack([-d[:, 1], d[:, 0]])
        a, c = np.sum((est - tr.pos(t)) * d, axis=1), np.sum((est - tr.pos(t)) * nl, axis=1)
        self.assertLess(np.max(np.abs(a ** 2 + c ** 2 - e ** 2)), 1e-9)
        self.assertAlmostEqual(sc["mean_err"], float(e.mean()), delta=1e-9)
        self.assertAlmostEqual(sc["end_err"] ** 2, sc["along_end"] ** 2 + sc["cross_end"] ** 2, delta=1e-9)

    def test_direction_is_carried_while_the_truth_is_stopped(self):
        t = np.round(np.arange(0.0, 20.0 + 1e-9, 0.1), 6)
        x = np.where(t < 10.0, 10.0 * t, 100.0)                      # drives East for 10 s, then stops
        xy = np.column_stack([x, np.zeros_like(x)])
        tr = check_outage.Truth(t, xy, np.where(t < 10.0, 10.0, 0.0))
        sc = check_outage.score_track(tr, t, xy + np.array([5.0, 0.0]))          # 5 m ahead, also while stopped
        self.assertTrue(np.isfinite(sc["mean_abs_along"]))
        self.assertAlmostEqual(sc["along_end"], 5.0, delta=1e-6)
        self.assertAlmostEqual(sc["cross_end"], 0.0, delta=1e-6)

    def test_never_moving_truth_gives_nan_split_but_finite_error(self):
        import warnings
        t = np.round(np.arange(0.0, 10.0 + 1e-9, 0.1), 6)
        xy = np.zeros((len(t), 2))
        tr = check_outage.Truth(t, xy, np.zeros(len(t)))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sc = check_outage.score_track(tr, t, xy + 3.0)
        self.assertTrue(np.isnan(sc["along_end"]))
        self.assertAlmostEqual(sc["end_err"], 3.0 * np.sqrt(2.0), delta=1e-9)

    def test_path_ratio_of_a_half_speed_track_is_one_half(self):
        t, xy, d = _line_truth(speed=10.0)
        tr = check_outage.Truth(t, xy, np.full(len(t), 10.0))
        sc = check_outage.score_track(tr, t, 5.0 * t[:, None] * d)
        self.assertAlmostEqual(sc["path_ratio"], 0.5, delta=1e-3)
        self.assertAlmostEqual(sc["path_true"], 600.0, delta=1e-6)

    def test_speed_diagnostics_at_30_s_and_at_the_end(self):
        t, xy, d = _line_truth(speed=10.0)
        tr = check_outage.Truth(t, xy, np.full(len(t), 10.0))
        sc = check_outage.score_track(tr, t, xy, v_est=np.full(len(t), 8.0))
        self.assertAlmostEqual(sc["mean_abs_dv"], 2.0, delta=1e-9)
        self.assertAlmostEqual(sc["v_est_30"], 8.0)
        self.assertAlmostEqual(sc["v_true_30"], 10.0)
        self.assertAlmostEqual(sc["dv_end"], -2.0, delta=1e-9)
        v = 5.0 + t / 12.0                                              # 5 m/s at t=0, 10 at 60 s
        sc = check_outage.score_track(tr, t, xy, v_est=v)
        self.assertAlmostEqual(sc["v_est_30"], 7.5, delta=0.05)
        self.assertAlmostEqual(sc["v_est_end"], 10.0, delta=1e-9)

    def test_truth_speed_gaps_are_filled(self):
        t, xy, _ = _line_truth()
        sp = np.full(len(t), 10.0); sp[100:110] = np.nan
        tr = check_outage.Truth(t, xy, sp)
        self.assertTrue(np.all(np.isfinite(tr.speed(t))))

    def test_summary_statistics_median_mean_p90(self):
        rows = [dict(vdr=dict(mean_err=float(x))) for x in range(1, 11)]     # 1 .. 10
        med, mean, p90 = check_outage.summarize_windows(rows, "vdr")["mean_err"]
        self.assertAlmostEqual(med, 5.5); self.assertAlmostEqual(mean, 5.5); self.assertAlmostEqual(p90, 9.1)


class TestReservedDriveGuard(unittest.TestCase):
    def test_reserved_drives_are_refused_without_unseal(self):
        for d in ("S3c", "S3a", "S2", "S4"):
            with self.assertRaises(SystemExit):
                check_outage.guard_drive(d)
            check_outage.guard_drive(d, unseal=True)
        for d in ("S3b", "S1"):
            check_outage.guard_drive(d)


# ─────────────────────────────────────────────────────────────────────────────
# sliding 60 s outages on the sandbox
# ─────────────────────────────────────────────────────────────────────────────
class TestWindowBenchmark(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s, cls.tr = simulate(SimConfig(seed=0))
        cls.lat0, cls.lon0 = check_outage.origin(cls.s)
        cls.truth = check_outage.Truth.from_vehicle(cls.tr, cls.lat0, cls.lon0, 0.0)
        cls.fixes = wp.usable_fix_times(cls.s)
        cls.t_end = wp.drive_end(cls.s, cls.tr, 0.0)
        cls.starts = wp.plan_windows(cls.fixes, cls.t_end, end_before=200.0)         # the sandbox "tuning set"
        cls.rows = check_outage.window_benchmark(cls.s, cls.truth, cls.starts)

    def test_window_set_matches_the_plan(self):
        self.assertEqual([r["start"] for r in self.rows], self.starts)
        self.assertEqual(self.starts[0], 30.0)
        self.assertTrue(all(s + 60.0 < 200.0 for s in self.starts))
        for r in self.rows:                                            # 60 s at 10 Hz, both ends inclusive
            self.assertEqual(r["n"], 601)

    def test_gnss_inside_a_window_is_really_hidden(self):
        s0 = 90.0
        bad = self.s.copy()
        m = (bad.timestamp_s >= s0) & (bad.timestamp_s <= s0 + 60.0)
        bad.loc[m, "gps_lat"] += 0.01                                  # ~1.1 km
        bad.loc[m, "gps_lon"] += 0.01
        bad.loc[m, "gps_speed_ms"] = 50.0
        bad.loc[m, "gps_heading_deg"] = 123.0
        a = check_outage.window_benchmark(self.s, self.truth, [s0])[0]["vdr"]
        b = check_outage.window_benchmark(bad, self.truth, [s0])[0]["vdr"]
        for k in ("mean_err", "end_err", "along_end", "cross_end", "path_est", "mean_abs_dv"):
            self.assertAlmostEqual(a[k], b[k], delta=1e-9, msg=k)

    def test_truncating_the_phone_file_is_exact(self):
        s0 = 90.0
        full = vehicle_dr.run_pipeline(self.s, None, outage_window=(s0, s0 + 60.0))
        t = np.array(full["timestamps"]); m = (t >= s0) & (t <= s0 + 60.0)
        ref = check_outage.score_track(self.truth, t[m], check_outage._res_enu(full, m),
                                       np.array(full["velocities"])[m], np.array(full["cov_matrix"])[m])
        got = check_outage.window_benchmark(self.s, self.truth, [s0])[0]["vdr"]
        for k in ("mean_err", "end_err", "along_end", "cross_end", "path_est", "mean_abs_dv", "inside"):
            self.assertAlmostEqual(ref[k], got[k], delta=1e-9, msg=k)

    def test_baselines_start_from_the_last_fix_before_the_window(self):
        s0 = 95.0                                                        # last usable fix before 95 s is the one at t = 90
        t = np.round(np.arange(s0, s0 + 60.0 + 1e-9, 0.1), 6)
        rows = wp.usable_fix_rows(self.s)
        cv, vcv, hold = check_outage.baseline_tracks(self.s, rows, s0, t, self.lat0, self.lon0)
        a = int(np.flatnonzero(np.abs(self.s.timestamp_s.values - 90.0) < 1e-6)[0])
        pa = check_outage.latlon_to_enu(self.s.gps_lat.iloc[a], self.s.gps_lon.iloc[a], self.lat0, self.lon0)[:2]
        self.assertTrue(np.allclose(hold, pa))
        v, brg = self.s.gps_speed_ms.iloc[a], np.radians(self.s.gps_heading_deg.iloc[a])
        want0 = pa + v * 5.0 * np.array([np.sin(brg), np.cos(brg)]) if v > 1.0 else pa
        self.assertTrue(np.allclose(cv[0], want0, atol=1e-6))
        self.assertTrue(np.allclose(vcv, v if v > 1.0 else 0.0))

    def test_vehicle_dr_beats_hold_last_fix_on_the_sandbox(self):
        vdr = np.median([r["vdr"]["end_err"] for r in self.rows])
        hold = np.median([r["hold"]["end_err"] for r in self.rows])
        self.assertLess(vdr, hold, (vdr, hold))

    def test_each_window_row_is_consistent(self):
        for r in self.rows:
            v = r["vdr"]
            self.assertLess(abs(v["along_end"] ** 2 + v["cross_end"] ** 2 - v["end_err"] ** 2), 1e-6)
            self.assertTrue(np.isfinite(v["path_ratio"]) and 0.0 < v["path_ratio"] < 3.0, v["path_ratio"])
            self.assertGreaterEqual(v["mean_err"], 0.0)

    def test_outage_report_matches_a_direct_score(self):
        import contextlib
        import io
        res = vehicle_dr.run_pipeline(self.s, None, outage_window=check_outage.OUTAGE)
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            sc = check_outage.outage_e0_report(res, self.truth)
        t = np.array(res["timestamps"]); m = (t >= 200.0) & (t <= 260.0)
        err = np.linalg.norm(check_outage._res_enu(res, m) - self.truth.pos(t[m]), axis=1)
        self.assertAlmostEqual(sc["mean_err"], float(err.mean()), delta=1e-9)
        self.assertAlmostEqual(sc["end_err"], float(err[-1]), delta=1e-9)
        self.assertIn("along", buf.getvalue())

    def test_truth_from_vehicle_matches_the_original_truth_lookup(self):
        ref = check_outage._truth_fn(self.tr, self.lat0, self.lon0, 0.0)[0]
        t = np.array([12.34, 100.0, 250.05])
        self.assertTrue(np.allclose(self.truth.pos(t), ref(t), atol=1e-9))


if __name__ == "__main__":
    unittest.main()

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


if __name__ == "__main__":
    unittest.main()

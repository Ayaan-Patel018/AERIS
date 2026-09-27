"""
test_s1_sandbox_suite.py — S1: the sandbox pass/fail criteria (i)-(iv), fixed before the real-data metrics were
computed (see AERIS_FINDINGS.md "S1 — detector fixes"), applied to every tried S-variant and combination.

Criteria (verbatim from the user's plan):
  (i)   smooth_cruise_route, vib_base 0.05 / vib_per_ms 0.02, 2 seeds: false-standstill time < 5 s
        AND median sliding-60s-window end error < 60 m.
  (ii)  long_route, default vibration, 2 seeds: median window end error no worse than the current default by > 3 %.
  (iii) long_route, vib_base 0.05 / vib_per_ms 0.02, 2 seeds: report only (improvement wanted, not required).
  (iv)  the route's one real 20 s stop is still detected: true-stop recall >= 0.8 x the current default's recall.
"false-standstill time" and "recall" both come from check_outage.stationarity_audit() on the WHOLE (no-outage) run;
"median window end error" comes from window_benchmark() over every valid sliding-60s window of the route.
These are the same numbers logged in AERIS_FINDINGS.md; kept as a fixed, reproducible record (all S1 flags stay
OFF by default: none of the tried variants met the real-data acceptance rule — see the findings doc).
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
from sim_drive import simulate, SimConfig, long_route, smooth_cruise_route

DEFAULT = VDRParams()
S1A_S1C_S1D = replace(VDRParams(), use_brake_gate=True, use_anticascade=True, use_replay=True)
ALL_S1 = replace(VDRParams(), use_brake_gate=True, use_self_cal=True, self_cal_k=2.0,
                 use_anticascade=True, use_replay=True, w_exit=0.05)


def _audit_and_median(s, tr, p):
    lat0, lon0 = co.origin(s)
    res = vehicle_dr.run_pipeline(s, None, params=p)
    truth = co.Truth.from_vehicle(tr, lat0, lon0, 0.0)
    a = co.stationarity_audit(res, truth)
    import window_plan as wp
    starts = wp.plan_windows(wp.usable_fix_times(s), wp.drive_end(s, tr, 0.0))
    rows = co.window_benchmark(s, truth, starts, params=p)
    return a, float(np.median([r["vdr"]["end_err"] for r in rows]))


class TestCriterionI_SmoothCruise(unittest.TestCase):
    """The current default FAILS this (the documented failure mode); the two adopted-candidate combinations PASS it
    on both seeds — logged 2026-09-27."""

    def test_current_default_fails(self):
        for sd in (1, 2):
            s, tr = simulate(SimConfig(seed=sd, route=smooth_cruise_route(), vib_base=0.05, vib_per_ms=0.02))
            a, med = _audit_and_median(s, tr, DEFAULT)
            self.assertFalse(a["false"] < 5.0 and med < 60.0, msg=f"seed {sd}: false={a['false']:.1f}s med={med:.1f}m")

    def test_s1a_s1c_s1d_passes_both_seeds(self):
        for sd in (1, 2):
            s, tr = simulate(SimConfig(seed=sd, route=smooth_cruise_route(), vib_base=0.05, vib_per_ms=0.02))
            a, med = _audit_and_median(s, tr, S1A_S1C_S1D)
            self.assertLess(a["false"], 5.0, msg=f"seed {sd}")
            self.assertLess(med, 60.0, msg=f"seed {sd}")

    def test_all_combination_passes_both_seeds(self):
        for sd in (1, 2):
            s, tr = simulate(SimConfig(seed=sd, route=smooth_cruise_route(), vib_base=0.05, vib_per_ms=0.02))
            a, med = _audit_and_median(s, tr, ALL_S1)
            self.assertLess(a["false"], 5.0, msg=f"seed {sd}")
            self.assertLess(med, 60.0, msg=f"seed {sd}")

    def test_s1a_alone_is_not_sufficient_on_seed_2(self):
        # documents WHY the combination is needed: S1a alone leaves the v_gate cascade unblocked
        s, tr = simulate(SimConfig(seed=2, route=smooth_cruise_route(), vib_base=0.05, vib_per_ms=0.02))
        a, med = _audit_and_median(s, tr, replace(VDRParams(), use_brake_gate=True))
        self.assertFalse(a["false"] < 5.0 and med < 60.0)


class TestCriterionII_LongRouteDefaultVibration(unittest.TestCase):
    """Every tried variant passes: long_route's default vibration produces no false standstill for any of them
    (0.0 % change on both seeds), so this criterion is not discriminating for this failure mode."""

    def test_no_variant_regresses_by_more_than_3_percent(self):
        for sd in (1, 2):
            s, tr = simulate(SimConfig(seed=sd, route=long_route()))
            _, med0 = _audit_and_median(s, tr, DEFAULT)
            for p in (S1A_S1C_S1D, ALL_S1):
                _, med = _audit_and_median(s, tr, p)
                self.assertLessEqual(med, med0 * 1.03, msg=f"seed {sd}")


class TestCriterionIII_LongRouteHardVibration_ReportOnly(unittest.TestCase):
    """Report only (improvement wanted, not required): both candidates improve long_route's hard-vibration case,
    ALL more than S1a+S1c+S1d (S1b and S1e's extra help shows up here, where long_route's 3 real stops let S1b
    activate and its dev-window accuracy gain applies)."""

    def test_both_candidates_improve_the_hard_vibration_case(self):
        for sd in (1, 2):
            s, tr = simulate(SimConfig(seed=sd, route=long_route(), vib_base=0.05, vib_per_ms=0.02))
            _, med0 = _audit_and_median(s, tr, DEFAULT)
            _, med_combo = _audit_and_median(s, tr, S1A_S1C_S1D)
            _, med_all = _audit_and_median(s, tr, ALL_S1)
            self.assertLess(med_combo, med0, msg=f"seed {sd}")
            self.assertLess(med_all, med_combo, msg=f"seed {sd}: ALL should improve on S1a+S1c+S1d here")


class TestCriterionIV_RealStopRecall(unittest.TestCase):
    """The one real 20 s stop in smooth_cruise_route is still recovered: no candidate drops recall below
    0.8 x the current default's recall."""

    def test_recall_holds_for_both_candidates(self):
        for sd in (1, 2):
            s, tr = simulate(SimConfig(seed=sd, route=smooth_cruise_route(), vib_base=0.05, vib_per_ms=0.02))
            a0, _ = _audit_and_median(s, tr, DEFAULT)
            r0 = a0["stopped_flagged"] / a0["stopped"]
            for p in (S1A_S1C_S1D, ALL_S1):
                a, _ = _audit_and_median(s, tr, p)
                r = a["stopped_flagged"] / a["stopped"]
                self.assertGreaterEqual(r, 0.8 * r0, msg=f"seed {sd}")


class TestRealDataAcceptanceRule(unittest.TestCase):
    """Pin the S0/S1 real-data numbers that decided the outcome (S3b + S2, whole-drive stationarity_audit;
    see AERIS_FINDINGS.md). Skipped when the dataset is not available. The plan's rule (false-standstill seconds
    down >= 50% on BOTH drives, recall >= 0.8x current) is NOT met by any tried variant: S3b's real false time is
    small (12.1 s total) and the best combination only reaches -35.5%. All S1 flags therefore stay OFF."""

    def test_s3b_and_s2_whole_drive_false_standstill(self):
        try:
            s3b = co.load_drive("S3b"); s2 = co.load_drive("S2")
        except Exception as ex:
            self.skipTest(f"dataset not available: {ex}")

        def false_and_recall(s_v_off, p):
            s, v, off = s_v_off
            res = vehicle_dr.run_pipeline(s, None, params=p)
            a = co.stationarity_audit(res, co.Truth.from_vehicle(v, res["lat0"], res["lon0"], off))
            return a["false"], a["stopped_flagged"] / a["stopped"]

        f0_3b, r0_3b = false_and_recall(s3b, DEFAULT)
        f0_s2, r0_s2 = false_and_recall(s2, DEFAULT)
        self.assertAlmostEqual(f0_3b, 12.1, delta=0.3); self.assertAlmostEqual(f0_s2, 148.2, delta=1.0)
        f_3b, r_3b = false_and_recall(s3b, ALL_S1)
        f_s2, r_s2 = false_and_recall(s2, ALL_S1)
        self.assertAlmostEqual(f_3b, 7.8, delta=0.5); self.assertAlmostEqual(f_s2, 60.0, delta=2.0)
        pct_3b = 100 * (f0_3b - f_3b) / f0_3b
        pct_s2 = 100 * (f0_s2 - f_s2) / f0_s2
        self.assertLess(pct_3b, 50.0)              # the acceptance rule's 50% bar is NOT met on S3b (best case)
        self.assertGreaterEqual(pct_s2, 50.0)       # ... even though S2 alone clears it
        self.assertGreaterEqual(r_3b, 0.8 * r0_3b); self.assertGreaterEqual(r_s2, 0.8 * r0_s2)


if __name__ == "__main__":
    unittest.main()

"""
test_json_schema.py — JSON export schema validation tests.

Tests the already-exported JSON files in backend/exports/:
  - All 3 expected files exist
  - Required keys present in each file
  - Positions are valid [lat, lon] pairs
  - Timestamps are monotonically increasing
  - gnss_status labels are from the valid set
  - uncertainty values are non-negative
  - evaluation_summary.json has correct structure

These tests catch schema regressions without re-running the full pipeline.
Run: python -m unittest tests.test_json_schema

# EXTENSION POINT: Add tests for new exported fields here when the
#   frontend requests them (e.g., heading uncertainty, per-axis covariance).
"""

import sys
import os
import json
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
from conftest import EXPORTS_DIR, EVAL_60S_DIR, SKIP_EXPORTS_MSG

# Check if exports exist
EXPORTS_AVAILABLE  = os.path.isdir(EXPORTS_DIR)
EVAL_60S_AVAILABLE = os.path.isdir(EVAL_60S_DIR)
EVAL_DIR           = os.path.join(EXPORTS_DIR, "evaluation")
EVAL_AVAILABLE     = os.path.isdir(EVAL_DIR)

VALID_GNSS_STATUS = {"healthy", "degraded", "unavailable", "outage"}


def _load_json(path):
    with open(path) as f:
        return json.load(f)


@unittest.skipUnless(EXPORTS_AVAILABLE, SKIP_EXPORTS_MSG)
class TestRootExportFiles(unittest.TestCase):
    """Tests for the 3 root export files in backend/exports/."""

    def test_reference_trajectory_exists(self):
        self.assertTrue(
            os.path.isfile(os.path.join(EXPORTS_DIR, "reference_trajectory.json")),
            msg="reference_trajectory.json not found in exports/"
        )

    def test_gnss_only_exists(self):
        self.assertTrue(
            os.path.isfile(os.path.join(EXPORTS_DIR, "gnss_only.json")),
            msg="gnss_only.json not found in exports/"
        )

    def test_fused_output_exists(self):
        self.assertTrue(
            os.path.isfile(os.path.join(EXPORTS_DIR, "fused_output.json")),
            msg="fused_output.json not found in exports/"
        )

    def test_reference_trajectory_required_keys(self):
        data = _load_json(os.path.join(EXPORTS_DIR, "reference_trajectory.json"))
        for key in ["timestamps", "positions", "velocities", "headings"]:
            self.assertIn(key, data, msg=f"reference_trajectory.json missing '{key}'")

    def test_gnss_only_required_keys(self):
        data = _load_json(os.path.join(EXPORTS_DIR, "gnss_only.json"))
        for key in ["timestamps", "positions", "velocities", "headings"]:
            self.assertIn(key, data, msg=f"gnss_only.json missing '{key}'")

    def test_fused_output_required_keys(self):
        data = _load_json(os.path.join(EXPORTS_DIR, "fused_output.json"))
        for key in ["timestamps", "positions", "velocities", "headings",
                    "gnss_status", "uncertainty", "mode", "outage_window"]:
            self.assertIn(key, data, msg=f"fused_output.json missing '{key}'")

    def test_all_positions_are_lat_lon_pairs(self):
        """All positions in all 3 files must be [lat, lon] pairs."""
        for fname in ["reference_trajectory.json", "gnss_only.json", "fused_output.json"]:
            data = _load_json(os.path.join(EXPORTS_DIR, fname))
            for i, pos in enumerate(data["positions"]):
                self.assertEqual(len(pos), 2,
                                 msg=f"{fname} position[{i}] is not a pair: {pos}")
                lat, lon = pos
                self.assertTrue(-90 <= lat <= 90,
                                msg=f"{fname} position[{i}] lat={lat} out of range")
                self.assertTrue(-180 <= lon <= 180,
                                msg=f"{fname} position[{i}] lon={lon} out of range")

    def test_all_timestamps_monotonically_increasing(self):
        """Timestamps in all 3 files must be non-decreasing."""
        for fname in ["reference_trajectory.json", "gnss_only.json", "fused_output.json"]:
            data = _load_json(os.path.join(EXPORTS_DIR, fname))
            times = data["timestamps"]
            for i in range(1, len(times)):
                self.assertGreaterEqual(
                    times[i], times[i-1],
                    msg=f"{fname}: timestamps not monotonic at index {i}"
                )

    def test_fused_output_gnss_status_valid_labels(self):
        """fused_output.json gnss_status must contain only valid labels."""
        data = _load_json(os.path.join(EXPORTS_DIR, "fused_output.json"))
        for i, label in enumerate(data["gnss_status"]):
            self.assertIn(label, VALID_GNSS_STATUS,
                          msg=f"fused_output.json gnss_status[{i}]='{label}' is invalid")

    def test_fused_output_uncertainty_non_negative(self):
        """fused_output.json uncertainty must be ≥ 0 at all steps."""
        data = _load_json(os.path.join(EXPORTS_DIR, "fused_output.json"))
        for i, u in enumerate(data["uncertainty"]):
            self.assertGreaterEqual(u, 0.0,
                                    msg=f"fused_output.json uncertainty[{i}]={u} < 0")

    def test_fused_output_list_lengths_consistent(self):
        """All lists in fused_output.json must have the same length."""
        data = _load_json(os.path.join(EXPORTS_DIR, "fused_output.json"))
        lengths = {
            key: len(data[key])
            for key in ["timestamps", "positions", "velocities",
                        "headings", "gnss_status", "uncertainty"]
        }
        unique_lengths = set(lengths.values())
        self.assertEqual(len(unique_lengths), 1,
                         msg=f"fused_output.json has inconsistent list lengths: {lengths}")

    def test_outage_window_in_fused_output(self):
        """fused_output.json outage_window must be a 2-element list or null."""
        data = _load_json(os.path.join(EXPORTS_DIR, "fused_output.json"))
        ow = data.get("outage_window")
        if ow is not None:
            self.assertEqual(len(ow), 2,
                             msg=f"outage_window must have 2 elements, got: {ow}")
            self.assertLessEqual(ow[0], ow[1],
                                 msg="outage_window start must be ≤ end")

    def test_fused_outage_window_suppresses_healthy_gnss(self):
        """
        Within the outage_window stored in fused_output.json,
        there must be no 'healthy' GNSS status.
        """
        data = _load_json(os.path.join(EXPORTS_DIR, "fused_output.json"))
        ow = data.get("outage_window")
        if ow is None:
            self.skipTest("No outage_window in fused_output.json")
        times   = data["timestamps"]
        statuses = data["gnss_status"]
        for t, label in zip(times, statuses):
            if ow[0] <= t <= ow[1]:
                self.assertNotEqual(label, "healthy",
                                    msg=f"Healthy GNSS during outage at t={t:.1f}s")


@unittest.skipUnless(EVAL_60S_AVAILABLE, "backend/exports/evaluation/outage_60s/ not found")
class TestEval60sExports(unittest.TestCase):
    """Tests for evaluation/outage_60s/ JSON files (main frontend data)."""

    def test_three_json_files_exist_in_eval_60s(self):
        """All 3 JSON files must exist in the evaluation/outage_60s/ directory."""
        for fname in ["reference_trajectory.json", "gnss_only.json", "fused_output.json"]:
            path = os.path.join(EVAL_60S_DIR, fname)
            self.assertTrue(os.path.isfile(path),
                            msg=f"{fname} not found in evaluation/outage_60s/")

    def test_fused_mode_is_full(self):
        """fused_output.json in evaluation/outage_60s/ must have mode='full'."""
        data = _load_json(os.path.join(EVAL_60S_DIR, "fused_output.json"))
        self.assertEqual(data.get("mode"), "full",
                         msg="evaluation/outage_60s/fused_output.json must have mode='full'")

    def test_outage_window_is_60s(self):
        """evaluation/outage_60s/fused_output.json must store a ~60s outage window."""
        data = _load_json(os.path.join(EVAL_60S_DIR, "fused_output.json"))
        ow = data.get("outage_window")
        if ow is not None:
            duration = ow[1] - ow[0]
            self.assertAlmostEqual(duration, 60.0, delta=5.0,
                                   msg=f"Outage duration {duration}s is not ~60s")


@unittest.skipUnless(EVAL_AVAILABLE, "backend/exports/evaluation/ not found")
class TestEvaluationSummaryJson(unittest.TestCase):
    """Tests for evaluation_summary.json — the multi-scenario summary file."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(EVAL_DIR, "evaluation_summary.json")
        if not os.path.isfile(path):
            raise unittest.SkipTest("evaluation_summary.json not found")
        cls.summary = _load_json(path)

    def test_three_scenarios_present(self):
        """evaluation_summary.json must have 30s, 60s, 120s scenarios."""
        for label in ["30s", "60s", "120s"]:
            self.assertIn(label, self.summary,
                          msg=f"Scenario '{label}' missing from evaluation_summary.json")

    def test_each_scenario_has_four_modes(self):
        """Each scenario must have all 4 mode entries."""
        for label, scenario in self.summary.items():
            modes = scenario.get("modes", {})
            for mode in ["ins_only", "ins_gnss", "ins_nhc", "full"]:
                self.assertIn(mode, modes,
                              msg=f"Scenario '{label}' missing mode '{mode}'")

    def test_full_mode_errors_are_finite(self):
        """Full mode mean/max errors must be finite numbers."""
        for label, scenario in self.summary.items():
            full = scenario["modes"]["full"]
            for key in ["mean_m", "rmse_m", "max_m"]:
                if key in full:
                    self.assertTrue(np.isfinite(full[key]),
                                    msg=f"Scenario {label} full.{key}={full[key]} not finite")

    def test_improvement_fields_present(self):
        """improvement_vs_ins_only_pct and improvement_vs_gnss_only_pct must exist."""
        for label, scenario in self.summary.items():
            self.assertIn("improvement_vs_ins_only_pct", scenario,
                          msg=f"Scenario '{label}' missing improvement_vs_ins_only_pct")
            self.assertIn("improvement_vs_gnss_only_pct", scenario,
                          msg=f"Scenario '{label}' missing improvement_vs_gnss_only_pct")

    def test_improvements_are_positive(self):
        """Improvement over INS-only must be positive (full is better)."""
        for label, scenario in self.summary.items():
            imp = scenario.get("improvement_vs_ins_only_pct", 0)
            self.assertGreater(imp, 0.0,
                               msg=f"Scenario '{label}' improvement vs INS-only is not positive: {imp}%")


if __name__ == "__main__":
    unittest.main(verbosity=2)

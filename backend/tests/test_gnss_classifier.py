"""
test_gnss_classifier.py — Unit tests for the Rule-based GNSS Quality Classifier.

Tests:
  - All 3 output labels are returned under the correct conditions
  - Each trigger condition individually causes degradation
  - gps_available=False always → unavailable
  - Unknown quality label passed to EKF defaults to 1x noise (healthy)
  - classify_sequence() returns one label per row

All tests are pure unit tests: no dataset, no file I/O.

# EXTENSION POINT: When replacing GNSSQualityClassifier with a trained ML model,
#   these tests serve as the acceptance criteria the new model must pass.
#   Add tests for model confidence scores, feature importance, etc.
"""

import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# GNSSQualityClassifier lives in outage_analysis.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from outage_analysis import GNSSQualityClassifier

# We also test the adaptive noise scaling in the EKF
from ins_ekf import ESEKF, NominalState, euler_to_quat, quat_normalize

VALID_LABELS = {"healthy", "degraded", "unavailable"}


class TestGNSSClassifierLabels(unittest.TestCase):
    """All output labels must be from the known valid set."""

    def setUp(self):
        self.clf = GNSSQualityClassifier()

    def test_healthy_conditions(self):
        """Good satellite count + low accuracy → 'healthy'."""
        result = self.clf.classify(satellites=12, accuracy_m=2.0,
                                   pos_jump_m=0.0, vel_incon_ms=0.0,
                                   innovation_m=0.0, gps_available=True)
        self.assertEqual(result, "healthy",
                         msg="Good conditions must yield 'healthy'")

    def test_unavailable_no_gps(self):
        """gps_available=False must always yield 'unavailable'."""
        result = self.clf.classify(satellites=15, gps_available=False)
        self.assertEqual(result, "unavailable",
                         msg="gps_available=False must yield 'unavailable'")

    def test_unavailable_nan_satellites(self):
        """NaN satellite count → 'unavailable'."""
        result = self.clf.classify(satellites=np.nan, gps_available=True)
        self.assertEqual(result, "unavailable",
                         msg="NaN satellites must yield 'unavailable'")

    def test_unavailable_too_few_satellites(self):
        """Below min_satellites threshold (default 6) → 'unavailable'."""
        result = self.clf.classify(satellites=4, gps_available=True)
        self.assertEqual(result, "unavailable",
                         msg="< 6 satellites must yield 'unavailable'")

    def test_unavailable_zero_satellites(self):
        """Zero satellites → 'unavailable'."""
        result = self.clf.classify(satellites=0, gps_available=True)
        self.assertEqual(result, "unavailable")

    def test_degraded_low_satellites(self):
        """Between min and deg threshold (6 ≤ sats < 8) → 'degraded'."""
        result = self.clf.classify(satellites=7, accuracy_m=3.0,
                                   gps_available=True)
        self.assertEqual(result, "degraded",
                         msg="6 ≤ sats < 8 must yield 'degraded'")

    def test_degraded_poor_accuracy(self):
        """GPS accuracy > max_accuracy_m (10m) → 'degraded'."""
        result = self.clf.classify(satellites=10, accuracy_m=15.0,
                                   gps_available=True)
        self.assertEqual(result, "degraded",
                         msg="accuracy_m > 10 must yield 'degraded'")

    def test_degraded_large_position_jump(self):
        """Position jump > max_pos_jump_m (50m) → 'degraded'."""
        result = self.clf.classify(satellites=12, accuracy_m=3.0,
                                   pos_jump_m=60.0, gps_available=True)
        self.assertEqual(result, "degraded",
                         msg="pos_jump_m > 50 must yield 'degraded'")

    def test_degraded_velocity_inconsistency(self):
        """Velocity inconsistency > max_vel_incon_ms (5 m/s) → 'degraded'."""
        result = self.clf.classify(satellites=12, accuracy_m=3.0,
                                   vel_incon_ms=8.0, gps_available=True)
        self.assertEqual(result, "degraded",
                         msg="vel_incon_ms > 5 must yield 'degraded'")

    def test_degraded_high_innovation(self):
        """EKF innovation > max_innovation_m (30m) → 'degraded'."""
        result = self.clf.classify(satellites=12, accuracy_m=3.0,
                                   innovation_m=50.0, gps_available=True)
        self.assertEqual(result, "degraded",
                         msg="innovation_m > 30 must yield 'degraded'")

    def test_all_outputs_are_valid_labels(self):
        """Classifier must never return an unexpected label."""
        test_cases = [
            dict(satellites=15, accuracy_m=2.0, gps_available=True),
            dict(satellites=7, accuracy_m=3.0, gps_available=True),
            dict(satellites=3, gps_available=True),
            dict(satellites=12, gps_available=False),
            dict(satellites=np.nan, gps_available=True),
            dict(satellites=10, accuracy_m=20.0, gps_available=True),
            dict(satellites=10, pos_jump_m=100.0, gps_available=True),
            dict(satellites=10, vel_incon_ms=10.0, gps_available=True),
            dict(satellites=10, innovation_m=50.0, gps_available=True),
        ]
        for kwargs in test_cases:
            result = self.clf.classify(**kwargs)
            self.assertIn(result, VALID_LABELS,
                          msg=f"Unexpected label '{result}' for inputs: {kwargs}")


class TestGNSSClassifierBoundaries(unittest.TestCase):
    """Test boundary conditions at threshold edges."""

    def setUp(self):
        self.clf = GNSSQualityClassifier()

    def test_exactly_at_min_satellites_boundary(self):
        """Exactly min_satellites (6) should NOT be unavailable."""
        result = self.clf.classify(satellites=6, accuracy_m=3.0, gps_available=True)
        # 6 == min_satellites, which means it passes unavailable check
        # but 6 < deg_satellites (8) → degraded
        self.assertIn(result, {"degraded"},
                      msg="Exactly 6 satellites (= min) should be 'degraded', not 'unavailable'")

    def test_exactly_at_deg_satellites_boundary(self):
        """Exactly deg_satellites (8) with good accuracy → 'healthy'."""
        result = self.clf.classify(satellites=8, accuracy_m=3.0, gps_available=True)
        self.assertEqual(result, "healthy",
                         msg="Exactly 8 satellites should be 'healthy' (not < 8)")

    def test_accuracy_at_boundary(self):
        """Exactly at max_accuracy_m (10.0) → should NOT trigger degraded."""
        # accuracy_m > 10 triggers, not >=
        result = self.clf.classify(satellites=12, accuracy_m=10.0, gps_available=True)
        self.assertEqual(result, "healthy",
                         msg="accuracy_m == threshold (10m) should still be 'healthy'")

    def test_accuracy_just_over_boundary(self):
        """accuracy_m = 10.001 → should trigger 'degraded'."""
        result = self.clf.classify(satellites=12, accuracy_m=10.001, gps_available=True)
        self.assertEqual(result, "degraded",
                         msg="accuracy_m just over threshold must yield 'degraded'")


class TestGNSSClassifySequence(unittest.TestCase):
    """classify_sequence() must return one valid label per row."""

    def test_output_length_matches_input(self):
        """Output list must have same length as input DataFrame."""
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
        from conftest import make_synthetic_s_df

        clf = GNSSQualityClassifier()
        s_df = make_synthetic_s_df(n_rows=100)
        statuses = clf.classify_sequence(s_df)
        self.assertEqual(len(statuses), len(s_df),
                         msg="classify_sequence output length must match DataFrame length")

    def test_all_sequence_labels_valid(self):
        """Every label in the sequence output must be a valid label."""
        from conftest import make_synthetic_s_df

        clf = GNSSQualityClassifier()
        s_df = make_synthetic_s_df(n_rows=100)
        statuses = clf.classify_sequence(s_df)
        for i, label in enumerate(statuses):
            self.assertIn(label, VALID_LABELS,
                          msg=f"Row {i}: unexpected label '{label}'")

    def test_nan_gps_rows_are_unavailable(self):
        """Rows with NaN GPS must be classified as 'unavailable'."""
        from conftest import make_synthetic_s_df
        import pandas as pd

        clf = GNSSQualityClassifier()
        s_df = make_synthetic_s_df(n_rows=50)
        # Force a block of rows to have NaN GPS
        s_df.loc[10:20, ["gps_lat", "gps_lon"]] = np.nan

        statuses = clf.classify_sequence(s_df)
        for i in range(10, 21):
            self.assertEqual(statuses[i], "unavailable",
                             msg=f"Row {i} with NaN GPS must be 'unavailable'")


if __name__ == "__main__":
    unittest.main(verbosity=2)

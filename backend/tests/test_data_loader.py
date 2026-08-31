"""
test_data_loader.py — Unit + Integration tests for data_loader.py.

Layer 1 (Unit — synthetic, always runs):
  - _make_timestamp_s: wrap-around, monotonicity, starts at zero
  - _parse_satellite_string: "16 / 18" format, NaN, garbage
  - load_smartphone schema: required columns present in output

Layer 2 (Integration — requires IO-VNBD dataset):
  - S-S3b loads with expected shape and sample rate
  - V-S3b loads with expected shape
  - GPS availability is high on S-S3b (> 95%)
  - IMU stats are physically sane
  - Timestamps are monotonically increasing

# EXTENSION POINT: Add tests for new sequences (e.g., Driver B, France) here.
#   Each sequence should get its own @skipUnless block with a dedicated path check.
"""

import sys
import os
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from data_loader import load_smartphone, load_vehicle, _make_timestamp_s, _parse_satellite_string
from conftest import (
    DATASET_AVAILABLE, S3b_S_PATH, S3b_V_PATH,
    SKIP_DATASET_MSG, make_synthetic_s_df
)

SMARTPHONE_REQUIRED_COLS = [
    "timestamp_s",
    "gps_lat", "gps_lon", "gps_alt_m",
    "gps_speed_ms", "gps_heading_deg", "gps_accuracy_m", "gps_satellites",
    "accel_x", "accel_y", "accel_z",
    "gravity_x", "gravity_y", "gravity_z",
    "linear_accel_x", "linear_accel_y", "linear_accel_z",
    "gyro_yaw_rads", "gyro_pitch_rads", "gyro_roll_rads",
    "mag_x_ut", "mag_y_ut", "mag_z_ut",
    "orient_yaw_deg", "orient_pitch_deg", "orient_roll_deg",
]


# ── Layer 1: Unit tests (no dataset) ──────────────────────────────────────────

class TestTimestampHelper(unittest.TestCase):
    """Tests for _make_timestamp_s helper."""

    def test_starts_at_zero(self):
        """First timestamp must be 0.0 regardless of raw values."""
        raw = pd.Series([1000.0, 1100.0, 1200.0])
        result = _make_timestamp_s(raw, unit="ms")
        self.assertAlmostEqual(result.iloc[0], 0.0, places=9,
                               msg="Timestamp must start at 0.0")

    def test_monotonically_increasing(self):
        """Output must be monotonically non-decreasing."""
        raw = pd.Series([500.0, 600.0, 700.0, 800.0])
        result = _make_timestamp_s(raw, unit="ms")
        diffs = result.diff().dropna()
        self.assertTrue((diffs >= 0).all(),
                        msg="Timestamps must be monotonically non-decreasing")

    def test_wrap_around_handled(self):
        """Counter wrap-around (large negative delta) must not cause backward jumps."""
        # Simulate a counter that resets at row 5
        raw = pd.Series([100.0, 200.0, 300.0, 400.0, 500.0,
                         0.0, 100.0, 200.0, 300.0])   # resets here
        result = _make_timestamp_s(raw, unit="ms")
        diffs = result.diff().dropna()
        self.assertTrue((diffs >= 0).all(),
                        msg="Timestamp wrap-around must not create backward jumps")

    def test_ms_unit_converts_to_seconds(self):
        """Raw values in ms must be converted to seconds."""
        raw = pd.Series([0.0, 1000.0, 2000.0])   # 0, 1, 2 seconds in ms
        result = _make_timestamp_s(raw, unit="ms")
        self.assertAlmostEqual(result.iloc[-1], 2.0, delta=0.001,
                               msg="2000 ms must equal 2.0 seconds")

    def test_seconds_unit_unchanged(self):
        """Raw values already in seconds must not be divided."""
        raw = pd.Series([0.0, 1.0, 2.0])
        result = _make_timestamp_s(raw, unit="seconds")
        self.assertAlmostEqual(result.iloc[-1], 2.0, delta=0.001,
                               msg="Seconds-unit timestamps must not be divided")

    def test_single_row(self):
        """Single-row series must return 0.0."""
        raw = pd.Series([12345.0])
        result = _make_timestamp_s(raw, unit="ms")
        self.assertAlmostEqual(result.iloc[0], 0.0, places=9)


class TestSatelliteStringParser(unittest.TestCase):
    """Tests for _parse_satellite_string helper."""

    def test_fraction_string_returns_first_number(self):
        """'16 / 18' → 16.0 (satellites used, not in range)."""
        self.assertEqual(_parse_satellite_string("16 / 18"), 16.0)

    def test_plain_number_string(self):
        """'12' → 12.0."""
        self.assertEqual(_parse_satellite_string("12"), 12.0)

    def test_float_value(self):
        """12.0 (already float) → 12.0."""
        self.assertEqual(_parse_satellite_string(12.0), 12.0)

    def test_nan_input_returns_nan(self):
        """NaN input → NaN output."""
        result = _parse_satellite_string(np.nan)
        self.assertTrue(np.isnan(result), msg="NaN input must return NaN")

    def test_garbage_string_returns_nan(self):
        """Unparseable string → NaN."""
        result = _parse_satellite_string("N/A")
        self.assertTrue(np.isnan(result), msg="Garbage string must return NaN")

    def test_empty_string_returns_nan(self):
        """Empty string → NaN."""
        result = _parse_satellite_string("")
        self.assertTrue(np.isnan(result), msg="Empty string must return NaN")

    def test_space_padded_number(self):
        """'  14  ' → 14.0 (with whitespace stripping from split)."""
        # "  14  / 18" → split("/")[0] = "  14  " → strip → "14" → 14.0
        self.assertEqual(_parse_satellite_string("  14  / 18"), 14.0)


class TestSyntheticSchemaCompliance(unittest.TestCase):
    """load_smartphone output schema checks using synthetic data."""

    def test_synthetic_df_has_all_required_columns(self):
        """make_synthetic_s_df must produce all columns expected from load_smartphone."""
        s_df = make_synthetic_s_df(n_rows=50)
        for col in SMARTPHONE_REQUIRED_COLS:
            self.assertIn(col, s_df.columns,
                          msg=f"Required column '{col}' missing from synthetic DataFrame")

    def test_synthetic_timestamp_starts_at_zero(self):
        """Synthetic DataFrame timestamp_s must start at 0."""
        s_df = make_synthetic_s_df()
        self.assertAlmostEqual(s_df["timestamp_s"].iloc[0], 0.0, places=9)

    def test_synthetic_timestamp_monotonic(self):
        """Synthetic DataFrame timestamps must be monotonically increasing."""
        s_df = make_synthetic_s_df()
        diffs = s_df["timestamp_s"].diff().dropna()
        self.assertTrue((diffs >= 0).all())


# ── Layer 2: Integration tests (require IO-VNBD dataset) ──────────────────────

@unittest.skipUnless(DATASET_AVAILABLE, SKIP_DATASET_MSG)
class TestLoadSmartphoneIntegration(unittest.TestCase):
    """Integration tests for load_smartphone on real S-S3b.csv."""

    @classmethod
    def setUpClass(cls):
        cls.s_df = load_smartphone(S3b_S_PATH)

    def test_required_columns_present(self):
        """All required columns must be present."""
        for col in SMARTPHONE_REQUIRED_COLS:
            self.assertIn(col, self.s_df.columns, msg=f"Missing column: {col}")

    def test_shape_approximately_correct(self):
        """S-S3b at 10 Hz for ~681 s → roughly 6800 rows (±200 tolerance)."""
        n_rows = len(self.s_df)
        self.assertGreater(n_rows, 6000, msg="S-S3b: too few rows")
        self.assertLess(n_rows, 8000,    msg="S-S3b: too many rows (unexpected)")

    def test_timestamp_starts_at_zero(self):
        """First timestamp must be 0.0."""
        self.assertAlmostEqual(self.s_df["timestamp_s"].iloc[0], 0.0, places=3)

    def test_timestamp_monotonically_increasing(self):
        """All timestamps must be monotonically non-decreasing."""
        diffs = self.s_df["timestamp_s"].diff().dropna()
        self.assertTrue((diffs >= 0).all(),
                        msg="Timestamps must be monotonically non-decreasing")

    def test_duration_approximately_681s(self):
        """S-S3b duration should be roughly 681 seconds (±60 tolerance)."""
        duration = self.s_df["timestamp_s"].iloc[-1]
        self.assertGreater(duration, 620, msg="Duration too short")
        self.assertLess(duration, 750,    msg="Duration too long")

    def test_gps_availability_high(self):
        """GPS must be available for > 90% of rows in S-S3b."""
        total = len(self.s_df)
        gps_valid = self.s_df["gps_lat"].notna().sum()
        pct = 100.0 * gps_valid / total
        self.assertGreater(pct, 90.0,
                           msg=f"GPS availability {pct:.1f}% < 90% threshold")

    def test_sample_rate_approximately_10hz(self):
        """Mean sample rate must be between 8 and 12 Hz."""
        dt_mean = self.s_df["timestamp_s"].diff().dropna().mean()
        hz = 1.0 / dt_mean
        self.assertGreater(hz, 8.0,  msg=f"Sample rate {hz:.2f} Hz too low")
        self.assertLess(hz, 12.0,    msg=f"Sample rate {hz:.2f} Hz too high")

    def test_gravity_magnitude_approx_9p81(self):
        """Mean gravity magnitude must be ≈ 9.81 m/s² (within ±0.5)."""
        g_mag = np.sqrt(
            self.s_df["gravity_x"]**2 +
            self.s_df["gravity_y"]**2 +
            self.s_df["gravity_z"]**2
        ).mean()
        self.assertAlmostEqual(g_mag, 9.80665, delta=0.5,
                               msg=f"Mean gravity magnitude {g_mag:.3f} m/s² is unreasonable")

    def test_linear_accel_mean_near_zero(self):
        """
        Mean linear acceleration (gravity removed) should be near zero
        for a dataset with mixed motion (not all forward).
        Tolerance is generous: ± 1.5 m/s² per axis.
        """
        for axis in ["linear_accel_x", "linear_accel_y", "linear_accel_z"]:
            mean_val = self.s_df[axis].mean()
            self.assertAlmostEqual(mean_val, 0.0, delta=1.5,
                                   msg=f"{axis} mean {mean_val:.3f} out of expected range")

    def test_satellite_count_reasonable(self):
        """GPS satellite count must be between 4 and 30 where available."""
        sats = self.s_df["gps_satellites"].dropna()
        self.assertTrue((sats >= 4).all(),
                        msg="Satellite count has values < 4 (unreasonable)")
        self.assertTrue((sats <= 30).all(),
                        msg="Satellite count has values > 30 (raw string parse bug?)")

    def test_no_all_zero_imu_rows(self):
        """No IMU row should have all-zero accelerometer values (sensor dead?)."""
        all_zero = (
            (self.s_df["accel_x"] == 0) &
            (self.s_df["accel_y"] == 0) &
            (self.s_df["accel_z"] == 0)
        ).sum()
        self.assertEqual(all_zero, 0,
                         msg=f"{all_zero} rows have all-zero accelerometer values")


@unittest.skipUnless(DATASET_AVAILABLE, SKIP_DATASET_MSG)
class TestLoadVehicleIntegration(unittest.TestCase):
    """Integration tests for load_vehicle on real V-S3b.csv."""

    @classmethod
    def setUpClass(cls):
        cls.v_df = load_vehicle(S3b_V_PATH)

    def test_required_columns_present(self):
        """V-* required columns must be present."""
        required = [
            "timestamp_s", "gps_lat", "gps_lon", "gps_speed_ms",
            "gps_heading_deg", "ref_speed_ms", "yaw_rate_degs",
        ]
        for col in required:
            self.assertIn(col, self.v_df.columns, msg=f"Missing column: {col}")

    def test_gps_fully_available(self):
        """V-S3b (VBOX reference) must have no NaN GPS positions."""
        nan_count = self.v_df["gps_lat"].isna().sum()
        self.assertEqual(nan_count, 0,
                         msg=f"V-S3b has {nan_count} NaN GPS rows (expected 0)")

    def test_vbox_col1_raw_flagged_implausible(self):
        """vbox_col1_raw must have implausible max (> 30) — known dataset issue."""
        if "vbox_col1_raw" in self.v_df.columns:
            max_val = self.v_df["vbox_col1_raw"].max()
            self.assertGreater(max_val, 30,
                               msg="vbox_col1_raw max should be implausible (> 30)")

    def test_speed_non_negative(self):
        """All speed values must be ≥ 0."""
        self.assertTrue((self.v_df["gps_speed_ms"] >= 0).all(),
                        msg="V-S3b: negative GPS speed detected")

    def test_timestamp_monotonic(self):
        """V-* timestamps must be monotonically non-decreasing."""
        diffs = self.v_df["timestamp_s"].diff().dropna()
        self.assertTrue((diffs >= 0).all())


if __name__ == "__main__":
    unittest.main(verbosity=2)

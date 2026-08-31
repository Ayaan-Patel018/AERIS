"""
conftest.py — Shared fixtures for the IDRS backend test suite.

Provides:
  - Synthetic DataFrames (no dataset required for unit tests)
  - DATASET_AVAILABLE flag (skips integration tests gracefully)
  - Dataset path constants
"""

import os
import numpy as np
import pandas as pd

# ── dataset availability ──────────────────────────────────────────────────────
# tests/ → backend/ → project_root/ → GNN and RAG/ (where IO-VNBD lives)
_REPO_ROOT   = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DATASET_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

S3b_BASE = os.path.join(
    _DATASET_ROOT, "IO-VNBD", "Synchronised V abd S datasets",
    "Categorised IOVNB Dataset", "S (Driver A)", "S3b"
)
S1_BASE = os.path.join(
    _DATASET_ROOT, "IO-VNBD", "Synchronised V abd S datasets",
    "Categorised IOVNB Dataset", "S (Driver A)", "S1"
)

S3b_S_PATH = os.path.join(S3b_BASE, "S-S3b.csv")
S3b_V_PATH = os.path.join(S3b_BASE, "V-S3b.csv")
S1_S_PATH  = os.path.join(S1_BASE,  "S-S1.csv")
S1_V_PATH  = os.path.join(S1_BASE,  "V-S1.csv")

DATASET_AVAILABLE = os.path.isfile(S3b_S_PATH) and os.path.isfile(S3b_V_PATH)
S1_AVAILABLE      = os.path.isfile(S1_S_PATH)  and os.path.isfile(S1_V_PATH)

EXPORTS_DIR = os.path.join(_REPO_ROOT, "backend", "exports")
EVAL_60S_DIR = os.path.join(EXPORTS_DIR, "evaluation", "outage_60s")
EXPORTS_AVAILABLE = os.path.isdir(EXPORTS_DIR)

SKIP_DATASET_MSG = "IO-VNBD dataset not found — skipping integration test"
SKIP_S1_MSG      = "IO-VNBD S1 sequence not found — skipping S1 validation test"
SKIP_EXPORTS_MSG = "backend/exports/ not found — run outage_analysis.py first"


# ── synthetic DataFrame factories ─────────────────────────────────────────────

def make_synthetic_s_df(n_rows: int = 200,
                        lat0: float = 52.3696,
                        lon0: float = -1.2993,
                        dt: float = 0.1) -> pd.DataFrame:
    """
    Build a minimal synthetic smartphone DataFrame that matches
    load_smartphone() output schema exactly.

    The vehicle moves forward at ~10 m/s on a straight heading.
    IMU contains realistic-order-of-magnitude values (not zeros).
    GPS updates every 10 rows (1 Hz rate at 10 Hz IMU).
    """
    np.random.seed(42)
    t = np.arange(n_rows) * dt

    # GPS: update every 10 rows (1 Hz), interpolate between
    R_earth = 6_371_000.0
    speed_ms = 10.0
    lat_arr = np.full(n_rows, np.nan)
    lon_arr = np.full(n_rows, np.nan)
    sat_arr = np.full(n_rows, np.nan)
    acc_arr = np.full(n_rows, np.nan)
    spd_arr = np.full(n_rows, np.nan)
    hdg_arr = np.full(n_rows, np.nan)
    alt_arr = np.full(n_rows, np.nan)

    for i in range(0, n_rows, 10):
        elapsed = t[i]
        dlat = (speed_ms * elapsed) / R_earth * (180 / np.pi)
        lat_arr[i] = lat0 + dlat
        lon_arr[i] = lon0
        sat_arr[i] = 12.0
        acc_arr[i] = 3.0
        spd_arr[i] = speed_ms
        hdg_arr[i] = 0.0   # heading North
        alt_arr[i] = 100.0

    # IMU: small forward acceleration + gravity already subtracted
    linear_accel_x = np.random.normal(0.0,  0.05, n_rows)
    linear_accel_y = np.random.normal(0.0,  0.05, n_rows)
    linear_accel_z = np.random.normal(0.0,  0.02, n_rows)

    gravity_x = np.full(n_rows, 0.0)
    gravity_y = np.full(n_rows, 0.0)
    gravity_z = np.full(n_rows, 9.80665)

    gyro_yaw_rads   = np.random.normal(0.0, 0.001, n_rows)
    gyro_pitch_rads = np.random.normal(0.0, 0.001, n_rows)
    gyro_roll_rads  = np.random.normal(0.0, 0.001, n_rows)

    return pd.DataFrame({
        "timestamp_s":      t,
        "gps_lat":          lat_arr,
        "gps_lon":          lon_arr,
        "gps_alt_m":        alt_arr,
        "gps_speed_ms":     spd_arr,
        "gps_heading_deg":  hdg_arr,
        "gps_accuracy_m":   acc_arr,
        "gps_satellites":   sat_arr,
        "accel_x":          linear_accel_x + gravity_x,
        "accel_y":          linear_accel_y + gravity_y,
        "accel_z":          linear_accel_z + gravity_z,
        "gravity_x":        gravity_x,
        "gravity_y":        gravity_y,
        "gravity_z":        gravity_z,
        "linear_accel_x":   linear_accel_x,
        "linear_accel_y":   linear_accel_y,
        "linear_accel_z":   linear_accel_z,
        "gyro_yaw_rads":    gyro_yaw_rads,
        "gyro_pitch_rads":  gyro_pitch_rads,
        "gyro_roll_rads":   gyro_roll_rads,
        "mag_x_ut":         np.random.normal(20.0, 1.0, n_rows),
        "mag_y_ut":         np.random.normal(-5.0, 1.0, n_rows),
        "mag_z_ut":         np.random.normal(40.0, 1.0, n_rows),
        "orient_yaw_deg":   np.zeros(n_rows),
        "orient_pitch_deg": np.zeros(n_rows),
        "orient_roll_deg":  np.zeros(n_rows),
    })


def make_synthetic_v_df(n_rows: int = 200,
                        lat0: float = 52.3696,
                        lon0: float = -1.2993,
                        dt: float = 0.1) -> pd.DataFrame:
    """
    Build a minimal synthetic VBOX reference DataFrame matching
    load_vehicle() output schema.
    """
    np.random.seed(43)
    t = np.arange(n_rows) * dt

    R_earth = 6_371_000.0
    speed_ms = 10.0
    dlat = (speed_ms * t) / R_earth * (180 / np.pi)

    return pd.DataFrame({
        "timestamp_s":      t,
        "gps_lat":          lat0 + dlat,
        "gps_lon":          np.full(n_rows, lon0),
        "gps_alt_km":       np.full(n_rows, 0.1),
        "gps_speed_ms":     np.full(n_rows, speed_ms),
        "gps_heading_deg":  np.full(n_rows, 0.0),
        "ref_speed_ms":     np.full(n_rows, speed_ms),
        "vert_vel_ms":      np.zeros(n_rows),
        "long_accel_ms2":   np.zeros(n_rows),
        "lat_accel_ms2":    np.zeros(n_rows),
        "yaw_rate_degs":    np.zeros(n_rows),
        "ws_fl_rads":       np.full(n_rows, 5.0),
        "ws_fr_rads":       np.full(n_rows, 5.0),
        "ws_rl_rads":       np.full(n_rows, 5.0),
        "ws_rr_rads":       np.full(n_rows, 5.0),
        "vbox_col1_raw":    np.full(n_rows, 10.0),
    })

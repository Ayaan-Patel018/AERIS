"""
data_loader.py — IO-VNBD dataset loader for SIH 26168
Part I of the backend pipeline.

Confirmed against real S-S3b.csv and V-S3b.csv before writing.
See docs/DATASET.md for the full column reference and terminology decisions.

Usage:
    from data_loader import load_smartphone, load_vehicle, inspect, plot_raw_trajectory

    s_df = load_smartphone("path/to/S-S3b.csv")
    v_df = load_vehicle("path/to/V-S3b.csv")
    inspect(s_df, label="S-S3b")
    inspect(v_df, label="V-S3b")
    plot_raw_trajectory(s_df, v_df)
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ── constants ────────────────────────────────────────────────────────────────
G_TO_MS2 = 9.80665   # 1 g in m/s²
KMH_TO_MS = 1 / 3.6  # km/h to m/s


# ── helpers ──────────────────────────────────────────────────────────────────
def _parse_satellite_string(val):
    """
    S-* GPS SATELLITES IN RANGE is a string like '16 / 18'.
    We keep only the first number (satellites used for fix).
    Returns NaN if unparseable.
    """
    try:
        return float(str(val).split("/")[0].strip())
    except (ValueError, AttributeError):
        return np.nan


def _make_timestamp_s(raw_series, unit):
    """
    Convert a raw timestamp column to a canonical timestamp_s:
    float seconds, monotonically increasing, starting at 0.

    Handles counter wrap-around / resets by using cumulative sum
    of absolute forward deltas instead of simple subtraction from first value.

    unit: 'seconds' for V-* (time since start of day)
          'ms'      for S-* (time since start of sequence in milliseconds)
    """
    if unit == "ms":
        t = raw_series.astype(float) / 1000.0  # ms → s
    else:
        t = raw_series.astype(float)

    # Build monotonic timestamps from forward deltas only
    # This handles wrap-around: if delta is negative (counter reset),
    # treat it as a very small forward step (0) rather than a backward jump
    deltas = t.diff().fillna(0)
    deltas = deltas.clip(lower=0)  # discard negative jumps (resets/wrap)
    timestamp_s = deltas.cumsum()
    return timestamp_s


# ── smartphone loader (S-* files) ────────────────────────────────────────────
def load_smartphone(path: str) -> pd.DataFrame:
    """
    Load an S-* CSV file (AndroSensor, ~10 Hz IMU / 1 Hz GPS).
    Returns a clean DataFrame with:
      - canonical timestamp_s column (seconds from sequence start)
      - linear_accel_x/y/z (m/s²) = accelerometer - gravity
      - all other columns in SI units
    Raw column names are preserved with a 'raw_' prefix where transformed.
    """
    df = pd.read_csv(path, skipinitialspace=True, encoding="latin-1")

    # Strip whitespace from column names (CSV headers sometimes have spaces)
    df.columns = df.columns.str.strip()

    # ── timestamp ────────────────────────────────────────────────────────────
    df["timestamp_s"] = _make_timestamp_s(df["TIME SINCE START (ms)"], unit="ms")

    # ── GPS ──────────────────────────────────────────────────────────────────
    df.rename(columns={
        "GPS LATITUDE (degrees)":    "gps_lat",
        "GPS LONGITUDE (degrees)":   "gps_lon",
        "GPS ALTITUDE (m)":          "gps_alt_m",
        "GPS ACCURACY (m)":          "gps_accuracy_m",
        "GPS ORIENTATION (Â°)":      "gps_heading_deg",
    }, inplace=True)

    # GPS speed: km/h → m/s
    df["gps_speed_ms"] = df["GPS SPEED (Kmh)"] * KMH_TO_MS

    # Satellite count: parse "16 / 18" → 16.0
    df["gps_satellites"] = df["GPS SATELLITES IN RANGE"].apply(_parse_satellite_string)

    # ── IMU ──────────────────────────────────────────────────────────────────
    # Accelerometer (includes gravity — subtract gravity component)
    df["accel_x"] = df["ACCELEROMETER X (m/s²)"]
    df["accel_y"] = df["ACCELEROMETER Y (m/s²)"]
    df["accel_z"] = df["ACCELEROMETER Z (m/s²)"]

    df["gravity_x"] = df["GRAVITY X (m/s²)"]
    df["gravity_y"] = df["GRAVITY Y (m/s²)"]
    df["gravity_z"] = df["GRAVITY Z (m/s²)"]

    # Linear acceleration (gravity removed) — ready for INS
    df["linear_accel_x"] = df["accel_x"] - df["gravity_x"]
    df["linear_accel_y"] = df["accel_y"] - df["gravity_y"]
    df["linear_accel_z"] = df["accel_z"] - df["gravity_z"]

    # Gyroscope — confirmed axis order: Yaw, Pitch, Roll
    df.rename(columns={
        "GYROSCOPE Yaw (rad/s)":   "gyro_yaw_rads",
        "GYROSCOPE Pitch (rad/s)": "gyro_pitch_rads",
        "GYROSCOPE Roll (rad/s)":  "gyro_roll_rads",
    }, inplace=True)

    # Magnetometer
    df.rename(columns={
        "MAGNETIC FIELD X (Î¼T)": "mag_x_ut",
        "MAGNETIC FIELD Y (Î¼T)": "mag_y_ut",
        "MAGNETIC FIELD Z (Î¼T)": "mag_z_ut",
    }, inplace=True)

    # Orientation (from AndroSensor — useful for alignment, not INS input)
    df.rename(columns={
        "ORIENTATION (Yaw) (Â°)":   "orient_yaw_deg",
        "ORIENTATION (Pitch) (Â°)": "orient_pitch_deg",
        "ORIENTATION (Roll ) (Â°)": "orient_roll_deg",
    }, inplace=True)

    # ── select and order final columns ───────────────────────────────────────
    keep = [
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
    return df[keep].reset_index(drop=True)


# ── vehicle/VBOX loader (V-* files) ──────────────────────────────────────────
def load_vehicle(path: str) -> pd.DataFrame:
    """
    Load a V-* CSV file (Racelogic VBOX, 10 Hz, 29 columns).
    Returns a clean DataFrame with:
      - canonical timestamp_s column (seconds from sequence start)
      - all velocities in m/s (converted from km/h)
      - all accelerations in m/s² (converted from g)
    This is the REFERENCE TRAJECTORY — not ground truth.
    See docs/DATASET.md for the terminology decision.
    """
    df = pd.read_csv(path, skipinitialspace=True, encoding="latin-1")
    df.columns = df.columns.str.strip()

    # ── timestamp ────────────────────────────────────────────────────────────
    raw_ts_col = "Time Since Start of Day (seconds)"
    df["timestamp_s"] = _make_timestamp_s(df[raw_ts_col], unit="seconds")

    # ── GPS / position ───────────────────────────────────────────────────────
    df.rename(columns={
        "Latitude (degrees)":  "gps_lat",
        "Longitude (degrees)": "gps_lon",
        "Height (km)":         "gps_alt_km",
        "Heading (degrees)":   "gps_heading_deg",
    }, inplace=True)

    # NOTE: 'No of GPS Satellites Available' column shows implausible values
    # (max 137) in V-S3b — likely a column-order mismatch vs the paper's table.
    # We keep the raw column for now but do NOT rename it to gps_satellites
    # to avoid propagating bad data. Investigate with: df.head() in a notebook.
    if "No of GPS Satellites Available" in df.columns:
        df["vbox_col1_raw"] = df["No of GPS Satellites Available"]

    # Velocity: km/h → m/s
    df["gps_speed_ms"]    = df["Velocity (km/hr)"]         * KMH_TO_MS
    df["ref_speed_ms"]    = df["Indicated Vehicle Speed (km/hr)"] * KMH_TO_MS
    df["vert_vel_ms"]     = df["Vertical velocity (km/hr)"] * KMH_TO_MS

    # ── IMU / dynamics ───────────────────────────────────────────────────────
    # Accelerations: g → m/s²
    df["long_accel_ms2"]  = df["Indicated Longitudinal Acceleration (g)"] * G_TO_MS2
    df["lat_accel_ms2"]   = df["Indicated Lateral Acceleration (g)"]      * G_TO_MS2

    # Yaw rate stays in deg/s (will convert to rad/s when fusing if needed)
    df.rename(columns={"Yaw Rate (deg/sec)": "yaw_rate_degs"}, inplace=True)

    # Wheel speeds (rad/s) — useful for odometry / sanity check
    df.rename(columns={
        "Wheel Speed Front Left (rad/sec)":  "ws_fl_rads",
        "Wheel Speed Front Right (rad/sec)": "ws_fr_rads",
        "Wheel Speed Rear Left (rad/sec)":   "ws_rl_rads",
        "Wheel Speed Rear Right (rad/sec)":  "ws_rr_rads",
    }, inplace=True)

    # ── select and order final columns ───────────────────────────────────────
    keep = [
        "timestamp_s",
        "gps_lat", "gps_lon", "gps_alt_km",
        "gps_speed_ms", "gps_heading_deg",
        "ref_speed_ms", "vert_vel_ms",
        "long_accel_ms2", "lat_accel_ms2",
        "yaw_rate_degs",
        "ws_fl_rads", "ws_fr_rads", "ws_rl_rads", "ws_rr_rads",
        "vbox_col1_raw",
    ]
    return df[keep].reset_index(drop=True)


# ── inspection ───────────────────────────────────────────────────────────────
def inspect(df: pd.DataFrame, label: str = "DataFrame") -> None:
    """
    Print key statistics for a loaded dataframe.
    Satisfies Part I completion criteria.
    """
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Shape:          {df.shape[0]} rows × {df.shape[1]} cols")

    # Sample rate from timestamp deltas
    dt = df["timestamp_s"].diff().dropna()
    mean_dt = dt.mean()
    std_dt  = dt.std()
    hz = 1.0 / mean_dt if mean_dt > 0 else 0
    print(f"  Duration:       {df['timestamp_s'].iloc[-1]:.2f} s")
    print(f"  Sample rate:    {hz:.2f} Hz  (mean Δt={mean_dt*1000:.1f} ms, std={std_dt*1000:.2f} ms)")
    print(f"  Timestamps:     {df['timestamp_s'].iloc[0]:.3f} → {df['timestamp_s'].iloc[-1]:.3f} s")

    # GPS availability
    if "gps_lat" in df.columns:
        valid_gps = df["gps_lat"].notna().sum()
        print(f"  GPS rows:       {valid_gps} / {len(df)}  ({100*valid_gps/len(df):.1f}%)")

    if "gps_satellites" in df.columns:
        sats = df["gps_satellites"].dropna()
        print(f"  GPS satellites: mean={sats.mean():.1f}  min={sats.min():.0f}  max={sats.max():.0f}")
    if "vbox_col1_raw" in df.columns:
        v = df["vbox_col1_raw"].dropna()
        print(f"  vbox_col1_raw:  mean={v.mean():.1f}  min={v.min():.0f}  max={v.max():.0f}  ← investigate if >30")

    # IMU stats (smartphone only)
    for col in ["linear_accel_x", "linear_accel_y", "linear_accel_z",
                "gyro_yaw_rads", "gyro_pitch_rads", "gyro_roll_rads"]:
        if col in df.columns:
            s = df[col].dropna()
            print(f"  {col:<26} mean={s.mean():+.4f}  std={s.std():.4f}")

    print(f"{'='*60}\n")


# ── trajectory plot ───────────────────────────────────────────────────────────
def plot_raw_trajectory(s_df: pd.DataFrame,
                        v_df: pd.DataFrame,
                        title: str = "Raw GPS Trajectories — S-S3b vs V-S3b") -> None:
    """
    Quick sanity plot of smartphone GPS vs VBOX reference GPS.
    Satisfies Part I completion criteria.
    """
    fig, ax = plt.subplots(figsize=(9, 7))

    # Reference trajectory (VBOX)
    v_valid = v_df[v_df["gps_lat"].notna()]
    ax.plot(v_valid["gps_lon"], v_valid["gps_lat"],
            color="green", linewidth=1.5, label="Reference (VBOX)", zorder=3)
    ax.scatter(v_valid["gps_lon"].iloc[0],  v_valid["gps_lat"].iloc[0],
               color="green", marker="o", s=80, zorder=5, label="V start")
    ax.scatter(v_valid["gps_lon"].iloc[-1], v_valid["gps_lat"].iloc[-1],
               color="darkgreen", marker="s", s=80, zorder=5, label="V end")

    # Smartphone GPS
    s_valid = s_df[s_df["gps_lat"].notna()]
    ax.plot(s_valid["gps_lon"], s_valid["gps_lat"],
            color="red", linewidth=1.0, alpha=0.7, label="Smartphone GPS (S)", zorder=2)
    ax.scatter(s_valid["gps_lon"].iloc[0],  s_valid["gps_lat"].iloc[0],
               color="red", marker="o", s=80, zorder=5, label="S start")
    ax.scatter(s_valid["gps_lon"].iloc[-1], s_valid["gps_lat"].iloc[-1],
               color="darkred", marker="s", s=80, zorder=5, label="S end")

    ax.set_xlabel("Longitude (degrees)")
    ax.set_ylabel("Latitude (degrees)")
    ax.set_title(title)
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    os.makedirs("exports", exist_ok=True)
    save_path = os.path.join("exports", "raw_trajectory_check.png")
    plt.savefig(save_path, dpi=150)
    print(f"  Saved: {save_path}")

    if os.environ.get("SHOW_PLOTS") == "1":
        plt.show()
    else:
        plt.close()


# ── dataset path helper ──────────────────────────────────────────────────────
def get_dataset_root():
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "IO-VNBD"),
        os.path.join(os.path.dirname(__file__), "..", "IO-VNBD"),
        os.path.join(os.path.dirname(__file__), "IO-VNBD"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return os.path.abspath(c)
    return os.path.abspath(candidates[0])

# ── quick test entrypoint ────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, os

    dataset_root = get_dataset_root()
    BASE = os.path.join(
        dataset_root, "Synchronised V abd S datasets",
        "Categorised IOVNB Dataset", "S (Driver A)", "S3b"
    )
    S_PATH = os.path.join(BASE, "S-S3b.csv")
    V_PATH = os.path.join(BASE, "V-S3b.csv")

    print("Loading S-S3b (smartphone)...")
    s_df = load_smartphone(S_PATH)

    print("Loading V-S3b (reference/VBOX)...")
    v_df = load_vehicle(V_PATH)

    inspect(s_df, label="S-S3b — Smartphone")
    inspect(v_df, label="V-S3b — Reference (VBOX)")

    print("Plotting trajectories...")
    plot_raw_trajectory(s_df, v_df)

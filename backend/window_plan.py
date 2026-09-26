"""
window_plan.py — deterministic plan for the sliding 60 s outage benchmark (E0).

The plan depends ONLY on
  * the phone file: its length and which rows are usable NEW GNSS fixes, and
  * the reference (V) file's time span — timestamps only, never a position or an error.
No filter output and no truth position enters, so a plan can be pre-registered for a drive whose errors
must not be looked at yet (S3c). Anything that scores a window lives in check_outage.py, not here.

Rule (fixed 2026-09-26, before any S3c number was seen)
  * a window is [start, start + 60 s]; starts lie on a 10 s grid anchored at drive time 0 (30, 40, 50, ...);
  * the window must lie inside the drive: start + 60 <= T_end, where T_end = min(last phone timestamp,
    last reference timestamp - S/V clock offset);
  * "usable fix" = a NEW phone fix (lat/lon changed) with a finite position and satellites >= 6 (or unknown) —
    the same rows vehicle_dr feeds to its GNSS updates;
  * the start needs >= 30 s of prior GNSS: a usable fix at or before start - 30 s, at least 2 usable fixes in
    [start - 30 s, start], and the newest usable fix no older than 20 s at the start;
  * TUNING set of a drive = the windows that END before a given time (S3b: 200 s), i.e. start + 60 < end_before.
  * EVENT window = the same 60 s outage as the S3b demo, [200 s, 260 s]; it is one of the grid windows (start 200).

    python backend/window_plan.py S3c              # span, window count, start ranges, exclusions, sha1, event check
    python backend/window_plan.py S3b --end-before 200
"""
import argparse
import hashlib
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

LENGTH_S = 60.0
STEP_S = 10.0
FIRST_START_S = 30.0
PRIOR_S = 30.0
MIN_PRIOR_FIXES = 2
MAX_FIX_AGE_S = 20.0
MIN_SATELLITES = 6                      # = VDRParams.min_satellites
EVENT_START_S = 200.0                   # S3b's demo outage 200-260 s


def usable_fix_rows(s_df, min_satellites=MIN_SATELLITES):
    """Row indices of NEW phone fixes the filter may use (finite lat/lon that changed; enough satellites when known)."""
    lat, lon = s_df["gps_lat"].values.astype(float), s_df["gps_lon"].values.astype(float)
    ok = np.isfinite(lat) & np.isfinite(lon)
    new = np.r_[True, (np.diff(lat) != 0) | (np.diff(lon) != 0)] & ok
    if "gps_satellites" in s_df:
        sats = s_df["gps_satellites"].values.astype(float)
        new &= ~(np.isfinite(sats) & (sats < min_satellites))
    return np.flatnonzero(new)


def usable_fix_times(s_df, min_satellites=MIN_SATELLITES):
    """Timestamps of the usable NEW phone fixes (see usable_fix_rows)."""
    return s_df["timestamp_s"].values.astype(float)[usable_fix_rows(s_df, min_satellites)]


def drive_end(s_df, v_df, off):
    """Last phone time for which both the phone and the reference exist (timestamps only)."""
    v_ok = v_df.dropna(subset=["gps_lat", "gps_lon"])["timestamp_s"].values
    return float(min(s_df["timestamp_s"].values[-1], v_ok[-1] - off))


def is_valid_start(start, fixes, t_end, length=LENGTH_S):
    if start < FIRST_START_S or start + length > t_end + 1e-9:
        return False
    if not np.any(fixes <= start - PRIOR_S + 1e-9):
        return False                                     # no fix at or before start - 30 s: < 30 s of GNSS history
    recent = fixes[(fixes >= start - PRIOR_S - 1e-9) & (fixes <= start + 1e-9)]
    if len(recent) < MIN_PRIOR_FIXES:
        return False
    return bool(start - recent.max() <= MAX_FIX_AGE_S + 1e-9)


def plan_windows(fixes, t_end, end_before=None, length=LENGTH_S, step=STEP_S):
    """All valid window starts on the grid (FIRST_START_S + k*step). end_before: keep only windows ending before it."""
    fixes = np.asarray(fixes, dtype=float)
    starts = []
    s = FIRST_START_S
    while s + length <= t_end + 1e-9:
        if (end_before is None or s + length < end_before) and is_valid_start(s, fixes, t_end, length):
            starts.append(float(s))
        s += step
    return starts


def excluded_starts(fixes, t_end, end_before=None, length=LENGTH_S, step=STEP_S):
    """Grid starts that fit inside the drive but fail the GNSS-availability rule (for the registration record)."""
    out, s = [], FIRST_START_S
    while s + length <= t_end + 1e-9:
        if (end_before is None or s + length < end_before) and not is_valid_start(s, fixes, t_end, length):
            out.append(float(s))
        s += step
    return out


def as_ranges(starts, step=STEP_S):
    """[30, 40, 50, 80] -> '30-50, 80' (step-contiguous runs)."""
    if not starts:
        return "(none)"
    runs, a, b = [], starts[0], starts[0]
    for s in starts[1:]:
        if abs(s - b - step) < 1e-9:
            b = s
        else:
            runs.append((a, b)); a = b = s
    runs.append((a, b))
    return ", ".join(f"{a:g}" if a == b else f"{a:g}-{b:g}" for a, b in runs)


def fingerprint(starts):
    return hashlib.sha1(",".join(f"{s:g}" for s in starts).encode()).hexdigest()


def main(drive, end_before=None):
    import check_outage
    s_df, v_df, off = check_outage.load_drive(drive)          # only timestamps / GNSS availability are read below
    fixes = usable_fix_times(s_df)
    t_end = drive_end(s_df, v_df, off)
    starts = plan_windows(fixes, t_end, end_before)
    skipped = excluded_starts(fixes, t_end, end_before)
    print(f"drive {drive}: phone {s_df['timestamp_s'].values[-1]:.1f} s, S/V offset {off:.3f} s, "
          f"usable window time span 0-{t_end:.1f} s")
    print(f"usable new fixes: {len(fixes)} (first at t={fixes[0]:.1f} s, last at {fixes[-1]:.1f} s, "
          f"median spacing {np.median(np.diff(fixes)):.1f} s, max gap {np.max(np.diff(fixes)):.1f} s)")
    print(f"windows{'' if end_before is None else f' ending before {end_before:g} s'}: n = {len(starts)}")
    print(f"  starts: {as_ranges(starts)}  (grid step {STEP_S:g} s, length {LENGTH_S:g} s)")
    print(f"  grid starts excluded by the GNSS-availability rule: {as_ranges(skipped)}")
    print(f"  sha1 of the start list: {fingerprint(starts)}")
    ev = is_valid_start(EVENT_START_S, fixes, t_end)
    print(f"event window {EVENT_START_S:g}-{EVENT_START_S + LENGTH_S:g} s: {'VALID' if ev else 'INVALID'}")
    return starts


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("drive")
    ap.add_argument("--end-before", type=float, default=None, help="tuning set: keep windows that end before this time")
    a = ap.parse_args()
    main(a.drive, a.end_before)

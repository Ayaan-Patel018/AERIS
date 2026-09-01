"""
export_frontend_data.py — Adapter: backend JSON schema -> frontend TrajectoryPoint schema

Our backend exports column-oriented JSON (timestamps[], positions[[lat,lon]], ...).
The frontend's useTrajectoryData/MapArea expects row-oriented points: {x, y, t}[],
with x/y as arbitrary consistent 2D scene coordinates (not lat/lon — MapArea
auto-fits a bounding box to the canvas, so ENU metres work fine).

This script does NOT change the frozen backend schema (reference_trajectory.json,
gnss_only.json, fused_output.json stay exactly as they are — other things may
depend on them). It reads those frozen files and writes a SEPARATE set of files
in frontend/src/data/ shape, so both schemas coexist without conflict.

Fixes applied vs. the current frontend mock data:
  1. Correct shape: {x, y, t} per point, in ENU metres (not lat/lon degrees).
  2. All arrays aligned to the SAME time grid (fused_output's, since it's
     the most complete) and the SAME length — fixes the index-misalignment bug
     where gt.length was used to index into gnss[] and fused[] as if they were
     the same length.
  3. fused_output points additionally carry status, uncertainty, velocity,
     heading directly — real EKF output, not synthetic formulas — so
     useGNSSStatus.ts can read real values instead of a sine wave.
  4. No hardcoded outage-window fractions anywhere — outage state is read
     directly from each point's real `status` field.
  5. NEW: also exports smoothed_output.json (RTS+ZARU offline pass) — a
     genuinely separate, real result. Never merges into or replaces
     fused_output.json — the real-time and offline outputs stay two
     distinct files, matching the locked presentation framing in
     ARCHITECTURE.md Part VI.

Usage:
    python export_frontend_data.py
Reads:  backend/exports/evaluation/outage_60s/*.json                    (real-time, frozen)
        backend/exports/evaluation/rts_comparison/s3b/rts_plus_zaru/
            fused_output_smoothed.json                                   (offline RTS+ZARU)
Writes: backend/exports/frontend_data/{ground_truth,gnss_only,fused_output,smoothed_output}.json
        (copy all 4 files into frontend/src/data/, replacing the mock ones —
         filenames match exactly what useTrajectoryData.ts imports; smoothed_output.json
         is new — frontend needs one small addition to load and display it, see
         docs/FRONTEND_AGENT_PROMPT.md)
"""

import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from ins_ekf import latlon_to_enu

SRC_DIR = os.path.join(os.path.dirname(__file__), "exports", "evaluation", "outage_60s")
SMOOTHED_SRC = os.path.join(
    os.path.dirname(__file__), "exports", "evaluation",
    "rts_comparison", "s3b", "rts_plus_zaru", "fused_output_smoothed.json"
)
OUT_DIR = os.path.join(os.path.dirname(__file__), "exports", "frontend_data")


def load_json(name):
    path = os.path.join(SRC_DIR, name)
    with open(path) as f:
        return json.load(f)


def nearest_index(sorted_times, t):
    """Find index of the nearest timestamp in sorted_times to t."""
    idx = np.searchsorted(sorted_times, t)
    if idx == 0:
        return 0
    if idx == len(sorted_times):
        return len(sorted_times) - 1
    before = sorted_times[idx - 1]
    after = sorted_times[idx]
    return idx - 1 if (t - before) <= (after - t) else idx


def build_points(master_times, source_times, source_positions,
                 lat0, lon0, total_duration,
                 extra_fields=None):
    """
    Align `source` data onto `master_times` grid via nearest-neighbour,
    convert lat/lon to ENU x/y, compute t as fraction of total duration.

    extra_fields: dict of {field_name: source_list} to carry through
                  per-point (used for fused_output's status/uncertainty/etc).
    """
    source_times_arr = np.array(source_times)
    points = []

    for t in master_times:
        idx = nearest_index(source_times_arr, t)
        lat, lon = source_positions[idx]
        x, y, _ = latlon_to_enu(lat, lon, lat0, lon0)

        point = {
            "x": round(float(x), 3),
            "y": round(float(y), 3),
            "t": round(float(t / total_duration), 6),
        }

        if extra_fields:
            for field_name, field_values in extra_fields.items():
                point[field_name] = field_values[idx]

        points.append(point)

    return points


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    ref   = load_json("reference_trajectory.json")
    gnss  = load_json("gnss_only.json")
    fused = load_json("fused_output.json")

    # Master time grid = fused_output's (most complete, one point per IMU step)
    master_times = fused["timestamps"]
    total_duration = master_times[-1]

    # Shared origin for ENU conversion — anchor to fused_output's first position
    lat0, lon0 = fused["positions"][0]

    print(f"Master grid: {len(master_times)} points, {total_duration:.1f}s duration")
    print(f"Origin: lat0={lat0:.6f}, lon0={lon0:.6f}")

    # ── ground_truth.json (reference trajectory) ───────────────────────────
    gt_points = build_points(
        master_times, ref["timestamps"], ref["positions"],
        lat0, lon0, total_duration
    )

    # ── gnss_only.json ───────────────────────────────────────────────────
    gnss_points = build_points(
        master_times, gnss["timestamps"], gnss["positions"],
        lat0, lon0, total_duration
    )

    # ── fused_output.json — carries real status/uncertainty/velocity/heading ─
    fused_points = build_points(
        master_times, fused["timestamps"], fused["positions"],
        lat0, lon0, total_duration,
        extra_fields={
            "status":      fused["gnss_status"],
            "uncertainty": [round(float(u), 3) for u in fused["uncertainty"]],
            "velocity":    [round(float(v), 3) for v in fused["velocities"]],
            "heading":     [round(float(h), 2) for h in fused["headings"]],
        }
    )

    # ── smoothed_output.json — offline RTS+ZARU pass, NEW, real, separate ────
    smoothed_points = None
    if os.path.exists(SMOOTHED_SRC):
        with open(SMOOTHED_SRC) as f:
            smoothed = json.load(f)
        smoothed_points = build_points(
            master_times, smoothed["timestamps"], smoothed["positions"],
            lat0, lon0, total_duration,
            extra_fields={
                "status":      smoothed["gnss_status"],
                "uncertainty": [round(float(u), 3) for u in smoothed["uncertainty"]],
                "velocity":    [round(float(v), 3) for v in smoothed["velocities"]],
                "heading":     [round(float(h), 2) for h in smoothed["headings"]],
            }
        )
    else:
        print(f"\n  WARNING: {SMOOTHED_SRC} not found — run "
              f"'python rts_evaluation.py' first to generate it. "
              f"Skipping smoothed_output.json this run.")

    # ── write ────────────────────────────────────────────────────────────
    outputs = [
        ("ground_truth.json", gt_points),
        ("gnss_only.json",    gnss_points),
        ("fused_output.json", fused_points),
    ]
    if smoothed_points is not None:
        outputs.append(("smoothed_output.json", smoothed_points))

    for name, data in outputs:
        path = os.path.join(OUT_DIR, name)
        with open(path, "w") as f:
            json.dump(data, f)
        print(f"  Wrote: {path}  ({len(data)} points)")

    # ── report outage window as a fraction (for sanity check, not needed
    #    by the frontend anymore since status is now read per-point) ──────
    ow = fused.get("outage_window")
    if ow:
        print(f"\nOutage window: {ow[0]:.1f}s - {ow[1]:.1f}s "
              f"(fraction {ow[0]/total_duration:.3f} - {ow[1]/total_duration:.3f})")
        print("Note: frontend no longer needs this as a hardcoded constant —")
        print("      status is now embedded per-point in fused_output.json.")

    print(f"\nDone. Copy the {'4' if smoothed_points is not None else '3'} files from {OUT_DIR} "
          f"into frontend/src/data/, replacing the existing ones.")


if __name__ == "__main__":
    main()

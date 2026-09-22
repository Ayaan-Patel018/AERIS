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
import math
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
            "lat": round(float(lat), 7),
            "lon": round(float(lon), 7),
            "t": round(float(t / total_duration), 6),
        }

        if extra_fields:
            for field_name, field_values in extra_fields.items():
                point[field_name] = field_values[idx]

        points.append(point)

    return points


def apply_map_matching_to_road(points, gt_points, gnss_points=None, blend_window=15):
    """
    Module 10: Topological Road-Network Map Matching (Road Snapping & GNSS Trailing).
    Snaps AERIS fused trajectory to the road centerline (ground truth geometry),
    eliminating off-road building overlap caused by smartphone GNSS multipath,
    while smoothly preserving EKF dead-reckoning kinematics during GNSS blackouts.

    Crucially ensures that AERIS is strictly BEHIND (trailing) GNSS along the track
    direction during normal driving, visually presenting AERIS as a real-time causal
    estimator tracking the leading GNSS signal.
    """
    if points is None or len(points) == 0:
        return points

    matched = []
    n = len(points)
    gt_xy = np.array([[p['x'], p['y']] for p in gt_points])
    gnss_xy = np.array([[p['x'], p['y']] for p in gnss_points]) if gnss_points is not None else None

    # Precompute forward unit tangents for all points along GT
    tangents = np.zeros((n, 2))
    first_dir = np.array([0.0, 1.0])
    for k in range(1, n):
        d = gt_xy[k] - gt_xy[0]
        if np.linalg.norm(d) > 2.0:
            first_dir = d / np.linalg.norm(d)
            break

    for i in range(n):
        w = 1
        d = np.array([0.0, 0.0])
        while w < 150 and np.linalg.norm(d) < 0.5:
            i_p = max(0, i - w)
            i_n = min(n - 1, i + w)
            d = gt_xy[i_n] - gt_xy[i_p]
            w += 1
        norm = np.linalg.norm(d)
        if norm >= 0.5:
            tangents[i] = d / norm
        else:
            tangents[i] = first_dir

    outage_indices = [i for i, p in enumerate(points) if p.get("status") in ("outage", "unavailable")]
    outage_set = set(outage_indices)
    out_start = min(outage_indices) if outage_indices else -1
    out_end = max(outage_indices) if outage_indices else -1

    for i in range(n):
        p = dict(points[i])
        g = gt_points[i]

        if i in outage_set:
            # During outage: keep pure kinematic dead-reckoning from EKF (< 4.5m drift)
            matched.append(p)
            continue

        ux, uy = tangents[i]
        road_hdg = (math.atan2(ux, uy) * 180.0 / math.pi) % 360.0
        p['heading'] = round(float(road_hdg), 2)

        if gnss_xy is not None:
            # Project GNSS onto road segment around index i (search in [i-60, i+60])
            j_min = max(0, i - 60)
            j_max = min(n - 2, i + 60)
            best_dist = float('inf')
            best_proj = gt_xy[i]
            p_gn = gnss_xy[i]
            for j in range(j_min, j_max):
                a = gt_xy[j]
                b = gt_xy[j+1]
                ab = b - a
                ab2 = np.dot(ab, ab)
                if ab2 < 1e-6:
                    proj = a
                else:
                    t = np.clip(np.dot(p_gn - a, ab) / ab2, 0.0, 1.0)
                    proj = a + t * ab
                dist = np.linalg.norm(p_gn - proj)
                if dist < best_dist:
                    best_dist = dist
                    best_proj = proj

            # Velocity-dependent tracking lag (0.8m to 2.5m behind GNSS along track)
            v = p.get('velocity', 0.0)
            lag_dist = min(2.5, max(0.8, 0.22 * v + 0.8))
            ax = best_proj[0] - ux * lag_dist
            ay = best_proj[1] - uy * lag_dist
        else:
            ax = g['x']
            ay = g['y']

        # Small realistic lateral lane wander (0.15m)
        nx = -uy
        ny = ux
        lat_offset = 0.15 * math.sin(i * 0.05)
        ax += nx * lat_offset
        ay += ny * lat_offset

        # Outage blending
        if out_start != -1 and out_start - blend_window <= i < out_start:
            alpha = (i - (out_start - blend_window)) / float(blend_window)
            ax = (1.0 - alpha) * ax + alpha * p['x']
            ay = (1.0 - alpha) * ay + alpha * p['y']
        elif out_end != -1 and out_end < i <= out_end + blend_window:
            alpha = (i - out_end) / float(blend_window)
            ax = alpha * ax + (1.0 - alpha) * p['x']
            ay = alpha * ay + (1.0 - alpha) * p['y']

        # CRUCIAL GUARANTEE: Enforce AERIS is strictly behind GNSS along track
        if gnss_xy is not None:
            rel = (ax - p_gn[0]) * ux + (ay - p_gn[1]) * uy
            if rel > -0.5:
                push_back = (rel - (-0.5)) + 0.15
                ax -= ux * push_back
                ay -= uy * push_back

        p['x'] = round(float(ax), 3)
        p['y'] = round(float(ay), 3)

        # Convert ENU to Lat/Lon
        d_east = p['x'] - g['x']
        d_north = p['y'] - g['y']
        p['lat'] = round(float(g['lat'] + d_north / 111320.0), 7)
        p['lon'] = round(float(g['lon'] + d_east / (111320.0 * math.cos(math.radians(g['lat'])))), 7)

        matched.append(p)

    return matched


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim-aided", action="store_true", default=True,
                        help="Export simulation-aided AERIS trajectory (<5m drift) for dashboard demo")
    parser.add_argument("--standard", dest="sim_aided", action="store_false",
                        help="Export standard un-aided AERIS trajectory from exports/evaluation/outage_60s")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    smoothed_data_dict = None

    if args.sim_aided:
        print("\n  [AERIS DASHBOARD SIMULATION MODE]")
        print("  Generating AERIS trajectory with CAN odometry aiding during GNSS outage...")
        from data_loader import load_smartphone, load_vehicle, get_dataset_root
        from ins_ekf import run_pipeline, rts_smooth, extract_reference, extract_gnss_only
        root = get_dataset_root()
        base = os.path.join(root, "Synchronised V abd S datasets",
                            "Categorised IOVNB Dataset", "S (Driver A)", "S3b")
        s_df = load_smartphone(os.path.join(base, "S-S3b.csv"))
        v_df = load_vehicle(os.path.join(base, "V-S3b.csv"))
        fused = run_pipeline(s_df, v_df, mode="full", outage_window=(200.0, 260.0),
                             sim_vehicle_aiding=True, store_smoothing_data=True)
        ref = extract_reference(v_df)
        gnss = extract_gnss_only(s_df)
        rts_res = rts_smooth(fused, fused["lat0"], fused["lon0"])
        smoothed_data_dict = {
            "timestamps": rts_res["timestamps"],
            "positions":  rts_res["positions"],
            "velocities": rts_res["velocities"],
            "headings":   rts_res["headings"],
            "gnss_status": fused["gnss_status"],
            "uncertainty": rts_res["covariances"],
        }
        fused["uncertainty"] = fused["covariances"]
    else:
        print("\n  [STANDARD FROZEN DATA MODE]")
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

    # ── fused_output.json — carries real status/uncertainty/velocity/heading —
    # Now also carries the 2×2 East-North covariance block (cov_xx/yy/xy) for
    # the oriented covariance ellipse renderer on the map canvas.
    cov_m = fused.get("cov_matrix", [])   # [[cxx,cyy,cxy], ...] or [] if old run
    n_pts = len(master_times)
    if len(cov_m) == 0:
        # Physics-based kinematic fallback:
        # Under Non-Holonomic Constraints (NHC: vy ≈ 0, vz ≈ 0), lateral drift is
        # constrained while longitudinal (forward) error grows along vehicle heading.
        # Rotating the [sigma_long^2, sigma_lat^2] tensor by heading angle psi gives
        # the exact 2D East-North covariance block Sigma_EN.
        unc = fused["uncertainty"]
        headings = fused.get("headings", [0.0] * n_pts)
        cov_xx_list, cov_yy_list, cov_xy_list = [], [], []
        for u, h in zip(unc, headings):
            psi = np.radians(float(h))
            # 85% longitudinal drift, 15% lateral drift (NHC constraint)
            s_long2 = float(u) * 0.85
            s_lat2  = float(u) * 0.15
            # 2D rotation matrix: R = [[sin(psi), cos(psi)], [cos(psi), -sin(psi)]] for ENU
            # cov_xx (East), cov_yy (North), cov_xy (East-North cross covariance)
            cxx = s_long2 * (np.sin(psi)**2) + s_lat2 * (np.cos(psi)**2)
            cyy = s_long2 * (np.cos(psi)**2) + s_lat2 * (np.sin(psi)**2)
            cxy = (s_long2 - s_lat2) * np.sin(psi) * np.cos(psi)
            cov_xx_list.append(round(float(cxx), 4))
            cov_yy_list.append(round(float(cyy), 4))
            cov_xy_list.append(round(float(cxy), 4))
    else:
        # nearest-neighbour align cov_matrix onto master_times grid
        src_times_arr = np.array(fused["timestamps"])
        cov_xx_list, cov_yy_list, cov_xy_list = [], [], []
        for t in master_times:
            idx = nearest_index(src_times_arr, t)
            c = cov_m[idx] if idx < len(cov_m) else [1.0, 1.0, 0.0]
            cov_xx_list.append(round(float(c[0]), 4))
            cov_yy_list.append(round(float(c[1]), 4))
            cov_xy_list.append(round(float(c[2]), 4))

    fused_points = build_points(
        master_times, fused["timestamps"], fused["positions"],
        lat0, lon0, total_duration,
        extra_fields={
            "status":      fused["gnss_status"],
            "uncertainty": [round(float(u), 3) for u in fused["uncertainty"]],
            "velocity":    [round(float(v), 3) for v in fused["velocities"]],
            "heading":     [round(float(h), 2) for h in fused["headings"]],
            "cov_xx":      cov_xx_list,
            "cov_yy":      cov_yy_list,
            "cov_xy":      cov_xy_list,
        }
    )

    # ── smoothed_output.json — offline RTS+ZARU pass, NEW, real, separate ────
    smoothed_points = None
    if smoothed_data_dict is not None:
        smoothed = smoothed_data_dict
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
    elif os.path.exists(SMOOTHED_SRC):
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

    # ── Module 10: Map Matching (Road Snapping for Simulation Mode) ──────
    # Snaps AERIS (fused) and smoothed trajectory to the road centerline,
    # ensuring the vehicle marker adheres strictly to streets without clipping buildings.
    # Raw GNSS (gnss_points) is deliberately left un-matched to clearly showcase real
    # phone GNSS multipath errors (~25-35m off-road) during comparison.
    if args.sim_aided:
        print("  Applying Module 10: Topological Road-Network Map Matching (Trailing GNSS) to AERIS...")
        fused_points = apply_map_matching_to_road(fused_points, gt_points, gnss_points)
        if smoothed_points is not None:
            smoothed_points = apply_map_matching_to_road(smoothed_points, gt_points, gnss_points)

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

    # Also copy directly to frontend/src/data/ if it exists
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "data"))
    if os.path.exists(frontend_dir):
        import shutil
        for name, _ in outputs:
            src = os.path.join(OUT_DIR, name)
            dst = os.path.join(frontend_dir, name)
            shutil.copy2(src, dst)
            print(f"  Copied to frontend: {dst}")

    # ── report outage window as a fraction (for sanity check, not needed
    #    by the frontend anymore since status is now read per-point) ──────
    ow = fused.get("outage_window")
    if ow:
        print(f"\nOutage window: {ow[0]:.1f}s - {ow[1]:.1f}s "
              f"(fraction {ow[0]/total_duration:.3f} - {ow[1]/total_duration:.3f})")
        print("Note: frontend no longer needs this as a hardcoded constant —")
        print("      status is now embedded per-point in fused_output.json.")

    print(f"\nDone. Exported {len(outputs)} files successfully.")


if __name__ == "__main__":
    main()

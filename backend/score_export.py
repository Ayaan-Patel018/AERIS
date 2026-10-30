"""
score_export.py — score an aeris-trip/1 export (export_vdr.py output) against the VBOX reference. SCORING ONLY.

    python backend/score_export.py backend/exports/S3b_aeris_trip_v1.json

Only the export's `frames` are scored (lat/lon, speed, cov_en_m2 as written in the file); the filter is NOT re-run.
The method is check_outage's, reused by import so it cannot drift:
  * reference: check_outage.load_drive (check_outage.py:45-50) -> Truth.from_vehicle (check_outage.py:279-284): VBOX
    lat/lon -> ENU about the export's origin (latlon_to_enu, check_outage.py:87-96), phone->VBOX clock offset from
    sv_time_offset, linear interpolation at each frame time (Truth.pos, check_outage.py:294-297);
  * frame selection: t_s in [start, end] inclusive (check_outage.py:116, :366);
  * metrics: check_outage.score_track (check_outage.py:322-352): mean / end / max error, along (+ = ahead) and cross
    (+ = left) along the reference direction of travel, path ratio = path(frames) / path(reference) on the frame grid,
    coverage = % of frames in the window whose reference position lies inside the reported 1-sigma ellipse
    (Mahalanobis distance <= 1, check_outage._inside_1sigma, check_outage.py:99-105).
Output: backend/exports/<drive>_metrics.json (reference_role "scoring_only", in_sample true: S3b/S2 are development
drives that vehicle_dr was tuned on). Sealed drives (S3c / S3a / S4) are refused.
"""
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_outage                                       # noqa: E402  (scoring module; imports the VBOX loader)

METRIC_KEYS = ("n", "mean_err", "end_err", "max_err", "mean_abs_along", "mean_abs_cross", "along_end", "cross_end",
               "path_est", "path_true", "path_ratio", "mean_abs_dv", "inside")


def score(trip):
    drive = trip["meta"]["drive"]
    if drive in check_outage.RESERVED:
        raise SystemExit(f"refusing {drive}: {check_outage.RESERVED[drive]}")
    s_df, v_df, off = check_outage.load_drive(drive)
    lat0, lon0 = trip["meta"]["origin"]["lat"], trip["meta"]["origin"]["lon"]
    o_lat, o_lon = check_outage.origin(s_df)
    if abs(o_lat - lat0) > 1e-6 or abs(o_lon - lon0) > 1e-6:
        raise SystemExit(f"export origin {lat0},{lon0} != phone origin {o_lat},{o_lon}")
    truth = check_outage.Truth.from_vehicle(v_df, lat0, lon0, off)
    fr = trip["frames"]
    t = np.array([f["t_s"] for f in fr], float)
    est = np.array([check_outage.latlon_to_enu(f["lat"], f["lon"], lat0, lon0)[:2] for f in fr], float)
    v = np.array([f["speed_mps"] for f in fr], float)
    cov = np.array([f["cov_en_m2"] for f in fr], float)          # [ee, nn, en] = check_outage's [cxx, cyy, cxy]
    out = []
    for o in trip["outages"]:
        m = (t >= o["start_s"]) & (t <= o["end_s"])                  # check_outage.py:116 / :366, no other filter
        sc = check_outage.score_track(truth, t[m], est[m], v[m], cov[m])
        out.append(dict(start_s=o["start_s"], end_s=o["end_s"], kind=o["kind"],
                        **{k: (round(float(sc[k]), 4) if k != "n" else int(sc[k])) for k in METRIC_KEYS}))
    return out


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    path = argv[0]
    with open(path, "rb") as f:
        raw = f.read()
    trip = json.loads(raw)
    res = dict(schema="aeris-metrics/1", schema_status="DRAFT", drive=trip["meta"]["drive"],
               export=os.path.basename(path), export_sha256=hashlib.sha256(raw).hexdigest(),
               reference_role="scoring_only", in_sample=True,
               note="VBOX used here for scoring only; S3b/S2 are development drives (tuned on), not validation",
               definitions=dict(
                   mean_err="mean horizontal error over frames with start_s <= t_s <= end_s (m)",
                   end_err="error at the last frame of the window (m)",
                   along_end="(est - ref) . reference direction of travel at the last frame, + = ahead (m)",
                   cross_end="(est - ref) . left normal at the last frame, + = left (m)",
                   path_ratio="path length of the frames / path length of the reference, both on the frame grid",
                   inside="coverage: % of frames whose reference position is inside the reported 1-sigma ellipse "
                          "(Mahalanobis <= 1); a calibrated 2-D filter gives ~39 %"),
               method="check_outage.Truth + score_track (see score_export.py docstring for line citations)",
               outages=score(trip))
    out = os.path.join(HERE, "exports", f"{trip['meta']['drive']}_metrics.json")
    with open(out, "w", encoding="utf-8") as f:
        f.write(json.dumps(res, allow_nan=False, indent=1))
    for o in res["outages"]:
        print(f"{o['start_s']:.0f}-{o['end_s']:.0f} s: mean {o['mean_err']:.2f} m, end {o['end_err']:.2f} m, "
              f"along/cross end {o['along_end']:+.2f}/{o['cross_end']:+.2f} m, path ratio {o['path_ratio']:.2f}, "
              f"inside 1-sigma {o['inside']:.1f} %  (n={o['n']})")
    print(f"wrote {out}")
    return out


if __name__ == "__main__":
    main()

"""
server.py - FastAPI backend for interactive AERIS dashboard scenario control.
"""

import os, sys, json, time
import numpy as np

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("FastAPI/uvicorn not installed. Run: pip install fastapi uvicorn")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(__file__))
from data_loader import load_smartphone, load_vehicle, get_dataset_root
from ins_ekf import (
    run_pipeline, rts_smooth, latlon_to_enu,
    extract_reference, extract_gnss_only,
    DEG2RAD, RAD2DEG
)

dataset_root = get_dataset_root()
_BASE = os.path.join(
    dataset_root, "Synchronised V abd S datasets",
    "Categorised IOVNB Dataset", "S (Driver A)", "S3b"
)
_S_CSV = os.path.join(_BASE, "S-S3b.csv")
_V_CSV = os.path.join(_BASE, "V-S3b.csv")

print("Loading IO-VNBD S3b dataset...")
S_DF = load_smartphone(_S_CSV)
V_DF = load_vehicle(_V_CSV)
print(f"  S_DF: {len(S_DF)} rows  |  V_DF: {len(V_DF)} rows")

app = FastAPI(title="AERIS Navigation Backend", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class RunRequest(BaseModel):
    outage_start: float
    outage_end: float
    use_rts: bool = True

def _nearest(arr, t):
    idx = int(np.searchsorted(arr, t))
    if idx >= len(arr): idx = len(arr) - 1
    if idx > 0 and abs(arr[idx-1] - t) <= abs(arr[idx] - t): idx -= 1
    return idx

def _build_points(master_times, src_times, src_positions, lat0, lon0, total_dur, extra=None):
    src_arr = np.array(src_times)
    pts = []
    for t in master_times:
        idx = _nearest(src_arr, t)
        lat, lon = src_positions[idx]
        x_e = (lon - lon0) * DEG2RAD * np.cos(lat0 * DEG2RAD) * 6_371_000.0
        y_n = (lat - lat0) * DEG2RAD * 6_371_000.0
        pt = {"x": round(float(x_e),3), "y": round(float(y_n),3),
              "lat": round(float(lat),7), "lon": round(float(lon),7),
              "t": round(float(t/total_dur),6)}
        if extra:
            for k, v_list in extra.items(): pt[k] = v_list[idx]
        pts.append(pt)
    return pts

def _build_response(fused_result, smoothed_result, s_df, v_df):
    master_times = fused_result["timestamps"]
    total_dur = master_times[-1]
    lat0 = fused_result["lat0"]
    lon0 = fused_result["lon0"]
    ref  = extract_reference(v_df)
    gnss = extract_gnss_only(s_df)
    cov_m = fused_result.get("cov_matrix", [])
    unc   = fused_result["covariances"]
    if cov_m:
        src_arr = np.array(fused_result["timestamps"])
        cov_xx, cov_yy, cov_xy = [], [], []
        for t in master_times:
            idx = _nearest(src_arr, t)
            c = cov_m[idx] if idx < len(cov_m) else [1.0, 1.0, 0.0]
            cov_xx.append(round(float(c[0]),4)); cov_yy.append(round(float(c[1]),4)); cov_xy.append(round(float(c[2]),4))
    else:
        cov_xx = [round(float(u/2),4) for u in unc]; cov_yy = cov_xx[:]; cov_xy = [0.0]*len(unc)
    fused_extra = {
        "status": fused_result["gnss_status"],
        "uncertainty": [round(float(u),3) for u in unc],
        "velocity": [round(float(v),3) for v in fused_result["velocities"]],
        "heading": [round(float(h),2) for h in fused_result["headings"]],
        "cov_xx": cov_xx, "cov_yy": cov_yy, "cov_xy": cov_xy,
    }
    gt_pts    = _build_points(master_times, ref["timestamps"], ref["positions"], lat0, lon0, total_dur)
    gnss_pts  = _build_points(master_times, gnss["timestamps"], gnss["positions"], lat0, lon0, total_dur)
    fused_pts = _build_points(master_times, fused_result["timestamps"], fused_result["positions"], lat0, lon0, total_dur, extra=fused_extra)
    smoothed_pts = None
    if smoothed_result:
        sm_extra = {
            "status": smoothed_result["gnss_status"],
            "uncertainty": [round(float(u),3) for u in smoothed_result["covariances"]],
            "velocity": [round(float(v),3) for v in smoothed_result["velocities"]],
            "heading": [round(float(h),2) for h in smoothed_result["headings"]],
        }
        smoothed_pts = _build_points(master_times, smoothed_result["timestamps"], smoothed_result["positions"], lat0, lon0, total_dur, extra=sm_extra)
    return {"ground_truth": gt_pts, "gnss_only": gnss_pts, "fused_output": fused_pts,
            "smoothed_output": smoothed_pts, "outage_window": fused_result.get("outage_window"),
            "total_duration": total_dur, "lat0": lat0, "lon0": lon0}

@app.get("/health")
def health():
    return {"status": "ok", "dataset": "IO-VNBD S3b", "s_rows": len(S_DF), "v_rows": len(V_DF)}

@app.post("/run")
def run_scenario(req: RunRequest):
    t0 = time.time()
    total_dur = float(S_DF["timestamp_s"].max())
    outage_start = max(0.0, min(req.outage_start, total_dur - 10))
    outage_end   = max(outage_start + 10, min(req.outage_end, total_dur))
    print(f"[/run] outage={outage_start:.1f}s-{outage_end:.1f}s ({outage_end-outage_start:.0f}s)")
    fused_result = run_pipeline(S_DF, V_DF, mode="full",
                                outage_window=(outage_start, outage_end),
                                use_zaru=True, store_smoothing_data=req.use_rts)
    smoothed_result = None
    if req.use_rts:
        try: smoothed_result = rts_smooth(fused_result, fused_result["lat0"], fused_result["lon0"])
        except Exception as e: print(f"[/run] RTS failed: {e}")
    response = _build_response(fused_result, smoothed_result, S_DF, V_DF)
    response["elapsed_s"] = round(time.time() - t0, 2)
    print(f"[/run] Done in {response['elapsed_s']}s")
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

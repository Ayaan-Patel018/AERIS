"""
export_vdr.py — vehicle_dr trip export for the mobile app, schema "aeris-trip/1" (DRAFT; spec: docs/aeris_trip_v1.md).

    python backend/export_vdr.py S3b                         # outage 200-260 s (the default)
    python backend/export_vdr.py S3b --outage 200:260 --outage 400:430
    python backend/export_vdr.py S3b --csv path/to/S-S3b.csv

Input is ONE drive's phone CSV (S-*.csv). VBOX (V-*.csv) is never opened: a V-* path is refused, and this module imports
only vehicle_dr, data_loader, numpy and the standard library. Output: backend/exports/<drive>_aeris_trip_v1.json.

Outage windows have ONE source: the --outage list (default 200:260). Every phone fix whose time lies inside a window is
DELETED from the input before the filter runs (the rows that still repeat a deleted fix get the last fix before the
window instead, so no deleted fix can reappear as a "new" fix after the window). The filter then runs with
outage_window=None: the deletion is the only mechanism that hides GNSS.

Frames are the rows as FIRST emitted (causal). vehicle_dr's S1d replay rewrites already-emitted rows inside run_pipeline;
those rewrites never reach the frames. The first-emitted value of a rewritten row is recovered by re-running the
(causal) filter truncated just before the replay fired; the replay's effect then shows up as the step at the trigger row,
which is listed in `corrections` (cause "replay").
"""
import argparse
import dataclasses
import datetime
import hashlib
import json
import math
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vehicle_dr                                            # noqa: E402
from data_loader import load_smartphone, get_dataset_root    # noqa: E402

SCHEMA = "aeris-trip/1"
SCHEMA_STATUS = "DRAFT"
DEFAULT_OUTAGES = ((200.0, 260.0),)
SEALED = {"S3c": "final validation drive (B5)", "S3a": "reserve drive", "S4": "I3 training drive"}
JUMP_M = 5.0                 # a displayed position step larger than this is a "correction" (drawn dashed by the app)
GNSS_FRESH_S = 2.0           # status "gnss" while the last usable fix is at most this old
GNSS_COLS = ("gps_lat", "gps_lon", "gps_alt_m", "gps_speed_ms", "gps_heading_deg", "gps_accuracy_m", "gps_satellites")
NOTE = "development drive, tuned on S3b/S2, not validation"
SIGMA = {"calibrated": False, "definition": "1-sigma ellipse, Mahalanobis<=1, expect 39% in 2D"}
T_ZERO = {
    "definition": "t_s = 0 at the FIRST ROW of the phone CSV; t_s = seconds since then on the phone wall clock "
                  "(column 'DATE (YYYY-MO-DD HH-MI-SS_SSS)'). Phone data only, no VBOX.",
    "source": "data_loader.py:66 _wallclock_timestamp_s, :128 df['timestamp_s'] = wall_s — the same load_smartphone() "
              "that check_outage.load_drive uses (check_outage.py:45-50)",
}
ORIGIN_SOURCE = "first phone row with a finite lat/lon (vehicle_dr.py:515-516; same rule as check_outage.origin)"
WARMUP_SOURCE = ("warmup = before the first GNSS course initialises the heading (vehicle_dr.py:609 / :794-796, "
                 "result['psi_init_time']) or between an IMU release and the end of its launch calibration "
                 "(evaluated launch_n_after samples after the release, vehicle_dr.py:707-725, result['launches'] "
                 "t_release..t_eval)")


# ── small helpers ─────────────────────────────────────────────────────────────
def _r(x, nd):
    """Round to nd decimals; None for missing / non-finite (strict JSON has no NaN)."""
    if x is None:
        return None
    x = float(x)
    return round(x, nd) if math.isfinite(x) else None


def bearing_deg(psi_enu_deg):
    """vehicle_dr heading (ENU degrees, counter-clockwise from East) -> bearing in [0, 360), clockwise from North."""
    return float(vehicle_dr.psi_to_bearing_deg(np.radians(psi_enu_deg)))


def ellipse(ee, nn, en):
    """1-sigma ellipse of the East/North covariance [[ee, en], [en, nn]] (m^2).
    Returns (sigma_major_m, sigma_minor_m, angle_deg): angle = direction of the MAJOR axis, clockwise from North, [0, 180)."""
    tr, det = ee + nn, ee * nn - en * en
    d = math.sqrt(max(tr * tr / 4.0 - det, 0.0))
    l1, l2 = max(tr / 2.0 + d, 0.0), max(tr / 2.0 - d, 0.0)
    th_enu = 0.5 * math.atan2(2.0 * en, ee - nn)              # major axis, radians counter-clockwise from East
    ang = (90.0 - math.degrees(th_enu)) % 180.0
    return math.sqrt(l1), math.sqrt(l2), ang


def new_fix_mask(lat, lon):
    """NEW phone fix = lat or lon changed (row 0 counts) — the vehicle_dr.py:549-553 / check_outage.new_fix_rows rule."""
    return np.r_[True, (np.diff(lat) != 0) | (np.diff(lon) != 0)] & np.isfinite(lat) & np.isfinite(lon)


def phone_csv(drive):
    base = os.path.join(get_dataset_root(), "Synchronised V abd S datasets", "Categorised IOVNB Dataset",
                        "S (Driver A)", drive)
    return os.path.join(base, f"S-{drive}.csv")


def check_input(drive, csv_path):
    if drive in SEALED:
        raise SystemExit(f"refusing {drive}: {SEALED[drive]} (sealed)")
    if os.path.basename(csv_path).upper().startswith("V-"):
        raise SystemExit(f"refusing {csv_path}: VBOX files are scoring-only and never an export input")


# ── GNSS withholding (the single outage mechanism) ───────────────────────────
def withhold_fixes(s_df, outages):
    """Copy of s_df with every phone fix inside an outage window deleted. Rows that still repeat a deleted fix get the
    last kept fix's values (or NaN before any kept fix), so the filter sees no new fix until the first one after the window.
    Returns (clean_df, info) with info = per-outage dict(last_fix_s, first_fix_after_s, withheld_fix_count)."""
    ts = s_df["timestamp_s"].values.astype(float)
    lat, lon = s_df["gps_lat"].values.astype(float), s_df["gps_lon"].values.astype(float)
    is_fix = new_fix_mask(lat, lon)
    inside = np.zeros(len(ts), dtype=bool)
    for a, b in outages:
        inside |= (ts >= a) & (ts <= b)
    withheld = is_fix & inside
    idx = np.arange(len(ts))
    src = np.maximum.accumulate(np.where(is_fix, idx, -1))                 # the fix each row is repeating
    keep = np.maximum.accumulate(np.where(is_fix & ~withheld, idx, -1))    # the last fix that is NOT withheld
    rows = np.flatnonzero((src >= 0) & withheld[np.maximum(src, 0)])
    clean = s_df.copy()
    for c in GNSS_COLS:
        if c in clean:
            v = clean[c].values.astype(float).copy()
            k = keep[rows]
            v[rows] = np.where(k >= 0, v[np.maximum(k, 0)], np.nan)
            clean[c] = v
    fix_t = ts[is_fix]
    info = []
    for a, b in outages:
        before, after = fix_t[fix_t < a], fix_t[fix_t > b]
        info.append(dict(last_fix_s=float(before[-1]) if len(before) else None,
                         first_fix_after_s=float(after[0]) if len(after) else None,
                         withheld_fix_count=int(np.sum(withheld & (ts >= a) & (ts <= b)))))
    return clean, info


# ── causal frames ─────────────────────────────────────────────────────────────
ROW_KEYS = ("positions", "velocities", "headings", "cov_matrix", "stationary")


def first_emitted(clean, res, params):
    """Per-output-row values as FIRST emitted. Only rows rewritten by a replay differ from `res`; for replay k (in time
    order) the filter is re-run truncated at the row just before it fired, and every row of its span not already taken
    from an earlier replay's truncated run is read from there (rows not rewritten before replay k are still first-emitted)."""
    rows = {k: list(res[k]) for k in ROW_KEYS}
    ts = clean["timestamp_s"].values.astype(float)
    done = set()
    for rep in sorted(res["replay_log"], key=lambda r: r["i_now"]):
        i_entry, i_now = rep["i_entry"], rep["i_now"]
        t_cut = float(ts[i_now - 1])
        if np.sum(ts <= t_cut) != i_now:                         # duplicate timestamps would make t_end ambiguous
            raise RuntimeError(f"cannot truncate cleanly before the replay at row {i_now}")
        tr = vehicle_dr.run_pipeline(clean, None, outage_window=None, params=params, t_end=t_cut)
        for i in range(i_entry, i_now):
            k = i - 1                                            # output row k <-> input row i (outputs start at row 1)
            if k >= 0 and k not in done:
                for key in ROW_KEYS:
                    rows[key][k] = tr[key][k]
                done.add(k)
    return rows, len(done)


def build_trip(s_df, drive, outages=DEFAULT_OUTAGES, params=None):
    """Everything except the provenance block. Returns (trip_dict, clean_df, res) — res = the plain filter result."""
    params = params or vehicle_dr.VDRParams()
    outages = tuple((float(a), float(b)) for a, b in outages)
    clean, oinfo = withhold_fixes(s_df, outages)
    res = vehicle_dr.run_pipeline(clean, None, outage_window=None, params=params)
    rows, n_rewritten = first_emitted(clean, res, params)

    ts_in = clean["timestamp_s"].values.astype(float)
    lat_in, lon_in = clean["gps_lat"].values.astype(float), clean["gps_lon"].values.astype(float)
    sats = clean["gps_satellites"].values.astype(float) if "gps_satellites" in clean else np.full(len(ts_in), np.nan)
    acc = clean["gps_accuracy_m"].values.astype(float) if "gps_accuracy_m" in clean else np.full(len(ts_in), np.nan)
    fix = new_fix_mask(lat_in, lon_in)
    usable = fix & ~(np.isfinite(sats) & (sats < params.min_satellites))      # vehicle_dr.py:728-729 (no outage left)
    usable_t = ts_in[usable]

    t = np.asarray(res["timestamps"], float)
    lat0, lon0 = float(res["lat0"]), float(res["lon0"])
    cos0 = math.cos(math.radians(lat0))
    psi0 = res["psi_init_time"]
    launch_iv = [(L["t_release"], L["t_eval"]) for L in res["launches"] if "t_eval" in L]
    launch_ok_t = {round(L["t_eval"], 6) for L in res["launches"] if L.get("accepted")}
    replay_by_t = {round(r["t"], 6): r for r in res["replay_log"]}
    usable_set = {round(x, 6) for x in usable_t}

    frames, corrections = [], []
    prev = None
    for k in range(len(t)):
        tk = float(t[k])
        la, lo = rows["positions"][k]
        ee, nn, en = rows["cov_matrix"][k]
        smaj, smin, ang = ellipse(ee, nn, en)
        j = int(np.searchsorted(usable_t, tk, side="right")) - 1
        age = tk - float(usable_t[j]) if j >= 0 else None
        if psi0 is None or tk < psi0 or any(a <= tk <= b for a, b in launch_iv):
            status = "warmup"
        elif age is not None and age <= GNSS_FRESH_S:
            status = "gnss"
        else:
            status = "dr"
        fr = dict(t_s=_r(tk, 3), lat=_r(la, 7), lon=_r(lo, 7), bearing_deg=_r(bearing_deg(rows["headings"][k]) % 360.0, 1),
                  speed_mps=_r(rows["velocities"][k], 2), sigma_major_m=_r(smaj, 2), sigma_minor_m=_r(smin, 2),
                  ellipse_angle_deg=_r(ang, 1), cov_en_m2=[_r(ee, 2), _r(nn, 2), _r(en, 2)],
                  fix_age_s=_r(age, 2), status=status, stationary=bool(rows["stationary"][k]))
        if fr["bearing_deg"] is not None:
            fr["bearing_deg"] = fr["bearing_deg"] % 360.0                   # 359.96 rounds to 360.0 -> 0.0
        if fr["ellipse_angle_deg"] is not None:
            fr["ellipse_angle_deg"] = fr["ellipse_angle_deg"] % 180.0
        if prev is not None:
            dn = math.radians(la - prev[0]) * vehicle_dr.R_EARTH
            de = math.radians(lo - prev[1]) * vehicle_dr.R_EARTH * cos0
            jump = math.hypot(de, dn)
            if jump > JUMP_M:
                key = round(tk, 6)
                c = dict(t_s=_r(tk, 3), **{"from": [_r(prev[0], 7), _r(prev[1], 7)]}, to=[_r(la, 7), _r(lo, 7)],
                         jump_m=_r(jump, 2))
                if key in replay_by_t:
                    rp = replay_by_t[key]
                    c.update(cause="replay", replaced_span_s=[_r(rp["t_enter"], 3), _r(rp["t"], 3)])
                elif key in launch_ok_t:
                    c["cause"] = "launch_cal"
                elif key in usable_set:
                    c["cause"] = "gnss_rejoin"
                else:
                    c["cause"] = "other"
                corrections.append(c)
        prev = (la, lo)
        frames.append(fr)

    gnss = [dict(t_s=_r(tf, 3), lat=_r(a, 7), lon=_r(b, 7), accuracy_m=_r(c, 2))
            for tf, a, b, c in zip(ts_in[fix], lat_in[fix], lon_in[fix], acc[fix])]
    outs = [dict(start_s=a, end_s=b, kind="simulated", **info) for (a, b), info in zip(outages, oinfo)]
    for o in outs:
        o["last_fix_s"], o["first_fix_after_s"] = _r(o["last_fix_s"], 3), _r(o["first_fix_after_s"], 3)
    trip = dict(
        meta=dict(schema=SCHEMA, schema_status=SCHEMA_STATUS, drive=drive, filter="vehicle_dr",
                  params=dataclasses.asdict(params),
                  origin=dict(lat=_r(lat0, 7), lon=_r(lon0, 7), source=ORIGIN_SOURCE),
                  t_zero=dict(T_ZERO, wall_clock_start_time_of_day_s=_r(s_df.attrs.get("wall_clock_start_s"), 3)),
                  duration_s=_r(t[-1], 3), referenceUsed=False, note=NOTE, sigma=SIGMA,
                  status_rule=dict(gnss=f"fix_age_s <= {GNSS_FRESH_S}", dr="otherwise", warmup=WARMUP_SOURCE),
                  correction_rule=f"displayed step > {JUMP_M} m between consecutive frames",
                  replays=dict(count=len(res["replay_log"]), rewritten_rows_not_shown=n_rewritten)),
        outages=outs, frames=frames, gnss=gnss, corrections=corrections)
    return trip, clean, res


# ── provenance + output ───────────────────────────────────────────────────────
def _sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def provenance():
    files = {"export_vdr.py": os.path.join(HERE, "export_vdr.py"), "vehicle_dr.py": os.path.join(HERE, "vehicle_dr.py")}
    def git(*a):
        try:
            return subprocess.run(["git", *a], cwd=HERE, capture_output=True, text=True, timeout=30).stdout.strip()
        except Exception:
            return None
    dirty = git("status", "--porcelain", "--", *files.values())
    return dict(git_commit=git("rev-parse", "HEAD"), sha256={k: _sha256(p) for k, p in files.items()},
                dirty=bool(dirty) if dirty is not None else None,
                generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))


def dumps(trip):
    return json.dumps(trip, allow_nan=False, separators=(",", ":"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("drive")
    ap.add_argument("--csv", help="phone CSV (default: the IO-VNBD S-<drive>.csv)")
    ap.add_argument("--outage", action="append", help="start:end in s (repeatable; default 200:260)")
    a = ap.parse_args(argv)
    csv_path = a.csv or phone_csv(a.drive)
    check_input(a.drive, csv_path)
    outages = tuple(tuple(float(x) for x in o.split(":")) for o in a.outage) if a.outage else DEFAULT_OUTAGES
    s_df = load_smartphone(csv_path)
    trip, _, _ = build_trip(s_df, a.drive, outages)
    trip["meta"].update(provenance())
    out = os.path.join(HERE, "exports", f"{a.drive}_aeris_trip_v1.json")
    text = dumps(trip)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {out}: {len(trip['frames'])} frames, {len(trip['gnss'])} fixes, {len(trip['corrections'])} corrections, "
          f"{len(text) / 1e6:.2f} MB")
    return out


if __name__ == "__main__":
    main()

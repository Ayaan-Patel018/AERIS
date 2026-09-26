"""
dev_eval.py — development-window evaluation for the H / I steps (drive registry v2).

Scores one VDRParams on
  * S3b dev windows  : the 11 sliding 60 s outages that END before 200 s (starts 30-130)
  * S2  dev windows  : the 861 pre-registered S2 windows (run in parallel worker processes)
  * S3b mini-outages : mean error of the 20 intervals ending <= 200 s
  * S3b event 200-260 s : mean / end / path ratio (REPORT ONLY, never tuned on)
  * launch-from-stop : dev windows (S3b + S2 pooled) that START within 10 s after an IMU standstill
hold-last-fix and last-fix + const-v are scored on exactly the same windows. VBOX is used for scoring only.
Noise rule: windows overlap heavily; a change < 5 % on the median end error is "no change".

    python backend/dev_eval.py --name "E0 default"
    python backend/dev_eval.py --name "H1a" --set use_gyro_scale=True --set gs_window_s=300
    python backend/dev_eval.py --drives S3b                     # S3b only (fast)
Windows console: set PYTHONUTF8=1 when piping.
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import fields, replace
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import check_outage as co
import window_plan
import vehicle_dr
from vehicle_dr import VDRParams

DEV_DRIVES = ("S3b", "S2")
_LOADED = {}


def load_dev(drive):
    """(s_df, v_df, offset, Truth, registered window starts) — cached per process."""
    if drive not in _LOADED:
        s, v, off = co.load_drive(drive)
        lat0, lon0 = co.origin(s)
        end_before = co.OUTAGE[0] if drive == "S3b" else None          # S3b: tune only windows that END before 200 s
        starts = window_plan.plan_windows(window_plan.usable_fix_times(s), window_plan.drive_end(s, v, off), end_before)
        _LOADED[drive] = (s, v, off, co.Truth.from_vehicle(v, lat0, lon0, off), starts)
    return _LOADED[drive]


def _task(args):
    drive, starts, params, run_kw = args
    s, _, _, truth, _ = load_dev(drive)
    return co.window_benchmark(s, truth, starts, params=params, run_kw=run_kw)


def window_rows(drive, params, pool=None, workers=4, run_kw=None, stride=1):
    """stride > 1 = screening run: every stride-th registered window of a drive with more than 24 windows (S2). S3b is never thinned."""
    starts = load_dev(drive)[4] if pool is None else _starts_only(drive)
    if len(starts) > 24:
        starts = starts[::stride]
    if pool is None or len(starts) <= 24:
        return _task((drive, starts, params, run_kw))
    k = workers * 3
    chunks = [starts[i::k] for i in range(k)]                            # interleaved: window cost grows with the start time
    rows = [r for part in pool.map(_task, [(drive, c, params, run_kw) for c in chunks if c]) for r in part]
    return sorted(rows, key=lambda r: r["start"])


def _starts_only(drive):
    if drive == "S3b":
        return load_dev(drive)[4]
    s, v, off = co.load_drive(drive)
    return window_plan.plan_windows(window_plan.usable_fix_times(s), window_plan.drive_end(s, v, off), None)


def s3b_extras(params, run_kw=None):
    """S3b mini-outage stats and the 200-260 s event (report only) for `params`."""
    s, v, off, truth, _ = load_dev("S3b")
    kw = run_kw or {}
    sub = s[s["timestamp_s"] <= 201.0]
    sub.attrs = s.attrs
    res = vehicle_dr.run_pipeline(sub, None, outage_window=None, params=params, t_end=201.0, **kw)
    mini = co.mini_outage(res, sub, v, off, t_max=200.0)
    ev = vehicle_dr.run_pipeline(s, None, outage_window=co.OUTAGE, params=params, t_end=co.OUTAGE[1], **kw)
    t = np.array(ev["timestamps"])
    m = (t >= co.OUTAGE[0]) & (t <= co.OUTAGE[1])
    sc = co.score_track(truth, t[m], co._res_enu(ev, m), np.array(ev["velocities"])[m], np.array(ev["cov_matrix"])[m])
    return dict(mini_mean=float(np.mean([r["aeris"] for r in mini])), mini_median=float(np.median([r["aeris"] for r in mini])),
                mini_cov=100.0 * float(np.mean([r["inside"] for r in mini])),
                event=dict(mean=sc["mean_err"], end=sc["end_err"], ratio=sc["path_ratio"],
                           along_end=sc["along_end"], cross_end=sc["cross_end"]))


def summ(rows, who):
    """median / p90 end error, median |cross| and |along| at the end, median mean error, median path ratio, median 1-sigma %."""
    if not rows:
        return dict(n=0)
    g = lambda key: np.array([r[who].get(key, np.nan) for r in rows], dtype=float)
    end = g("end_err")
    return dict(n=len(rows), med_end=float(np.median(end)), p90_end=float(np.percentile(end, 90)),
                med_cross=float(np.nanmedian(g("abs_cross_end"))), med_along=float(np.nanmedian(g("abs_along_end"))),
                med_mean=float(np.median(g("mean_err"))), med_ratio=float(np.nanmedian(g("path_ratio"))),
                med_cov=float(np.nanmedian(g("inside"))) if who == "vdr" else float("nan"))


def evaluate(params, pool=None, drives=DEV_DRIVES, workers=4, run_kw=None, extras=True, stride=1):
    out = dict(windows={d: window_rows(d, params, pool, workers, run_kw, stride) for d in drives})
    if extras and "S3b" in drives:
        out.update(s3b_extras(params, run_kw))
    pooled = [r for d in drives for r in out["windows"][d]]
    out["launch"] = [r for r in pooled if r["stopped_recently"]]
    out["pooled"] = pooled
    return out


def _f(x, w=6, d=1):
    return f"{x:{w}.{d}f}" if np.isfinite(x) else " " * (w - 1) + "-"


def print_table(name, out, drives=DEV_DRIVES, baselines=True):
    """Compact plan-table rows: hold, const-v (same windows) and the filter."""
    hdr = "step | " + " | ".join(f"{d} dev windows: med end / p90 end / med |cross| / med |along|" for d in drives)
    hdr += " | pooled med end | S3b mini mean | launch-from-stop med end (n) | event mean / end / path ratio | 1σ mini / S3b-win / S2-win"
    if baselines:
        print(hdr)
    for who, label in (("hold", "hold-last-fix"), ("cv", "const-v"), ("vdr", name)):
        if who != "vdr" and not baselines:
            continue
        cells = []
        for d in drives:
            s = summ(out["windows"][d], who)
            cells.append(f"{_f(s['med_end'])} / {_f(s['p90_end'])} / {_f(s['med_cross'])} / {_f(s['med_along'])}" if s["n"] else "-")
        pooled = summ(out["pooled"], who)
        lau = summ(out["launch"], who)
        if who == "vdr" and "mini_mean" in out:
            ev = out["event"]
            tail = (f"{out['mini_mean']:.2f} | {_f(lau.get('med_end', np.nan))} ({lau['n']}) | "
                    f"{ev['mean']:.2f} / {ev['end']:.2f} / {ev['ratio']:.2f} | "
                    f"{out['mini_cov']:.0f}% / " + " / ".join(f"{summ(out['windows'][d], 'vdr')['med_cov']:.0f}%" for d in drives))
        else:
            tail = f"- | {_f(lau.get('med_end', np.nan))} ({lau['n']}) | - | -"
        print(f"{label} | " + " | ".join(cells) + f" | {_f(pooled['med_end'])} | {tail}")


def parse_set(params, items):
    kinds = {f.name: f.type for f in fields(VDRParams)}
    upd = {}
    for it in items or []:
        k, v = it.split("=", 1)
        if k not in kinds:
            raise SystemExit(f"unknown VDRParams field: {k}")
        cur = getattr(params, k)
        upd[k] = (v.lower() in ("1", "true", "yes")) if isinstance(cur, bool) else (type(cur)(float(v) if v.lower() in ("inf", "all") else v))
    return replace(params, **upd)


def _lower_priority():
    """Workers run at below-normal priority so an interactive machine stays responsive (Windows; no-op elsewhere)."""
    try:
        import ctypes
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)   # BELOW_NORMAL_PRIORITY_CLASS
    except Exception:
        pass


def open_pool(workers=4):
    return ProcessPoolExecutor(max_workers=workers, initializer=_lower_priority)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="vehicle_dr")
    ap.add_argument("--set", action="append", help="VDRParams override, e.g. --set turn_noise=0.3 (repeatable)")
    ap.add_argument("--config", action="append", help="NAME|key=value|key=value ... (repeatable): several parameter sets evaluated with one worker pool; "
                                                      "overrides are applied on top of --set")
    ap.add_argument("--drives", nargs="+", default=list(DEV_DRIVES))
    ap.add_argument("--workers", type=int, default=4, help="worker processes (each holds S2: ~300 MB; keep small on a shared machine)")
    ap.add_argument("--s2-stride", type=int, default=1, help="screening: use every k-th registered S2 window (1 = the full 861-window list)")
    ap.add_argument("--json", default=None, help="write the summary numbers to this file")
    a = ap.parse_args()
    base_p = parse_set(VDRParams(), a.set)
    cfgs = [(c.split("|")[0], parse_set(base_p, c.split("|")[1:])) for c in a.config] if a.config else [(a.name, base_p)]
    drives = tuple(a.drives)
    dump = {}
    with open_pool(a.workers) as pool:
        for i, (nm, p) in enumerate(cfgs):
            t0 = time.time()
            out = evaluate(p, pool, drives, a.workers, stride=a.s2_stride)
            print_table(nm, out, drives, baselines=(i == 0))
            print(f"  ({time.time() - t0:.0f} s; S3b n={len(out['windows'].get('S3b', []))}, S2 n={len(out['windows'].get('S2', []))}"
                  f"{' (stride ' + str(a.s2_stride) + ' screening)' if a.s2_stride > 1 else ''}, "
                  f"launch-from-stop n={len(out['launch'])})", flush=True)
            dump[nm] = dict(summary={d: {w: summ(out['windows'][d], w) for w in ('vdr', 'cv', 'hold')} for d in drives},
                            **{k: out[k] for k in ('mini_mean', 'mini_cov', 'event') if k in out})
    if a.json:
        json.dump(dump, open(a.json, "w"), indent=1)

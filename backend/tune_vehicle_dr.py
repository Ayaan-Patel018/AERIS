"""
tune_vehicle_dr.py — tuning harness for vehicle_dr. TUNES ONLY ON THE S3b MINI-OUTAGES (intervals between
consecutive new phone fixes ending <= 200 s). The 200-260 s outage and S1 are never used here.

Selection rule (fixed in advance): among grid points whose mini-outage 1-sigma coverage is within
[cov_lo, cov_hi] % (target ~39 %), take the lowest mean error; if none qualifies, the one closest to 39 %.
Overfitting check: leave-one-interval-out (LOO) — for each interval, re-select on the other intervals and
score the held-out one. LOO mean >> in-sample mean means the grid is fitting noise.

    python backend/tune_vehicle_dr.py                      # coarse default grid for the core noise parameters
"""
import itertools
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from dataclasses import replace
import check_outage
import vehicle_dr
from vehicle_dr import VDRParams

COV_LO, COV_HI, COV_TARGET = 30.0, 50.0, 39.0


class Evaluator:
    def __init__(self, drive="S3b", t_max=200.0):
        s_df, v_df, off = check_outage.load_drive(drive)
        self.t_max = t_max
        self.s = s_df[s_df["timestamp_s"] <= t_max + 1.0].reset_index(drop=True)   # causal filter: safe to truncate
        self.s.attrs = s_df.attrs
        self.v, self.off = v_df, off

    def run(self, params: VDRParams, **kw):
        res = vehicle_dr.run_pipeline(self.s, None, outage_window=None, params=params, t_end=self.t_max + 1.0, **kw)
        rows = check_outage.mini_outage(res, self.s, self.v, self.off, t_max=self.t_max)
        return rows, res

    @staticmethod
    def arrays(rows):
        return (np.array([r["aeris"] for r in rows]), np.array([r["inside"] for r in rows], dtype=float),
                np.array([r["cv"] for r in rows]))


def _select(cands, idx=None):
    """cands: list of (params, err[n], inside[n]). Returns index of the chosen candidate using intervals idx."""
    best, best_key = None, None
    for k, (_, err, ins) in enumerate(cands):
        sl = slice(None) if idx is None else idx
        cov = 100.0 * ins[sl].mean()
        mean = err[sl].mean()
        ok = COV_LO <= cov <= COV_HI
        key = (0, mean) if ok else (1, abs(cov - COV_TARGET) + 1e-3 * mean)
        if best_key is None or key < best_key:
            best, best_key = k, key
    return best


def grid_search(ev: Evaluator, base: VDRParams, grid: dict, run_kw=None, verbose=True):
    keys = list(grid)
    cands = []
    for combo in itertools.product(*[grid[k] for k in keys]):
        p = replace(base, **dict(zip(keys, combo)))
        rows, _ = ev.run(p, **(run_kw or {}))
        err, ins, _ = ev.arrays(rows)
        cands.append((p, err, ins))
        if verbose:
            print(f"  {dict(zip(keys, combo))}: mean {err.mean():6.2f}  median {np.median(err):6.2f}  cov {100*ins.mean():4.0f}%", flush=True)
    n = len(cands[0][1])
    best = _select(cands)
    loo_err, loo_ins = [], []
    for i in range(n):
        idx = np.array([j for j in range(n) if j != i])
        k = _select(cands, idx)
        loo_err.append(cands[k][1][i]); loo_ins.append(cands[k][2][i])
    p, err, ins = cands[best]
    return dict(params=p, keys=keys, err=err, cov=100.0 * ins.mean(),
                loo_mean=float(np.mean(loo_err)), loo_cov=100.0 * float(np.mean(loo_ins)),
                cands=cands, best_index=best)


def summarize(name, r):
    e = r["err"]
    return (f"{name}: mean {e.mean():.2f} / median {np.median(e):.2f} / max {e.max():.2f}  "
            f"LOO mean {r['loo_mean']:.2f}  coverage {r['cov']:.0f}% (LOO {r['loo_cov']:.0f}%)")


if __name__ == "__main__":
    ev = Evaluator("S3b")
    base = VDRParams()
    rows, _ = ev.run(base)
    e, ins, cv = ev.arrays(rows)
    print(f"untuned defaults: mean {e.mean():.2f} / median {np.median(e):.2f} / max {e.max():.2f}  coverage {100*ins.mean():.0f}%   (CV baseline {cv.mean():.2f})")
    grid = dict(rw_v=[0.8, 1.2, 1.5, 2.0, 3.0], turn_noise=[0.1, 0.2, 0.3, 0.5],
                sigma_gnss_speed=[0.3, 0.5, 1.0])
    r = grid_search(ev, base, grid)
    print("\nBEST:", {k: getattr(r["params"], k) for k in r["keys"]})
    print(summarize("tuned", r))

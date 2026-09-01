"""
rts_evaluation.py — Evaluate RTS smoothing and ZARU improvements.

Protocol (locked, per team review — do not deviate):
  1. Tune on S3b only. Report BOTH overall and during-outage-only metrics
     for baseline (real-time full EKF), RTS-smoothed, and RTS+ZARU.
  2. Run S1 exactly ONCE with the final settings as unseen validation.
     Do not iterate on S1 numbers. If S1 looks worse, report it honestly —
     that is itself useful diagnostic information, not a failure to hide.

Why "during outage" is reported separately from "overall" (GPT's point,
correct and important): RTS can benefit enormously from measurements
AFTER the outage ends, which can make the "overall" number look better
without necessarily meaning the hardest, no-GNSS portion improved as much.
Splitting the two prevents accidentally celebrating a misleading average.

Usage:
    python rts_evaluation.py            # runs S3b tuning
    python rts_evaluation.py --s1       # ALSO runs S1 (once, final validation only)
"""

import os, sys, json, argparse
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from data_loader import load_smartphone, load_vehicle, get_dataset_root
from ins_ekf import (run_pipeline, rts_smooth, export_smoothed_json,
                     evaluate_error, latlon_to_enu)

dataset_root = get_dataset_root()

BASE_S3b = os.path.join(
    dataset_root, "Synchronised V abd S datasets",
    "Categorised IOVNB Dataset", "S (Driver A)", "S3b"
)
BASE_S1 = os.path.join(
    dataset_root, "Synchronised V abd S datasets",
    "Categorised IOVNB Dataset", "S (Driver A)", "S1"
)

OUTAGE_WINDOW = (200.0, 260.0)   # the 60s headline scenario


def evaluate_split(result: dict, v_df, outage_window) -> dict:
    """
    Compute BOTH overall and during-outage-only error metrics for one result.
    """
    ev = evaluate_error(result, v_df)
    errors = np.array(ev["errors_m"])
    times  = np.array(ev["timestamps"])

    overall = {
        "mean_m":  float(np.mean(errors)),
        "rmse_m":  float(np.sqrt(np.mean(errors**2))),
        "max_m":   float(np.max(errors)),
        "p95_m":   float(np.percentile(errors, 95)),
        "final_m": float(errors[-1]) if len(errors) else 0.0,
    }

    in_window = (times >= outage_window[0]) & (times <= outage_window[1])
    if in_window.any():
        outage_errors = errors[in_window]
        during_outage = {
            "mean_m": float(np.mean(outage_errors)),
            "rmse_m": float(np.sqrt(np.mean(outage_errors**2))),
            "max_m":  float(np.max(outage_errors)),
            "p95_m":  float(np.percentile(outage_errors, 95)),
        }
    else:
        during_outage = {"mean_m": 0.0, "rmse_m": 0.0, "max_m": 0.0, "p95_m": 0.0}

    return {"overall": overall, "during_outage": during_outage}


def print_comparison_table(label: str, results: dict) -> None:
    print(f"\n{'='*72}")
    print(f"  {label}")
    print(f"{'='*72}")
    print(f"  {'Version':<16} {'Scope':<15} {'Mean':>8} {'RMSE':>8} {'Max':>8} {'P95':>8}")
    print(f"  {'-'*68}")
    for version, split in results.items():
        for scope_name, scope_key in [("overall", "overall"), ("during outage", "during_outage")]:
            m = split[scope_key]
            print(f"  {version:<16} {scope_name:<15} {m['mean_m']:>8.1f} "
                  f"{m['rmse_m']:>8.1f} {m['max_m']:>8.1f} {m['p95_m']:>8.1f}")


def run_full_comparison(s_df, v_df, label: str, outdir_base: str) -> dict:
    """
    Runs: baseline (real-time full EKF), RTS-smoothed, RTS+ZARU-smoothed.
    Returns the 3-way comparison dict for this sequence.
    """
    print(f"\nRunning baseline (real-time, full EKF)...")
    baseline = run_pipeline(s_df, v_df, mode="full",
                            outage_window=OUTAGE_WINDOW,
                            store_smoothing_data=True)

    print(f"Running RTS smoother on baseline forward pass...")
    rts_only = rts_smooth(baseline, baseline["lat0"], baseline["lon0"])

    print(f"Running full EKF + ZARU (forward pass, for RTS+ZARU)...")
    zaru_forward = run_pipeline(s_df, v_df, mode="full",
                                outage_window=OUTAGE_WINDOW,
                                use_zaru=True,
                                store_smoothing_data=True)
    print(f"  ZARU triggered on {zaru_forward['zaru_trigger_count']} / {len(s_df)-1} steps "
          f"({100*zaru_forward['zaru_trigger_count']/(len(s_df)-1):.1f}%)")
    rts_plus_zaru = rts_smooth(zaru_forward, zaru_forward["lat0"], zaru_forward["lon0"])

    results = {
        "baseline (real-time)": evaluate_split(baseline, v_df, OUTAGE_WINDOW),
        "RTS only":             evaluate_split(rts_only, v_df, OUTAGE_WINDOW),
        "RTS + ZARU":           evaluate_split(rts_plus_zaru, v_df, OUTAGE_WINDOW),
    }

    print_comparison_table(f"{label} — 3-way comparison (60s outage)", results)

    # Export all three for the dashboard / further inspection
    outdir = os.path.join(outdir_base, "rts_comparison", label.lower())
    os.makedirs(outdir, exist_ok=True)
    export_smoothed_json(rts_only, outdir=os.path.join(outdir, "rts_only"))
    export_smoothed_json(rts_plus_zaru, outdir=os.path.join(outdir, "rts_plus_zaru"))

    summary_path = os.path.join(outdir, "comparison_summary.json")
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Summary: {summary_path}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--s1", action="store_true",
                       help="ALSO run S1 (unseen validation — run once, final settings only)")
    args = parser.parse_args()

    OUTDIR_BASE = os.path.join(os.path.dirname(__file__), "exports", "evaluation")

    print("Loading S3b (development/tuning sequence)...")
    s_df = load_smartphone(os.path.join(BASE_S3b, "S-S3b.csv"))
    v_df = load_vehicle(os.path.join(BASE_S3b, "V-S3b.csv"))

    s3b_results = run_full_comparison(s_df, v_df, "S3b", OUTDIR_BASE)

    if args.s1:
        print(f"\n{'#'*72}")
        print(f"  RUNNING S1 — UNSEEN VALIDATION, FINAL SETTINGS, RUN ONCE ONLY")
        print(f"  (Per protocol: do NOT iterate on these numbers)")
        print(f"{'#'*72}")

        print("\nLoading S1 (unseen validation sequence)...")
        s1_s_df = load_smartphone(os.path.join(BASE_S1, "S-S1.csv"))
        s1_v_df = load_vehicle(os.path.join(BASE_S1, "V-S1.csv"))

        s1_results = run_full_comparison(s1_s_df, s1_v_df, "S1", OUTDIR_BASE)

        # Honest side-by-side — does the improvement generalize?
        print(f"\n{'='*72}")
        print(f"  GENERALIZATION CHECK — full EKF+RTS+ZARU, overall mean error")
        print(f"{'='*72}")
        s3b_full = s3b_results["RTS + ZARU"]["overall"]["mean_m"]
        s1_full  = s1_results["RTS + ZARU"]["overall"]["mean_m"]
        print(f"  S3b (development): {s3b_full:.1f} m")
        print(f"  S1  (unseen):      {s1_full:.1f} m")
        print(f"  {'Improvement generalizes' if s1_full < 250 else 'Review before claiming generalization'}")

    print("\nDone. All comparison JSONs + summaries in exports/evaluation/rts_comparison/")

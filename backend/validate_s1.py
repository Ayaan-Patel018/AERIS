"""
validate_s1.py — Second sequence validation (Polish 3)
Runs the EXACT same pipeline on S1 (unseen sequence) with NO parameter changes.
This proves we're not cherry-picked/tuned to S3b.

DO NOT tune any parameters based on S1 results.
"""

import os, sys, json
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from data_loader import load_smartphone, load_vehicle
from ins_ekf import (run_all_modes, evaluate_error,
                     extract_reference, extract_gnss_only)

# ── S1 paths ──────────────────────────────────────────────────────────────────
BASE = os.path.join(
    os.path.dirname(__file__), "..",
    "IO-VNBD", "Synchronised V abd S datasets",
    "Categorised IOVNB Dataset", "S (Driver A)", "S1"
)
S_PATH = os.path.join(BASE, "S-S1.csv")
V_PATH = os.path.join(BASE, "V-S1.csv")

# Same outage configs as S3b — same start time, same durations
OUTAGE_START = 200.0
OUTAGE_CONFIGS = {
    "30s":  (OUTAGE_START, OUTAGE_START + 30),
    "60s":  (OUTAGE_START, OUTAGE_START + 60),
    "120s": (OUTAGE_START, OUTAGE_START + 120),
}

OUTDIR = os.path.join(os.path.dirname(__file__), "exports", "validation_s1")

if __name__ == "__main__":
    os.makedirs(OUTDIR, exist_ok=True)

    print("Loading S1 data (unseen validation sequence)...")
    s_df = load_smartphone(S_PATH)
    v_df = load_vehicle(V_PATH)

    print(f"  S1: {len(s_df)} rows, {s_df['timestamp_s'].iloc[-1]:.1f} s")
    print(f"  V1: {len(v_df)} rows, {v_df['timestamp_s'].iloc[-1]:.1f} s")

    # ── run all scenarios ─────────────────────────────────────────────────
    all_records = {}
    colors = {
        "ins_only": "orange", "ins_gnss": "royalblue",
        "ins_nhc": "purple", "full": "green",
    }

    fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)

    for ax, (label, outage) in zip(axes, OUTAGE_CONFIGS.items()):
        print(f"\n  Running {label} outage ({outage[0]}–{outage[1]} s)...")
        results = run_all_modes(s_df, v_df, outage_window=outage)

        records = {}
        for mode, res in results.items():
            ev = evaluate_error(res, v_df)
            records[mode] = {
                "mean_m":  ev["mean_m"],
                "rmse_m":  ev["rmse_m"],
                "max_m":   ev["max_m"],
                "final_m": ev["errors_m"][-1] if ev["errors_m"] else 0.0,
            }
            ax.plot(ev["timestamps"], ev["errors_m"],
                    color=colors[mode], label=mode, lw=1.3)

        ax.axvspan(outage[0], outage[1], alpha=0.12, color="red")
        ax.set_title(f"Outage {label}")
        ax.set_xlabel("Time (s)")
        ax.grid(True, alpha=0.3)
        if ax == axes[0]:
            ax.set_ylabel("Position error (m)")
            ax.legend(fontsize=8)

        all_records[label] = records

        # Print table
        print(f"  {'Mode':<15} {'Mean':>8} {'RMSE':>8} {'Max':>8} {'Final':>8}")
        print(f"  {'-'*44}")
        for mode, r in records.items():
            print(f"  {mode:<15} {r['mean_m']:>8.1f} {r['rmse_m']:>8.1f} "
                  f"{r['max_m']:>8.1f} {r['final_m']:>8.1f}")

        # Improvement
        full_m = records["full"]["mean_m"]
        ins_m  = records["ins_only"]["mean_m"]
        imp = (ins_m - full_m) / ins_m * 100 if ins_m > 0 else 0
        print(f"  Improvement vs INS-only: {imp:.1f}%")

    fig.suptitle("VALIDATION — S1 Sequence (unseen, no parameter tuning)",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    plot_path = os.path.join(OUTDIR, "s1_validation.png")
    plt.savefig(plot_path, dpi=150)
    print(f"\n  Saved: {plot_path}")

    # ── save summary ──────────────────────────────────────────────────────
    summary_path = os.path.join(OUTDIR, "s1_validation_summary.json")
    with open(summary_path, "w") as f:
        json.dump({
            "sequence": "S1 (Driver A, Coventry, 86.3 min)",
            "note": "Unseen validation — zero parameter tuning from S3b",
            "results": all_records,
        }, f, indent=2)
    print(f"  Saved: {summary_path}")

    # ── headline ──────────────────────────────────────────────────────────
    r60 = all_records["60s"]
    full_m = r60["full"]["mean_m"]
    full_max = r60["full"]["max_m"]
    ins_m = r60["ins_only"]["mean_m"]
    imp = (ins_m - full_m) / ins_m * 100
    print(f"\n{'='*60}")
    print(f"  S1 VALIDATION (60s outage):")
    print(f"    Full system: {full_m:.1f} m mean / {full_max:.1f} m max")
    print(f"    vs INS-only: {imp:.1f}% improvement")
    print(f"    (S3b was: 68.9 m mean / 153.4 m max)")
    print(f"{'='*60}")

    if os.environ.get("SHOW_PLOTS") == "1":
        plt.show()
    else:
        plt.close()

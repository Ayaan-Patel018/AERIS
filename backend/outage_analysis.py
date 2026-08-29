"""
outage_analysis.py — Part III + Part V
SIH 26168 backend pipeline.

Part III: Multi-scenario outage evaluation (30s / 60s / 120s).
           Exports all JSON variants + a summary table.

Part V:   Rule-based GNSS Reliability Classifier.
           Uses satellite count, GPS accuracy, position jump,
           velocity inconsistency, and EKF innovation magnitude.
           Honest name: Rule-based classifier, not "trained" — no ML model.

Usage:
    python outage_analysis.py
"""

import os, sys, json
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from data_loader import load_smartphone, load_vehicle
from ins_ekf     import (run_pipeline, run_all_modes, export_json,
                          extract_reference, extract_gnss_only,
                          evaluate_error, latlon_to_enu)

# ── dataset paths ─────────────────────────────────────────────────────────────
BASE = os.path.join(
    os.path.dirname(__file__), "..",
    "IO-VNBD", "Synchronised V abd S datasets",
    "Categorised IOVNB Dataset", "S (Driver A)", "S3b"
)
S_PATH = os.path.join(BASE, "S-S3b.csv")
V_PATH = os.path.join(BASE, "V-S3b.csv")

# ── outage scenarios ──────────────────────────────────────────────────────────
# All three use the same start time so comparison is clean.
OUTAGE_START   = 200.0   # seconds
OUTAGE_CONFIGS = {
    "30s":  (OUTAGE_START, OUTAGE_START + 30),
    "60s":  (OUTAGE_START, OUTAGE_START + 60),
    "120s": (OUTAGE_START, OUTAGE_START + 120),
}
DEMO_SCENARIO  = "60s"   # headline scenario for the SIH presentation


# ═══════════════════════════════════════════════════════════════════════════════
# PART V — Rule-based GNSS Reliability Classifier
# ═══════════════════════════════════════════════════════════════════════════════

class GNSSQualityClassifier:
    """
    Rule-based GNSS Reliability Classifier.

    Inputs (per GPS epoch):
      - satellite count
      - GPS accuracy (m), where available
      - position jump (m from previous fix)
      - velocity inconsistency (|GPS speed - EKF speed|, m/s)
      - innovation magnitude (|GPS position - EKF predicted position|, m)

    Output: 'healthy' | 'degraded' | 'unavailable'

    Thresholds chosen from IO-VNBD paper characteristics and
    standard GNSS quality guidance (HDOP / satellite count heuristics).
    """

    def __init__(self):
        # Thresholds — adjust after observing real data distribution
        self.min_satellites     = 6      # below this → unavailable
        self.deg_satellites     = 8      # below this → degraded
        self.max_accuracy_m     = 10.0   # GPS accuracy > 10m → degraded
        self.max_pos_jump_m     = 50.0   # sudden jump > 50m → degraded
        self.max_vel_incon_ms   = 5.0    # |GPS speed - EKF speed| > 5 m/s → degraded
        self.max_innovation_m   = 30.0   # EKF innovation > 30m → degraded

    def classify(
        self,
        satellites:      float,
        accuracy_m:      float  = None,
        pos_jump_m:      float  = 0.0,
        vel_incon_ms:    float  = 0.0,
        innovation_m:    float  = 0.0,
        gps_available:   bool   = True,
    ) -> str:
        """Classify one GPS epoch."""
        if not gps_available or np.isnan(satellites):
            return "unavailable"

        if satellites < self.min_satellites:
            return "unavailable"

        flags = []

        if satellites < self.deg_satellites:
            flags.append("low_sats")

        if accuracy_m is not None and not np.isnan(accuracy_m):
            if accuracy_m > self.max_accuracy_m:
                flags.append("poor_accuracy")

        if pos_jump_m > self.max_pos_jump_m:
            flags.append("pos_jump")

        if vel_incon_ms > self.max_vel_incon_ms:
            flags.append("vel_incon")

        if innovation_m > self.max_innovation_m:
            flags.append("high_innovation")

        # Two or more flags → degraded; one flag → still degraded (conservative)
        if flags:
            return "degraded"

        return "healthy"

    def classify_sequence(self, s_df, ekf_positions=None) -> list:
        """
        Classify every row in a smartphone DataFrame.
        ekf_positions: list of ENU [E,N] arrays from the EKF (for innovation check).
        Returns list of status strings, one per row.
        """
        statuses = []
        prev_enu = None
        lat0 = s_df["gps_lat"].dropna().iloc[0]
        lon0 = s_df["gps_lon"].dropna().iloc[0]

        for i, row in s_df.iterrows():
            gps_ok = not (np.isnan(row["gps_lat"]) or np.isnan(row["gps_lon"]))

            if not gps_ok:
                statuses.append("unavailable")
                prev_enu = None
                continue

            sats     = row["gps_satellites"]
            acc      = row.get("gps_accuracy_m", np.nan)
            curr_enu = latlon_to_enu(row["gps_lat"], row["gps_lon"], lat0, lon0)

            pos_jump = (np.linalg.norm(curr_enu[:2] - prev_enu[:2])
                        if prev_enu is not None else 0.0)

            gps_spd = row["gps_speed_ms"] if not np.isnan(row["gps_speed_ms"]) else 0.0

            # Innovation magnitude: distance from EKF-predicted position
            if (ekf_positions is not None
                    and i < len(ekf_positions)
                    and ekf_positions[i] is not None):
                innovation = np.linalg.norm(
                    curr_enu[:2] - np.array(ekf_positions[i])[:2]
                )
            else:
                innovation = 0.0

            status = self.classify(
                satellites    = sats,
                accuracy_m    = acc,
                pos_jump_m    = pos_jump,
                vel_incon_ms  = 0.0,     # no EKF speed readily available here
                innovation_m  = innovation,
                gps_available = gps_ok,
            )
            statuses.append(status)
            prev_enu = curr_enu

        return statuses


# ═══════════════════════════════════════════════════════════════════════════════
# PART III — Multi-scenario evaluation and export
# ═══════════════════════════════════════════════════════════════════════════════

def run_evaluation_protocol(s_df, v_df, outage_window, label):
    """
    Run all 4 modes for one outage scenario and return a complete
    evaluation record — locked protocol (same window, all modes).

    Returns dict with metrics for the evaluation table.
    """
    print(f"\n  Running scenario: {label} "
          f"(outage {outage_window[0]}s → {outage_window[1]}s)...")

    all_results = run_all_modes(s_df, v_df, outage_window=outage_window)

    records = {}
    for mode, res in all_results.items():
        ev = evaluate_error(res, v_df)
        records[mode] = {
            "mean_m":   ev["mean_m"],
            "rmse_m":   ev["rmse_m"],
            "max_m":    ev["max_m"],
            "final_m":  ev["errors_m"][-1] if ev["errors_m"] else 0.0,
        }
    return all_results, records


def compute_improvement(records):
    """
    Compute percentage improvement of 'full' mode
    vs 'ins_only' and 'ins_gnss' baselines.
    """
    full_mean  = records["full"]["mean_m"]
    ins_mean   = records["ins_only"]["mean_m"]
    gnss_mean  = records["ins_gnss"]["mean_m"]

    imp_vs_ins  = (ins_mean  - full_mean) / ins_mean  * 100 if ins_mean  > 0 else 0
    imp_vs_gnss = (gnss_mean - full_mean) / gnss_mean * 100 if gnss_mean > 0 else 0
    return imp_vs_ins, imp_vs_gnss


def print_evaluation_table(records, label, outage_window):
    """Print the clean evaluation table for one scenario."""
    print(f"\n  ── Evaluation: {label} "
          f"(outage {outage_window[0]}–{outage_window[1]} s) ──")
    print(f"  {'Mode':<15} {'Mean (m)':>10} {'RMSE (m)':>10} "
          f"{'Max (m)':>10} {'Final (m)':>10}")
    print(f"  {'-'*55}")
    for mode, r in records.items():
        print(f"  {mode:<15} {r['mean_m']:>10.1f} {r['rmse_m']:>10.1f} "
              f"{r['max_m']:>10.1f} {r['final_m']:>10.1f}")

    imp_ins, imp_gnss = compute_improvement(records)
    print(f"\n  Improvement (full vs ins_only):  {imp_ins:+.1f}%")
    print(f"  Improvement (full vs ins_gnss):  {imp_gnss:+.1f}%")
    print(f"\n  Measured result: ES-EKF+GNSS+NHC achieves "
          f"{records['full']['mean_m']:.1f} m mean / "
          f"{records['full']['max_m']:.1f} m max position error "
          f"during the simulated {int(outage_window[1]-outage_window[0])}-second outage.")


def export_scenario(all_results, v_df, s_df, label, outdir_base):
    """Export JSON files for one outage scenario."""
    outdir = os.path.join(outdir_base, f"outage_{label}")
    full_result = all_results["full"]
    export_json(full_result, v_df, s_df, outdir=outdir)
    return outdir


def build_summary_json(all_records, outdir_base):
    """
    Build a compact summary JSON across all three scenarios.
    Frontend can use this to show the multi-scenario comparison.
    """
    summary = {}
    for label, records in all_records.items():
        imp_ins, imp_gnss = compute_improvement(records)
        summary[label] = {
            "outage_duration_s": int(label.replace("s", "")),
            "modes": records,
            "improvement_vs_ins_only_pct":  round(imp_ins,  1),
            "improvement_vs_gnss_only_pct": round(imp_gnss, 1),
        }
    path = os.path.join(outdir_base, "evaluation_summary.json")
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Summary exported: {path}")
    return summary


def plot_multi_scenario(all_scenario_results, v_df, outdir_base):
    """
    One figure, three subplots — one per outage duration.
    Error-vs-time for all 4 modes.
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
    colors = {
        "ins_only": "orange",
        "ins_gnss": "royalblue",
        "ins_nhc":  "purple",
        "full":     "green",
    }

    for ax, (label, (all_results, records)) in zip(
            axes, all_scenario_results.items()):
        outage = OUTAGE_CONFIGS[label]
        for mode, res in all_results.items():
            ev = evaluate_error(res, v_df)
            ax.plot(ev["timestamps"], ev["errors_m"],
                    color=colors[mode], label=mode, lw=1.3)
        ax.axvspan(outage[0], outage[1], alpha=0.12, color="red")
        ax.set_title(f"Outage {label}")
        ax.set_xlabel("Time (s)")
        ax.grid(True, alpha=0.3)
        if ax == axes[0]:
            ax.set_ylabel("Position error (m)")
            ax.legend(fontsize=8)

    fig.suptitle("ES-EKF Position Error — S-S3b Sequence (4-mode ablation)",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(outdir_base, "multi_scenario_comparison.png")
    plt.savefig(path, dpi=150)
    print(f"  Saved: {path}")
    if os.environ.get("SHOW_PLOTS") == "1":
        plt.show()
    else:
        plt.close()


def plot_gnss_quality(s_df, statuses, outdir_base):
    """
    Plot GNSS quality classification over time.
    Shows healthy/degraded/unavailable bands.
    """
    t = s_df["timestamp_s"].values
    color_map = {"healthy": "green", "degraded": "orange", "unavailable": "red"}
    numeric   = {"healthy": 2, "degraded": 1, "unavailable": 0}

    vals = np.array([numeric.get(s, 0) for s in statuses])

    fig, ax = plt.subplots(figsize=(12, 3))
    for label, val in numeric.items():
        mask = vals == val
        if mask.any():
            ax.fill_between(t, 0, 1,
                            where=mask,
                            transform=ax.get_xaxis_transform(),
                            color=color_map[label],
                            alpha=0.4, label=label)
    ax.set_yticks([])
    ax.set_xlabel("Time (s)")
    ax.set_title("GNSS Quality Classification — Rule-based Reliability Classifier")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()
    path = os.path.join(outdir_base, "gnss_quality.png")
    plt.savefig(path, dpi=150)
    print(f"  Saved: {path}")
    if os.environ.get("SHOW_PLOTS") == "1":
        plt.show()
    else:
        plt.close()


# ── main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    OUTDIR_BASE = os.path.join(os.path.dirname(__file__), "exports", "evaluation")
    os.makedirs(OUTDIR_BASE, exist_ok=True)

    print("Loading data...")
    s_df = load_smartphone(S_PATH)
    v_df = load_vehicle(V_PATH)

    # ── Part V: GNSS quality classification ──────────────────────────────
    print("\nRunning GNSS quality classification (Part V)...")
    classifier = GNSSQualityClassifier()
    statuses = classifier.classify_sequence(s_df)

    counts = {k: statuses.count(k) for k in ["healthy", "degraded", "unavailable"]}
    total  = len(statuses)
    print(f"  Healthy:     {counts['healthy']:>5}  ({100*counts['healthy']/total:.1f}%)")
    print(f"  Degraded:    {counts['degraded']:>5}  ({100*counts['degraded']/total:.1f}%)")
    print(f"  Unavailable: {counts['unavailable']:>5}  ({100*counts['unavailable']/total:.1f}%)")

    plot_gnss_quality(s_df, statuses, OUTDIR_BASE)

    # ── Part III: multi-scenario evaluation ──────────────────────────────
    print("\nRunning multi-scenario evaluation (Part III)...")
    all_scenario_results = {}
    all_records = {}

    for label, outage_window in OUTAGE_CONFIGS.items():
        all_results, records = run_evaluation_protocol(
            s_df, v_df, outage_window, label
        )
        print_evaluation_table(records, label, outage_window)
        export_scenario(all_results, v_df, s_df, label, OUTDIR_BASE)

        all_scenario_results[label] = (all_results, records)
        all_records[label] = records

    # ── summary JSON ──────────────────────────────────────────────────────
    summary = build_summary_json(all_records, OUTDIR_BASE)

    # ── headline result (60s — demo scenario) ────────────────────────────
    rec_60 = all_records[DEMO_SCENARIO]
    imp_ins, imp_gnss = compute_improvement(rec_60)
    print(f"\n{'='*60}")
    print(f"  HEADLINE RESULT (SIH demo — {DEMO_SCENARIO} outage):")
    print(f"  ES-EKF + GNSS + NHC:")
    print(f"    Mean position error : {rec_60['full']['mean_m']:.1f} m")
    print(f"    Max  position error : {rec_60['full']['max_m']:.1f} m")
    print(f"    vs INS-only         : {imp_ins:.1f}% improvement")
    print(f"    vs GNSS-only        : {imp_gnss:.1f}% improvement")
    print(f"{'='*60}")

    # ── multi-scenario comparison plot ────────────────────────────────────
    plot_multi_scenario(all_scenario_results, v_df, OUTDIR_BASE)
    print("\nAll done. Check exports/evaluation/ for JSON files and plots.")

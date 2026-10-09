/**
 * BottomGraphs.tsx — Time-series charts (SVG, no external charting library).
 *
 * Charts shown:
 *   1. Position error vs time (GNSS raw vs AERIS InES-EKF vs RTS smoothed)
 *   2. Speed vs time (AERIS EKF)
 *   3. Position uncertainty (1σ) vs time — spikes during outage, decays after
 *
 * GNSS outage bands sourced from REAL driveMetadata.outage_windows — no hardcoded times.
 * Playhead line synced to current scrubber position across all three graphs.
 */
import React from "react";
import { useTrajectoryData } from "../../hooks/useTrajectoryData";
import { useDashboardContext } from "../../context/DashboardContext";

export const BottomGraphs: React.FC = () => {
  const { gt, gnss, fused, smoothed, currentIndex } = useTrajectoryData();
  const { progress, layers, driveMetadata, totalDurationS } = useDashboardContext();

  if (!gt.length || !gnss.length || !fused.length) return null;

  const N = fused.length;

  // Outage bands from real metadata (normalised 0-1 fractions)
  const outageBands = driveMetadata?.outage_windows ?? [];

  // ── Helpers ────────────────────────────────────────────────────────────────
  const pts2path = (vals: number[], mx: number, W = 300, H = 72) =>
    vals
      .map((v, i) => {
        const x  = ((i / Math.max(vals.length - 1, 1)) * W).toFixed(1);
        const sv = isNaN(v) ? 0 : v;
        const sm = isNaN(mx) || mx === 0 ? 1 : mx;
        const y  = Math.max(4, Math.min(H - 2, H - (sv / sm) * (H - 12))).toFixed(1);
        return `${x},${y}`;
      })
      .join(" ");

  const playheadX = (progress * 300).toFixed(1);

  const outageRects = (H = 72) =>
    outageBands.map((ow, i) => (
      <g key={i}>
        <rect
          x={ow.start_t * 300}
          width={Math.max(0.5, (ow.end_t - ow.start_t) * 300)}
          height={H}
          fill="rgba(229,72,77,0.07)"
        />
        <line x1={ow.start_t * 300} y1={0} x2={ow.start_t * 300} y2={H} stroke="#E5484D" strokeWidth="0.7" strokeDasharray="2,2" opacity="0.55" />
        <line x1={ow.end_t   * 300} y1={0} x2={ow.end_t   * 300} y2={H} stroke="#E5484D" strokeWidth="0.7" strokeDasharray="2,2" opacity="0.55" />
      </g>
    ));

  // ── 1. Position error (vs ground truth) ────────────────────────────────────
  const gnssErrPts     = gnss.map((p, i)   => Math.hypot(p.x - (gt[i]?.x ?? p.x), p.y - (gt[i]?.y ?? p.y)));
  const fusedErrPts    = fused.map((p, i)  => Math.hypot(p.x - (gt[i]?.x ?? p.x), p.y - (gt[i]?.y ?? p.y)));
  const smoothedErrPts = (smoothed && smoothed.length)
    ? smoothed.map((p, i) => Math.hypot(p.x - (gt[i]?.x ?? p.x), p.y - (gt[i]?.y ?? p.y)))
    : [];
  const maxErr = Math.max(...gnssErrPts, ...fusedErrPts, ...(smoothedErrPts.length ? smoothedErrPts : []), 1);

  const pathGnssErr     = pts2path(gnssErrPts, maxErr);
  const pathFusedErr    = pts2path(fusedErrPts, maxErr);
  const pathSmoothedErr = smoothedErrPts.length ? pts2path(smoothedErrPts, maxErr) : "";

  const curGnssErr    = gnssErrPts[currentIndex] ?? 0;
  const curFusedErr   = fusedErrPts[currentIndex] ?? 0;
  const curSmoothedErr = smoothedErrPts[currentIndex] ?? 0;

  // ── 2. Speed (EKF, m/s → km/h) ─────────────────────────────────────────────
  const speedPts = fused.map((p) => (p.velocity ?? 0) * 3.6);
  const maxSpeed = Math.max(...speedPts, 1);
  const pathSpeed = pts2path(speedPts, maxSpeed);
  const curSpeed  = speedPts[currentIndex] ?? 0;

  // ── 3. 1σ uncertainty vs time (the key graph for the demo pitch) ─────────────
  const uncPts  = fused.map((p) => p.uncertainty ?? 0);
  const maxUnc  = Math.max(...uncPts, 0.001);
  const pathUnc = pts2path(uncPts, maxUnc);
  const curUnc  = uncPts[currentIndex] ?? 0;

  const graphCard = (
    title: string,
    legend: React.ReactNode,
    currentStat: React.ReactNode,
    svgContent: React.ReactNode
  ) => (
    <div className="graph-card">
      <div className="graph-meta-header">
        <div className="graph-title-wrap">
          <span className="graph-title">{title}</span>
          <span className="graph-legend">{legend}</span>
        </div>
        <div className="graph-current-stats">{currentStat}</div>
      </div>
      <svg className="graph-svg" viewBox="0 0 300 75" preserveAspectRatio="none">
        <rect x="0" y="0" width="300" height="75" fill="#0E0E12" />
        {outageRects(75)}
        <line x1="0" y1="37" x2="300" y2="37" stroke="#1A1A22" strokeWidth="0.5" />
        <line x1="0" y1="65" x2="300" y2="65" stroke="#1A1A22" strokeWidth="0.5" />
        {svgContent}
        <line x1={playheadX} y1="0" x2={playheadX} y2="75" stroke="#FFF" strokeWidth="1" strokeDasharray="2,2" opacity="0.65" />
      </svg>
    </div>
  );

  return (
    <div className="bottom-graphs-container">
      <div style={{ gridColumn: "2 / 3", display: "flex" }}>

        {/* Graph 1: Position Error */}
        {graphCard(
          "POSITION ERROR",
          <>
            <span className="leg-dot cyan" /> GNSS RAW
            <span className="leg-dot orange" /> AERIS EKF
            {layers.smoothed && <><span className="leg-dot" style={{ background: "#A855F7", display: "inline-block", width: 7, height: 7, borderRadius: "50%", marginLeft: 6 }} /> RTS</>}
          </>,
          <>
            <span className="stat-item cyan">RAW: <strong>{curGnssErr.toFixed(2)} m</strong></span>
            <span className="stat-item orange">EKF: <strong>{curFusedErr.toFixed(2)} m</strong></span>
            {layers.smoothed && smoothedErrPts.length > 0 && (
              <span className="stat-item purple" style={{ color: "#A855F7" }}>RTS: <strong>{curSmoothedErr.toFixed(2)} m</strong></span>
            )}
          </>,
          <>
            <polyline points={pathGnssErr}  fill="none" stroke="#2DD4BF" strokeWidth="1.2" opacity="0.7" />
            <polyline points={pathFusedErr}  fill="none" stroke="#F0801E" strokeWidth="1.8" />
            {layers.smoothed && pathSmoothedErr && (
              <polyline points={pathSmoothedErr} fill="none" stroke="#A855F7" strokeWidth="1.6" />
            )}
          </>
        )}

        {/* Graph 2: Speed */}
        {graphCard(
          "SPEED",
          <><span className="leg-dot orange" /> AERIS EKF (km/h)</>,
          <span className="stat-item orange">CURRENT: <strong>{curSpeed.toFixed(1)} km/h</strong></span>,
          <polyline points={pathSpeed} fill="none" stroke="#F0801E" strokeWidth="1.6" />
        )}

        {/* Graph 3: 1σ Uncertainty — key pitch graph */}
        {graphCard(
          "1σ UNCERTAINTY",
          <><span className="leg-dot orange" /> AERIS (m)</>,
          <span className={`stat-item ${curUnc > 0.5 ? "orange" : "ok"}`} style={{ color: curUnc > 0.5 ? "#F0801E" : "var(--status-ok)" }}>
            NOW: <strong>±{curUnc.toFixed(3)} m</strong>
          </span>,
          <polyline points={pathUnc} fill="none" stroke="#F0801E" strokeWidth="1.8" />
        )}

      </div>
    </div>
  );
};

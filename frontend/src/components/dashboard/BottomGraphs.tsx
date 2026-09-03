import React from 'react';
import { useTrajectoryData } from '../../hooks/useTrajectoryData';
import { useGNSSStatus, OUTAGE_START, OUTAGE_END } from '../../hooks/useGNSSStatus';
import { useDashboardContext } from '../../context/DashboardContext';

export const BottomGraphs: React.FC = () => {
  const { gt, gnss, fused, currentIndex } = useTrajectoryData();
  const { isOutage, aerisError, gnssError, currentVelocity, confidence } = useGNSSStatus();
  const { progress } = useDashboardContext();

  if (!gt.length || !gnss.length || !fused.length) return null;

  const N = gnss.length;
  const OS = OUTAGE_START;
  const OE = OUTAGE_END;

  // ── 1. Position Error Data ──────────────────────────────────────
  const errPts = gnss.map((p, i) => Math.sqrt((p.x - gt[i].x)**2 + (p.y - gt[i].y)**2));
  const fusedErrPts = fused.map((p, i) => Math.sqrt((p.x - gt[i].x)**2 + (p.y - gt[i].y)**2));
  const maxErr = Math.max(...errPts, 1);

  const pts2path = (vals: number[], mx: number, width = 300, height = 65) => {
    return vals.map((v, i) => {
      const x = (i / (vals.length - 1) * width).toFixed(1);
      const safeV = isNaN(v) ? 0 : v;
      const safeMx = isNaN(mx) || mx === 0 ? 1 : mx;
      const y = (height - (safeV / safeMx) * (height - 10)).toFixed(1);
      return `${x},${y}`;
    }).join(' ');
  };

  const pathGnssErr = pts2path(errPts, maxErr);
  const pathFusedErr = pts2path(fusedErrPts, maxErr);

  // ── 2. Velocity Data ────────────────────────────────────────────
  const velPts = fused.map((p) => (p.velocity ?? 0) * 3.6);
  const maxVel = Math.max(...velPts, 1);
  const gnssVelPts = velPts.map((v, i) => {
    const t = i / N;
    return (t >= OS && t <= OE) ? null : v;
  });

  let pathGnssVel = '', prevNull = true;
  gnssVelPts.forEach((v, i) => {
    const x = (i / (N - 1) * 300).toFixed(1);
    if (v === null) { prevNull = true; return; }
    const y = (65 - (v / maxVel) * 55).toFixed(1);
    pathGnssVel += prevNull ? `M${x},${y} ` : `L${x},${y} `;
    prevNull = false;
  });

  const pathFusedVel = pts2path(velPts, maxVel);

  // ── 3. Confidence Trend Data ───────────────────────────────────
  const confPts = fused.map((p, i) => {
    const t = i / N;
    if (t >= OS && t <= OE) {
      const progressInOutage = (t - OS) / (OE - OS);
      return Math.max(50, 95 - progressInOutage * 45);
    }
    return 95;
  });
  const pathConf = pts2path(confPts, 100);

  const playheadX = (progress * 300).toFixed(1);

  // Current values
  const curGnssErrStr = `${gnssError.toFixed(2)} m`;
  const curFusedErrStr = `${aerisError.toFixed(2)} m`;
  const curVelStr = `${currentVelocity.toFixed(1)} km/h`;
  const curConfStr = `${confidence.toFixed(0)}%`;

  return (
    <div className="bottom-graphs-container">
      {/* ── GRAPH 1: POSITION ERROR ──────────────────────────── */}
      <div className="graph-card">
        <div className="graph-meta-header">
          <div className="graph-title-wrap">
            <span className="graph-title">POSITION ERROR</span>
            <span className="graph-legend">
              <span className="leg-dot cyan"></span> GNSS RAW
              <span className="leg-dot orange"></span> AERIS ES-EKF
            </span>
          </div>
          <div className="graph-current-stats">
            <span className="stat-item cyan">RAW: <strong>{curGnssErrStr}</strong></span>
            <span className="stat-item orange">EKF: <strong>{curFusedErrStr}</strong></span>
          </div>
        </div>

        <svg className="graph-svg" viewBox="0 0 300 75" preserveAspectRatio="none">
          <defs>
            <linearGradient id="outageShade" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#E5484D" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#E5484D" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          <rect x="0" y="0" width="300" height="75" fill="#0E0E12" />
          {/* Outage Zone */}
          <rect x={OS * 300} width={(OE - OS) * 300} height="75" fill="url(#outageShade)" />
          <line x1={OS * 300} y1="0" x2={OS * 300} y2="75" stroke="#E5484D" strokeWidth="0.8" strokeDasharray="2,2" opacity="0.6" />
          <line x1={OE * 300} y1="0" x2={OE * 300} y2="75" stroke="#E5484D" strokeWidth="0.8" strokeDasharray="2,2" opacity="0.6" />

          {/* Minimal Gridlines */}
          <line x1="0" y1="35" x2="300" y2="35" stroke="#1A1A22" strokeWidth="0.5" />
          <line x1="0" y1="65" x2="300" y2="65" stroke="#1A1A22" strokeWidth="0.5" />

          {/* Curves */}
          <polyline points={pathGnssErr} fill="none" stroke="#2DD4BF" strokeWidth="1.2" opacity="0.7" />
          <polyline points={pathFusedErr} fill="none" stroke="#F0801E" strokeWidth="1.8" />

          {/* Vertical Playhead Sweep Line */}
          <line x1={playheadX} y1="0" x2={playheadX} y2="75" stroke="#FFFFFF" strokeWidth="1" strokeDasharray="2,2" opacity="0.7" />
        </svg>
      </div>

      {/* ── GRAPH 2: VELOCITY ────────────────────────────────── */}
      <div className="graph-card">
        <div className="graph-meta-header">
          <div className="graph-title-wrap">
            <span className="graph-title">VELOCITY</span>
            <span className="graph-legend">
              <span className="leg-dot cyan"></span> GNSS (1 Hz)
              <span className="leg-dot orange"></span> EKF (100 Hz)
            </span>
          </div>
          <div className="graph-current-stats">
            <span className="stat-item orange">CURRENT: <strong>{curVelStr}</strong></span>
          </div>
        </div>

        <svg className="graph-svg" viewBox="0 0 300 75" preserveAspectRatio="none">
          <rect x="0" y="0" width="300" height="75" fill="#0E0E12" />
          <rect x={OS * 300} width={(OE - OS) * 300} height="75" fill="url(#outageShade)" />
          <line x1={OS * 300} y1="0" x2={OS * 300} y2="75" stroke="#E5484D" strokeWidth="0.8" strokeDasharray="2,2" opacity="0.6" />
          <line x1={OE * 300} y1="0" x2={OE * 300} y2="75" stroke="#E5484D" strokeWidth="0.8" strokeDasharray="2,2" opacity="0.6" />

          <line x1="0" y1="35" x2="300" y2="35" stroke="#1A1A22" strokeWidth="0.5" />
          <line x1="0" y1="65" x2="300" y2="65" stroke="#1A1A22" strokeWidth="0.5" />

          <path d={pathGnssVel} fill="none" stroke="#2DD4BF" strokeWidth="1.2" strokeDasharray="3,2" opacity="0.8" />
          <polyline points={pathFusedVel} fill="none" stroke="#F0801E" strokeWidth="1.6" />

          <line x1={playheadX} y1="0" x2={playheadX} y2="75" stroke="#FFFFFF" strokeWidth="1" strokeDasharray="2,2" opacity="0.7" />
        </svg>
      </div>

      {/* ── GRAPH 3: FILTER CONFIDENCE ───────────────────────── */}
      <div className="graph-card">
        <div className="graph-meta-header">
          <div className="graph-title-wrap">
            <span className="graph-title">FILTER CONFIDENCE</span>
            <span className="graph-legend">
              <span className="leg-dot green"></span> ES-EKF HEALTH
            </span>
          </div>
          <div className="graph-current-stats">
            <span className="stat-item green">CONFIDENCE: <strong>{curConfStr}</strong></span>
          </div>
        </div>

        <svg className="graph-svg" viewBox="0 0 300 75" preserveAspectRatio="none">
          <rect x="0" y="0" width="300" height="75" fill="#0E0E12" />
          <rect x={OS * 300} width={(OE - OS) * 300} height="75" fill="url(#outageShade)" />
          <line x1={OS * 300} y1="0" x2={OS * 300} y2="75" stroke="#E5484D" strokeWidth="0.8" strokeDasharray="2,2" opacity="0.6" />
          <line x1={OE * 300} y1="0" x2={OE * 300} y2="75" stroke="#E5484D" strokeWidth="0.8" strokeDasharray="2,2" opacity="0.6" />

          <line x1="0" y1="35" x2="300" y2="35" stroke="#1A1A22" strokeWidth="0.5" />
          <line x1="0" y1="65" x2="300" y2="65" stroke="#1A1A22" strokeWidth="0.5" />

          <polyline points={pathConf} fill="none" stroke="#2DD4BF" strokeWidth="1.6" />

          <line x1={playheadX} y1="0" x2={playheadX} y2="75" stroke="#FFFFFF" strokeWidth="1" strokeDasharray="2,2" opacity="0.7" />
        </svg>
      </div>
    </div>
  );
};

import React from 'react';
import { useTrajectoryData } from '../../hooks/useTrajectoryData';
import { OUTAGE_START, OUTAGE_END } from '../../hooks/useGNSSStatus';

interface ChartsPanelProps {
  isOpen: boolean;
}

export const ChartsPanel: React.FC<ChartsPanelProps> = ({ isOpen }) => {
  const { gt, gnss, fused } = useTrajectoryData();

  if (!gt.length || !gnss.length || !fused.length) return null;

  const N = gnss.length;
  const OS = OUTAGE_START, OE = OUTAGE_END;
  const VB_H = 90; // viewBox height
  const TOP_PAD = 10; // top padding (label area)
  const BOT_PAD = 10; // bottom padding
  const DRAW_H = VB_H - TOP_PAD - BOT_PAD; // drawable height

  // Pre-calculate error paths
  const errPts = gnss.map((p, i) => Math.sqrt((p.x - gt[i].x) ** 2 + (p.y - gt[i].y) ** 2));
  const fusedErrPts = fused.map((p, i) => Math.sqrt((p.x - gt[i].x) ** 2 + (p.y - gt[i].y) ** 2));
  const maxErr = Math.max(
    ...errPts.filter(v => !isNaN(v)),
    ...fusedErrPts.filter(v => !isNaN(v)),
    1
  );

  // pts2path: maps data values into SVG coordinates, clamped to the viewBox
  const pts2path = (vals: number[], mx: number) => {
    return vals.map((v, i) => {
      const x = (i / (vals.length - 1) * 300).toFixed(1);
      const safeV = isNaN(v) ? 0 : Math.max(0, v);
      const safeMx = isNaN(mx) || mx === 0 ? 1 : mx;
      // y grows downward in SVG — clamp to [TOP_PAD, VB_H - BOT_PAD]
      const y = Math.max(TOP_PAD, Math.min(VB_H - BOT_PAD,
        (VB_H - BOT_PAD) - (safeV / safeMx) * DRAW_H
      )).toFixed(1);
      return `${x},${y}`;
    }).join(' ');
  };

  const errPathGnss = pts2path(errPts, maxErr);
  const errPathFused = pts2path(fusedErrPts, maxErr);

  // Velocity — real EKF output (m/s → km/h)
  const velPts = fused.map((p) => (p.velocity ?? 0) * 3.6);
  const gnssVelPts = velPts.map((v, i) => {
    const t = i / N;
    return (t >= OS && t <= OE) ? null : v;
  });
  const maxV = Math.max(...velPts.filter(v => !isNaN(v)), 1);

  let vPath = '', prevNull = true;
  gnssVelPts.forEach((v, i) => {
    const x = (i / (N - 1) * 300).toFixed(1);
    if (v === null) { prevNull = true; return; }
    const y = Math.max(TOP_PAD, Math.min(VB_H - BOT_PAD,
      (VB_H - BOT_PAD) - (Math.max(0, v) / maxV) * DRAW_H
    )).toFixed(1);
    vPath += prevNull ? `M${x},${y} ` : `L${x},${y} `;
    prevNull = false;
  });

  // Fused velocity path (full, for comparison)
  const fusedVPath = pts2path(velPts, maxV);

  return (
    <div className={`charts-panel ${isOpen ? 'open' : ''}`} id="chartsPanel">
      <div className="chart-cell">
        <div className="chart-lbl">POSITION ERROR OVER TIME</div>
        <svg className="chart-svg" viewBox={`0 0 300 ${VB_H}`} preserveAspectRatio="none">
          <rect x="0" y="0" width="300" height={VB_H} fill="none"/>
          {/* Outage region shading */}
          <rect x={OS * 300} width={(OE - OS) * 300} height={VB_H} fill="rgba(229,72,77,.08)"/>
          {/* Axis labels */}
          <text x="2" y={TOP_PAD} fontFamily="IBM Plex Mono" fontSize="6" fill="rgba(255,255,255,.35)">{maxErr.toFixed(0)}m</text>
          <text x="2" y={VB_H - 2} fontFamily="IBM Plex Mono" fontSize="6" fill="rgba(255,255,255,.35)">0m</text>
          {/* Data lines */}
          <polyline points={errPathGnss} fill="none" stroke="rgba(45,212,191,.6)" strokeWidth="1.5"/>
          <polyline points={errPathFused} fill="none" stroke="rgba(240,128,30,.7)" strokeWidth="1.5"/>
          {/* Legend */}
          <text x="298" y={TOP_PAD + 2} fontFamily="IBM Plex Mono" fontSize="6" fill="rgba(45,212,191,.7)" textAnchor="end">GNSS</text>
          <text x="298" y={TOP_PAD + 10} fontFamily="IBM Plex Mono" fontSize="6" fill="rgba(240,128,30,.7)" textAnchor="end">FUSED</text>
        </svg>
      </div>
      <div className="chart-cell">
        <div className="chart-lbl">VELOCITY: AI ESTIMATE vs GNSS</div>
        <svg className="chart-svg" viewBox={`0 0 300 ${VB_H}`} preserveAspectRatio="none">
          <rect x={OS * 300} width={(OE - OS) * 300} height={VB_H} fill="rgba(229,72,77,.08)"/>
          <text x="2" y={TOP_PAD} fontFamily="IBM Plex Mono" fontSize="6" fill="rgba(255,255,255,.35)">{maxV.toFixed(0)} km/h</text>
          <text x="2" y={VB_H - 2} fontFamily="IBM Plex Mono" fontSize="6" fill="rgba(255,255,255,.35)">0</text>
          <polyline points={fusedVPath} fill="none" stroke="rgba(240,128,30,.65)" strokeWidth="1.5"/>
          <path d={vPath} fill="none" stroke="rgba(45,212,191,.55)" strokeWidth="1" strokeDasharray="3,2"/>
          <text x="298" y={TOP_PAD + 2} fontFamily="IBM Plex Mono" fontSize="7" fill="rgba(240,128,30,.7)" textAnchor="end">FUSED</text>
          <text x="298" y={TOP_PAD + 10} fontFamily="IBM Plex Mono" fontSize="7" fill="rgba(45,212,191,.7)" textAnchor="end">GNSS</text>
        </svg>
      </div>
    </div>
  );
};

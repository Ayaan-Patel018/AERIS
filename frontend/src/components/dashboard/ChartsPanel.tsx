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

  // Pre-calculate path strings
  const errPts = gnss.map((p, i) => Math.sqrt((p.x - gt[i].x)**2 + (p.y - gt[i].y)**2));
  const fusedErrPts = fused.map((p, i) => Math.sqrt((p.x - gt[i].x)**2 + (p.y - gt[i].y)**2));
  const maxErr = Math.max(...errPts, 1);

  const pts2path = (vals: number[], mx: number) => {
    return vals.map((v, i) => {
      const x = (i / (vals.length - 1) * 300).toFixed(1);
      const safeV = isNaN(v) ? 0 : v;
      const safeMx = isNaN(mx) || mx === 0 ? 1 : mx;
      const y = (70 - (safeV / safeMx) * 60).toFixed(1); // ample padding from top/bottom
      return `${x},${y}`;
    }).join(' ');
  };

  const errPathGnss = pts2path(errPts, maxErr);
  const errPathFused = pts2path(fusedErrPts, maxErr);

  // Velocity
  const velPts = Array.from({length: N}, (_, i) => 33 + Math.sin(i / N * 22) * 9);
  const gnssVelPts = velPts.map((v, i) => { 
    const t = i / N; 
    return (t >= OS && t <= OE) ? null : v + (Math.random() - 0.5) * 4; 
  });
  const maxV = 50;
  
  let vPath = '', prevNull = true;
  gnssVelPts.forEach((v, i) => {
    const x = (i / (N - 1) * 300).toFixed(1);
    if (v === null) { prevNull = true; return; }
    const y = (70 - (v / maxV) * 60).toFixed(1);
    vPath += prevNull ? `M${x},${y} ` : `L${x},${y} `;
    prevNull = false;
  });

  return (
    <div className={`charts-panel ${isOpen ? 'open' : ''}`} id="chartsPanel">
      <div className="chart-cell">
        <div className="chart-lbl">POSITION ERROR OVER TIME</div>
        <svg className="chart-svg" viewBox="0 0 300 80" preserveAspectRatio="none">
          <rect x="0" y="0" width="300" height="80" fill="none"/>
          <rect x={OS * 300} width={(OE - OS) * 300} height="80" fill="rgba(229,72,77,.08)"/>
          <polyline points={errPathGnss} fill="none" stroke="rgba(45,212,191,.6)" strokeWidth="1.5"/>
          <polyline points={errPathFused} fill="none" stroke="rgba(240,128,30,.7)" strokeWidth="1.5"/>
        </svg>
      </div>
      <div className="chart-cell">
        <div className="chart-lbl">VELOCITY: AI ESTIMATE vs GNSS</div>
        <svg className="chart-svg" viewBox="0 0 300 80" preserveAspectRatio="none">
          <rect x={OS * 300} width={(OE - OS) * 300} height="80" fill="rgba(229,72,77,.08)"/>
          <polyline points={pts2path(velPts, maxV)} fill="none" stroke="rgba(240,128,30,.65)" strokeWidth="1.5"/>
          <path d={vPath} fill="none" stroke="rgba(45,212,191,.55)" strokeWidth="1" strokeDasharray="3,2"/>
          <text x="4" y="12" fontFamily="IBM Plex Mono" fontSize="7" fill="rgba(240,128,30,.7)">AERIS</text>
          <text x="4" y="22" fontFamily="IBM Plex Mono" fontSize="7" fill="rgba(45,212,191,.7)">GNSS</text>
        </svg>
      </div>
    </div>
  );
};

import React from 'react';
import { useTrajectoryData } from '../../hooks/useTrajectoryData';
import { OUTAGE_START, OUTAGE_END } from '../../hooks/useGNSSStatus';
import { useDashboardContext } from '../../context/DashboardContext';

interface ChartsPanelProps {
  isOpen: boolean;
}

export const ChartsPanel: React.FC<ChartsPanelProps> = ({ isOpen }) => {
  const { gt, gnss, fused } = useTrajectoryData();
  const { progress } = useDashboardContext();

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
      const y = (70 - (safeV / safeMx) * 60).toFixed(1);
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
  const maxV = Math.max(...velPts, 1);
  
  let vPath = '', prevNull = true;
  gnssVelPts.forEach((v, i) => {
    const x = (i / (N - 1) * 300).toFixed(1);
    if (v === null) { prevNull = true; return; }
    const y = (70 - (v / maxV) * 60).toFixed(1);
    vPath += prevNull ? `M${x},${y} ` : `L${x},${y} `;
    prevNull = false;
  });

  const playheadX = (progress * 300).toFixed(1);

  return (
    <div className={`charts-panel ${isOpen ? 'open' : ''}`} id="chartsPanel">
      <div className="chart-cell">
        <div className="chart-header">
          <span className="chart-lbl">POSITION ERROR OVER TIME (METERS)</span>
          <div className="chart-legend-pills">
            <span className="pill-gnss">GNSS RAW</span>
            <span className="pill-fused">AERIS ES-EKF</span>
          </div>
        </div>
        <svg className="chart-svg" viewBox="0 0 300 80" preserveAspectRatio="none">
          <defs>
            <linearGradient id="outageGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#E5484D" stopOpacity="0.18" />
              <stop offset="100%" stopColor="#E5484D" stopOpacity="0.03" />
            </linearGradient>
          </defs>
          <rect x="0" y="0" width="300" height="80" fill="#0C0C0F"/>
          {/* Outage shaded boundary */}
          <rect x={OS * 300} width={(OE - OS) * 300} height="80" fill="url(#outageGrad)"/>
          <line x1={OS * 300} y1="0" x2={OS * 300} y2="80" stroke="#E5484D" strokeWidth="0.8" strokeDasharray="2,2"/>
          <line x1={OE * 300} y1="0" x2={OE * 300} y2="80" stroke="#E5484D" strokeWidth="0.8" strokeDasharray="2,2"/>
          
          {/* Grid lines */}
          <line x1="0" y1="40" x2="300" y2="40" stroke="#1A1A22" strokeWidth="0.5"/>
          <line x1="0" y1="70" x2="300" y2="70" stroke="#1A1A22" strokeWidth="0.5"/>

          <text x="4" y="12" fontFamily="JetBrains Mono, monospace" fontSize="6" fill="#888">{maxErr.toFixed(0)}m</text>
          <text x="4" y="74" fontFamily="JetBrains Mono, monospace" fontSize="6" fill="#555">0m</text>

          {/* Data Lines */}
          <polyline points={errPathGnss} fill="none" stroke="#2DD4BF" strokeWidth="1.2" opacity="0.6"/>
          <polyline points={errPathFused} fill="none" stroke="#F0801E" strokeWidth="1.8"/>

          {/* Current Playhead Tracking Line */}
          <line x1={playheadX} y1="0" x2={playheadX} y2="80" stroke="#FFF" strokeWidth="1" strokeDasharray="1,2" opacity="0.8"/>
          <circle cx={playheadX} cy="10" r="2" fill="#F0801E"/>
        </svg>
      </div>

      <div className="chart-cell">
        <div className="chart-header">
          <span className="chart-lbl">VELOCITY PROFILE: EKF vs SATELLITE (KM/H)</span>
          <div className="chart-legend-pills">
            <span className="pill-fused">100 Hz EKF</span>
            <span className="pill-gnss">1 Hz GNSS</span>
          </div>
        </div>
        <svg className="chart-svg" viewBox="0 0 300 80" preserveAspectRatio="none">
          <rect x="0" y="0" width="300" height="80" fill="#0C0C0F"/>
          <rect x={OS * 300} width={(OE - OS) * 300} height="80" fill="url(#outageGrad)"/>
          <line x1={OS * 300} y1="0" x2={OS * 300} y2="80" stroke="#E5484D" strokeWidth="0.8" strokeDasharray="2,2"/>
          <line x1={OE * 300} y1="0" x2={OE * 300} y2="80" stroke="#E5484D" strokeWidth="0.8" strokeDasharray="2,2"/>
          
          <line x1="0" y1="40" x2="300" y2="40" stroke="#1A1A22" strokeWidth="0.5"/>
          <line x1="0" y1="70" x2="300" y2="70" stroke="#1A1A22" strokeWidth="0.5"/>

          <text x="4" y="12" fontFamily="JetBrains Mono, monospace" fontSize="6" fill="#888">{maxV.toFixed(0)} km/h</text>
          <text x="4" y="74" fontFamily="JetBrains Mono, monospace" fontSize="6" fill="#555">0</text>
          
          <polyline points={pts2path(velPts, maxV)} fill="none" stroke="#F0801E" strokeWidth="1.6"/>
          <path d={vPath} fill="none" stroke="#2DD4BF" strokeWidth="1.2" strokeDasharray="3,2" opacity="0.8"/>

          {/* Current Playhead Tracking Line */}
          <line x1={playheadX} y1="0" x2={playheadX} y2="80" stroke="#FFF" strokeWidth="1" strokeDasharray="1,2" opacity="0.8"/>
          <circle cx={playheadX} cy="10" r="2" fill="#2DD4BF"/>
        </svg>
      </div>
    </div>
  );
};

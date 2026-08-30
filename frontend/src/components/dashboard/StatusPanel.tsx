import React, { useState } from 'react';
import { useGNSSStatus } from '../../hooks/useGNSSStatus';

export const StatusPanel: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { isOutage, isRecovered, outageTime, drift } = useGNSSStatus();

  let stateBig = 'GNSS AVAILABLE';
  let stateSub = 'Satellite fix — 11 sats in view';
  let stateCol = 'var(--status-ok)';
  
  if (isOutage) {
    stateBig = 'SIGNAL LOST';
    stateSub = `Dead reckoning — ${outageTime.toFixed(1)}s elapsed`;
    stateCol = 'var(--status-err)';
  } else if (isRecovered) {
    stateBig = 'GNSS REACQUIRED';
    stateSub = 'Fusing back to satellite fix';
  }

  return (
    <div className={`sb-panel ${collapsed ? 'collapsed' : ''}`}>
      <div className="sb-head" onClick={() => setCollapsed(!collapsed)}>
        STATUS <span className="sb-toggle">▾</span>
      </div>
      <div className="sb-body">
        <div className="sb-state-big" style={{ color: stateCol }}>{stateBig}</div>
        <div className="sb-state-sub">{stateSub}</div>
        
        <div className="sb-stat-row">
          <span className="sb-k">STATE</span>
          <span className={`sb-v ${isOutage ? 'err' : 'ok'}`}>{isOutage ? 'LOST' : 'HEALTHY'}</span>
        </div>
        <div className="sb-stat-row">
          <span className="sb-k">SATELLITES</span>
          <span className="sb-v data">{isOutage ? '0' : '11'}</span>
        </div>
        <div className="sb-stat-row">
          <span className="sb-k">OUTAGE TIMER</span>
          <span className="sb-v">{isOutage ? `${outageTime.toFixed(1)}s` : '—'}</span>
        </div>
        <div className="sb-stat-row">
          <span className="sb-k">EST. DRIFT</span>
          <span className="sb-v">{drift.toFixed(3)} m/s</span>
        </div>
      </div>
    </div>
  );
};

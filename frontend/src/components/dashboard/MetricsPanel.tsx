import React, { useState } from 'react';
import { useGNSSStatus } from '../../hooks/useGNSSStatus';

export const MetricsPanel: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { currentVelocity, currentHeading, confidence, aerisError, gnssError, isOutage } = useGNSSStatus();

  return (
    <div className={`sb-panel ${collapsed ? 'collapsed' : ''}`}>
      <div className="sb-head" onClick={() => setCollapsed(!collapsed)}>
        METRICS <span className="sb-toggle">▾</span>
      </div>
      <div className="sb-body">
        <div className="sb-stat-row">
          <span className="sb-k">VELOCITY</span>
          <span className="sb-v data">{currentVelocity.toFixed(1)} km/h</span>
        </div>
        <div className="sb-stat-row">
          <span className="sb-k">HEADING</span>
          <span className="sb-v data">{currentHeading.toString().padStart(3, '0')}°</span>
        </div>
        <div className="sb-stat-row">
          <span className="sb-k">POS ERROR</span>
          <span className="sb-v">
            {isOutage ? `${aerisError.toFixed(1)}m vs ${gnssError.toFixed(1)}m` : '—'}
          </span>
        </div>
        <div className="sb-stat-row">
          <span className="sb-k">VEL ERROR</span>
          <span className="sb-v">0.4 m/s</span>
        </div>
        <div className="sb-stat-row">
          <span className="sb-k">CONFIDENCE</span>
          <span className={`sb-v ${confidence < 72 ? 'warn' : 'ok'}`}>{confidence.toFixed(0)}%</span>
        </div>
        <div className="pbar">
          <div className="pbar-f" style={{ width: `${confidence}%` }}></div>
        </div>
        <div className="sb-stat-row" style={{ marginTop: '8px' }}>
          <span className="sb-k">AI ESTIMATOR</span>
          <span className="sb-v ok">ACTIVE</span>
        </div>
        <div className="sb-stat-row">
          <span className="sb-k">UPDATE RATE</span>
          <span className="sb-v">10 Hz</span>
        </div>
      </div>
    </div>
  );
};

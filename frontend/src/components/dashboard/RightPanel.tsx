import React from 'react';
import { useGNSSStatus } from '../../hooks/useGNSSStatus';

export const RightPanel: React.FC = () => {
  const { 
    aerisError, 
    currentHeading, 
    currentVelocity, 
    confidence 
  } = useGNSSStatus();

  return (
    <aside className="key-values-panel">
      <div className="kv-header">KEY VALUES</div>

      <div className="kv-block">
        <div className="kv-label">POSITION / ACCURACY</div>
        <div className="kv-value data">±{aerisError.toFixed(2)} m</div>
      </div>

      <div className="kv-block">
        <div className="kv-label">HEADING</div>
        <div className="kv-value data">{currentHeading.toFixed(1)}°</div>
      </div>

      <div className="kv-block">
        <div className="kv-label">GROUND SPEED</div>
        <div className="kv-value data">{currentVelocity.toFixed(1)} km/h</div>
      </div>

      <div className="kv-block">
        <div className="kv-label">FILTER CONFIDENCE</div>
        <div className="kv-value data kv-confidence">{confidence.toFixed(0)}%</div>
      </div>
    </aside>
  );
};

import React from 'react';
import { useGNSSStatus } from '../../hooks/useGNSSStatus';
import { useDashboardContext } from '../../context/DashboardContext';
import { Zap } from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { 
    isOutage, 
    confidence, 
    aerisError, 
    drift, 
    currentVelocity, 
    currentHeading 
  } = useGNSSStatus();
  
  const { layers, toggleLayer, simulateOutage, setSimulateOutage } = useDashboardContext();

  const getCardinal = (deg: number): string => {
    const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    return dirs[Math.round(((deg % 360) + 360) % 360 / 45) % 8];
  };

  const carrierBars = isOutage ? 0 : 5;
  const satFixText = isOutage ? 'SEARCHING (0 SATS)' : 'LOCKED (11 SATS)';
  const gnssAvailText = isOutage ? 'UNAVAILABLE (OUTAGE)' : 'AVAILABLE';
  const gnssAvailClass = isOutage ? 'val-warn' : 'val-ok';

  return (
    <aside className="telemetry-sidebar">
      {/* ── GROUP 1: SYSTEM ─────────────────────────────────── */}
      <div className="telem-group">
        <div className="telem-group-title">SYSTEM</div>
        
        <div className="telem-row">
          <span className="telem-label">GNSS Available</span>
          <span className={`telem-value ${gnssAvailClass}`}>{gnssAvailText}</span>
        </div>

        <div className="telem-row">
          <span className="telem-label">RF Carrier Strength</span>
          <div className="telem-rf-wrap">
            <span className="telem-value">{carrierBars}/5 BARS</span>
            <div className="telem-rf-meter">
              {[1, 2, 3, 4, 5].map((b) => (
                <span
                  key={b}
                  className={`rf-segment ${b <= carrierBars ? 'active' : ''} ${isOutage ? 'outage' : ''}`}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="telem-row">
          <span className="telem-label">Satellite Fix</span>
          <span className={`telem-value ${isOutage ? 'val-warn' : ''}`}>{satFixText}</span>
        </div>

        <div className="telem-row">
          <span className="telem-label">Estimated Accuracy</span>
          <span className="telem-value data">±{aerisError.toFixed(2)} m</span>
        </div>

        <div className="telem-row">
          <span className="telem-label">Filter Confidence</span>
          <span className="telem-value val-ok">{confidence.toFixed(0)}%</span>
        </div>
      </div>

      {/* ── GROUP 2: MOTION ─────────────────────────────────── */}
      <div className="telem-group">
        <div className="telem-group-title">MOTION</div>

        <div className="telem-row">
          <span className="telem-label">Ground Speed</span>
          <span className="telem-value data">{currentVelocity.toFixed(1)} km/h</span>
        </div>

        <div className="telem-row">
          <span className="telem-label">Heading</span>
          <span className="telem-value data">{currentHeading.toFixed(1)}° {getCardinal(currentHeading)}</span>
        </div>

        <div className="telem-row">
          <span className="telem-label">Drift Velocity</span>
          <span className={`telem-value data ${drift > 0.1 ? 'val-warn' : ''}`}>
            {drift.toFixed(3)} m/s
          </span>
        </div>
      </div>

      {/* ── GROUP 3: TRAJECTORY LAYERS ──────────────────────── */}
      <div className="telem-group telem-layers-group">
        <div className="telem-group-title">MAP LAYERS</div>
        
        <div className="telem-layer-list">
          <label className="telem-layer-item">
            <input 
              type="checkbox" 
              checked={layers.gt} 
              onChange={() => toggleLayer('gt')} 
              className="layer-toggle-input"
            />
            <div className="layer-toggle-slider slider-gt"></div>
            <span className="layer-name">Ground Truth</span>
          </label>

          <label className="telem-layer-item">
            <input 
              type="checkbox" 
              checked={layers.gnss} 
              onChange={() => toggleLayer('gnss')} 
              className="layer-toggle-input"
            />
            <div className="layer-toggle-slider slider-gnss"></div>
            <span className="layer-name">GNSS Raw</span>
          </label>

          <label className="telem-layer-item">
            <input 
              type="checkbox" 
              checked={layers.fused} 
              onChange={() => toggleLayer('fused')} 
              className="layer-toggle-input"
            />
            <div className="layer-toggle-slider slider-fused"></div>
            <span className="layer-name">AERIS ES-EKF</span>
          </label>

          <label className="telem-layer-item">
            <input 
              type="checkbox" 
              checked={layers.smoothed} 
              onChange={() => toggleLayer('smoothed')} 
              className="layer-toggle-input"
            />
            <div className="layer-toggle-slider slider-smoothed"></div>
            <span className="layer-name">RTS Smoothed (Analysis)</span>
          </label>
        </div>


      </div>
    </aside>
  );
};

import React, { useState } from 'react';
import { useGNSSStatus } from '../../hooks/useGNSSStatus';
import { Gauge, Navigation, Compass, ShieldAlert, Cpu, Zap, ChevronDown, ChevronUp } from 'lucide-react';

export const MetricsPanel: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { currentVelocity, currentHeading, confidence, aerisError, gnssError, isOutage } = useGNSSStatus();

  const compassDirections = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  const headingIdx = Math.round(currentHeading / 45) % 8;
  const compassCardinal = compassDirections[headingIdx];

  return (
    <div className="sb-panel">
      <div className="sb-head" onClick={() => setCollapsed(!collapsed)}>
        <div className="sb-head-left">
          <Gauge size={13} className="sb-head-ic" />
          <span>KINEMATIC METRICS</span>
        </div>
        <span className="sb-toggle">{collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}</span>
      </div>

      {!collapsed && (
        <div className="sb-body">
          {/* Heading Gyro Mini Display */}
          <div className="sb-heading-widget">
            <div className="gyro-disc">
              <div 
                className="gyro-needle" 
                style={{ transform: `rotate(${currentHeading}deg)` }}
              >
                <div className="gyro-pointer-north"></div>
                <div className="gyro-pointer-south"></div>
              </div>
              <div className="gyro-reticle-ring"></div>
              <span className="gyro-cardinal n">N</span>
              <span className="gyro-cardinal e">E</span>
              <span className="gyro-cardinal s">S</span>
              <span className="gyro-cardinal w">W</span>
            </div>
            <div className="gyro-data">
              <div className="gyro-deg">{currentHeading.toString().padStart(3, '0')}°</div>
              <div className="gyro-label">HEADING // {compassCardinal}</div>
              <div className="gyro-sub">{currentVelocity.toFixed(1)} KM/H</div>
            </div>
          </div>

          {/* Dual Error Comparison Block */}
          {isOutage && (
            <div className="sb-error-compare">
              <div className="err-col aeris">
                <span className="err-col-tag">AERIS FUSED</span>
                <span className="err-col-val">{aerisError.toFixed(1)}m</span>
              </div>
              <div className="err-divider">vs</div>
              <div className="err-col gnss">
                <span className="err-col-tag">RAW GNSS DRIFT</span>
                <span className="err-col-val">{gnssError.toFixed(1)}m</span>
              </div>
            </div>
          )}

          {/* Core Metrics Rows */}
          <div className="sb-stat-row">
            <span className="sb-k"><Gauge size={12} /> GROUND SPEED</span>
            <span className="sb-v data">{currentVelocity.toFixed(1)} km/h</span>
          </div>

          <div className="sb-stat-row">
            <span className="sb-k"><Compass size={12} /> BEARING</span>
            <span className="sb-v data">{currentHeading.toString().padStart(3, '0')}° ({compassCardinal})</span>
          </div>

          <div className="sb-stat-row">
            <span className="sb-k"><ShieldAlert size={12} /> ESTIMATED ACCURACY</span>
            <span className={`sb-v ${isOutage ? 'warn' : 'ok'}`}>
              {isOutage ? `±${aerisError.toFixed(1)}m (DR)` : '±0.08m (FIX)'}
            </span>
          </div>

          {/* Confidence Meter */}
          <div className="sb-stat-row" style={{ marginTop: '6px' }}>
            <span className="sb-k"><Zap size={12} /> FILTER CONFIDENCE</span>
            <span className={`sb-v ${confidence < 72 ? 'warn' : 'ok'}`}>{confidence.toFixed(0)}%</span>
          </div>
          <div className="pbar">
            <div 
              className={`pbar-f ${confidence < 72 ? 'warn' : 'ok'}`} 
              style={{ width: `${confidence}%` }}
            ></div>
          </div>

          {/* Estimator Specs */}
          <div className="sb-stat-row" style={{ marginTop: '10px' }}>
            <span className="sb-k"><Cpu size={12} /> ESTIMATOR</span>
            <span className="sb-v ok">15-STATE ES-EKF</span>
          </div>
          <div className="sb-stat-row">
            <span className="sb-k"><Navigation size={12} /> UPDATE FREQUENCY</span>
            <span className="sb-v data">10 Hz (100 Hz IMU)</span>
          </div>
        </div>
      )}
    </div>
  );
};

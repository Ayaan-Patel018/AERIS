import React from 'react';
import { useGNSSStatus } from '../../hooks/useGNSSStatus';
import { useDashboardContext } from '../../context/DashboardContext';
import { useTrajectoryData } from '../../hooks/useTrajectoryData';
import { useOutageRerun } from '../../hooks/useOutageRerun';
import { RefreshCw, Server, Wifi, WifiOff } from 'lucide-react';

export const Sidebar: React.FC = () => {
  const {
    isOutage,
    confidence,
    aerisError,
    drift,
    currentVelocity,
    currentHeading,
  } = useGNSSStatus();

  const {
    layers,
    toggleLayer,
    outageStartSec,
    outageEndSec,
    isRecomputing,
    backendStatus,
  } = useDashboardContext();

  const { currentFusedPos } = useTrajectoryData();
  const { rerunScenario } = useOutageRerun();

  const getCardinal = (deg: number): string => {
    const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    return dirs[Math.round((((deg % 360) + 360) % 360) / 45) % 8];
  };

  const carrierBars = isOutage ? 0 : 5;
  const satFixText = isOutage ? 'SEARCHING (0 SATS)' : 'LOCKED (11 SATS)';
  const gnssAvailText = isOutage ? 'UNAVAILABLE (OUTAGE)' : 'AVAILABLE';
  const gnssAvailClass = isOutage ? 'val-warn' : 'val-ok';

  // 2σ Covariance Ellipse metrics
  const cxx = currentFusedPos?.cov_xx ?? (aerisError * aerisError) / 2;
  const cyy = currentFusedPos?.cov_yy ?? (aerisError * aerisError) / 2;
  const cxy = currentFusedPos?.cov_xy ?? 0;
  const tr = cxx + cyy;
  const det = cxx * cyy - cxy * cxy;
  const disc = Math.max(0, (tr * tr) / 4 - det);
  const sqrtDisc = Math.sqrt(disc);
  const lambda1 = Math.max(0, tr / 2 + sqrtDisc);
  const lambda2 = Math.max(0, tr / 2 - sqrtDisc);
  const majorAxis2Sigma = 2 * Math.sqrt(lambda1);
  const minorAxis2Sigma = 2 * Math.sqrt(lambda2);

  return (
    <aside className="telemetry-sidebar">
      {/* ── GROUP 1: SYSTEM & INEKF ESTIMATOR ───────────────── */}
      <div className="telem-group">
        <div className="telem-group-title">FILTER / ESTIMATOR</div>

        <div className="telem-row">
          <span className="telem-label">GNSS State</span>
          <span className={`telem-value ${gnssAvailClass}`}>{gnssAvailText}</span>
        </div>

        <div className="telem-row">
          <span className="telem-label">RF Carrier</span>
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
          <span className="telem-label">2σ Ellipse (Major)</span>
          <span className={`telem-value data ${isOutage ? 'val-warn' : ''}`}>
            ±{majorAxis2Sigma.toFixed(2)} m
          </span>
        </div>

        <div className="telem-row">
          <span className="telem-label">2σ Lateral (NHC)</span>
          <span className="telem-value data">±{minorAxis2Sigma.toFixed(2)} m</span>
        </div>

        <div className="telem-row">
          <span className="telem-label">Filter Confidence</span>
          <span className="telem-value val-ok">{confidence.toFixed(0)}%</span>
        </div>
      </div>

      {/* ── GROUP 2: MOTION ─────────────────────────────────── */}
      <div className="telem-group">
        <div className="telem-group-title">KINEMATICS</div>

        <div className="telem-row">
          <span className="telem-label">Ground Speed</span>
          <span className="telem-value data">{currentVelocity.toFixed(1)} km/h</span>
        </div>

        <div className="telem-row">
          <span className="telem-label">Heading</span>
          <span className="telem-value data">
            {currentHeading.toFixed(1)}° {getCardinal(currentHeading)}
          </span>
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
        <div className="telem-group-title">SIMULTANEOUS LAYERS</div>

        <div className="telem-layer-list">
          <label className="telem-layer-item">
            <input
              type="checkbox"
              checked={layers.gt}
              onChange={() => toggleLayer('gt')}
              className="layer-toggle-input"
            />
            <div className="layer-toggle-slider slider-gt"></div>
            <span className="layer-name">
              <span className="layer-color-dot" style={{ background: '#5A5A64' }}></span>
              Ground Truth
            </span>
          </label>

          <label className="telem-layer-item">
            <input
              type="checkbox"
              checked={layers.gnss}
              onChange={() => toggleLayer('gnss')}
              className="layer-toggle-input"
            />
            <div className="layer-toggle-slider slider-gnss"></div>
            <span className="layer-name">
              <span className="layer-color-dot" style={{ background: '#2DD4BF' }}></span>
              Raw GNSS
            </span>
          </label>

          <label className="telem-layer-item">
            <input
              type="checkbox"
              checked={layers.fused}
              onChange={() => toggleLayer('fused')}
              className="layer-toggle-input"
            />
            <div className="layer-toggle-slider slider-fused"></div>
            <span className="layer-name">
              <span className="layer-color-dot" style={{ background: '#F0801E' }}></span>
              AERIS InES-EKF
            </span>
          </label>

          <label className="telem-layer-item">
            <input
              type="checkbox"
              checked={layers.smoothed}
              onChange={() => toggleLayer('smoothed')}
              className="layer-toggle-input"
            />
            <div className="layer-toggle-slider slider-smoothed"></div>
            <span className="layer-name">
              <span className="layer-color-dot" style={{ background: '#A855F7' }}></span>
              RTS Smoothed (Offline)
            </span>
          </label>
        </div>
      </div>

      {/* ── GROUP 4: LIVE SCENARIO CONTROL & BACKEND STATUS ─── */}
      <div className="telem-group">
        <div className="telem-group-title">SCENARIO ENGINE</div>

        <div className="telem-row">
          <span className="telem-label">Backend Status</span>
          <span
            className={`telem-value ${backendStatus === 'connected' ? 'val-ok' : 'val-warn'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            {backendStatus === 'connected' ? <Wifi size={11} /> : <WifiOff size={11} />}
            {backendStatus === 'connected' ? 'FASTAPI LIVE' : 'OFFLINE (REPLAY)'}
          </span>
        </div>

        <div className="telem-row">
          <span className="telem-label">Outage Window</span>
          <span className="telem-value data">
            {outageStartSec.toFixed(0)}s – {outageEndSec.toFixed(0)}s ({(outageEndSec - outageStartSec).toFixed(0)}s)
          </span>
        </div>

        <button
          className="map-ctrl-btn"
          style={{
            width: '100%',
            marginTop: '8px',
            padding: '6px 10px',
            fontSize: '10px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            background: isRecomputing ? '#F0801E' : 'rgba(255, 255, 255, 0.06)',
            borderColor: isRecomputing ? '#F0801E' : 'rgba(255, 255, 255, 0.15)',
            color: isRecomputing ? '#000' : '#FFF',
          }}
          disabled={isRecomputing}
          onClick={() => rerunScenario(outageStartSec, outageEndSec, true)}
        >
          <RefreshCw size={11} className={isRecomputing ? 'spin-anim' : ''} />
          {isRecomputing ? 'RECOMPUTING INEKF...' : 'RE-RUN SCENARIO'}
        </button>
      </div>
    </aside>
  );
};

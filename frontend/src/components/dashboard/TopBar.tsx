import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGNSSStatus, TOTAL_DURATION } from '../../hooks/useGNSSStatus';
import { useDashboardContext } from '../../context/DashboardContext';
import { useTrajectoryData } from '../../hooks/useTrajectoryData';
import { Users, ArrowLeft, Radio, Compass } from 'lucide-react';

export const TopBar: React.FC = () => {
  const [time, setTime] = useState('——:——:—— UTC');
  const { isOutage, isRecovered } = useGNSSStatus();
  const { progress } = useDashboardContext();
  const { currentFusedPos } = useTrajectoryData();
  const navigate = useNavigate();

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(now.toTimeString().slice(0, 8) + ' UTC');
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleBack = (e: React.MouseEvent) => {
    e.preventDefault();
    const pt = document.getElementById('pageTransition');
    if (pt) pt.classList.add('active');
    setTimeout(() => {
      navigate('/');
    }, 280);
  };

  const handleDevs = () => {
    const pt = document.getElementById('pageTransition');
    if (pt) pt.classList.add('active');
    setTimeout(() => {
      navigate('/developers');
    }, 280);
  };

  let statusClass = 's-gnss';
  let statusText = 'GNSS ACQUIRED (100 Hz)';
  
  if (isOutage) {
    statusClass = 's-lost';
    statusText = 'GNSS DENIED // ES-EKF DR';
  } else if (isRecovered) {
    statusClass = 's-ok';
    statusText = 'GNSS BLENDED FIX';
  }

  // Calculate Mission Elapsed Time (MET)
  const currentSec = Math.floor(progress * TOTAL_DURATION);
  const metM = Math.floor(currentSec / 60);
  const metS = currentSec % 60;
  const metStr = `MET T+${metM.toString().padStart(2, '0')}:${metS.toString().padStart(2, '0')}`;

  const latStr = currentFusedPos?.lat ? `${currentFusedPos.lat.toFixed(5)}°N` : '52.37045°N';
  const lonStr = currentFusedPos?.lon ? `${Math.abs(currentFusedPos.lon).toFixed(5)}°W` : '1.25444°W';

  return (
    <header className="portal-top">
      <div className="portal-top-left">
        <a href="/" className="portal-back" onClick={handleBack}>
          <ArrowLeft size={14} />
          <span>BRIEFING</span>
        </a>
        <div className="portal-divider"></div>
        <div className="portal-cadre-cell">
          <button className="portal-devs-link" onClick={handleDevs} title="View Project Engineering Team">
            <Users size={13} />
            <span>DEVELOPERS</span>
          </button>
        </div>
        <div className="portal-divider"></div>
        <span className="portal-title">AERIS COCKPIT</span>
        <span className="portal-badge-es">15-STATE ES-EKF</span>
      </div>

      <div className="portal-top-center">
        <div className="portal-telemetry-ticker">
          <Compass size={13} className="ticker-ic" />
          <span className="ticker-label">FIX:</span>
          <span className="ticker-coord">{latStr}</span>
          <span className="ticker-coord">{lonStr}</span>
          <span className="ticker-label" style={{ marginLeft: '6px' }}>RUGBY (B5414)</span>
        </div>
      </div>

      <div className="portal-top-right">
        <div className="portal-met-badge">
          <Radio size={12} className={isOutage ? 'pulse-alert' : 'pulse-ok'} />
          <span className="met-text">{metStr}</span>
        </div>
        <div className={`status ${statusClass}`} id="portalStatus">
          <span className="dot"></span>
          <span id="portalStatusTxt">{statusText}</span>
        </div>
        <span className="portal-top-clock">{time}</span>
      </div>
    </header>
  );
};

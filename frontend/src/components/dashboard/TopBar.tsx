import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGNSSStatus } from '../../hooks/useGNSSStatus';
import { useTrajectoryData } from '../../hooks/useTrajectoryData';
import { ArrowLeft, Users } from 'lucide-react';
import aerisLogo from '../../assets/aeris-logo-transparent.svg';

export const TopBar: React.FC = () => {
  const [time, setTime] = useState('——:——:—— UTC');
  const { isOutage, isRecovered } = useGNSSStatus();
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
    navigate('/');
  };

  const handleDevs = (e: React.MouseEvent) => {
    e.preventDefault();
    navigate('/developers');
  };

  const latStr = currentFusedPos?.lat ? `${currentFusedPos.lat.toFixed(5)}°N` : '52.37045°N';
  const lonStr = currentFusedPos?.lon ? `${Math.abs(currentFusedPos.lon).toFixed(5)}°W` : '1.25444°W';

  let gnssStatusText = 'GNSS AVAILABLE';
  let gnssStatusClass = 'gnss-pill-ok';
  if (isOutage) {
    gnssStatusText = 'GNSS DENIED // DR ACTIVE';
    gnssStatusClass = 'gnss-pill-warn';
  } else if (isRecovered) {
    gnssStatusText = 'GNSS REACQUIRED';
    gnssStatusClass = 'gnss-pill-ok';
  }

  return (
    <header className="portal-top">
      <div className="top-left">
        <button className="top-nav-link" onClick={handleBack} title="Return to Overview">
          <ArrowLeft size={13} />
          <span>HOME</span>
        </button>
        <button className="top-nav-link" onClick={handleDevs} title="View Developers">
          <Users size={13} />
          <span>DEVS</span>
        </button>
        <div className="top-brand-wrap">
          <img src={aerisLogo} alt="AERIS" className="top-brand-logo" />
          <span className="top-sub-tag">15-STATE ES-EKF</span>
        </div>
      </div>

      <div className="top-center">
        <span className="top-meta-item">
          <span className="meta-label">ROUTE:</span>
          <span className="meta-value">RUGBY (B5414)</span>
        </span>
        <span className="meta-divider">•</span>
        <span className="top-meta-item">
          <span className="meta-label">POS:</span>
          <span className="meta-value data">{latStr}, {lonStr}</span>
        </span>
      </div>

      <div className="top-right">
        <span className={`gnss-status-chip ${gnssStatusClass}`}>
          <span className="status-dot"></span>
          <span>{gnssStatusText}</span>
        </span>
        <span className="top-utc-time">{time}</span>
      </div>
    </header>
  );
};

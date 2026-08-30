import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGNSSStatus } from '../../hooks/useGNSSStatus';

export const TopBar: React.FC = () => {
  const [time, setTime] = useState('——:——:—— IST');
  const { isOutage, isRecovered } = useGNSSStatus();
  const navigate = useNavigate();

  useEffect(() => {
    const tick = () => setTime(new Date().toTimeString().slice(0, 8) + ' IST');
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
    }, 340);
  };

  let statusClass = 's-gnss';
  let statusText = 'GNSS AVAILABLE';
  
  if (isOutage) {
    statusClass = 's-lost';
    statusText = 'SIGNAL LOST';
  } else if (isRecovered) {
    statusClass = 's-ok';
    statusText = 'GNSS REACQUIRED';
  }

  return (
    <header className="portal-top">
      <a href="/" className="portal-back" onClick={handleBack}>◄ Back to Home</a>
      <div className="portal-divider"></div>
      <span className="portal-title">GNSS PORTAL</span>
      <div className="portal-top-spacer"></div>
      <div className={`status ${statusClass}`} id="portalStatus">
        <span className="dot"></span>
        <span id="portalStatusTxt">{statusText}</span>
      </div>
      <span className="portal-top-clock">{time}</span>
    </header>
  );
};

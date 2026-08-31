import React, { useRef } from 'react';
import { useDashboardContext } from '../../context/DashboardContext';
import { OUTAGE_START, OUTAGE_END, TOTAL_DURATION } from '../../hooks/useGNSSStatus';

export const TimelineSlider: React.FC = () => {
  const { progress, setProgress, simulateOutage } = useDashboardContext();
  const trackRef = useRef<HTMLDivElement>(null);

  const handleSeek = (e: React.MouseEvent) => {
    if (!trackRef.current) return;
    const r = trackRef.current.getBoundingClientRect();
    const newProg = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
    setProgress(newProg);
  };

  const formatTime = (totalSeconds: number) => {
  const m = Math.floor(totalSeconds / 60);
  const s = Math.floor(totalSeconds % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
};

const currentSec = Math.floor(progress * TOTAL_DURATION);
const timeStr = `${formatTime(currentSec)} / ${formatTime(TOTAL_DURATION)}`;

  const effectiveOS = simulateOutage ? 0 : OUTAGE_START;
  const effectiveOE = simulateOutage ? progress : OUTAGE_END;

  return (
    <>
      <div className="tl-track" ref={trackRef} onClick={handleSeek}>
        <div className="tl-fill" style={{ width: `${progress * 100}%` }}></div>
        {/* Outage indicator block */}
        <div 
          className="tl-out" 
          style={{ 
            left: `${effectiveOS * 100}%`, 
            width: `${(effectiveOE - effectiveOS) * 100}%` 
          }}
        ></div>
        <div className="tl-hnd" style={{ left: `${progress * 100}%` }}></div>
      </div>
      <span className="tl-lbl">{timeStr}</span>
    </>
  );
};

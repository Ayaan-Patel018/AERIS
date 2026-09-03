import React, { useRef, useState } from 'react';
import { useDashboardContext } from '../../context/DashboardContext';
import { OUTAGE_START, OUTAGE_END, TOTAL_DURATION } from '../../hooks/useGNSSStatus';

export const TimelineSlider: React.FC = () => {
  const { progress, setProgress, simulateOutage } = useDashboardContext();
  const trackRef = useRef<HTMLDivElement>(null);
  const [hoverPos, setHoverPos] = useState<{ x: number; time: string } | null>(null);

  const formatTime = (totalSeconds: number) => {
    const m = Math.floor(totalSeconds / 60);
    const s = Math.floor(totalSeconds % 60);
    return `${m}:${String(s).padStart(2, '0')}`;
  };

  const handleSeek = (e: React.MouseEvent) => {
    if (!trackRef.current) return;
    const r = trackRef.current.getBoundingClientRect();
    const newProg = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
    setProgress(newProg);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!trackRef.current) return;
    const r = trackRef.current.getBoundingClientRect();
    const relX = Math.max(0, Math.min(r.width, e.clientX - r.left));
    const progAtMouse = relX / r.width;
    const secAtMouse = Math.floor(progAtMouse * TOTAL_DURATION);
    setHoverPos({
      x: relX,
      time: formatTime(secAtMouse)
    });
  };

  const handleMouseLeave = () => {
    setHoverPos(null);
  };

  const currentSec = Math.floor(progress * TOTAL_DURATION);
  const timeStr = `${formatTime(currentSec)} / ${formatTime(TOTAL_DURATION)}`;

  const effectiveOS = simulateOutage ? 0 : OUTAGE_START;
  const effectiveOE = simulateOutage ? progress : OUTAGE_END;

  return (
    <div className="tl-container">
      <div 
        className="tl-track" 
        ref={trackRef} 
        onClick={handleSeek}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        {/* Fill progress */}
        <div className="tl-fill" style={{ width: `${progress * 100}%` }}></div>

        {/* 60s Outage indicator block with hazard styling */}
        <div 
          className="tl-out" 
          style={{ 
            left: `${effectiveOS * 100}%`, 
            width: `${(effectiveOE - effectiveOS) * 100}%` 
          }}
          title="GNSS Outage Window (200s - 260s)"
        >
          <span className="tl-out-label">JAMMING // 60s OUTAGE</span>
        </div>

        {/* Scrub handle */}
        <div className="tl-hnd" style={{ left: `${progress * 100}%` }}>
          <div className="tl-hnd-core"></div>
        </div>

        {/* Hover preview tooltip */}
        {hoverPos && (
          <div className="tl-tooltip" style={{ left: `${hoverPos.x}px` }}>
            {hoverPos.time}
          </div>
        )}
      </div>

      <span className="tl-lbl">{timeStr}</span>
    </div>
  );
};

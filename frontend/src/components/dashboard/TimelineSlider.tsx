import React, { useRef, useState } from 'react';
import { useDashboardContext } from '../../context/DashboardContext';
import { TOTAL_DURATION } from '../../hooks/useGNSSStatus';
import { useOutageRerun } from '../../hooks/useOutageRerun';

type DragMode = 'scrub' | 'outage-move' | 'outage-left' | 'outage-right' | null;

export const TimelineSlider: React.FC = () => {
  const {
    progress,
    setProgress,
    simulateOutage,
    outageStartSec,
    outageEndSec,
    setOutageWindow,
    isRecomputing,
    backendStatus,
  } = useDashboardContext();

  const { rerunScenario } = useOutageRerun();

  const trackRef = useRef<HTMLDivElement>(null);
  const [hoverPos, setHoverPos] = useState<{ x: number; time: string } | null>(null);
  const [outageTooltip, setOutageTooltip] = useState<string | null>(null);

  const dragModeRef = useRef<DragMode>(null);
  const dragStartXRef = useRef<number>(0);
  const initialWindowRef = useRef<{ start: number; end: number }>({ start: 200, end: 260 });
  const hasDraggedRef = useRef<boolean>(false);

  const formatTime = (totalSeconds: number) => {
    const m = Math.floor(totalSeconds / 60);
    const s = Math.floor(totalSeconds % 60);
    return `${m}:${String(s).padStart(2, '0')}`;
  };

  const getSecFromClientX = (clientX: number): number => {
    if (!trackRef.current) return 0;
    const r = trackRef.current.getBoundingClientRect();
    const frac = Math.max(0, Math.min(1, (clientX - r.left) / r.width));
    return frac * TOTAL_DURATION;
  };

  // ── Global Pointer Handlers ─────────────────────────────────────
  const handlePointerDownTrack = (e: React.PointerEvent) => {
    // If pointer hit handle or outage block, those have their own handlers
    dragModeRef.current = 'scrub';
    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch {}

    const sec = getSecFromClientX(e.clientX);
    setProgress(sec / TOTAL_DURATION);
  };

  const handlePointerDownOutage = (e: React.PointerEvent) => {
    e.stopPropagation();
    dragModeRef.current = 'outage-move';
    dragStartXRef.current = e.clientX;
    initialWindowRef.current = { start: outageStartSec, end: outageEndSec };
    hasDraggedRef.current = false;
    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch {}
  };

  const handlePointerDownLeftHandle = (e: React.PointerEvent) => {
    e.stopPropagation();
    dragModeRef.current = 'outage-left';
    dragStartXRef.current = e.clientX;
    initialWindowRef.current = { start: outageStartSec, end: outageEndSec };
    hasDraggedRef.current = true;
    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch {}
  };

  const handlePointerDownRightHandle = (e: React.PointerEvent) => {
    e.stopPropagation();
    dragModeRef.current = 'outage-right';
    dragStartXRef.current = e.clientX;
    initialWindowRef.current = { start: outageStartSec, end: outageEndSec };
    hasDraggedRef.current = true;
    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch {}
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    const mode = dragModeRef.current;
    if (!mode && trackRef.current) {
      // Normal hover preview
      const r = trackRef.current.getBoundingClientRect();
      const relX = Math.max(0, Math.min(r.width, e.clientX - r.left));
      const secAtMouse = Math.floor((relX / r.width) * TOTAL_DURATION);
      setHoverPos({
        x: relX,
        time: formatTime(secAtMouse),
      });
      return;
    }

    if (!trackRef.current) return;
    const r = trackRef.current.getBoundingClientRect();
    const currentSec = getSecFromClientX(e.clientX);
    const deltaSec = ((e.clientX - dragStartXRef.current) / r.width) * TOTAL_DURATION;

    if (Math.abs(deltaSec) > 1.0) {
      hasDraggedRef.current = true;
    }

    if (mode === 'scrub') {
      setProgress(currentSec / TOTAL_DURATION);
    } else if (mode === 'outage-move') {
      const dur = initialWindowRef.current.end - initialWindowRef.current.start;
      let newStart = Math.max(0, initialWindowRef.current.start + deltaSec);
      let newEnd = newStart + dur;
      if (newEnd > TOTAL_DURATION) {
        newEnd = TOTAL_DURATION;
        newStart = Math.max(0, newEnd - dur);
      }
      setOutageWindow(newStart, newEnd);
      setOutageTooltip(`Outage: ${newStart.toFixed(0)}s – ${newEnd.toFixed(0)}s (${dur.toFixed(0)}s) • Release to recompute`);
    } else if (mode === 'outage-left') {
      let newStart = Math.max(0, Math.min(outageEndSec - 5, initialWindowRef.current.start + deltaSec));
      setOutageWindow(newStart, outageEndSec);
      const dur = outageEndSec - newStart;
      setOutageTooltip(`Start: ${newStart.toFixed(0)}s (Duration: ${dur.toFixed(0)}s) • Release to recompute`);
    } else if (mode === 'outage-right') {
      let newEnd = Math.min(TOTAL_DURATION, Math.max(outageStartSec + 5, initialWindowRef.current.end + deltaSec));
      setOutageWindow(outageStartSec, newEnd);
      const dur = newEnd - outageStartSec;
      setOutageTooltip(`End: ${newEnd.toFixed(0)}s (Duration: ${dur.toFixed(0)}s) • Release to recompute`);
    }
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    const mode = dragModeRef.current;
    if (!mode) return;

    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {}

    dragModeRef.current = null;
    setOutageTooltip(null);

    // If clicked on outage without moving, jump playhead into outage
    if (mode === 'outage-move' && !hasDraggedRef.current) {
      setProgress((outageStartSec + 2) / TOTAL_DURATION);
      return;
    }

    // If an outage drag just ended, trigger backend re-computation!
    if (mode === 'outage-move' || mode === 'outage-left' || mode === 'outage-right') {
      rerunScenario(outageStartSec, outageEndSec, true);
    }
  };

  const handleMouseLeave = () => {
    if (!dragModeRef.current) {
      setHoverPos(null);
      setOutageTooltip(null);
    }
  };

  // Fractions for positioning
  const effectiveOS = simulateOutage ? 0 : outageStartSec / TOTAL_DURATION;
  const effectiveOE = simulateOutage ? progress : outageEndSec / TOTAL_DURATION;
  const outageDuration = Math.round(outageEndSec - outageStartSec);

  const currentSec = Math.floor(progress * TOTAL_DURATION);
  const timeStr = `${formatTime(currentSec)} / ${formatTime(TOTAL_DURATION)}`;

  return (
    <div className="tl-container">
      <div
        className="tl-track"
        ref={trackRef}
        onPointerDown={handlePointerDownTrack}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onMouseLeave={handleMouseLeave}
      >
        {/* Fill progress */}
        <div className="tl-fill" style={{ width: `${progress * 100}%` }}></div>

        {/* Interactive Outage Window Block */}
        <div
          className={`tl-out ${isRecomputing ? 'recomputing' : ''}`}
          style={{
            left: `${effectiveOS * 100}%`,
            width: `${Math.max(1.5, (effectiveOE - effectiveOS) * 100)}%`,
          }}
          onPointerDown={handlePointerDownOutage}
          title={`Outage: ${outageStartSec.toFixed(0)}s - ${outageEndSec.toFixed(0)}s (${outageDuration}s). Drag edges to resize, drag middle to move.`}
        >
          {/* Left Resize Handle */}
          <div
            className="tl-out-handle tl-out-handle-left"
            onPointerDown={handlePointerDownLeftHandle}
            title="Drag to adjust outage start time"
          />

          {/* Central Label & Status */}
          <span className="tl-out-label">
            {isRecomputing
              ? 'RECOMPUTING InESEKF...'
              : `JAMMING // ${outageDuration}s OUTAGE`}
          </span>

          {/* Right Resize Handle */}
          <div
            className="tl-out-handle tl-out-handle-right"
            onPointerDown={handlePointerDownRightHandle}
            title="Drag to adjust outage end time"
          />
        </div>

        {/* Scrub Playhead Handle */}
        <div className="tl-hnd" style={{ left: `${progress * 100}%` }}>
          <div className="tl-hnd-core"></div>
        </div>

        {/* Hover preview tooltip */}
        {hoverPos && !outageTooltip && (
          <div className="tl-tooltip" style={{ left: `${hoverPos.x}px` }}>
            {hoverPos.time}
          </div>
        )}

        {/* Active Outage drag info tooltip */}
        {outageTooltip && (
          <div
            className="tl-tooltip"
            style={{
              left: `${Math.min(
                Math.max(60, ((effectiveOS + effectiveOE) / 2) * (trackRef.current?.clientWidth || 300)),
                (trackRef.current?.clientWidth || 300) - 120
              )}px`,
              background: '#E5484D',
              color: '#FFF',
              fontWeight: 600,
              padding: '3px 8px',
              borderRadius: '4px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
              transform: 'translate(-50%, -32px)',
            }}
          >
            {outageTooltip}
          </div>
        )}
      </div>

      <span className="tl-lbl">{timeStr}</span>
    </div>
  );
};

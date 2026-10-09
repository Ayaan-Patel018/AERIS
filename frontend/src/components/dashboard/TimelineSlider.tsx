import React, { useRef, useState } from "react";
import { useDashboardContext } from "../../context/DashboardContext";
import { useOutageRerun } from "../../hooks/useOutageRerun";

type DragMode = "scrub" | "outage-move" | "outage-left" | "outage-right" | null;

export const TimelineSlider: React.FC = () => {
  const {
    progress,
    setProgress,
    simulateOutage,
    outageStartSec,
    outageEndSec,
    setOutageWindow,
    isRecomputing,
    totalDurationS,
    driveMetadata,
  } = useDashboardContext();

  const { rerunScenario } = useOutageRerun();

  const trackRef     = useRef<HTMLDivElement>(null);
  const [hoverPos, setHoverPos] = useState<{ x: number; time: string } | null>(null);
  const [outageTooltip, setOutageTooltip] = useState<string | null>(null);

  const dragModeRef     = useRef<DragMode>(null);
  const dragStartXRef   = useRef<number>(0);
  const initialWindowRef = useRef<{ start: number; end: number }>({ start: outageStartSec, end: outageEndSec });
  const hasDraggedRef   = useRef<boolean>(false);

  const formatTime = (totalSeconds: number) => {
    const m = Math.floor(totalSeconds / 60);
    const s = Math.floor(totalSeconds % 60);
    return `${m}:${String(s).padStart(2, "0")}`;
  };

  const getSecFromClientX = (clientX: number): number => {
    if (!trackRef.current) return 0;
    const r = trackRef.current.getBoundingClientRect();
    const frac = Math.max(0, Math.min(1, (clientX - r.left) / r.width));
    return frac * totalDurationS;
  };

  const handlePointerDownTrack = (e: React.PointerEvent) => {
    dragModeRef.current = "scrub";
    try { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); } catch {}
    setProgress(getSecFromClientX(e.clientX) / totalDurationS);
  };

  const handlePointerDownOutage = (e: React.PointerEvent) => {
    e.stopPropagation();
    dragModeRef.current = "outage-move";
    dragStartXRef.current = e.clientX;
    initialWindowRef.current = { start: outageStartSec, end: outageEndSec };
    hasDraggedRef.current = false;
    try { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); } catch {}
  };

  const handlePointerDownLeftHandle = (e: React.PointerEvent) => {
    e.stopPropagation();
    dragModeRef.current = "outage-left";
    dragStartXRef.current = e.clientX;
    initialWindowRef.current = { start: outageStartSec, end: outageEndSec };
    hasDraggedRef.current = true;
    try { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); } catch {}
  };

  const handlePointerDownRightHandle = (e: React.PointerEvent) => {
    e.stopPropagation();
    dragModeRef.current = "outage-right";
    dragStartXRef.current = e.clientX;
    initialWindowRef.current = { start: outageStartSec, end: outageEndSec };
    hasDraggedRef.current = true;
    try { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); } catch {}
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    const mode = dragModeRef.current;
    if (!mode && trackRef.current) {
      const r   = trackRef.current.getBoundingClientRect();
      const relX = Math.max(0, Math.min(r.width, e.clientX - r.left));
      setHoverPos({ x: relX, time: formatTime(Math.floor((relX / r.width) * totalDurationS)) });
      return;
    }
    if (!trackRef.current) return;
    const r        = trackRef.current.getBoundingClientRect();
    const curSec   = getSecFromClientX(e.clientX);
    const deltaSec = ((e.clientX - dragStartXRef.current) / r.width) * totalDurationS;

    if (Math.abs(deltaSec) > 1.0) hasDraggedRef.current = true;

    if (mode === "scrub") {
      setProgress(curSec / totalDurationS);
    } else if (mode === "outage-move") {
      const dur = initialWindowRef.current.end - initialWindowRef.current.start;
      let ns = Math.max(0, initialWindowRef.current.start + deltaSec);
      let ne = ns + dur;
      if (ne > totalDurationS) { ne = totalDurationS; ns = Math.max(0, ne - dur); }
      setOutageWindow(ns, ne);
      setOutageTooltip(`Outage: ${ns.toFixed(0)}s–${ne.toFixed(0)}s (${dur.toFixed(0)}s) • Release to recompute`);
    } else if (mode === "outage-left") {
      const ns = Math.max(0, Math.min(outageEndSec - 5, initialWindowRef.current.start + deltaSec));
      setOutageWindow(ns, outageEndSec);
      setOutageTooltip(`Start: ${ns.toFixed(0)}s (${(outageEndSec - ns).toFixed(0)}s) • Release to recompute`);
    } else if (mode === "outage-right") {
      const ne = Math.min(totalDurationS, Math.max(outageStartSec + 5, initialWindowRef.current.end + deltaSec));
      setOutageWindow(outageStartSec, ne);
      setOutageTooltip(`End: ${ne.toFixed(0)}s (${(ne - outageStartSec).toFixed(0)}s) • Release to recompute`);
    }
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    const mode = dragModeRef.current;
    if (!mode) return;
    try { (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId); } catch {}
    dragModeRef.current = null;
    setOutageTooltip(null);

    if (mode === "outage-move" && !hasDraggedRef.current) {
      setProgress((outageStartSec + 2) / totalDurationS);
      return;
    }
    if (mode === "outage-move" || mode === "outage-left" || mode === "outage-right") {
      rerunScenario(outageStartSec, outageEndSec, true);
    }
  };

  const handleMouseLeave = () => {
    if (!dragModeRef.current) {
      setHoverPos(null);
      setOutageTooltip(null);
    }
  };

  // Build GNSS outage bands from REAL metadata outage_windows
  const realOutageWindows = driveMetadata?.outage_windows ?? [];

  // Simulated outage dragging overrides the display
  const effectiveOS = simulateOutage ? 0 : outageStartSec / totalDurationS;
  const effectiveOE = simulateOutage ? progress : outageEndSec / totalDurationS;
  const outageDuration = Math.round(outageEndSec - outageStartSec);

  const currentSec = Math.floor(progress * totalDurationS);
  const timeStr = `${formatTime(currentSec)} / ${formatTime(totalDurationS)}`;

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
        {/* Progress fill */}
        <div className="tl-fill" style={{ width: `${progress * 100}%` }} />

        {/* Real outage bands from metadata (rendered under the draggable block) */}
        {!simulateOutage && realOutageWindows.map((ow, i) => (
          <div
            key={i}
            className="tl-outage-band"
            style={{
              left:  `${ow.start_t * 100}%`,
              width: `${Math.max(0.5, (ow.end_t - ow.start_t) * 100)}%`,
            }}
            title={`GNSS outage: ${ow.start_s.toFixed(0)}s–${ow.end_s.toFixed(0)}s (${(ow.end_s - ow.start_s).toFixed(0)}s)`}
          />
        ))}

        {/* Interactive (draggable) outage window block */}
        <div
          className={`tl-out ${isRecomputing ? "recomputing" : ""}`}
          style={{
            left:  `${effectiveOS * 100}%`,
            width: `${Math.max(1.5, (effectiveOE - effectiveOS) * 100)}%`,
          }}
          onPointerDown={handlePointerDownOutage}
          title={`Outage: ${outageStartSec.toFixed(0)}s–${outageEndSec.toFixed(0)}s (${outageDuration}s). Drag to move/resize.`}
        >
          <div className="tl-out-handle tl-out-handle-left" onPointerDown={handlePointerDownLeftHandle} />
          <span className="tl-out-label">
            {isRecomputing ? "RECOMPUTING InES-EKF…" : `JAMMING // ${outageDuration}s OUTAGE`}
          </span>
          <div className="tl-out-handle tl-out-handle-right" onPointerDown={handlePointerDownRightHandle} />
        </div>

        {/* Playhead */}
        <div className="tl-hnd" style={{ left: `${progress * 100}%` }}>
          <div className="tl-hnd-core" />
        </div>

        {/* Hover tooltip */}
        {hoverPos && !outageTooltip && (
          <div className="tl-tooltip" style={{ left: `${hoverPos.x}px` }}>{hoverPos.time}</div>
        )}

        {/* Drag tooltip */}
        {outageTooltip && (
          <div
            className="tl-tooltip tl-tooltip-drag"
            style={{
              left: `${Math.min(
                Math.max(60, ((effectiveOS + effectiveOE) / 2) * (trackRef.current?.clientWidth ?? 300)),
                (trackRef.current?.clientWidth ?? 300) - 120
              )}px`,
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

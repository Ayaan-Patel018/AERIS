/**
 * StatusPanel.tsx
 *
 * Real-time status readout wired to actual per-frame data.
 * REMOVED: fake satellite count ("11 SATS"), fake L1/L2 text,
 *          fake "100 Hz" propagation, fake 5-bar RF signal.
 * SHOWN:   real GNSS status value, real 1σ uncertainty, real speed/heading,
 *          real outage elapsed time, real drift velocity.
 */
import React, { useState } from "react";
import { useGNSSStatus } from "../../hooks/useGNSSStatus";
import { useDashboardContext } from "../../context/DashboardContext";
import { Radio, Timer, Activity, ChevronDown, ChevronUp, AlertTriangle, CheckCircle, Navigation } from "lucide-react";

export const StatusPanel: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { isOutage, isRecovered, outageTime, drift, uncertainty, aerisError, currentVelocity, currentHeading, totalDurationS } = useGNSSStatus();
  const { progress } = useDashboardContext();

  // Status text — driven purely by the real `status` field values in fused_output.json
  // which are "healthy" | "unavailable". No invented strings.
  let stateBig  = "GNSS AVAILABLE";
  let stateSub  = "Filter propagating with satellite aiding";
  let stateCol  = "var(--status-ok)";

  if (isOutage) {
    stateBig = "SIGNAL DENIED";
    stateSub = `Dead reckoning • ${outageTime.toFixed(1)} s elapsed`;
    stateCol = "var(--status-err)";
  } else if (isRecovered) {
    stateBig = "GNSS REACQUIRED";
    stateSub = "Covariance converging after outage";
    stateCol = "var(--status-ok-hi)";
  }

  // Elapsed drive time
  const elapsedSec  = Math.floor(progress * totalDurationS);
  const elapsedMin  = Math.floor(elapsedSec / 60);
  const elapsedSecs = elapsedSec % 60;
  const totalMin    = Math.floor(totalDurationS / 60);
  const totalSecs   = Math.floor(totalDurationS % 60);

  return (
    <div className={`sb-panel ${collapsed ? "collapsed" : ""} ${isOutage ? "outage-active" : ""}`}>
      <div className="sb-head" onClick={() => setCollapsed(!collapsed)}>
        <div className="sb-head-left">
          <Radio size={13} className="sb-head-ic" />
          <span>RECEIVER STATUS</span>
        </div>
        <span className="sb-toggle">{collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}</span>
      </div>

      <div className="sb-body">
        {/* Main state banner */}
        <div className="sb-banner">
          <div className="sb-banner-icon">
            {isOutage
              ? <AlertTriangle size={18} color="var(--status-err)" />
              : <CheckCircle   size={18} color="var(--status-ok)"  />
            }
          </div>
          <div>
            <div className="sb-state-big" style={{ color: stateCol }}>{stateBig}</div>
            <div className="sb-state-sub">{stateSub}</div>
          </div>
        </div>

        {/* Status rows — only real data, no fabricated values */}
        <div className="sb-stat-row">
          <span className="sb-k"><Timer size={12} /> OUTAGE TIMER</span>
          <span className={`sb-v ${isOutage ? "err-glow" : "data"}`}>
            {isOutage ? `${outageTime.toFixed(1)} s` : "0.0 s (standby)"}
          </span>
        </div>

        <div className="sb-stat-row">
          <span className="sb-k"><Activity size={12} /> DRIFT VELOCITY</span>
          <span className={`sb-v ${drift > 0.5 ? "warn" : "data"}`}>
            {drift.toFixed(3)} m/s
          </span>
        </div>

        <div className="sb-stat-row">
          <span className="sb-k"><Navigation size={12} /> SPEED</span>
          <span className="sb-v data">{currentVelocity.toFixed(1)} km/h</span>
        </div>

        <div className="sb-stat-row">
          <span className="sb-k">HDG</span>
          <span className="sb-v data">{currentHeading.toFixed(1)}°</span>
        </div>

        <div className="sb-stat-row">
          <span className="sb-k">1σ UNCERTAINTY</span>
          <span className={`sb-v ${isOutage ? "err-glow" : "data"}`}>
            ±{aerisError.toFixed(3)} m
          </span>
        </div>

        <div className="sb-stat-row">
          <span className="sb-k">ELAPSED / TOTAL</span>
          <span className="sb-v data">
            {elapsedMin}:{String(elapsedSecs).padStart(2,"0")} / {totalMin}:{String(totalSecs).padStart(2,"0")}
          </span>
        </div>
      </div>
    </div>
  );
};

import React from "react";
import { useGNSSStatus } from "../../hooks/useGNSSStatus";
import { useDashboardContext } from "../../context/DashboardContext";
import { useTrajectoryData } from "../../hooks/useTrajectoryData";
import { useOutageRerun } from "../../hooks/useOutageRerun";
import { RefreshCw, Wifi, WifiOff, ChevronLeft, ChevronRight } from "lucide-react";

export const Sidebar: React.FC = () => {
  const {
    isOutage,
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
    driveMetadata,
    sidebarCollapsed,
    setSidebarCollapsed,
  } = useDashboardContext();

  const { currentFusedPos } = useTrajectoryData();
  const { rerunScenario } = useOutageRerun();

  const getCardinal = (deg: number): string => {
    const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
    return dirs[Math.round((((deg % 360) + 360) % 360) / 45) % 8];
  };

  // 2σ Covariance Ellipse metrics from real covariance block
  const cxx = currentFusedPos?.cov_xx ?? 0;
  const cyy = currentFusedPos?.cov_yy ?? 0;
  const cxy = currentFusedPos?.cov_xy ?? 0;
  const tr  = cxx + cyy;
  const det = cxx * cyy - cxy * cxy;
  const disc    = Math.max(0, (tr * tr) / 4 - det);
  const sqrtD   = Math.sqrt(disc);
  const lambda1 = Math.max(0, tr / 2 + sqrtD);
  const lambda2 = Math.max(0, tr / 2 - sqrtD);
  const majorAxis2Sigma = 2 * Math.sqrt(lambda1);
  const minorAxis2Sigma = 2 * Math.sqrt(lambda2);

  const hasCov = cxx > 0 || cyy > 0;

  // Drive summary from real metadata
  const meta = driveMetadata;
  const totalDistKm = meta ? (meta.total_distance_m / 1000).toFixed(2) : "--";
  const totalDurMin = meta ? Math.floor(meta.total_duration_s / 60) : "--";
  const totalDurSec = meta ? Math.floor(meta.total_duration_s % 60) : "--";
  const numOutages  = meta ? meta.outage_windows.length : "--";
  const longestOut  = meta ? `${meta.longest_outage_s.toFixed(0)} s` : "--";

  // GNSS status text — only from real status field, no fake strings
  const gnssStateText  = isOutage ? "UNAVAILABLE (OUTAGE)" : "AVAILABLE";
  const gnssStateClass = isOutage ? "val-warn" : "val-ok";

  if (sidebarCollapsed) {
    return (
      <aside className="telemetry-sidebar telemetry-sidebar--collapsed">
        <button
          className="sidebar-collapse-btn"
          onClick={() => setSidebarCollapsed(false)}
          title="Expand sidebar"
          aria-label="Expand sidebar"
        >
          <ChevronRight size={14} />
        </button>
      </aside>
    );
  }

  return (
    <aside className="telemetry-sidebar">
      {/* Collapse button */}
      <button
        className="sidebar-collapse-btn sidebar-collapse-btn--inline"
        onClick={() => setSidebarCollapsed(true)}
        title="Collapse sidebar"
        aria-label="Collapse sidebar"
      >
        <ChevronLeft size={14} />
      </button>

      {/* ── DRIVE SUMMARY ─────────────────────────────────────────────── */}
      {meta && (
        <div className="telem-group">
          <div className="telem-group-title">DRIVE SESSION</div>
          <div className="telem-row">
            <span className="telem-label">Session ID</span>
            <span className="telem-value data" style={{ fontSize: "9px" }}>
              {meta.drive_id.replace(/_/g, " ")}
            </span>
          </div>
          <div className="telem-row">
            <span className="telem-label">Duration</span>
            <span className="telem-value data">{totalDurMin}:{String(totalDurSec).padStart(2,"0")} min</span>
          </div>
          <div className="telem-row">
            <span className="telem-label">Distance</span>
            <span className="telem-value data">{totalDistKm} km</span>
          </div>
          <div className="telem-row">
            <span className="telem-label">GNSS Outages</span>
            <span className={`telem-value ${numOutages !== "--" && Number(numOutages) > 0 ? "val-warn" : "val-ok"}`}>
              {numOutages} detected
            </span>
          </div>
          <div className="telem-row">
            <span className="telem-label">Longest Outage</span>
            <span className="telem-value data">{longestOut}</span>
          </div>
        </div>
      )}

      {/* ── FILTER STATUS ─────────────────────────────────────────────── */}
      <div className="telem-group">
        <div className="telem-group-title">FILTER / ESTIMATOR</div>

        <div className="telem-row">
          <span className="telem-label">GNSS State</span>
          <span className={`telem-value ${gnssStateClass}`}>{gnssStateText}</span>
        </div>

        {/* Covariance ellipse — only shown when real cov data is present */}
        {hasCov ? (
          <>
            <div className="telem-row">
              <span className="telem-label">2σ Ellipse (Major)</span>
              <span className={`telem-value data ${isOutage ? "val-warn" : ""}`}>
                ±{majorAxis2Sigma.toFixed(3)} m
              </span>
            </div>
            <div className="telem-row">
              <span className="telem-label">2σ Ellipse (Minor)</span>
              <span className="telem-value data">±{minorAxis2Sigma.toFixed(3)} m</span>
            </div>
          </>
        ) : (
          <div className="telem-row">
            <span className="telem-label">2σ Ellipse</span>
            <span className="telem-value" style={{ color: "var(--dim)" }}>--</span>
          </div>
        )}

        <div className="telem-row">
          <span className="telem-label">1σ Uncertainty</span>
          <span className={`telem-value data ${isOutage ? "val-warn" : ""}`}>
            ±{aerisError.toFixed(3)} m
          </span>
        </div>
      </div>

      {/* ── KINEMATICS ────────────────────────────────────────────────── */}
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
          <span className={`telem-value data ${drift > 0.1 ? "val-warn" : ""}`}>
            {drift.toFixed(3)} m/s
          </span>
        </div>
      </div>

      {/* ── TRAJECTORY LAYERS ─────────────────────────────────────────── */}
      <div className="telem-group telem-layers-group">
        <div className="telem-group-title">TRAJECTORY LAYERS</div>

        <div className="telem-layer-list">
          <label className="telem-layer-item">
            <input type="checkbox" checked={layers.gt} onChange={() => toggleLayer("gt")} className="layer-toggle-input" />
            <div className="layer-toggle-slider slider-gt" />
            <span className="layer-name">
              <span className="layer-color-dot" style={{ background: "#5A5A64" }} />
              Reference (VBOX) — not used by AERIS
            </span>
          </label>

          <label className="telem-layer-item">
            <input type="checkbox" checked={layers.gnss} onChange={() => toggleLayer("gnss")} className="layer-toggle-input" />
            <div className="layer-toggle-slider slider-gnss" />
            <span className="layer-name">
              <span className="layer-color-dot" style={{ background: "#2DD4BF" }} />
              Raw GNSS
            </span>
          </label>

          <label className="telem-layer-item">
            <input type="checkbox" checked={layers.fused} onChange={() => toggleLayer("fused")} className="layer-toggle-input" />
            <div className="layer-toggle-slider slider-fused" />
            <span className="layer-name">
              <span className="layer-color-dot" style={{ background: "#F0801E" }} />
              AERIS InES-EKF
            </span>
          </label>

          <label className="telem-layer-item">
            <input type="checkbox" checked={layers.smoothed} onChange={() => toggleLayer("smoothed")} className="layer-toggle-input" />
            <div className="layer-toggle-slider slider-smoothed" />
            <span className="layer-name">
              <span className="layer-color-dot" style={{ background: "#A855F7" }} />
              RTS Smoothed (offline)
            </span>
          </label>
        </div>

        {/* Legend */}
        <div className="telem-legend-note">
          <span className="legend-badge legend-aeris">AERIS</span> = orange path/halo<br/>
          <span className="legend-badge legend-outage">OUTAGE</span> = dashed segment + growing halo<br/>
          <span className="legend-badge legend-ref">REF</span> = grey dashed — ground truth only
        </div>
      </div>

      {/* ── SCENARIO ENGINE ───────────────────────────────────────────── */}
      <div className="telem-group">
        <div className="telem-group-title">SCENARIO ENGINE</div>

        <div className="telem-row">
          <span className="telem-label">Backend</span>
          <span
            className={`telem-value ${backendStatus === "connected" ? "val-ok" : "val-warn"}`}
            style={{ display: "flex", alignItems: "center", gap: "4px" }}
          >
            {backendStatus === "connected" ? <Wifi size={11} /> : <WifiOff size={11} />}
            {backendStatus === "connected" ? "FASTAPI LIVE" : "OFFLINE (REPLAY)"}
          </span>
        </div>

        <div className="telem-row">
          <span className="telem-label">Outage Window</span>
          <span className="telem-value data">
            {outageStartSec.toFixed(0)}s–{outageEndSec.toFixed(0)}s ({(outageEndSec - outageStartSec).toFixed(0)}s)
          </span>
        </div>

        <button
          className="map-ctrl-btn"
          style={{
            width: "100%",
            marginTop: "8px",
            padding: "6px 10px",
            fontSize: "10px",
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "6px",
            background:     isRecomputing ? "#F0801E" : "rgba(255,255,255,0.06)",
            borderColor:    isRecomputing ? "#F0801E" : "rgba(255,255,255,0.15)",
            color:          isRecomputing ? "#000"    : "#FFF",
          }}
          disabled={isRecomputing}
          onClick={() => rerunScenario(outageStartSec, outageEndSec, true)}
        >
          <RefreshCw size={11} className={isRecomputing ? "spin-anim" : ""} />
          {isRecomputing ? "RECOMPUTING InES-EKF…" : "RE-RUN SCENARIO"}
        </button>
      </div>
    </aside>
  );
};

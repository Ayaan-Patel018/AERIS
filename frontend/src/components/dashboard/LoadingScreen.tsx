/**
 * LoadingScreen.tsx
 * Full-screen boot screen. Progress driven by REAL async load stages, not timers.
 * Stages: 1) Parse JSON  2) Init Leaflet CSS  3) Validate trajectory arrays
 * On success → calls onReady(). On failure → honest error + retry.
 */
import React, { useEffect, useRef, useState, useCallback } from "react";

export interface LoadedDriveData {
  metadata: any;
  fused: any[];
  gnss: any[];
  gt: any[];
  smoothed: any[];
}

interface StageStatus {
  label: string;
  state: "pending" | "running" | "done" | "error";
  error?: string;
}

interface Props {
  onReady: (data: LoadedDriveData) => void;
}

const RadarRing: React.FC<{ active: boolean }> = ({ active }) => (
  <svg
    className={`ls-radar-svg ${active ? "ls-radar-active" : ""}`}
    viewBox="0 0 120 120"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <circle cx="60" cy="60" r="56" stroke="rgba(240,128,30,0.12)" strokeWidth="1" />
    <circle cx="60" cy="60" r="38" stroke="rgba(240,128,30,0.08)" strokeWidth="0.8" />
    <circle cx="60" cy="60" r="20" stroke="rgba(240,128,30,0.15)" strokeWidth="0.8" />
    <line x1="60" y1="4" x2="60" y2="116" stroke="rgba(240,128,30,0.06)" strokeWidth="0.6" />
    <line x1="4" y1="60" x2="116" y2="60" stroke="rgba(240,128,30,0.06)" strokeWidth="0.6" />
    <line className="ls-radar-arm" x1="60" y1="60" x2="60" y2="4" stroke="#F0801E" strokeWidth="1.4" strokeLinecap="round" />
    <circle cx="60" cy="60" r="3" fill="#F0801E" opacity="0.85" />
  </svg>
);

const StageRow: React.FC<{ stage: StageStatus; index: number }> = ({ stage, index }) => {
  const icons: Record<StageStatus["state"], string> = {
    pending: "○",
    running: "◌",
    done: "✓",
    error: "✗",
  };
  return (
    <div className={`ls-stage ls-stage-${stage.state}`} style={{ animationDelay: `${index * 80}ms` }}>
      <span className="ls-stage-icon">{icons[stage.state]}</span>
      <span className="ls-stage-label">{stage.label}</span>
      {stage.state === "error" && stage.error && (
        <span className="ls-stage-err">{stage.error}</span>
      )}
    </div>
  );
};

export const LoadingScreen: React.FC<Props> = ({ onReady }) => {
  const [stages, setStages] = useState<StageStatus[]>([
    { label: "Loading drive data…", state: "pending" },
    { label: "Initializing map…", state: "pending" },
    { label: "Preparing trajectory…", state: "pending" },
  ]);
  const [fatalError, setFatalError] = useState<string | null>(null);
  const [driveId, setDriveId] = useState<string | null>(null);
  const [pct, setPct] = useState(0);
  const [exiting, setExiting] = useState(false);
  const ranRef = useRef(false);

  const patchStage = (i: number, patch: Partial<StageStatus>) =>
    setStages((prev) => {
      const n = [...prev];
      n[i] = { ...n[i], ...patch };
      return n;
    });

  const runLoad = useCallback(async () => {
    // ── Stage 0: JSON parse ─────────────────────────────────────────────────
    patchStage(0, { state: "running" });
    setPct(5);

    let metadata: any, fused: any[], gnss: any[], gt: any[], smoothed: any[];
    try {
      const [m, f, g, gT, sm] = await Promise.all([
        import("../../data/metadata.json"),
        import("../../data/fused_output.json"),
        import("../../data/gnss_only.json"),
        import("../../data/ground_truth.json"),
        import("../../data/smoothed_output.json"),
      ]);
      metadata = m.default;
      fused    = f.default  as any[];
      gnss     = g.default  as any[];
      gt       = gT.default as any[];
      smoothed = sm.default as any[];
      setDriveId(metadata?.drive_id ?? "unknown");
    } catch (err: any) {
      const msg = String(err?.message ?? err);
      const file = ["metadata","fused","gnss","ground","smoothed"].find((k) => msg.toLowerCase().includes(k)) ?? "data";
      patchStage(0, { state: "error", error: `Failed: ${file}.json — ${msg}` });
      setFatalError(`Could not parse drive data. Check frontend/src/data/. Error: ${msg}`);
      return;
    }
    patchStage(0, { state: "done" });
    setPct(35);

    // ── Stage 1: Leaflet CSS ────────────────────────────────────────────────
    patchStage(1, { state: "running" });
    try {
      await import("leaflet/dist/leaflet.css");
      await new Promise<void>((res) => requestAnimationFrame(() => res()));
    } catch (err: any) {
      patchStage(1, { state: "error", error: `Leaflet init: ${err?.message}` });
      setFatalError("Leaflet CSS could not be loaded. Ensure leaflet is installed.");
      return;
    }
    patchStage(1, { state: "done" });
    setPct(65);

    // ── Stage 2: Validate trajectory ────────────────────────────────────────
    patchStage(2, { state: "running" });
    try {
      if (!Array.isArray(fused) || fused.length === 0) throw new Error("fused_output.json empty/malformed");
      if (!Array.isArray(gnss)  || gnss.length  === 0) throw new Error("gnss_only.json empty/malformed");
      if (!Array.isArray(gt)    || gt.length    === 0) throw new Error("ground_truth.json empty/malformed");
      const s = fused[0] as any;
      if (!("lat" in s && "lon" in s && "t" in s)) throw new Error("fused_output.json missing lat/lon/t");
      if (!("status"  in s)) throw new Error("fused_output.json missing `status` field");
      if (!("cov_xx"  in s)) throw new Error("fused_output.json missing covariance fields");
      await new Promise<void>((res) => requestAnimationFrame(() => res()));
    } catch (err: any) {
      patchStage(2, { state: "error", error: err?.message });
      setFatalError(`Trajectory validation failed: ${err?.message}`);
      return;
    }
    patchStage(2, { state: "done" });
    setPct(100);

    // ── Exit transition ──────────────────────────────────────────────────────
    await new Promise<void>((res) => setTimeout(res, 400));
    setExiting(true);
    await new Promise<void>((res) => setTimeout(res, 350));
    onReady({ metadata, fused, gnss, gt, smoothed });
  }, [onReady]);

  useEffect(() => {
    if (ranRef.current) return;
    ranRef.current = true;
    runLoad();
  }, [runLoad]);

  const handleRetry = () => {
    ranRef.current = false;
    setFatalError(null);
    setPct(0);
    setDriveId(null);
    setExiting(false);
    setStages([
      { label: "Loading drive data…", state: "pending" },
      { label: "Initializing map…", state: "pending" },
      { label: "Preparing trajectory…", state: "pending" },
    ]);
    setTimeout(runLoad, 60);
  };

  return (
    <div className={`ls-root${exiting ? " ls-exit" : ""}`} aria-label="AERIS loading">
      {/* Decorative corner brackets */}
      <div className="ls-corner ls-corner-tl" aria-hidden="true" />
      <div className="ls-corner ls-corner-tr" aria-hidden="true" />
      <div className="ls-corner ls-corner-bl" aria-hidden="true" />
      <div className="ls-corner ls-corner-br" aria-hidden="true" />

      <div className="ls-center">
        {/* Radar */}
        <div className="ls-radar-wrap">
          <RadarRing active={!fatalError} />
        </div>

        {/* Wordmark */}
        <div className="ls-wordmark" aria-label="AERIS">
          <span className="ls-wordmark-aeris">AERIS</span>
          <span className="ls-wordmark-sub">Adaptive Error-state Recursive Inertial System</span>
        </div>

        {/* Session ID — only shown once metadata is parsed */}
        {driveId && (
          <div className="ls-session-id">
            SESSION&nbsp;<span className="ls-session-val">{driveId.replace(/_/g, " ")}</span>
          </div>
        )}

        {fatalError ? (
          <div className="ls-error-box" role="alert">
            <div className="ls-error-title">⚠ INITIALIZATION FAILED</div>
            <div className="ls-error-msg">{fatalError}</div>
            <button className="ls-retry-btn" onClick={handleRetry}>↺ RETRY</button>
          </div>
        ) : (
          <div className="ls-stages" role="status">
            {stages.map((s, i) => (
              <StageRow key={i} stage={s} index={i} />
            ))}
          </div>
        )}

        {!fatalError && (
          <div className="ls-progress-track" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
            <div className="ls-progress-fill" style={{ width: `${pct}%` }} />
          </div>
        )}

        <div className="ls-sys-label" aria-hidden="true">
          INERTIAL NAVIGATION SYSTEM — BOOT SEQUENCE
        </div>
      </div>
    </div>
  );
};

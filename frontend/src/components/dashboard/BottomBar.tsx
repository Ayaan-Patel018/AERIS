import React, { useEffect } from "react";
import { PlaybackControls } from "./PlaybackControls";
import { TimelineSlider } from "./TimelineSlider";
import { useDashboardContext } from "../../context/DashboardContext";
import { BarChart2, SkipForward, SkipBack } from "lucide-react";

export const BottomBar: React.FC = () => {
  const {
    speed,
    setSpeed,
    isPlaying,
    setIsPlaying,
    setProgress,
    simulateOutage,
    setSimulateOutage,
    showCharts,
    setShowCharts,
    driveMetadata,
    totalDurationS,
  } = useDashboardContext();

  const speeds = [0.5, 1, 2, 4, 8];

  // Jump to next/prev outage from real metadata
  const outageWindows = driveMetadata?.outage_windows ?? [];

  const jumpToNextOutage = () => {
    if (!outageWindows.length) return;
    // For now jump to first outage start (multi-outage: find next after current progress)
    const first = outageWindows[0];
    setProgress(Math.max(0, first.start_t - 0.005));
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (["INPUT", "TEXTAREA"].includes((e.target as HTMLElement)?.tagName)) return;

      if (e.code === "Space") {
        e.preventDefault();
        setIsPlaying(!isPlaying);
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        setProgress((prev) => Math.min(1, prev + 0.02));
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        setProgress((prev) => Math.max(0, prev - 0.02));
      } else if (e.key === "o" || e.key === "O") {
        e.preventDefault();
        setSimulateOutage(!simulateOutage);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isPlaying, setIsPlaying, setProgress, simulateOutage, setSimulateOutage]);

  return (
    <div className="portal-bottom-bar">
      <PlaybackControls />
      <TimelineSlider />

      {/* Speed selector */}
      <div className="speed-pill-group">
        {speeds.map((s) => (
          <button
            key={s}
            className={`speed-pill-btn ${speed === s ? "active" : ""}`}
            onClick={() => setSpeed(s)}
            title={`Speed: ${s}×`}
          >
            {s}×
          </button>
        ))}
      </div>

      {/* Jump to outage — only shown if metadata has real outage windows */}
      {outageWindows.length > 0 && (
        <button
          className="outage-toggle-btn"
          onClick={jumpToNextOutage}
          title={`Jump to GNSS outage (${outageWindows[0].start_s.toFixed(0)}s–${outageWindows[0].end_s.toFixed(0)}s)`}
          style={{ borderColor: "rgba(229,72,77,0.4)", color: "#FF7B7F" }}
        >
          <SkipForward size={13} />
          <span>
            {outageWindows[0].end_s - outageWindows[0].start_s}s OUTAGE
          </span>
        </button>
      )}

      {/* Charts toggle */}
      <button
        className={`outage-toggle-btn ${showCharts ? "active-outage" : ""}`}
        onClick={() => setShowCharts(!showCharts)}
        title="Toggle performance charts"
      >
        <BarChart2 size={13} />
        <span>{showCharts ? "HIDE CHARTS" : "SHOW CHARTS"}</span>
      </button>
    </div>
  );
};

import React, { useState } from "react";
import { DashboardProvider } from "../context/DashboardContext";
import type { DriveMetadata } from "../context/DashboardContext";
import { LoadingScreen } from "../components/dashboard/LoadingScreen";
import type { LoadedDriveData } from "../components/dashboard/LoadingScreen";
import { usePlayback } from "../hooks/usePlayback";
import { TopBar } from "../components/dashboard/TopBar";
import { Sidebar } from "../components/dashboard/Sidebar";
import { MapArea } from "../components/dashboard/MapArea";
import { BottomGraphs } from "../components/dashboard/BottomGraphs";
import { BottomBar } from "../components/dashboard/BottomBar";
import { NotificationToast } from "../components/dashboard/NotificationToast";
import { useDashboardContext } from "../context/DashboardContext";

// ── Inner dashboard (mounted only after loading) ─────────────────────────────
const DashboardContent: React.FC = () => {
  usePlayback();
  const { showCharts, sidebarCollapsed } = useDashboardContext();

  return (
    <div className="portal-root">
      <TopBar />

      <div className={`portal-workspace${sidebarCollapsed ? " sidebar-hidden" : ""}`}>
        <Sidebar />
        <MapArea />
      </div>

      <div className="portal-footer-section">
        <div className={`charts-wrapper ${showCharts ? "charts-visible" : "charts-hidden"}`}>
          <BottomGraphs />
        </div>
        <BottomBar />
      </div>

      <NotificationToast />
    </div>
  );
};

// ── Page shell ───────────────────────────────────────────────────────────────
export const DashboardPage: React.FC = () => {
  const [ready, setReady] = useState(false);
  const [loadedMeta, setLoadedMeta] = useState<DriveMetadata | null>(null);

  const handleReady = (data: LoadedDriveData) => {
    setLoadedMeta(data.metadata as DriveMetadata);
    setReady(true);
  };

  return (
    <>
      {/* Loading screen is mounted until data is ready */}
      {!ready && <LoadingScreen onReady={handleReady} />}

      {/* Dashboard is mounted (and fades in) once ready */}
      {ready && loadedMeta && (
        <div className="dashboard-fadein">
          <DashboardProvider initialMetadata={loadedMeta}>
            <DashboardContent />
          </DashboardProvider>
        </div>
      )}
    </>
  );
};

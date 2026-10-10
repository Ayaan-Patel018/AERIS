import React, { createContext, useContext, useState } from "react";
import type { ReactNode } from "react";

export interface Layers {
  gt: boolean;
  gnss: boolean;
  fused: boolean;
  smoothed: boolean;
}

export interface DriveMetadata {
  drive_id: string;
  description: string;
  total_duration_s: number;
  total_points: number;
  sample_rate_hz: number;
  total_distance_m: number;
  origin_lat: number;
  origin_lon: number;
  outage_windows: Array<{ start_t: number; end_t: number; start_s: number; end_s: number }>;
  longest_outage_s: number;
  status_values: string[];
  velocity_unit: string;
  t_normalized: boolean;
  covariance_available_in: string[];
  files: Record<string, string>;
}

export interface DynamicScenarioData {
  ground_truth: any[];
  gnss_only: any[];
  fused_output: any[];
  smoothed_output: any[] | null;
  outage_window?: [number, number];
  total_duration?: number;
  lat0?: number;
  lon0?: number;
  elapsed_s?: number;
}

interface DashboardContextType {
  isPlaying: boolean;
  setIsPlaying: (val: boolean) => void;
  progress: number;
  setProgress: React.Dispatch<React.SetStateAction<number>>;
  speed: number;
  setSpeed: (val: number) => void;
  simulateOutage: boolean;
  setSimulateOutage: (val: boolean) => void;
  manualOutageStart: number | null;
  layers: Layers;
  setLayers: React.Dispatch<React.SetStateAction<Layers>>;
  toggleLayer: (key: keyof Layers) => void;
  resetSimulation: () => void;
  showCharts: boolean;
  setShowCharts: (val: boolean) => void;

  // Drive metadata (real, from metadata.json via loading screen)
  driveMetadata: DriveMetadata | null;
  setDriveMetadata: (data: DriveMetadata) => void;

  // Derived from metadata (or fallback until metadata loads)
  totalDurationS: number;

  // Interactive Scenario Control (Outage window in seconds)
  outageStartSec: number;
  outageEndSec: number;
  setOutageWindow: (startSec: number, endSec: number) => void;

  // Live EKF Re-computation state
  isRecomputing: boolean;
  setIsRecomputing: (val: boolean) => void;
  dynamicData: DynamicScenarioData | null;
  setDynamicData: (data: DynamicScenarioData | null) => void;
  backendStatus: "connected" | "disconnected" | "checking";
  setBackendStatus: (status: "connected" | "disconnected" | "checking") => void;

  // Sidebar collapse
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (val: boolean) => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

// Real fallback duration from metadata.json (only used if context not yet initialised)
const FALLBACK_DURATION_S = 681.1;

export const DashboardProvider: React.FC<{ children: ReactNode; initialMetadata?: DriveMetadata }> = ({
  children,
  initialMetadata,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [simulateOutage, setSimulateOutageRaw] = useState(false);
  const [manualOutageStart, setManualOutageStart] = useState<number | null>(null);

  const [layers, setLayers] = useState<Layers>({
    gt: false,      // §3.3: Reference/VBOX path OFF by default; user must toggle it on
    gnss: true,
    fused: true,
    smoothed: true,
  });

  const [showCharts, setShowCharts] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Drive metadata — pre-populated from loading screen if provided
  const [driveMetadata, setDriveMetadataRaw] = useState<DriveMetadata | null>(
    initialMetadata ?? null
  );
  const setDriveMetadata = (data: DriveMetadata) => setDriveMetadataRaw(data);

  const totalDurationS = driveMetadata?.total_duration_s ?? FALLBACK_DURATION_S;

  // Interactive Outage Window — initialised from real metadata outage_windows[0]
  const firstOutage = driveMetadata?.outage_windows?.[0];
  const [outageStartSec, setOutageStartSec] = useState<number>(firstOutage?.start_s ?? 200.0);
  const [outageEndSec, setOutageEndSec] = useState<number>(firstOutage?.end_s ?? 260.0);

  // Live EKF Re-computation state
  const [isRecomputing, setIsRecomputing] = useState<boolean>(false);
  const [dynamicData, setDynamicData] = useState<DynamicScenarioData | null>(null);
  const [backendStatus, setBackendStatus] = useState<"connected" | "disconnected" | "checking">("checking");

  const setOutageWindow = (startSec: number, endSec: number) => {
    const s = Math.max(0, Math.round(startSec * 10) / 10);
    const e = Math.max(s + 5, Math.round(endSec * 10) / 10);
    setOutageStartSec(s);
    setOutageEndSec(e);
  };

  const toggleLayer = (key: keyof Layers) => {
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const setSimulateOutage = (val: boolean) => {
    setSimulateOutageRaw(val);
    setManualOutageStart(val ? progress : null);
  };

  const resetSimulation = () => {
    setProgress(0);
    setIsPlaying(false);
    setSimulateOutageRaw(false);
    setManualOutageStart(null);
  };

  return (
    <DashboardContext.Provider
      value={{
        isPlaying,
        setIsPlaying,
        progress,
        setProgress,
        speed,
        setSpeed,
        simulateOutage,
        setSimulateOutage,
        manualOutageStart,
        layers,
        setLayers,
        toggleLayer,
        resetSimulation,
        showCharts,
        setShowCharts,
        driveMetadata,
        setDriveMetadata,
        totalDurationS,
        outageStartSec,
        outageEndSec,
        setOutageWindow,
        isRecomputing,
        setIsRecomputing,
        dynamicData,
        setDynamicData,
        backendStatus,
        setBackendStatus,
        sidebarCollapsed,
        setSidebarCollapsed,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
};

export const useDashboardContext = () => {
  const context = useContext(DashboardContext);
  if (!context) throw new Error("useDashboardContext must be used within DashboardProvider");
  return context;
};

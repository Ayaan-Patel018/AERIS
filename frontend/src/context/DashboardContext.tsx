import React, { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';

export interface Layers {
  gt: boolean;
  gnss: boolean;
  fused: boolean;
  smoothed: boolean;
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

  // Interactive Scenario Control (Outage window in seconds)
  outageStartSec: number;
  outageEndSec: number;
  setOutageWindow: (startSec: number, endSec: number) => void;

  // Live EKF Re-computation state
  isRecomputing: boolean;
  setIsRecomputing: (val: boolean) => void;
  dynamicData: DynamicScenarioData | null;
  setDynamicData: (data: DynamicScenarioData | null) => void;
  backendStatus: 'connected' | 'disconnected' | 'checking';
  setBackendStatus: (status: 'connected' | 'disconnected' | 'checking') => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export const DashboardProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [simulateOutage, setSimulateOutageRaw] = useState(false);
  const [manualOutageStart, setManualOutageStart] = useState<number | null>(null);

  // All 4 layers ON by default for comprehensive simultaneous comparison:
  // Reference (Ground Truth), Raw GNSS, Real-Time InESEKF, and Offline RTS Smoothed
  const [layers, setLayers] = useState<Layers>({
    gt: true,
    gnss: true,
    fused: true,
    smoothed: true,
  });

  const [showCharts, setShowCharts] = useState(true);

  // Interactive Outage Window (Headline 60s scenario: 200s to 260s)
  const [outageStartSec, setOutageStartSec] = useState<number>(200.0);
  const [outageEndSec, setOutageEndSec] = useState<number>(260.0);

  // Live EKF Re-computation state
  const [isRecomputing, setIsRecomputing] = useState<boolean>(false);
  const [dynamicData, setDynamicData] = useState<DynamicScenarioData | null>(null);
  const [backendStatus, setBackendStatus] = useState<'connected' | 'disconnected' | 'checking'>('checking');

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
        outageStartSec,
        outageEndSec,
        setOutageWindow,
        isRecomputing,
        setIsRecomputing,
        dynamicData,
        setDynamicData,
        backendStatus,
        setBackendStatus,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
};

export const useDashboardContext = () => {
  const context = useContext(DashboardContext);
  if (!context) throw new Error('useDashboardContext must be used within DashboardProvider');
  return context;
};

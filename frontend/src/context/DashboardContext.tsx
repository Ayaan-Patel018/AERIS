import React, { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';

export interface Layers {
  gt: boolean;
  gnss: boolean;
  fused: boolean;
  smoothed: boolean;
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
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export const DashboardProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [simulateOutage, setSimulateOutageRaw] = useState(false);
  const [manualOutageStart, setManualOutageStart] = useState<number | null>(null);
  const [layers, setLayers] = useState<Layers>({ gt: true, gnss: true, fused: true, smoothed: false });
  const [showCharts, setShowCharts] = useState(true);

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
    <DashboardContext.Provider value={{
      isPlaying, setIsPlaying,
      progress, setProgress,
      speed, setSpeed,
      simulateOutage, setSimulateOutage,
      manualOutageStart,
      layers, setLayers,
      toggleLayer,
      resetSimulation,
      showCharts, setShowCharts
    }}>
      {children}
    </DashboardContext.Provider>
  );
};

export const useDashboardContext = () => {
  const context = useContext(DashboardContext);
  if (!context) throw new Error("useDashboardContext must be used within DashboardProvider");
  return context;
};

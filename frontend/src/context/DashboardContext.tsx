import React, { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';

interface Layers {
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
  /** progress (0-1) at the moment Simulate Outage was clicked; null when off.
   *  Lets the UI compute a real elapsed timer for the manual outage instead of
   *  walking the recorded per-point status (which stays 'healthy' during a
   *  manual override — that mismatch was showing "SIGNAL LOST — 0.0s"). */
  manualOutageStart: number | null;
  layers: Layers;
  setLayers: React.Dispatch<React.SetStateAction<Layers>>;
  resetSimulation: () => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export const DashboardProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [simulateOutage, setSimulateOutageRaw] = useState(false);
  const [manualOutageStart, setManualOutageStart] = useState<number | null>(null);
  const [layers, setLayers] = useState<Layers>({ gt: true, gnss: true, fused: true, smoothed: true });

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
      resetSimulation
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

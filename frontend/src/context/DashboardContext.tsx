import React, { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';

interface Layers {
  gt: boolean;
  gnss: boolean;
  fused: boolean;
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
  layers: Layers;
  setLayers: React.Dispatch<React.SetStateAction<Layers>>;
  resetSimulation: () => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

export const DashboardProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [simulateOutage, setSimulateOutage] = useState(false);
  const [layers, setLayers] = useState<Layers>({ gt: true, gnss: true, fused: true });

  const resetSimulation = () => {
    setProgress(0);
    setIsPlaying(false);
  };

  return (
    <DashboardContext.Provider value={{
      isPlaying, setIsPlaying,
      progress, setProgress,
      speed, setSpeed,
      simulateOutage, setSimulateOutage,
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

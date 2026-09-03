import React from 'react';
import { DashboardProvider } from '../context/DashboardContext';
import { usePlayback } from '../hooks/usePlayback';
import { TopBar } from '../components/dashboard/TopBar';
import { Sidebar } from '../components/dashboard/Sidebar';
import { MapArea } from '../components/dashboard/MapArea';
import { RightPanel } from '../components/dashboard/RightPanel';
import { BottomGraphs } from '../components/dashboard/BottomGraphs';
import { BottomBar } from '../components/dashboard/BottomBar';
import { NotificationToast } from '../components/dashboard/NotificationToast';

const DashboardContent: React.FC = () => {
  usePlayback(); // initialize playback loop within provider

  return (
    <div className="portal-root">
      <TopBar />
      
      {/* 3-Column Main Content Area: Left Telemetry, Center Map, Right Key Values */}
      <div className="portal-workspace">
        <Sidebar />
        <MapArea />
        <RightPanel />
      </div>

      {/* Bottom Section: 3 Clean Performance Graphs + Playback Bar */}
      <div className="portal-footer-section">
        <BottomGraphs />
        <BottomBar />
      </div>

      <NotificationToast />
    </div>
  );
};

export const DashboardPage: React.FC = () => {
  return (
    <DashboardProvider>
      <DashboardContent />
    </DashboardProvider>
  );
};

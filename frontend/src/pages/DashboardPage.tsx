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
import { useDashboardContext } from '../context/DashboardContext';

const DashboardContent: React.FC = () => {
  usePlayback(); // initialize playback loop within provider
  const { showCharts } = useDashboardContext();

  return (
    <div className="portal-root">
      <TopBar />
      
      {/* 2-Column Main Content Area: Left Telemetry, Center Map */}
      <div className="portal-workspace">
        <Sidebar />
        <MapArea />
      </div>

      {/* Bottom Section: 3 Clean Performance Graphs + Playback Bar */}
      <div className="portal-footer-section">
        <div className={`charts-wrapper ${showCharts ? 'charts-visible' : 'charts-hidden'}`}>
          <BottomGraphs />
        </div>
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

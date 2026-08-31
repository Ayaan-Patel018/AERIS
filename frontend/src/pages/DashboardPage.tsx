import React from 'react';
import { DashboardProvider } from '../context/DashboardContext';
import { usePlayback } from '../hooks/usePlayback';
import { TopBar } from '../components/dashboard/TopBar';
import { Sidebar } from '../components/dashboard/Sidebar';
import { MapArea } from '../components/dashboard/MapArea';
import { BottomBar } from '../components/dashboard/BottomBar';
import { NotificationToast } from '../components/dashboard/NotificationToast';

const DashboardContent: React.FC = () => {
  usePlayback(); // initialize playback loop within provider

  return (
    <>
      <TopBar />
      <div className="portal-layout">
        <Sidebar />
        <MapArea />
      </div>
      <BottomBar />
      <NotificationToast />
    </>
  );
};

export const DashboardPage: React.FC = () => {
  return (
    <DashboardProvider>
      <DashboardContent />
    </DashboardProvider>
  );
};

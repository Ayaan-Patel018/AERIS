import React from 'react';
import { StatusPanel } from './StatusPanel';
import { MetricsPanel } from './MetricsPanel';
import { ControlsPanel } from './ControlsPanel';
import { Legend } from './Legend';
import { DataInfo } from './DataInfo';

export const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      <StatusPanel />
      <MetricsPanel />
      <ControlsPanel />
      <Legend />
      <DataInfo />
    </aside>
  );
};

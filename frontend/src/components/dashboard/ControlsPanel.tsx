import React, { useState } from 'react';
import { useDashboardContext } from '../../context/DashboardContext';

export const ControlsPanel: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { simulateOutage, setSimulateOutage, resetSimulation } = useDashboardContext();

  const handleSimulateOutage = () => {
    setSimulateOutage(!simulateOutage);
  };

  const handleReset = () => {
    resetSimulation();
  };

  return (
    <div className={`sb-panel ${collapsed ? 'collapsed' : ''}`}>
      <div className="sb-head" onClick={() => setCollapsed(!collapsed)}>
        CONTROLS <span className="sb-toggle">▾</span>
      </div>
      <div className="sb-body">
        <button 
          className={`ctrl-btn ${simulateOutage ? 'active' : ''}`} 
          style={{ width: '100%', marginBottom: '10px' }}
          onClick={handleSimulateOutage}
        >
          {simulateOutage ? 'CANCEL OUTAGE' : 'SIMULATE OUTAGE'}
        </button>
        <button 
          className="ctrl-btn" 
          style={{ width: '100%' }}
          onClick={handleReset}
        >
          RESET SIMULATION
        </button>
      </div>
    </div>
  );
};

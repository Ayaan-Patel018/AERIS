import React, { useState } from 'react';
import { useDashboardContext } from '../../context/DashboardContext';
import { Sliders, AlertTriangle, RotateCcw, ChevronDown, ChevronUp, ShieldCheck } from 'lucide-react';

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
    <div className="sb-panel">
      <div className="sb-head" onClick={() => setCollapsed(!collapsed)}>
        <div className="sb-head-left">
          <Sliders size={13} className="sb-head-ic" />
          <span>MISSION OVERRIDES</span>
        </div>
        <span className="sb-toggle">{collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}</span>
      </div>

      {!collapsed && (
        <div className="sb-body">
          {/* Guarded Outage Trigger */}
          <button 
            className={`guarded-outage-btn ${simulateOutage ? 'armed' : ''}`}
            onClick={handleSimulateOutage}
            title={simulateOutage ? 'Restore GNSS Signals' : 'Inject Simulated RF Jamming / Outage'}
          >
            <div className="guarded-hazard-strip"></div>
            <div className="guarded-content">
              {simulateOutage ? (
                <>
                  <AlertTriangle size={15} className="pulse-alert" />
                  <div className="guarded-labels">
                    <span className="guarded-title">CANCEL BLACKOUT</span>
                    <span className="guarded-sub">RECONNECT GNSS RECEIVER</span>
                  </div>
                </>
              ) : (
                <>
                  <ShieldCheck size={15} className="guarded-ic" />
                  <div className="guarded-labels">
                    <span className="guarded-title">SIMULATE BLACKOUT</span>
                    <span className="guarded-sub">FORCE IMU DEAD RECKONING</span>
                  </div>
                </>
              )}
            </div>
          </button>

          {/* Reset Action Button */}
          <button 
            className="solid-reset-btn"
            onClick={handleReset}
            title="Reset Simulation to T=0.0s"
          >
            <RotateCcw size={13} />
            <span>RESET TO EPOCH 00:00</span>
          </button>
        </div>
      )}
    </div>
  );
};

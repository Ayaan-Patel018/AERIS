import React, { useState } from 'react';
import { useGNSSStatus } from '../../hooks/useGNSSStatus';
import { Radio, Satellite, Timer, Activity, ChevronDown, ChevronUp, AlertTriangle, CheckCircle } from 'lucide-react';

export const StatusPanel: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { isOutage, isRecovered, outageTime, drift } = useGNSSStatus();

  let stateBig = 'GNSS AVAILABLE';
  let stateSub = 'L1/L2 Carrier Lock • 100 Hz Propagation';
  let stateCol = 'var(--status-ok)';
  let signalBars = 5;
  
  if (isOutage) {
    stateBig = 'SIGNAL DENIED';
    stateSub = `Dead Reckoning • ${outageTime.toFixed(1)}s elapsed`;
    stateCol = 'var(--status-err)';
    signalBars = 0;
  } else if (isRecovered) {
    stateBig = 'GNSS REACQUIRED';
    stateSub = 'Covariance blending to satellite fix';
    stateCol = 'var(--status-ok-hi)';
    signalBars = 4;
  }

  return (
    <div className={`sb-panel ${collapsed ? 'collapsed' : ''} ${isOutage ? 'outage-active' : ''}`}>
      <div className="sb-head" onClick={() => setCollapsed(!collapsed)}>
        <div className="sb-head-left">
          <Radio size={13} className="sb-head-ic" />
          <span>RECEIVER STATUS</span>
        </div>
        <span className="sb-toggle">{collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}</span>
      </div>

      <div className="sb-body">
        {/* Main Status Display */}
        <div className="sb-banner">
          <div className="sb-banner-icon">
            {isOutage ? <AlertTriangle size={18} color="var(--status-err)" /> : <CheckCircle size={18} color="var(--status-ok)" />}
          </div>
          <div>
            <div className="sb-state-big" style={{ color: stateCol }}>{stateBig}</div>
            <div className="sb-state-sub">{stateSub}</div>
          </div>
        </div>

        {/* 5-Segment RF Signal Strength Meter */}
        <div className="sb-signal-box">
          <div className="sb-signal-header">
            <span className="signal-title">RF CARRIER STRENGTH</span>
            <span className="signal-bars-count">{signalBars}/5 BARS</span>
          </div>
          <div className="sb-signal-meter">
            {[1, 2, 3, 4, 5].map((bar) => {
              const active = bar <= signalBars;
              return (
                <div 
                  key={bar} 
                  className={`signal-seg ${active ? 'active' : 'inactive'} ${isOutage ? 'jammed' : ''}`}
                ></div>
              );
            })}
          </div>
        </div>

        {/* Detailed Status Rows */}
        <div className="sb-stat-row">
          <span className="sb-k"><Satellite size={12} /> SATELLITE FIX</span>
          <span className={`sb-v ${isOutage ? 'err' : 'ok'}`}>
            {isOutage ? 'BLINDED (0)' : 'LOCKED (11 SATS)'}
          </span>
        </div>

        <div className="sb-stat-row">
          <span className="sb-k"><Timer size={12} /> OUTAGE TIMER</span>
          <span className={`sb-v ${isOutage ? 'err-glow' : 'data'}`}>
            {isOutage ? `${outageTime.toFixed(1)}s` : '0.0s (STANDBY)'}
          </span>
        </div>

        <div className="sb-stat-row">
          <span className="sb-k"><Activity size={12} /> DRIFT VELOCITY</span>
          <span className={`sb-v ${drift > 0.5 ? 'warn' : 'data'}`}>
            {drift.toFixed(3)} m/s
          </span>
        </div>
      </div>
    </div>
  );
};

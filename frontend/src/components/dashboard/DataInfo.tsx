import React, { useState } from 'react';

export const DataInfo: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className={`sb-panel ${collapsed ? 'collapsed' : ''}`} style={{ borderBottom: 'none' }}>
      <div className="sb-head" onClick={() => setCollapsed(!collapsed)}>
        DATA INFO <span className="sb-toggle">▾</span>
      </div>
      <div className="sb-body">
        <div className="sb-stat-row">
          <span className="sb-k">SOURCE</span>
          <span className="sb-v">IO-VNBD</span>
        </div>
        <div className="sb-stat-row">
          <span className="sb-k">SCENARIO</span>
          <span className="sb-v">Tunnel / Urban Canyon</span>
        </div>
        <div className="sb-stat-row">
          <span className="sb-k">DURATION</span>
          <span className="sb-v">60s</span>
        </div>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { useDashboardContext } from '../../context/DashboardContext';

export const Legend: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { layers, setLayers } = useDashboardContext();

  const toggleLayer = (layer: keyof typeof layers) => {
    setLayers(prev => ({ ...prev, [layer]: !prev[layer] }));
  };

  return (
    <div className={`sb-panel ${collapsed ? 'collapsed' : ''}`}>
      <div className="sb-head" onClick={() => setCollapsed(!collapsed)}>
        LEGEND & LAYERS <span className="sb-toggle">▾</span>
      </div>
      <div className="sb-body">
        <div className="sb-stat-row">
          <span className="sb-k" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', background: 'var(--line)' }}></span>
            GROUND TRUTH
          </span>
          <div 
            className={`layer-toggle ${layers.gt ? 'on' : ''}`} 
            onClick={() => toggleLayer('gt')}
          ></div>
        </div>
        <div className="sb-stat-row">
          <span className="sb-k" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', background: 'var(--status-ok)' }}></span>
            GNSS ONLY
          </span>
          <div 
            className={`layer-toggle ${layers.gnss ? 'on' : ''}`} 
            onClick={() => toggleLayer('gnss')}
          ></div>
        </div>
        <div className="sb-stat-row">
          <span className="sb-k" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', background: 'var(--orange)' }}></span>
            AERIS FUSED
          </span>
          <div 
            className={`layer-toggle ${layers.fused ? 'on or' : ''}`} 
            onClick={() => toggleLayer('fused')}
          ></div>
        </div>
        <div className="sb-stat-row">
          <span className="sb-k" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', background: '#A855F7' }}></span>
            RTS SMOOTHED
          </span>
          <div 
            className={`layer-toggle ${layers.smoothed ? 'on' : ''}`} 
            style={layers.smoothed ? { background: '#A855F7', borderColor: '#A855F7' } : {}}
            onClick={() => toggleLayer('smoothed')}
          ></div>
        </div>
      </div>
    </div>
  );
};

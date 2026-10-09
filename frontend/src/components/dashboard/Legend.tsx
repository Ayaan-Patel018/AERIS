import React, { useState } from 'react';
import { useDashboardContext } from '../../context/DashboardContext';
import { Layers, ChevronDown, ChevronUp, Eye, EyeOff, Info } from 'lucide-react';

export const Legend: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { layers, setLayers } = useDashboardContext();

  const toggleLayer = (layer: keyof typeof layers) => {
    setLayers(prev => ({ ...prev, [layer]: !prev[layer] }));
  };

  return (
    <div className="sb-panel">
      <div className="sb-head" onClick={() => setCollapsed(!collapsed)}>
        <div className="sb-head-left">
          <Layers size={13} className="sb-head-ic" />
          <span>TRAJECTORY LAYERS</span>
        </div>
        <span className="sb-toggle">{collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}</span>
      </div>

      {!collapsed && (
        <div className="sb-body">
          {/* Ground Truth Layer */}
          <div className="sb-layer-row">
            <div className="layer-ident">
              <span className="layer-symbol gt-symbol"></span>
              <div className="layer-meta">
                <span className="layer-title">GROUND TRUTH</span>
                <span className="layer-sub">Reference Path (RTK / GNSS)</span>
              </div>
            </div>
            <button 
              className={`cockpit-switch ${layers.gt ? 'active gt' : ''}`}
              onClick={() => toggleLayer('gt')}
              title="Toggle Ground Truth Layer"
            >
              <span className="switch-led"></span>
              <span className="switch-state">{layers.gt ? 'ON' : 'OFF'}</span>
            </button>
          </div>

          {/* GNSS Only Layer */}
          <div className="sb-layer-row">
            <div className="layer-ident">
              <span className="layer-symbol gnss-symbol"></span>
              <div className="layer-meta">
                <span className="layer-title">GNSS ONLY</span>
                <span className="layer-sub">Raw Receiver Stream (L1)</span>
              </div>
            </div>
            <button 
              className={`cockpit-switch ${layers.gnss ? 'active gnss' : ''}`}
              onClick={() => toggleLayer('gnss')}
              title="Toggle GNSS Only Layer"
            >
              <span className="switch-led"></span>
              <span className="switch-state">{layers.gnss ? 'ON' : 'OFF'}</span>
            </button>
          </div>

          {/* RTS Layer */}
          <div className="sb-layer-row">
            <div className="layer-ident">
              <span className="layer-symbol fused-symbol"></span>
              <div className="layer-meta">
                <span className="layer-title">RTS</span>
                <span className="layer-sub">Dead Reckoning</span>
              </div>
            </div>
            <button 
              className={`cockpit-switch ${layers.fused ? 'active fused' : ''}`}
              onClick={() => toggleLayer('fused')}
              title="Toggle RTS Layer"
            >
              <span className="switch-led"></span>
              <span className="switch-state">{layers.fused ? 'ON' : 'OFF'}</span>
            </button>
          </div>

          {/* AERIS Layer */}
          <div className="sb-layer-row">
            <div className="layer-ident">
              <span className="layer-symbol smoothed-symbol"></span>
              <div className="layer-meta">
                <span className="layer-title">AERIS</span>
                <span className="layer-sub">RTS Smoothed</span>
              </div>
            </div>
            <button 
              className={`cockpit-switch ${layers.smoothed ? 'active smoothed' : ''}`}
              onClick={() => toggleLayer('smoothed')}
              title="Toggle AERIS Layer"
            >
              <span className="switch-led"></span>
              <span className="switch-state">{layers.smoothed ? 'ON' : 'OFF'}</span>
            </button>
          </div>

          {/* Offline Smoothed Disclaimer Caption */}
          {layers.smoothed && (
            <div className="sb-disclaimer-box">
              <Info size={13} className="disclaimer-ic" />
              <span>Post-processed using the complete recorded drive — not available to a live system.</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

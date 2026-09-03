import React from 'react';
import { CTAButton } from '../shared/CTAButton';
import { Navigation, Play, Radio, Shield } from 'lucide-react';

export const DemoPreview: React.FC = () => {
  return (
    <section className="container preview-sec grid-5" style={{ position: 'relative' }}>
      <div className="b-dot tl"></div><div className="b-dot tr"></div>
      
      {/* Solid Instrument Bezel Framing */}
      <div className="prev-col-img" style={{ position: 'relative' }}>
        <div className="b-dot tr"></div><div className="b-dot br"></div>
        <div className="preview-bezel">
          <div className="bezel-top-bar">
            <div className="bezel-badge">
              <Radio size={12} color="var(--status-ok)" />
              <span>LIVE COCKPIT PREVIEW • REAL DATA</span>
            </div>
            <div className="bezel-status">6,812 TIMESTEPS</div>
          </div>
          <div className="bezel-image-container">
            <img 
              src="/portal_preview.jpg" 
              alt="AERIS GNSS Portal Telemetry Dashboard" 
              className="prev-img" 
            />
            <div className="bezel-overlay-prompt" onClick={() => window.location.href = '/portal'}>
              <div className="bezel-play-circle">
                <Play size={20} fill="#FFF" color="#FFF" />
              </div>
              <span>CLICK TO ENGAGE SIMULATION</span>
            </div>
          </div>
          <div className="bezel-foot-bar">
            <span>RUGBY B5414 ROADWAY • LEAFLET OPENSTREETMAP TILES • 15-STATE ES-EKF</span>
          </div>
        </div>
      </div>

      <div className="prev-col-txt">
        <div className="eyebrow rev in">INTERACTIVE SIMULATION</div>
        <h2 className="sec-title rev d1 in" style={{ fontSize: '32px' }}>Experience Real-Time Outage Recovery</h2>
        <p className="prob-bridge rev d2 in" style={{ fontSize: '15px', marginBottom: '24px' }}>
          Engage the GNSS Portal to explore a 60-second satellite blackout simulation. Inspect how raw GNSS diverges by up to 484 meters during signal loss, while AERIS holds sub-meter dead reckoning via continuous error-state covariance updates.
        </p>
        
        <div className="preview-features-list">
          <div className="prev-feat-item">
            <Shield size={14} color="var(--status-ok)" />
            <span>Multi-layer trajectory toggles (Ground Truth, GNSS, Fused, RTS Smoothed)</span>
          </div>
          <div className="prev-feat-item">
            <Navigation size={14} color="var(--orange)" />
            <span>Interactive timeline scrubbing with sub-centimeter WGS-84 coordinate projection</span>
          </div>
        </div>

        <div className="rev d3 in" style={{ marginTop: '32px' }}>
          <CTAButton to="/portal">OPEN GNSS PORTAL →</CTAButton>
        </div>
      </div>
    </section>
  );
};

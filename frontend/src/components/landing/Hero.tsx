import React, { useEffect, useRef, useState } from 'react';
import homeVideo from '../../assets/home-video.mp4';
import { Shield, Radio, Navigation, Terminal, Activity, ArrowRight } from 'lucide-react';

export const Hero: React.FC = () => {

  const [imuCount, setImuCount] = useState(6812);

  // Periodic IMU packet ticker effect
  useEffect(() => {
    const timer = setInterval(() => {
      setImuCount((prev) => prev + 10);
    }, 100);
    return () => clearInterval(timer);
  }, []);



  const handleLaunch = () => {
    const pt = document.getElementById('pageTransition');
    if (pt) pt.classList.add('active');
    setTimeout(() => {
      window.location.href = '/portal';
    }, 280);
  };

  return (
    <section className="hero container border-b">
      <div className="hero-inner grid-5">
        <div className="b-dot tl"></div><div className="b-dot tr"></div>
        <div className="b-dot bl"></div><div className="b-dot br"></div>
        <div className="hero-copy" style={{ position: 'relative' }}>
          <div className="b-dot tr"></div><div className="b-dot br"></div>
          <div className="hc-top">
            <div className="b-dot bl"></div><div className="b-dot br"></div>
            <h1 className="hero-title rev d1 in" style={{ marginBottom: 0 }}>
              Navigation That Never Stops
            </h1>
          </div>
          <div className="hc-mid">
            <div className="b-dot bl"></div><div className="b-dot br"></div>
            <p className="hero-sub rev d2 in">
              AERIS uses onboard inertial sensors and Error-State Kalman Filters to maintain sub-meter dead reckoning navigation when GPS signals are jammed, spoofed, or lost in tunnels and urban canyons.
            </p>
          </div>
          <div className="hc-bot">
            <div className="hc-btn-cell" style={{ borderRight: '1px solid var(--line)', position: 'relative' }} onClick={handleLaunch}>
              <div className="b-dot tr"></div><div className="b-dot br"></div>
              <a className="solid-hero-link" style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
                LAUNCH GNSS COCKPIT
                <ArrowRight size={14} />
              </a>
            </div>
            <div className="hc-btn-cell">
              <a href="#problem" className="solid-hero-link">SYSTEM SPECS ↓</a>
            </div>
          </div>
        </div>

        <div className="hero-vis">
          <div className="hero-top-spacer"></div>
          <div className="hero-video-box rev d3 in">
            <div className="b-dot tl"></div><div className="b-dot tr"></div>
            <div className="b-dot bl"></div><div className="b-dot br"></div>
            <video 
              src={homeVideo} 
              autoPlay 
              loop 
              muted 
              playsInline 
              disablePictureInPicture
              className="hero-video"
            />
          </div>

          {/* Solid Defense Telemetry Terminal Card */}
          <div className="hero-telemetry rev d4 in">
            <div className="telemetry-terminal-card">
              <div className="terminal-header">
                <div className="terminal-title">
                  <Terminal size={12} color="var(--status-ok)" />
                  <span>ONBOARD SENSOR BUS • TELEMETRY STREAM • 10 HZ</span>
                </div>
              </div>

              <div className="terminal-grid">
                <div className="term-cell">
                  <span className="term-k">ESTIMATOR</span>
                  <span className="term-v ok">15-STATE ES-EKF</span>
                </div>
                <div className="term-cell">
                  <span className="term-k">IMU FRAMES</span>
                  <span className="term-v data">{imuCount.toLocaleString()}</span>
                </div>
                <div className="term-cell">
                  <span className="term-k">FIX ORIGIN</span>
                  <span className="term-v">52.370°N, 1.254°W</span>
                </div>
                <div className="term-cell">
                  <span className="term-k">OUTAGE TOLERANCE</span>
                  <span className="term-v warn">60.0s UNCONSTRAINED</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

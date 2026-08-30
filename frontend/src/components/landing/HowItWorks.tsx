import React, { useEffect, useState } from 'react';

const MD: Record<string, any> = {
  imu: {
    title: 'Sensor Inputs', color: '#2DD4BF', tag: 'INPUT',
    desc: 'Raw inertial measurements are the only sensor that keeps working in all outage scenarios — tunnels, jamming, spoofing. The IMU is the backbone of dead-reckoning, augmented by GNSS when available.',
    rows: [['IMU Rate', '100 Hz'], ['GNSS Rate', '1 Hz'], ['Filter', 'Zero-phase Butterworth'], ['Calibration', 'Online bias via EKF state']]
  },
  ai: {
    title: 'AI Velocity Estimator', color: '#F0801E', tag: 'AI/ML',
    desc: 'Learns the mapping from IMU motion patterns to velocity. Trained on drive sessions with GNSS ground truth.',
    rows: [['Architecture', '1D CNN → Flatten → Dense'], ['Parameters', '2.1 M'], ['Output', '[vx, vy] m/s'], ['RMSE', '0.4 m/s']]
  },
  ekf: {
    title: 'Extended Kalman Filter', color: '#8B5CF6', tag: 'FUSION',
    desc: 'The fusion backbone. In GNSS-healthy mode it corrects IMU drift. In outage mode it integrates AI velocity and gyro heading continuously.',
    rows: [['State', '[x, y, vx, vy, hdg]'], ['Update (GNSS)', 'GPS observation matrix'], ['Update (DR)', 'AI vel + heading'], ['Covariance', 'Adaptive Q/R']]
  },
  out: {
    title: 'Fused Position Output', color: '#2DD4BF', tag: 'OUTPUT',
    desc: 'Continuous output — never freezes, never jumps. When GNSS returns the filter converges smoothly over 1–3 epochs.',
    rows: [['Rate', '10 Hz'], ['Format', 'WGS-84 lat/lon + alt'], ['Interface', 'NMEA / JSON stream'], ['60 s Error', '< 3 m (fused) vs 450 m']]
  },
};

export const HowItWorks: React.FC = () => {
  const [modalKey, setModalKey] = useState<string | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setModalKey(null);
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const d = modalKey ? MD[modalKey] : null;

  return (
    <>
      <section id="tech" className="container" style={{ borderTop: '1px solid var(--line)' }}>
        <div className="b-dot tl"></div><div className="b-dot tr"></div>
        <div style={{ padding: '120px 48px 48px' }}>
          <div className="eyebrow rev in">THE TECHNOLOGY</div>
          <h2 className="sec-title rev d1 in">AI-powered sensor fusion.</h2>
          <p className="prob-bridge rev d2 in" style={{ marginBottom: 0 }}>
            By combining classical Extended Kalman Filters with lightweight machine learning models, AERIS translates raw vehicle motion into a highly accurate continuous trajectory.
          </p>
        </div>

        <div className="arch-strip" style={{ position: 'relative', borderBottom: '1px solid var(--line)' }}>
          <div className="b-dot bl"></div><div className="b-dot br"></div>
          <svg id="archSvg" height="44" style={{ display: 'block', width: '100%', overflow: 'visible' }}>
            {/* React SVG implementation of the animated strip */}
            {[0.125, 0.375, 0.625, 0.875].map((x, i, arr) => (
              <g key={`arch-strip-${i}`}>
                {i < arr.length - 1 && (
                  <>
                    <line x1={`${x * 100}%`} y1="22" x2={`${arr[i+1] * 100}%`} y2="22" stroke="#26262B" strokeWidth="1" />
                    <circle r="3" fill={['#2DD4BF', '#F0801E', '#8B5CF6', '#2DD4BF'][i]}>
                      <animateMotion dur={`${1.6 + i * 0.3}s`} repeatCount="indefinite" path={`M0,22 L1000,22`} />
                    </circle>
                  </>
                )}
                <circle cx={`${x * 100}%`} cy="22" r="4" fill={['#2DD4BF', '#F0801E', '#8B5CF6', '#2DD4BF'][i]} opacity=".8" />
              </g>
            ))}
          </svg>
        </div>

        <div className="arch-cards" style={{ borderBottom: '1px solid var(--line)' }}>
          <div className="acard" onClick={() => setModalKey('imu')} style={{ position: 'relative' }}>
            <div className="b-dot tr"></div><div className="b-dot br"></div>
            <div className="acard-num">MODULE 01</div>
            <div className="acard-ic"><svg viewBox="0 0 24 24"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg></div>
            <h4>Sensor Inputs</h4>
            <p>Motion and satellite sensors stream continuously into AERIS.</p>
          </div>
          <div className="acard" onClick={() => setModalKey('ai')} style={{ position: 'relative' }}>
            <div className="b-dot tr"></div><div className="b-dot br"></div>
            <div className="acard-num">MODULE 02</div>
            <div className="acard-ic"><svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg></div>
            <h4>AI Velocity Model</h4>
            <p>A trained neural network estimates speed and direction from motion alone.</p>
          </div>
          <div className="acard" onClick={() => setModalKey('ekf')} style={{ position: 'relative' }}>
            <div className="b-dot tr"></div><div className="b-dot br"></div>
            <div className="acard-num">MODULE 03</div>
            <div className="acard-ic"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg></div>
            <h4>Kalman Fusion</h4>
            <p>All signals are mathematically blended into one best-guess position in real time.</p>
          </div>
          <div className="acard" onClick={() => setModalKey('out')}>
            <div className="acard-num">MODULE 04</div>
            <div className="acard-ic"><svg viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg></div>
            <h4>Continuous Output</h4>
            <p>A smooth position stream is generated — never frozen, never jumping.</p>
          </div>
        </div>
      </section>

      {/* Modal Overlay */}
      <div className={`amodal ${modalKey ? 'open' : ''}`} role="dialog" aria-modal="true">
        <button className="mod-close" onClick={() => setModalKey(null)}>✕</button>
        {d && (
          <div id="amodalBody">
            <div style={{ marginBottom: '22px' }}>
              <div style={{ fontFamily: 'var(--f-m)', fontSize: '9px', color: d.color, letterSpacing: '.14em', marginBottom: '8px' }}>MODULE DETAIL</div>
              <h3 style={{ fontFamily: 'var(--f-d)', fontWeight: 700, fontSize: '20px' }}>{d.title}</h3>
              <span style={{ fontFamily: 'var(--f-m)', fontSize: '8px', color: d.color, letterSpacing: '.1em', border: `1px solid ${d.color}`, padding: '2px 7px', opacity: .7, marginTop: '8px', display: 'inline-block' }}>{d.tag}</span>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--muted)', lineHeight: 1.7, marginBottom: '22px' }}>{d.desc}</p>
            {d.rows.map(([k, v]: [string, string], i: number) => (
              <div className="mod-row" key={i}>
                <span className="mod-k">{k}</span>
                <span className="mod-v">{v}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
};

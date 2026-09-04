import React, { useEffect, useState } from 'react';
import { Cpu, Shield, Layers, RefreshCw, X, ArrowRight, ExternalLink } from 'lucide-react';

const MD: Record<string, any> = {
  imu: {
    title: 'Sensor Inputs & Strapdown IMU', color: '#2DD4BF', tag: 'INPUT • 1 Hz',
    desc: 'Raw inertial measurements (3-axis accelerometer, 3-axis rate gyroscope) are the unjammable backbone of dead reckoning, augmented by GNSS when satellites are visible.',
    rows: [
      ['Sampling Rate', '1 Hz IMU / 10 Hz GNSS'],
      ['Attitude Representation', 'Unit Quaternion (Hamilton)'],
      ['Noise Handling', 'Online bias estimation in EKF state'],
      ['Coordinate Frame', 'WGS-84 to Local ENU (East-North-Up)']
    ]
  },
  ai: {
    title: 'AI Kinematic Velocity Model', color: '#F0801E', tag: 'AI/ML • INFERENCE',
    desc: 'Learns non-linear vehicle motion patterns from high-rate inertial signals to predict forward and lateral velocity when wheel odometry is unavailable.',
    rows: [
      ['Model Architecture', '1D CNN Feature Extractor → BiGRU'],
      ['Training Sequences', 'Oxford / Rugby IO-VNBD Datasets'],
      ['Inference Output', 'Planar Velocity Vector [vx, vy] m/s'],
      ['Runtime Overhead', '< 2.5ms on Edge Compute']
    ]
  },
  ekf: {
    title: '15-State Error-State Kalman Filter', color: '#5EEAD4', tag: 'FUSION • 15-STATE',
    desc: 'The primary estimation core. Propagates nominal state on manifold using quaternion kinematics, while updating the 15-dimensional error state via Joseph-form covariance updates.',
    rows: [
      ['State Vector', 'δp (3), δv (3), δθ (3), δba (3), δbg (3)'],
      ['Attitude Self-Propagation', 'Incorporated into Error Transition Matrix F'],
      ['Covariance Form', 'Joseph-stabilized: P = (I-KH)P(I-KH)ᵀ + KRKᵀ'],
      ['Constraint Updates', 'ZARU (Zero Angular Rate) + ZUPT']
    ]
  },
  rts: {
    title: 'Rauch-Tung-Striebel Offline Smoother', color: '#A855F7', tag: 'ANALYSIS • RTS POST-PASS',
    desc: 'Backward post-processing pass over forward filter estimates. Combines full mission history to produce the mathematically optimal trajectory for retrospective analysis.',
    rows: [
      ['Algorithm', 'Rauch-Tung-Striebel (RTS) Backward Smoother'],
      ['Gain on S3b (Tuning)', '−39.5% Mean Position Error (85.8m → 51.9m)'],
      ['Gain on S1 (Unseen)', '−69.1% Mean Position Error (166.5m → 51.5m)'],
      ['Mathematical Scope', 'Offline ground-truth recovery (not live guidance)']
    ]
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
        <div style={{ padding: '96px 48px 48px' }}>
          <div className="eyebrow rev in">ENGINEERING ARCHITECTURE</div>
          <h2 className="sec-title rev d1 in">15-State Error-State Sensor Fusion</h2>
          <p className="prob-bridge rev d2 in" style={{ marginBottom: 0 }}>
            AERIS fuses classical Kalman filtering with deep kinematic modeling to translate high-frequency inertial sensor physics into a mathematically optimal, divergence-resistant vehicle trajectory.
          </p>
        </div>

        {/* Tactical Pipeline Connector */}
        <div className="arch-strip" style={{ position: 'relative', borderBottom: '1px solid var(--line)' }}>
          <div className="b-dot bl"></div><div className="b-dot br"></div>
          <svg id="archSvg" height="44" style={{ display: 'block', width: '100%', overflow: 'visible' }}>
            {[0.125, 0.375, 0.625, 0.875].map((x, i, arr) => (
              <g key={`arch-strip-${i}`}>
                {i < arr.length - 1 && (
                  <>
                    <line x1={`${x * 100}%`} y1="22" x2={`${arr[i+1] * 100}%`} y2="22" stroke="#26262B" strokeWidth="1" />
                    <circle r="3" fill={['#2DD4BF', '#F0801E', '#5EEAD4', '#A855F7'][i]}>
                      <animateMotion dur={`${1.6 + i * 0.3}s`} repeatCount="indefinite" path={`M0,22 L1000,22`} />
                    </circle>
                  </>
                )}
                <circle cx={`${x * 100}%`} cy="22" r="4" fill={['#2DD4BF', '#F0801E', '#5EEAD4', '#A855F7'][i]} opacity=".8" />
              </g>
            ))}
          </svg>
        </div>

        {/* Solid Architecture Module Cards */}
        <div className="arch-cards" style={{ borderBottom: '1px solid var(--line)' }}>
          <div className="acard" onClick={() => setModalKey('imu')} style={{ position: 'relative' }}>
            <div className="b-dot tr"></div><div className="b-dot br"></div>
            <div className="acard-num">MODULE 01</div>
            <div className="acard-ic"><Layers size={22} color="var(--status-ok)" /></div>
            <h4>Sensor Inputs</h4>
            <p>1 Hz 6-axis IMU streams continuously into quaternion strapdown integration.</p>
            <div className="acard-tap">SPECIFICATIONS →</div>
          </div>

          <div className="acard" onClick={() => setModalKey('ai')} style={{ position: 'relative' }}>
            <div className="b-dot tr"></div><div className="b-dot br"></div>
            <div className="acard-num">MODULE 02</div>
            <div className="acard-ic"><Cpu size={22} color="var(--orange)" /></div>
            <h4>AI Kinematics</h4>
            <p>Recurrent BiGRU models estimate vehicle velocity vectors from motion signatures.</p>
            <div className="acard-tap">SPECIFICATIONS →</div>
          </div>

          <div className="acard" onClick={() => setModalKey('ekf')} style={{ position: 'relative' }}>
            <div className="b-dot tr"></div><div className="b-dot br"></div>
            <div className="acard-num">MODULE 03</div>
            <div className="acard-ic"><Shield size={22} color="var(--status-ok-hi)" /></div>
            <h4>15-State ES-EKF</h4>
            <p>Quaternion manifold propagation with Joseph-stabilized error covariance updates.</p>
            <div className="acard-tap">SPECIFICATIONS →</div>
          </div>

          <div className="acard" onClick={() => setModalKey('rts')}>
            <div className="acard-num">MODULE 04</div>
            <div className="acard-ic"><RefreshCw size={22} color="var(--neon-purple)" /></div>
            <h4>RTS Smoother</h4>
            <p>Backward recursion cuts mean error by up to 69.1% for post-mission analysis.</p>
            <div className="acard-tap">SPECIFICATIONS →</div>
          </div>
        </div>
      </section>

      {/* Solid Technical Drilldown Modal (No Glassmorphism) */}
      {modalKey && d && (
        <div className="solid-modal-overlay" onClick={() => setModalKey(null)}>
          <div className="solid-modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="solid-modal-head">
              <div className="solid-modal-tag" style={{ color: d.color }}>{d.tag}</div>
              <h3 className="solid-modal-title">{d.title}</h3>
              <button className="solid-modal-close" onClick={() => setModalKey(null)}>
                <X size={16} />
              </button>
            </div>

            <p className="solid-modal-desc">{d.desc}</p>

            <div className="solid-modal-table">
              {d.rows.map(([k, v]: [string, string]) => (
                <div key={k} className="solid-modal-row">
                  <span className="sm-k">{k}</span>
                  <span className="sm-v">{v}</span>
                </div>
              ))}
            </div>

            <div className="solid-modal-foot">
              <span className="sm-esc">PRESS [ESC] OR CLICK OUTSIDE TO CLOSE</span>
              <button className="sm-close-btn" onClick={() => setModalKey(null)}>
                DISMISS
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

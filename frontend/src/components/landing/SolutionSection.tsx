import React from 'react';
import { Eye, Zap, Shield, ArrowRight } from 'lucide-react';

export const SolutionSection: React.FC = () => {
  return (
    <section id="solution" className="container">
      <div style={{ padding: '96px 48px 48px' }}>
        <div className="eyebrow rev in">ARCHITECTURAL SOLUTION</div>
        <h2 className="sec-title rev d1 in">Zero-Latency Inertial Sensor Handoff</h2>
        <p className="prob-bridge rev d2 in" style={{ marginBottom: 0 }}>
          When external radio signals collapse, AERIS executes a seamless, deterministic transition to self-contained onboard strapdown inertial navigation.
        </p>
      </div>
      
      <div className="sol-grid" style={{ position: 'relative', borderBottom: '1px solid var(--line)' }}>
        <div className="b-dot tl"></div><div className="b-dot tr"></div>
        <div className="b-dot bl"></div><div className="b-dot br"></div>
        
        {/* Step 01 */}
        <div className="step rev d1 in" style={{ position: 'relative' }}>
          <div className="b-dot tl"></div><div className="b-dot tr"></div>
          <div className="b-dot bl"></div><div className="b-dot br"></div>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Eye size={20} color="var(--status-ok)" />
            Receiver Outage Detection
          </h3>
          <p>A statistical Innovation Monitor audits incoming satellite covariance and carrier-to-noise metrics. The exact millisecond of signal degradation triggers the outage flag instantly.</p>
          <div className="step-meta-foot">LATENCY &lt; 10ms • ZERO EXTERNAL OVERHEAD</div>
        </div>

        {/* Step 02 */}
        <div className="step rev d2 in" style={{ position: 'relative' }}>
          <div className="b-dot tl"></div><div className="b-dot tr"></div>
          <div className="b-dot bl"></div><div className="b-dot br"></div>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Zap size={20} color="var(--orange)" />
            1 Hz Strapdown Propagation
          </h3>
          <p>Inertial sensors (3-axis accelerometer, 3-axis rate gyroscope) take complete control of nominal attitude and velocity propagation using quaternion kinematics.</p>
          <div className="step-meta-foot">1 Hz SAMPLING • UNJAMMABLE PHYSICS</div>
        </div>

        {/* Step 03 */}
        <div className="step rev d3 in" style={{ position: 'relative' }}>
          <div className="b-dot tl"></div><div className="b-dot tr"></div>
          <div className="b-dot bl"></div><div className="b-dot br"></div>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Shield size={20} color="var(--status-ok)" />
            15-State Error-State EKF
          </h3>
          <p>The Kalman filter blends kinematic velocity predictions and zero-velocity constraints to continuously arrest sensor bias drift, holding sub-meter accuracy until satellites return.</p>
          <div className="step-meta-foot">JOSEPH-FORM COVARIANCE • ZERO POS JUMP</div>
        </div>
      </div>
    </section>
  );
};

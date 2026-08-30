import React from 'react';

export const SolutionSection: React.FC = () => {
  return (
    <section id="solution" className="container">
      <div style={{ padding: '120px 48px' }}>
        <div className="eyebrow rev in">THE SOLUTION</div>
        <h2 className="sec-title rev d1 in">A seamless handoff to onboard sensors.</h2>
      </div>
      
      <div className="sol-grid" style={{ position: 'relative', borderBottom: '1px solid var(--line)' }}>
        <div className="b-dot tl"></div><div className="b-dot tr"></div>
        <div className="b-dot bl"></div><div className="b-dot br"></div>
        <div className="step rev d1 in" style={{ position: 'relative' }}>
          <div className="b-dot tr"></div><div className="b-dot br"></div>
          <div className="step-num">STEP 01</div>
          <div className="step-tag">DETECT</div>
          <h3>Signal Lost</h3>
          <p>AERIS constantly monitors incoming satellite data. It knows the exact instant the signal weakens or degrades beyond reliability — no external input needed.</p>
        </div>
        <div className="step rev d2 in" style={{ position: 'relative' }}>
          <div className="b-dot tr"></div><div className="b-dot br"></div>
          <div className="step-num">STEP 02</div>
          <div className="step-tag">SWITCH</div>
          <h3>Inertial Mode</h3>
          <p>Within milliseconds, the system hands control to the vehicle's own internal motion sensors. These sensors are immune to external blocking or jamming.</p>
        </div>
        <div className="step rev d3 in">
          <div className="step-num">STEP 03</div>
          <div className="step-tag">HOLD</div>
          <h3>Position Held</h3>
          <p>Speed, heading, and acceleration data are mathematically fused to project the vehicle's ongoing path. The navigation dot never stops tracking.</p>
        </div>
      </div>
    </section>
  );
};

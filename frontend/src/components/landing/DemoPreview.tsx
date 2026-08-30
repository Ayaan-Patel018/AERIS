import React from 'react';
import { CTAButton } from '../shared/CTAButton';

export const DemoPreview: React.FC = () => {
  return (
    <section className="container preview-sec grid-5" style={{ position: 'relative' }}>
      <div className="b-dot tl"></div><div className="b-dot tr"></div>
      <div className="prev-col-img" style={{ position: 'relative' }}>
        <div className="b-dot tr"></div><div className="b-dot br"></div>
        <img src="/portal_preview.jpg" alt="AERIS GNSS Portal Dashboard" className="prev-img" />
      </div>
      <div className="prev-col-txt">
        <div className="eyebrow rev in">LIVE DEMONSTRATION</div>
        <h2 className="sec-title rev d1 in" style={{ fontSize: '32px' }}>See It In Action</h2>
        <p className="prob-bridge rev d2 in" style={{ fontSize: '15px', marginBottom: '40px' }}>
          Launch the GNSS Portal to explore a 60-second interactive simulation. Watch the raw satellite position drift off course during a simulated tunnel outage, while the AERIS fused trajectory holds the true path.
        </p>
        <div className="rev d3 in">
          <CTAButton to="/portal">OPEN GNSS PORTAL →</CTAButton>
        </div>
      </div>
    </section>
  );
};

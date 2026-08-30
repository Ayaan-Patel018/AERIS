import React from 'react';

export const AboutSection: React.FC = () => {
  return (
    <section id="about" className="container about-sec grid-5" style={{ position: 'relative' }}>
      <div className="b-dot tl"></div><div className="b-dot tr"></div>
      <div className="ab-left" style={{ position: 'relative' }}>
        <div className="b-dot tr"></div><div className="b-dot br"></div>
        <div className="eyebrow rev in">CONTEXT</div>
        <h2 className="sec-title rev d1 in" style={{ fontSize: '28px' }}>SIH 26168</h2>
        <p className="prob-bridge rev d2 in" style={{ fontSize: '14px', marginBottom: 0 }}>
          AERIS (Intelligent Dead Reckoning System) was developed to address critical vulnerabilities in satellite navigation. Supported by ISRO / Department of Space, this project demonstrates real-time sensor fusion and machine learning to maintain localization accuracy in the complete absence of GNSS signals.
        </p>
      </div>
      <div className="ab-right">
        <div className="eyebrow rev in">THE TEAM</div>
        <div className="team-list rev d2 in">
          <div className="team-member">
            <div className="tm-name">Anurag</div>
            <div className="tm-role">Team Lead / Navigation Algorithms</div>
          </div>
          <div className="team-member">
            <div className="tm-name">Ayaan</div>
            <div className="tm-role">AI / ML Pipeline</div>
          </div>
          <div className="team-member">
            <div className="tm-name">Aryan</div>
            <div className="tm-role">Systems Integration / Frontend</div>
          </div>
        </div>
      </div>
    </section>
  );
};

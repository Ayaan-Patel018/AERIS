import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, ArrowRight, ShieldCheck } from 'lucide-react';

export const AboutSection: React.FC = () => {
  const navigate = useNavigate();

  const handleDevs = () => {
    const pt = document.getElementById('pageTransition');
    if (pt) pt.classList.add('active');
    setTimeout(() => {
      navigate('/developers');
    }, 280);
  };

  const members = [
    { name: "Anurag Mishra", role: "Team Lead / Navigation Algorithms" },
    { name: "Ayaan Patel", role: "AI/ML Kinematics & RTS Smoother" },
    { name: "Aryan Badoriya", role: "Systems Integration & Frontend" },
    { name: "Ananya Sharma", role: "Data Engineering & GNSS Pipelines" },
    { name: "Shreya Zutshi", role: "Validation & Statistical Testing" },
    { name: "Ananya Tiwari", role: "QA & Embedded Modeling" }
  ];

  return (
    <section id="about" className="container about-sec grid-5" style={{ position: 'relative' }}>
      <div className="b-dot tl"></div><div className="b-dot tr"></div>
      
      <div className="ab-left" style={{ position: 'relative' }}>
        <div className="b-dot tr"></div><div className="b-dot br"></div>
        <div className="eyebrow rev in">ORGANIZATIONAL CONTEXT</div>
        <h2 className="sec-title rev d1 in" style={{ fontSize: '28px' }}>SIH 26168 // ISRO DOS</h2>
        <p className="prob-bridge rev d2 in" style={{ fontSize: '14px', marginBottom: '24px' }}>
          AERIS (Intelligent Dead Reckoning Navigation System) is engineered for Smart India Hackathon problem statement 26168, under the aegis of the Indian Space Research Organisation (ISRO) and Department of Space. The mission demonstrates production-grade sensor fusion and deep kinematic estimation to guarantee vehicle localization when satellite coverage is unavailable.
        </p>
        <div className="about-metrics-pill">
          <ShieldCheck size={14} color="var(--status-ok)" />
          <span>161/161 REGRESSION SUITE PASS • IO-VNBD BENCHMARK VERIFIED</span>
        </div>
      </div>

      <div className="ab-right">
        <div className="ab-right-head">
          <div className="eyebrow rev in" style={{ marginBottom: 0 }}>ENGINEERING CADRE</div>
          <button className="ab-view-devs-btn" onClick={handleDevs}>
            <span>VIEW FULL PROFILES</span>
            <ArrowRight size={13} />
          </button>
        </div>

        <div className="team-list rev d2 in" style={{ marginTop: '16px' }}>
          {members.map((m) => (
            <div key={m.name} className="team-member" onClick={handleDevs} style={{ cursor: 'pointer' }}>
              <div className="tm-name">{m.name}</div>
              <div className="tm-role">{m.role}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

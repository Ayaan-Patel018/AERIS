import React from 'react';

export const ProblemSection: React.FC = () => {
  return (
    <section id="problem" className="container border-b">
      <div className="b-dot bl"></div><div className="b-dot br"></div>
      <div style={{ padding: '120px 48px' }}>
        <div className="eyebrow rev in">THE PROBLEM</div>
        <h2 className="sec-title rev d1 in">What happens when GPS fails?</h2>
        <p className="prob-bridge rev d2 in" style={{ marginBottom: 0 }}>
          Modern navigation relies entirely on clear lines of sight to satellites in space. For autonomous fleets, defense vehicles, and everyday drivers, losing that signal means losing location data instantly. The dot freezes, the route is lost, and safety is compromised.
        </p>
      </div>
      
      <div className="prob-cards">
        <div className="pcard rev d1 in">
          <div className="pcard-ic">
            <svg viewBox="0 0 24 24"><path d="M4 22V10a8 8 0 0 1 16 0v12M8 22v-9a4 4 0 0 1 8 0v9"/></svg>
          </div>
          <h4>Tunnels & Underpasses</h4>
          <p>Solid concrete and earth instantly block all satellite signals. Navigation systems typically freeze at the entrance and jump erratically upon exit.</p>
        </div>
        <div className="pcard rev d2 in">
          <div className="pcard-ic">
            <svg viewBox="0 0 24 24"><path d="M4 22V9h4v13M8 22V5h4v17M12 22v-9h4v9M16 22V11h4v11"/></svg>
          </div>
          <h4>Urban Canyons</h4>
          <p>Tall buildings reflect and distort weak GPS signals, causing "multipath" errors that can throw location estimates off by entire city blocks.</p>
        </div>
        <div className="pcard rev d3 in">
          <div className="pcard-ic">
            <svg viewBox="0 0 24 24"><path d="M12 2v20M7.5 5.5l9 13M16.5 5.5l-9 13"/></svg>
          </div>
          <h4>Signal Jamming</h4>
          <p>Intentional interference is increasingly common in defense and commercial sectors, rendering standard receivers completely blind.</p>
        </div>
      </div>
    </section>
  );
};

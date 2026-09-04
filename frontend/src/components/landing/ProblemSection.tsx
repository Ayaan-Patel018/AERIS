import React from 'react';
import { Building, RadioOff, Mountain, AlertCircle } from 'lucide-react';

export const ProblemSection: React.FC = () => {
  return (
    <section id="problem" className="container border-b">
      <div className="b-dot bl"></div><div className="b-dot br"></div>
      <div style={{ padding: '96px 48px 48px' }}>
        <div className="eyebrow rev in">CRITICAL VULNERABILITY</div>
        <h2 className="sec-title rev d1 in">When Satellite Triangulation Fails</h2>
        <p className="prob-bridge rev d2 in" style={{ marginBottom: 0 }}>
          Modern defense, aviation, and autonomous systems depend critically on continuous GNSS signals. When line-of-sight to the satellite constellation is blocked or corrupted, traditional navigation suffers catastrophic position divergence.
        </p>
      </div>
      
      <div className="prob-cards">
        <div className="pcard rev d1 in" style={{ position: 'relative' }}>
          <div className="b-dot tl"></div><div className="b-dot tr"></div>
          <div className="b-dot bl"></div><div className="b-dot br"></div>
          <div className="pcard-badge">ATTENUATION: -90 dB</div>
          <h4 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Mountain size={22} color="var(--status-err)" />
            Tunnels & Subterranean
          </h4>
          <p>Overhead reinforced concrete and earth attenuate RF carrier waves below receiver sensitivity. Standard systems freeze at the entrance and violently jump upon exit.</p>
          <div className="pcard-foot-metric">
            <span className="pcard-foot-k">CONSEQUENCE</span>
            <span className="pcard-foot-v">TOTAL FIX LOSS (0 SATS)</span>
          </div>
        </div>

        <div className="pcard rev d2 in" style={{ position: 'relative' }}>
          <div className="b-dot tl"></div><div className="b-dot tr"></div>
          <div className="b-dot bl"></div><div className="b-dot br"></div>
          <div className="pcard-badge">DEVIATION: &gt; 450 METERS</div>
          <h4 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Building size={22} color="var(--orange)" />
            Urban Canyons & Multipath
          </h4>
          <p>High-rise glass and steel facades reflect pseudorange signals. Delayed multipath reflections trick receiver correlation algorithms, creating fatal false fixes.</p>
          <div className="pcard-foot-metric">
            <span className="pcard-foot-k">CONSEQUENCE</span>
            <span className="pcard-foot-v">DIVERGENT MULTIPATH DRIFT</span>
          </div>
        </div>

        <div className="pcard rev d3 in" style={{ position: 'relative' }}>
          <div className="b-dot tl"></div><div className="b-dot tr"></div>
          <div className="b-dot bl"></div><div className="b-dot br"></div>
          <div className="pcard-badge">INTERFERENCE: 1575.42 MHz</div>
          <h4 style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <RadioOff size={22} color="var(--status-err)" />
            Electronic Warfare & Jamming
          </h4>
          <p>Cheap portable RF jammers saturate the L1/L2 frequency band with white noise, completely blinding civilian and defense receivers across entire zones.</p>
          <div className="pcard-foot-metric">
            <span className="pcard-foot-k">CONSEQUENCE</span>
            <span className="pcard-foot-v">RF RECEIVER SATURATION</span>
          </div>
        </div>
      </div>
    </section>
  );
};

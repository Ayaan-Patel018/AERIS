import React from 'react';
import { useNavigate } from 'react-router-dom';
import aerisLogo from '../assets/aeris-logo-transparent.svg';
import { 
  Shield, 
  Cpu, 
  Layers, 
  Database, 
  CheckCircle2, 
  Zap, 
  ArrowLeft, 
  Navigation, 
  Terminal,
  Activity
} from 'lucide-react';

interface Member {
  name: string;
  role: string;
  badge: string;
  subtitle: string;
  accent: string;
  description: string;
  tags: string[];
  metrics: { label: string; value: string };
  icon: React.ReactNode;
}

const MEMBERS: Member[] = [
  {
    name: "Anurag Mishra",
    role: "Team Lead / Navigation Algorithms",
    badge: "LEAD // NAV ALGORITHMS",
    subtitle: "15-State Error-State EKF • Covariance Mechanics • Filter Architecture",
    accent: "var(--status-ok)",
    description: "Led core algorithmic architecture of the 15-state Error-State Kalman Filter (ES-EKF). Derived error dynamics Jacobians, dynamic process noise scaling with per-step Δt, Joseph-form covariance stabilization, and verified the 161-test automated suite.",
    tags: ["15-State ES-EKF", "Quaternion Kinematics", "Covariance Symmetry", "Joseph Form", "IO-VNBD Benchmark"],
    metrics: { label: "Filter Integrity", value: "161/161 Tests Passed" },
    icon: <Shield size={20} color="var(--status-ok)" />
  },
  {
    name: "Ayaan Patel",
    role: "AI/ML Kinematics & Offline Smoothing",
    badge: "AI // KINEMATICS & RTS",
    subtitle: "Rauch-Tung-Striebel Smoother • ZARU Zero-Velocity Logic • Deep Kinematics",
    accent: "var(--neon-purple)",
    description: "Architected the Rauch-Tung-Striebel (RTS) backward offline smoothing pass and Zero Angular Rate Update (ZARU) bias corrections. Achieved a verified 39.5% mean error reduction on S3b and 69.1% on unseen S1 benchmark data.",
    tags: ["RTS Smoother", "ZARU Drift Arrest", "Backward Recursion", "BiGRU Kinematics", "PyTorch"],
    metrics: { label: "Smoothed Gain", value: "−69.1% Mean Error (S1)" },
    icon: <Cpu size={20} color="var(--neon-purple)" />
  },
  {
    name: "Aryan Badoriya",
    role: "Systems Integration & Telemetry Cockpit",
    badge: "SYSTEMS // FRONTEND COCKPIT",
    subtitle: "Leaflet Map Tile Engine • Multi-Layer Canvas Sync • 60 FPS Telemetry",
    accent: "var(--orange)",
    description: "Engineered the real-time telemetry cockpit, synchronizing Leaflet OpenStreetMap tiles with high-frequency 60 FPS canvas rendering. Integrated multi-layer toggles, sub-centimeter WGS84 coordinate projections, and interactive diagnostics.",
    tags: ["React 19 / TypeScript", "Leaflet Tile Engine", "60 FPS Canvas", "WGS-84 Projection", "Vite Build"],
    metrics: { label: "Telemetry Rate", value: "60 FPS / Real-Time" },
    icon: <Layers size={20} color="var(--orange)" />
  },
  {
    name: "Ananya Sharma",
    role: "Data Engineering & GNSS Pipelines",
    badge: "DATA // INGESTION & PIPELINES",
    subtitle: "IO-VNBD Dataset Ingestion • Outage Injection • Coordinate Standardization",
    accent: "var(--data)",
    description: "Developed data loaders, schema validators, and dataset ingestion pipelines for the IO-VNBD Oxford/Rugby benchmark sequences. Engineered synthetic GNSS outage injection tools and WGS84 to local ENU coordinate transformations.",
    tags: ["IO-VNBD Dataset", "ENU Coordinates", "Outage Simulation", "NumPy / Pandas", "Schema Validation"],
    metrics: { label: "Dataset Sync", value: "6,812 Timesteps Aligned" },
    icon: <Database size={20} color="var(--data)" />
  },
  {
    name: "Shreya Zutshi",
    role: "Validation Engineering & Statistical Testing",
    badge: "QA // ALGORITHMIC VERIFICATION",
    subtitle: "Automated Test Suites • Covariance Convergence • Positive Definiteness",
    accent: "var(--status-ok-hi)",
    description: "Designed end-to-end regression test suites, verifying covariance positive-definiteness, numerical conditioning, and machine-epsilon symmetry across thousands of simulation epochs. Built synthetic smoke tests for filter resilience.",
    tags: ["Test Automation", "PSD Verification", "Numerical Stability", "Edge Cases", "Pytest / Unittest"],
    metrics: { label: "Unit Suite", value: "92 Tests in 0.57s" },
    icon: <CheckCircle2 size={20} color="var(--status-ok-hi)" />
  },
  {
    name: "Ananya Tiwari",
    role: "Quality Assurance & Embedded Modeling",
    badge: "EMBEDDED // EDGE OPTIMIZATION",
    subtitle: "Hardware Constraints • Edge Inference Optimization • Latency Benchmarking",
    accent: "var(--orange-hi)",
    description: "Evaluated real-time algorithmic execution limits to ensure zero-latency operation on low-power automotive compute units. Profiled memory consumption, execution timing, and edge-readiness for embedded deployment.",
    tags: ["Embedded Systems", "Latency Profiling", "Zero-Latency Handoff", "Resource Optimization", "Edge Profiling"],
    metrics: { label: "Compute Budget", value: "< 10ms Real-Time Latency" },
    icon: <Zap size={20} color="var(--orange-hi)" />
  }
];

export const DevelopersPage: React.FC = () => {
  const navigate = useNavigate();

  const handleNav = (path: string) => {
    const pt = document.getElementById('pageTransition');
    if (pt) pt.classList.add('active');
    setTimeout(() => {
      navigate(path);
    }, 280);
  };

  return (
    <div className="devs-page">
      {/* Top Tactical Navigation Header */}
      <header className="devs-nav container">
        <div className="devs-nav-inner">
          <div className="devs-nav-left">
            <button className="devs-back-btn" onClick={() => handleNav('/')}>
              <ArrowLeft size={16} />
              <span>BACK TO MISSION BRIEFING</span>
            </button>
            <div className="devs-divider"></div>
            <img src={aerisLogo} alt="AERIS Logo" className="devs-logo" />
            <span className="devs-tagline">ENGINEERING CADRE</span>
          </div>
          <div className="devs-nav-right">
            <button className="devs-cta-btn" onClick={() => handleNav('/portal')}>
              <Navigation size={14} />
              <span>LAUNCH GNSS PORTAL</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container devs-main">
        {/* Hero Section */}
        <section className="devs-hero-block">
          <div className="devs-reticle tl"></div>
          <div className="devs-reticle tr"></div>
          <div className="devs-reticle bl"></div>
          <div className="devs-reticle br"></div>

          <div className="devs-eyebrow">
            <Terminal size={14} />
            <span>SIH 26168 // ISRO DOS DOMAIN CADRE</span>
            <span className="devs-pulse-dot"></span>
          </div>

          <h1 className="devs-title">The Engineering Team</h1>

          <p className="devs-sub">
            The multi-disciplinary engineering group behind AERIS — building autonomous, satellite-independent dead reckoning navigation for mission-critical and GNSS-denied environments.
          </p>

          <div className="devs-meta-strip">
            <div className="devs-meta-item">
              <span className="meta-label">PROJECT:</span>
              <span className="meta-val">AERIS IDRS (SIH 26168)</span>
            </div>
            <div className="devs-meta-item">
              <span className="meta-label">DOMAIN:</span>
              <span className="meta-val">ISRO / Department of Space</span>
            </div>
            <div className="devs-meta-item">
              <span className="meta-label">ARCHITECTURE:</span>
              <span className="meta-val">15-State ES-EKF + RTS Smoother</span>
            </div>
            <div className="devs-meta-item">
              <span className="meta-label">ACTIVE CADRE:</span>
              <span className="meta-val highlight">6 Engineers</span>
            </div>
          </div>
        </section>

        {/* Member Cards Grid */}
        <section className="devs-grid">
          {MEMBERS.map((m, idx) => (
            <div key={m.name} className="dev-card" style={{ '--card-accent': m.accent } as React.CSSProperties}>
              <div className="dev-card-reticle tr"></div>
              <div className="dev-card-reticle bl"></div>

              {/* Card Header */}
              <div className="dev-card-head">
                <div className="dev-card-badge">
                  {m.icon}
                  <span>{m.badge}</span>
                </div>
                <div className="dev-card-idx">0{idx + 1} // CADRE</div>
              </div>

              {/* Member Identity */}
              <div className="dev-card-id">
                <h3 className="dev-card-name">{m.name}</h3>
                <div className="dev-card-role">{m.role}</div>
                <div className="dev-card-sub">{m.subtitle}</div>
              </div>

              {/* Description */}
              <p className="dev-card-desc">{m.description}</p>

              {/* Metric Callout */}
              <div className="dev-card-metric">
                <span className="metric-k">{m.metrics.label}</span>
                <span className="metric-v">{m.metrics.value}</span>
              </div>

              {/* Skill Tags */}
              <div className="dev-card-tags">
                {m.tags.map((t) => (
                  <span key={t} className="dev-tag">
                    {t}
                  </span>
                ))}
              </div>

              {/* Bottom Actions */}
              <div className="dev-card-foot">
                <div className="dev-social-slot">
                  <span className="dev-verified">
                    <CheckCircle2 size={12} /> VERIFIED CONTRIBUTOR
                  </span>
                </div>
                <div className="dev-links">
                  <a 
                    href="https://github.com/anuragmishra5159/Intelligent_Dead_Reckoning_Navigation_System" 
                    target="_blank" 
                    rel="noreferrer"
                    className="dev-link-btn"
                    title="View GitHub Repository"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"></path>
                      <path d="M9 18c-4.51 2-5-2-7-2"></path>
                    </svg>
                  </a>
                  <a 
                    href="https://github.com/anuragmishra5159/Intelligent_Dead_Reckoning_Navigation_System/graphs/contributors" 
                    target="_blank" 
                    rel="noreferrer"
                    className="dev-link-btn"
                    title="Contributor Activity"
                  >
                    <Activity size={14} />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </section>

        {/* Bottom Callout */}
        <section className="devs-bottom-bar">
          <div className="devs-bottom-text">
            <h4>Ready to test the live dead reckoning engine?</h4>
            <p>Experience 60 seconds of real-time satellite blackout simulation with 15-state ES-EKF sensor fusion.</p>
          </div>
          <button className="devs-launch-action" onClick={() => handleNav('/portal')}>
            LAUNCH GNSS PORTAL →
          </button>
        </section>
      </main>

      {/* Footer */}
      <footer className="devs-footer container">
        <div className="devs-footer-inner">
          <span>AERIS Intelligent Dead Reckoning System — SIH 26168</span>
          <span>ISRO / Department of Space Problem Statement</span>
        </div>
      </footer>
    </div>
  );
};

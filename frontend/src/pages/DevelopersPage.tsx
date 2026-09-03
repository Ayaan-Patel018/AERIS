import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import aerisLogo from '../assets/aeris-logo-transparent.svg';
import { ArrowLeft, Navigation, ExternalLink, Code2 } from 'lucide-react';

interface Developer {
  name: string;
  role: string;
  focus: string;
  avatar: string;
  github: string;
  linkedin?: string;
  description: string;
  tags: string[];
  metrics: { label: string; value: string };
}

const DEVELOPERS: Developer[] = [
  {
    name: "Ananya Sharma",
    role: "Developer // Data Engineering",
    focus: "Data Ingestion & GNSS Outage Simulation",
    avatar: "https://github.com/ananyascodes.png",
    github: "https://github.com/ananyascodes",
    linkedin: "https://www.linkedin.com/in/ananya-sharma-dev/",
    description: "Architected dataset loaders, schema validators, and data pipelines for the IO-VNBD Oxford/Rugby benchmark sequences. Engineered synthetic GNSS outage injection tools and WGS-84 to ENU conversions.",
    tags: ["IO-VNBD Dataset", "ENU Projection", "Outage Simulation", "NumPy / Pandas", "Pipeline Verification"],
    metrics: { label: "Dataset Sync", value: "6,812 Timesteps Aligned" }
  },
  {
    name: "Shreya Zutshi",
    role: "Developer // Validation Engineering",
    focus: "Automated Testing & Covariance Stability",
    avatar: "https://github.com/shreyazutshi.png",
    github: "https://github.com/shreyazutshi",
    linkedin: "https://www.linkedin.com/in/shreya-zutshi/",
    description: "Designed the automated test suite and regression harnesses, verifying covariance positive-definiteness, numerical conditioning, and filter stability across simulation epochs.",
    tags: ["Automated Testing", "PSD Verification", "Numerical Conditioning", "Pytest Suite", "Filter QA"],
    metrics: { label: "Automated Suite", value: "161/161 Tests Passed" }
  },
  {
    name: "Aryan Bhadoriya",
    role: "Developer // Systems Integration",
    focus: "Frontend Cockpit & Leaflet Canvas Sync",
    avatar: "https://github.com/Codewiz-cpp.png",
    github: "https://github.com/Codewiz-cpp",
    linkedin: "https://www.linkedin.com/in/aryan-bhadoriya-a53a34325/",
    description: "Engineered the real-time telemetry cockpit, Leaflet map engine, high-performance canvas multi-trajectory rendering, and interactive playback synchronization.",
    tags: ["React 19 / Vite", "Leaflet Maps Engine", "Canvas Overlays", "Telemetry Cockpit", "WGS-84 Projection"],
    metrics: { label: "Telemetry Rate", value: "60 FPS / Real-Time" }
  },
  {
    name: "Anurag Mishra",
    role: "Developer // Navigation Algorithms",
    focus: "15-State Error-State EKF & Covariance Mechanics",
    avatar: "https://github.com/anuragmishra5159.png",
    github: "https://github.com/anuragmishra5159",
    linkedin: "https://www.linkedin.com/in/anuragmishra5159/",
    description: "Derived error-state kinematics, dynamic process noise scaling with variable time steps, Joseph-form covariance stabilization, and attitude quaternion kinematics for the 15-state ES-EKF.",
    tags: ["15-State ES-EKF", "Quaternion Kinematics", "Covariance Mechanics", "Joseph Form", "Inertial Dead Reckoning"],
    metrics: { label: "Filter Mechanics", value: "15-State Error Dynamics" }
  },
  {
    name: "Ayaan Patel",
    role: "Developer // AI/ML Kinematics",
    focus: "Offline RTS Smoothing & ZARU Drift Arrest",
    avatar: "https://github.com/Ayaan-Patel018.png",
    github: "https://github.com/Ayaan-Patel018",
    description: "Implemented the Rauch-Tung-Striebel (RTS) backward smoothing pass and Zero Angular Rate Update (ZARU) for post-processing drift elimination, achieving up to 69.1% error reduction.",
    tags: ["RTS Smoother", "ZARU Drift Arrest", "Backward Recursion", "Kinematic Analysis", "PyTorch / NumPy"],
    metrics: { label: "Smoothing Gain", value: "−69.1% Error on S1" }
  },
  {
    name: "Ananya Tiwari",
    role: "Developer // Quality Assurance",
    focus: "Edge Optimization & Execution Profiling",
    avatar: "https://github.com/Ananya3107.png",
    github: "https://github.com/Ananya3107",
    linkedin: "https://www.linkedin.com/in/ananya-tiwari-devs/",
    description: "Evaluated algorithmic execution constraints, edge compute latency, and memory profiling to ensure zero-latency operation for embedded automotive deployment.",
    tags: ["Embedded Systems", "Latency Profiling", "Hardware Constraints", "Edge Optimization", "QA Verification"],
    metrics: { label: "Compute Budget", value: "< 10ms Real-Time Latency" }
  }
];

const GithubIcon: React.FC<{ size?: number }> = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"></path>
    <path d="M9 18c-4.51 2-5-2-7-2"></path>
  </svg>
);

const LinkedinIcon: React.FC<{ size?: number }> = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path>
    <rect x="2" y="9" width="4" height="12"></rect>
    <circle cx="4" cy="4" r="2"></circle>
  </svg>
);

const DevAvatar: React.FC<{ src: string; name: string }> = ({ src, name }) => {
  const [hasError, setHasError] = useState(false);

  const getInitials = (str: string) => {
    return str
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  if (hasError) {
    return <div className="dev-avatar-fallback">{getInitials(name)}</div>;
  }

  return (
    <img
      src={src}
      alt={name}
      className="dev-avatar-img"
      loading="lazy"
      onError={() => setHasError(true)}
    />
  );
};

export const DevelopersPage: React.FC = () => {
  const navigate = useNavigate();

  const handleNav = (path: string) => {
    const pt = document.getElementById('pageTransition');
    if (pt) pt.classList.add('active');
    setTimeout(() => {
      navigate(path);
    }, 250);
  };

  return (
    <div className="devs-page">
      {/* Top Navigation Header */}
      <header className="devs-nav">
        <div className="container devs-nav-inner">
          <div className="devs-nav-left">
            <button className="devs-back-btn" onClick={() => handleNav('/')}>
              <ArrowLeft size={15} />
              <span>HOME</span>
            </button>
            <div className="devs-divider" />
            <img src={aerisLogo} alt="AERIS Logo" className="devs-logo" />
            <span className="devs-tagline">PROJECT CONTRIBUTORS</span>
          </div>
          <div className="devs-nav-right">
            <button className="devs-cta-btn" onClick={() => handleNav('/portal')}>
              <Navigation size={14} />
              <span>LAUNCH COCKPIT</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container devs-main">
        {/* Intro Block */}
        <section className="devs-hero-block">
          <div className="devs-eyebrow">
            <Code2 size={14} />
            <span>SIH 26168 // ISRO DOS DOMAIN</span>
          </div>

          <h1 className="devs-title">Project Developers</h1>

          <p className="devs-sub">
            The engineering team behind AERIS — developing autonomous, satellite-independent inertial dead reckoning navigation for mission-critical and GNSS-denied environments.
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
              <span className="meta-label">ALGORITHMS:</span>
              <span className="meta-val">15-State ES-EKF + RTS Smoother</span>
            </div>
            <div className="devs-meta-item">
              <span className="meta-label">TEAM:</span>
              <span className="meta-val highlight">6 Developers</span>
            </div>
          </div>
        </section>

        {/* Member Cards Grid */}
        <section className="devs-grid">
          {DEVELOPERS.map((dev) => (
            <div key={dev.name} className="dev-card">
              {/* Card Header: Avatar + Identity */}
              <div className="dev-card-head">
                <div className="dev-avatar-wrap">
                  <DevAvatar src={dev.avatar} name={dev.name} />
                </div>
                <div className="dev-id-text">
                  <h3 className="dev-card-name">{dev.name}</h3>
                  <div className="dev-card-role">{dev.role}</div>
                  <div className="dev-card-focus">{dev.focus}</div>
                </div>
              </div>

              {/* Description */}
              <p className="dev-card-desc">{dev.description}</p>

              {/* Key Metric */}
              <div className="dev-card-metric">
                <span className="metric-k">{dev.metrics.label}</span>
                <span className="metric-v">{dev.metrics.value}</span>
              </div>

              {/* Tags */}
              <div className="dev-card-tags">
                {dev.tags.map((t) => (
                  <span key={t} className="dev-tag">
                    {t}
                  </span>
                ))}
              </div>

              {/* Action Links: GitHub & LinkedIn */}
              <div className="dev-card-foot">
                <a
                  href={dev.github}
                  target="_blank"
                  rel="noreferrer"
                  className="dev-link-btn"
                  title={`${dev.name} on GitHub`}
                >
                  <GithubIcon size={14} />
                  <span>GitHub</span>
                  <ExternalLink size={11} className="dev-link-ext" />
                </a>

                {dev.linkedin && (
                  <a
                    href={dev.linkedin}
                    target="_blank"
                    rel="noreferrer"
                    className="dev-link-btn dev-link-linkedin"
                    title={`${dev.name} on LinkedIn`}
                  >
                    <LinkedinIcon size={14} />
                    <span>LinkedIn</span>
                    <ExternalLink size={11} className="dev-link-ext" />
                  </a>
                )}
              </div>
            </div>
          ))}
        </section>

        {/* Bottom CTA Bar */}
        <section className="devs-bottom-bar">
          <div className="devs-bottom-text">
            <h4>Experience the Navigation System in Action</h4>
            <p>Test the 15-state ES-EKF and RTS Smoother through real-time satellite blackout simulation.</p>
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

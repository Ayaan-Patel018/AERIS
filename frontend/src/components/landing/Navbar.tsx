import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import aerisLogo from '../../assets/aeris-logo-transparent.svg';
import { Navigation, Users } from 'lucide-react';

export const Navbar: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToSection = (id: string) => {
    if (location.pathname !== '/') {
      window.location.href = `/#${id}`;
      return;
    }
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header className={`navbar ${scrolled ? 'scrolled' : ''}`} id="navbar">
      <div className="navbar-container">
        {/* Brand / Logo */}
        <Link to="/" className="navbar-brand" title="AERIS Dead Reckoning Navigation">
          <img src={aerisLogo} alt="AERIS Logo" className="navbar-logo-img" />
          <span className="navbar-brand-badge">SIH 26168</span>
        </Link>

        {/* Center Nav Links */}
        <nav className="navbar-links">
          <button className="nav-link-btn" onClick={() => scrollToSection('problem')}>
            Problem
          </button>
          <button className="nav-link-btn" onClick={() => scrollToSection('solution')}>
            Solution
          </button>
          <button className="nav-link-btn" onClick={() => scrollToSection('tech')}>
            Technology
          </button>
          <button className="nav-link-btn" onClick={() => scrollToSection('about')}>
            Overview
          </button>
          <Link to="/developers" className="nav-link-btn nav-link-devs" title="Meet the Engineering Team">
            <Users size={13} />
            <span>Developers</span>
          </Link>
        </nav>

        {/* Right CTA */}
        <div className="navbar-right">
          <div className="navbar-system-status">
            <span className="navbar-status-dot" />
            <span className="navbar-status-text">15-STATE ES-EKF</span>
          </div>
          <Link to="/portal" className="navbar-cta-btn">
            <span>LAUNCH COCKPIT</span>
            <Navigation size={13} />
          </Link>
        </div>
      </div>
    </header>
  );
};

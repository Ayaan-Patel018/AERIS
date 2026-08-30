import React, { useEffect, useState } from 'react';
import { CTAButton } from '../shared/CTAButton';
import aerisLogo from '../../assets/aeris-logo-transparent.svg';

export const Navbar: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <nav className={`navbar ${scrolled ? 'scrolled' : ''}`} id="navbar">
      <div className="nav-inner grid-5">
        <div className="b-dot bl"></div><div className="b-dot br"></div>
        <div className="nav-logo" style={{ position: 'relative' }}>
          <img src={aerisLogo} alt="AERIS Logo" style={{ height: '24px', opacity: 0.9 }} />
          <div className="b-dot br"></div>
        </div>
        <div className="nav-links" style={{ position: 'relative' }}>
          <a href="#problem">Problem</a>
          <a href="#solution">Solution</a>
          <a href="#tech">Technology</a>
          <a href="#about">About</a>
          <div className="b-dot br"></div>
        </div>
        <div className="nav-cta">
          <CTAButton to="/portal">OPEN GNSS PORTAL</CTAButton>
        </div>
      </div>
    </nav>
  );
};

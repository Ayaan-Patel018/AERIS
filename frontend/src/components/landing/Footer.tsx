import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer className="container footer" style={{ position: 'relative' }}>
      <div className="b-dot tl"></div><div className="b-dot tr"></div>
      <div className="b-dot bl"></div><div className="b-dot br"></div>
      <div className="footer-left">
        Dataset: IO-VNBD · Open Source License
      </div>
      <div className="footer-links">
        <a href="#">GitHub Repository</a>
        <a href="#">Contact Team</a>
      </div>
      <div className="footer-right">
        <div className="status s-ok" style={{ display: 'inline-flex' }}>
          <span className="dot"></span>
          <span>SYSTEM OPERATIONAL</span>
        </div>
        <span style={{ marginLeft: '24px' }}>© 2026 AERIS</span>
      </div>
    </footer>
  );
};

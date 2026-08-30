import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';

const ScrollToTop = () => {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
    // fade out the page transition on route change
    const pt = document.getElementById('pageTransition');
    if (pt) pt.classList.remove('active');
  }, [pathname]);
  return null;
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <div id="pageTransition" className="page-transition"></div>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/portal" element={<DashboardPage />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;

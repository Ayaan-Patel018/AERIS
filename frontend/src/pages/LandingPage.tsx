import React from 'react';
import { Navbar } from '../components/landing/Navbar';
import { Hero } from '../components/landing/Hero';
import { ProblemSection } from '../components/landing/ProblemSection';
import { SolutionSection } from '../components/landing/SolutionSection';
import { HowItWorks } from '../components/landing/HowItWorks';
import { DemoPreview } from '../components/landing/DemoPreview';
import { AboutSection } from '../components/landing/AboutSection';
import { Footer } from '../components/landing/Footer';

export const LandingPage: React.FC = () => {
  return (
    <>
      <div className="landing-grid">
        <div className="dot d1"></div><div className="dot d2"></div><div className="dot d3"></div><div className="dot d4"></div>
      </div>
      <Navbar />
      <Hero />
      <ProblemSection />
      <SolutionSection />
      <HowItWorks />
      <DemoPreview />
      <AboutSection />
      <Footer />
    </>
  );
};

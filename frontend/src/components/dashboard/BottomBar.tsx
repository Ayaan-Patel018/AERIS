import React, { useEffect } from 'react';
import { PlaybackControls } from './PlaybackControls';
import { TimelineSlider } from './TimelineSlider';
import { useDashboardContext } from '../../context/DashboardContext';
import { Zap } from 'lucide-react';

export const BottomBar: React.FC = () => {
  const { speed, setSpeed, isPlaying, setIsPlaying, setProgress, simulateOutage, setSimulateOutage } = useDashboardContext();

  const speeds = [0.5, 1, 2, 4];

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) return;

      if (e.code === 'Space') {
        e.preventDefault();
        setIsPlaying(!isPlaying);
      } else if (e.code === 'ArrowRight') {
        e.preventDefault();
        setProgress((prev) => Math.min(1, prev + 0.02));
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        setProgress((prev) => Math.max(0, prev - 0.02));
      } else if (e.key === 'o' || e.key === 'O') {
        e.preventDefault();
        setSimulateOutage(!simulateOutage);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isPlaying, setIsPlaying, setProgress, simulateOutage, setSimulateOutage]);

  return (
    <div className="portal-bottom-bar">
      <PlaybackControls />
      <TimelineSlider />

      {/* Speed Selector */}
      <div className="speed-pill-group">
        {speeds.map((s) => (
          <button
            key={s}
            className={`speed-pill-btn ${speed === s ? 'active' : ''}`}
            onClick={() => setSpeed(s)}
            title={`Speed: ${s}×`}
          >
            {s}×
          </button>
        ))}
      </div>

      {/* Outage Simulation Switch */}
      <button 
        className={`outage-toggle-btn ${simulateOutage ? 'active-outage' : ''}`}
        onClick={() => setSimulateOutage(!simulateOutage)}
        title="Simulate GNSS Outage [O]"
      >
        <Zap size={13} />
        <span>{simulateOutage ? 'RESTORE GNSS' : 'SIMULATE OUTAGE'}</span>
      </button>
    </div>
  );
};

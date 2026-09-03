import React, { useState, useEffect } from 'react';
import { PlaybackControls } from './PlaybackControls';
import { TimelineSlider } from './TimelineSlider';
import { ChartsPanel } from './ChartsPanel';
import { useDashboardContext } from '../../context/DashboardContext';
import { LineChart, ChevronUp, ChevronDown, Command } from 'lucide-react';

export const BottomBar: React.FC = () => {
  const [chartsOpen, setChartsOpen] = useState(false);
  const { speed, setSpeed, isPlaying, setIsPlaying, setProgress, simulateOutage, setSimulateOutage } = useDashboardContext();

  const speeds = [0.5, 1, 2, 4];

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input
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
      } else if (e.key === 'c' || e.key === 'C') {
        e.preventDefault();
        setChartsOpen((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isPlaying, setIsPlaying, setProgress, simulateOutage, setSimulateOutage]);

  return (
    <>
      <ChartsPanel isOpen={chartsOpen} />
      
      <div className="portal-bottom">
        <PlaybackControls />
        <TimelineSlider />

        {/* Speed Selector Segmented Pill */}
        <div className="speed-segment-group">
          {speeds.map((s) => (
            <button
              key={s}
              className={`speed-pill ${speed === s ? 'active' : ''}`}
              onClick={() => setSpeed(s)}
              title={`Playback Rate: ${s}×`}
            >
              {s}×
            </button>
          ))}
        </div>

        {/* Expandable Charts Button */}
        <button 
          className={`charts-toggle-btn ${chartsOpen ? 'open' : ''}`} 
          onClick={() => setChartsOpen(!chartsOpen)}
          title="Toggle Telemetry Graphs [C]"
        >
          <LineChart size={13} />
          <span>CHARTS</span>
          {chartsOpen ? <ChevronDown size={13} /> : <ChevronUp size={13} />}
        </button>

        {/* Keyboard Quick Help Badge */}
        <div className="bottom-kbd-hint" title="Keyboard controls: [Space] Play/Pause • [←/→] Scrub • [O] Outage • [C] Charts">
          <Command size={11} />
          <span>KBD</span>
        </div>
      </div>
    </>
  );
};

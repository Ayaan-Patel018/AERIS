import React from 'react';
import { PlaybackControls } from './PlaybackControls';
import { TimelineSlider } from './TimelineSlider';
import { ChartsPanel } from './ChartsPanel';
import { useDashboardContext } from '../../context/DashboardContext';

export const BottomBar: React.FC = () => {
  const { speed, setSpeed, chartsOpen, setChartsOpen } = useDashboardContext();

  const cycleSpeed = () => {
    const opts = [0.5, 1, 2, 4];
    const next = opts[(opts.indexOf(speed) + 1) % opts.length];
    setSpeed(next);
  };

  return (
    <>
      <ChartsPanel isOpen={chartsOpen} />
      
      <div className="portal-bottom">
        <PlaybackControls />
        <TimelineSlider />
        <button className="spd-btn" onClick={cycleSpeed}>{speed}×</button>
        <button className="expand-btn" onClick={() => setChartsOpen(!chartsOpen)}>
          CHARTS {chartsOpen ? '▼' : '▲'}
        </button>
      </div>
    </>
  );
};

import React from 'react';
import { useDashboardContext } from '../../context/DashboardContext';
import { Play, Pause } from 'lucide-react';

export const PlaybackControls: React.FC = () => {
  const { isPlaying, setIsPlaying } = useDashboardContext();

  const togglePlay = () => {
    setIsPlaying(!isPlaying);
  };

  return (
    <button 
      className={`cockpit-play-btn ${isPlaying ? 'playing' : ''}`}
      onClick={togglePlay} 
      aria-label={isPlaying ? 'Pause Simulation' : 'Start Simulation'}
      title={isPlaying ? 'Pause [Space]' : 'Play [Space]'}
    >
      {isPlaying ? <Pause size={14} /> : <Play size={14} className="play-triangle" />}
    </button>
  );
};

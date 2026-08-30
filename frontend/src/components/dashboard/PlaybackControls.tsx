import React from 'react';
import { useDashboardContext } from '../../context/DashboardContext';

export const PlaybackControls: React.FC = () => {
  const { isPlaying, setIsPlaying } = useDashboardContext();

  const togglePlay = () => {
    setIsPlaying(!isPlaying);
  };



  return (
    <>
      <button className="play-btn" onClick={togglePlay} aria-label="Play/Pause">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" stroke="none">
          {isPlaying 
            ? <polygon points="6 19 6 5 18 5 18 19" /> 
            : <polygon points="5 3 19 12 5 21 5 3" />
          }
        </svg>
      </button>
      {/* Expose speed btn externally so BottomBar can place it correctly if needed, 
          but we'll just return an array/fragment and let BottomBar structure it, 
          or better yet, keep them decoupled. */}
    </>
  );
};

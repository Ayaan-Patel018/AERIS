import { useEffect, useRef } from 'react';
import { useDashboardContext } from '../context/DashboardContext';
import { TOTAL_DURATION } from './useGNSSStatus';

// Was hardcoded to 60 (seconds), but our real S3b sequence is 681.1s
// (11:21) — that mismatch made 1x playback race through the data ~11x
// faster than real time, causing visible jumping/spinning through sharp
// turns. Now imports the same real duration constant useGNSSStatus.ts
// already exports, so 1x = actual real-time correspondence to the data.
// Use the `speed` control to play faster for a shorter demo loop —
// that's what it's for, rather than baking artificial compression in here.
const TOTAL_DURATION_SEC = TOTAL_DURATION;

export const usePlayback = () => {
  const { isPlaying, setIsPlaying, progress, setProgress, speed } = useDashboardContext();
  const requestRef = useRef<number>(0);
  const lastTimeRef = useRef<number>(0);

  const animate = (time: number) => {
    if (lastTimeRef.current !== 0) {
      const deltaTime = (time - lastTimeRef.current) / 1000;
      setProgress((prevProgress: number) => {
        let nextProgress = prevProgress + (deltaTime * speed) / TOTAL_DURATION_SEC;
        if (nextProgress >= 1) {
          nextProgress = 1;
          setIsPlaying(false);
        }
        return nextProgress;
      });
    }
    lastTimeRef.current = time;
    if (isPlaying) {
      requestRef.current = requestAnimationFrame(animate);
    }
  };

  useEffect(() => {
    if (isPlaying) {
      if (progress >= 1) setProgress(0); // auto-restart
      requestRef.current = requestAnimationFrame(animate);
    } else {
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
      lastTimeRef.current = 0;
    }
    return () => {
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
    };
  }, [isPlaying, speed]);
};

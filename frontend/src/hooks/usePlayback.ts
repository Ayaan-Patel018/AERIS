import { useEffect, useRef } from 'react';
import { useDashboardContext } from '../context/DashboardContext';

const TOTAL_DURATION_SEC = 60;

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

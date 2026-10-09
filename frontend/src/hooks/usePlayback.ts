import { useEffect, useRef } from "react";
import { useDashboardContext } from "../context/DashboardContext";

export const usePlayback = () => {
  const {
    isPlaying,
    setIsPlaying,
    progress,
    setProgress,
    speed,
    totalDurationS,
  } = useDashboardContext();

  const requestRef  = useRef<number>(0);
  const lastTimeRef = useRef<number>(0);

  const animate = (time: number) => {
    if (lastTimeRef.current !== 0) {
      const deltaTime = (time - lastTimeRef.current) / 1000;
      setProgress((prev: number) => {
        const next = prev + (deltaTime * speed) / totalDurationS;
        if (next >= 1) {
          setIsPlaying(false);
          return 1;
        }
        return next;
      });
    }
    lastTimeRef.current = time;
    if (isPlaying) {
      requestRef.current = requestAnimationFrame(animate);
    }
  };

  useEffect(() => {
    if (isPlaying) {
      if (progress >= 1) setProgress(0);
      requestRef.current = requestAnimationFrame(animate);
    } else {
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
      lastTimeRef.current = 0;
    }
    return () => {
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
    };
  }, [isPlaying, speed, totalDurationS]);
};

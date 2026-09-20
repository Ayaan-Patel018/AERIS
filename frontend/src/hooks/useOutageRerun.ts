import { useEffect, useCallback, useRef } from 'react';
import { useDashboardContext } from '../context/DashboardContext';

const API_BASE_URL = 'http://localhost:8000';

export const useOutageRerun = () => {
  const {
    outageStartSec,
    outageEndSec,
    setOutageWindow,
    isRecomputing,
    setIsRecomputing,
    setDynamicData,
    backendStatus,
    setBackendStatus,
  } = useDashboardContext();

  const abortControllerRef = useRef<AbortController | null>(null);

  // Health check on mount
  useEffect(() => {
    let isMounted = true;
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/health`, { method: 'GET', signal: AbortSignal.timeout(2000) });
        if (res.ok) {
          if (isMounted) setBackendStatus('connected');
        } else {
          if (isMounted) setBackendStatus('disconnected');
        }
      } catch {
        if (isMounted) setBackendStatus('disconnected');
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [setBackendStatus]);

  // Execute scenario re-run on backend
  const rerunScenario = useCallback(
    async (startSec: number, endSec: number, useRts: boolean = true) => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const controller = new AbortController();
      abortControllerRef.current = controller;

      setIsRecomputing(true);
      setOutageWindow(startSec, endSec);

      try {
        const response = await fetch(`${API_BASE_URL}/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            outage_start: startSec,
            outage_end: endSec,
            use_rts: useRts,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Server returned status ${response.status}`);
        }

        const data = await response.json();
        setDynamicData(data);
        setBackendStatus('connected');
        console.log(`[AERIS] InESEKF + RTS re-run completed in ${data.elapsed_s}s`);
      } catch (err: any) {
        if (err.name === 'AbortError') {
          return;
        }
        console.warn('[AERIS] Backend /run request failed or server offline:', err.message);
        setBackendStatus('disconnected');
      } finally {
        setIsRecomputing(false);
      }
    },
    [setIsRecomputing, setOutageWindow, setDynamicData, setBackendStatus]
  );

  return {
    rerunScenario,
    isRecomputing,
    backendStatus,
    outageStartSec,
    outageEndSec,
  };
};

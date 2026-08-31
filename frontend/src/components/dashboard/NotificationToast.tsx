import React, { useEffect, useState } from 'react';
import { useGNSSStatus } from '../../hooks/useGNSSStatus';

interface Toast {
  id: string;
  type: 'ok' | 'err' | 'warn' | 'dr';
  title: string;
  body: string;
}

export const NotificationToast: React.FC = () => {
  const { isOutage, isRecovered, confidence } = useGNSSStatus();
  const [toasts, setToasts] = useState<Toast[]>([]);
  
  // Track previous states to trigger toasts only on change
  const [prevOutage, setPrevOutage] = useState(false);
  const [prevRecovered, setPrevRecovered] = useState(false);
  const [lowConfToasted, setLowConfToasted] = useState(false);

  const addToast = (toast: Toast) => {
    setToasts(prev => [...prev, toast]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== toast.id));
    }, 3500);
  };

  useEffect(() => {
    if (isOutage && !prevOutage) {
      addToast({
        id: `lost-${Date.now()}`, type: 'err', 
        title: '⚠ GNSS SIGNAL LOST', 
        body: 'Dead reckoning engaged. Onboard sensors now tracking position.'
      });
      setTimeout(() => {
        addToast({
          id: `dr-${Date.now()}`, type: 'dr', 
          title: '◉ DEAD RECKONING ACTIVE', 
          body: 'AERIS holding position using motion sensors.'
        });
      }, 800);
      setPrevOutage(true);
      setPrevRecovered(false);
      setLowConfToasted(false);
    }
    
    if (isRecovered && !prevRecovered) {
      addToast({
        id: `reacq-${Date.now()}`, type: 'ok', 
        title: '✓ GNSS REACQUIRED', 
        body: 'Satellite fix restored. Fusing back to GNSS — no position jump.'
      });
      setPrevRecovered(true);
      setPrevOutage(false);
    }

    if (isOutage && confidence < 72 && !lowConfToasted) {
      addToast({
        id: `conf-${Date.now()}`, type: 'warn', 
        title: '△ LOW CONFIDENCE', 
        body: `Position estimate at ${confidence.toFixed(0)}% — error may be increasing.`
      });
      setLowConfToasted(true);
    }
    
    if (!isOutage && !isRecovered) {
      // Reset when back at start
      setPrevOutage(false);
      setPrevRecovered(false);
      setLowConfToasted(false);
    }
  }, [isOutage, isRecovered, confidence]);

  return (
    <div className="toast-wrap" id="toastWrap">
      {toasts.map(t => (
        <div key={t.id} className={`toast t-${t.type} show`}>
          <div className="toast-title">{t.title}</div>
          <div className="toast-body">{t.body}</div>
        </div>
      ))}
    </div>
  );
};

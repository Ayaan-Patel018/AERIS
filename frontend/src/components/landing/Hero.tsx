import React, { useEffect, useRef, useState } from 'react';
import homeVideo from '../../assets/home-video.mp4';
import { Shield, Radio, Navigation, Terminal, Activity, ArrowRight } from 'lucide-react';

export const Hero: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [imuCount, setImuCount] = useState(6812);

  // Periodic IMU packet ticker effect
  useEffect(() => {
    const timer = setInterval(() => {
      setImuCount((prev) => prev + 10);
    }, 100);
    return () => clearInterval(timer);
  }, []);

  // Military Radar Scope Canvas
  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const ctx = cv.getContext('2d');
    if (!ctx) return;
    
    let w: number, h: number;
    let angle = 0;
    
    const resize = () => {
      w = cv.width = cv.offsetWidth;
      h = cv.height = cv.offsetHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    // Target blips
    const blips = [
      { r: 0.28, theta: 0.75, size: 2.5, alpha: 0.8 },
      { r: 0.45, theta: 2.1, size: 2, alpha: 0.7 },
      { r: 0.65, theta: 4.2, size: 3, alpha: 0.9 },
      { r: 0.82, theta: 5.3, size: 2, alpha: 0.6 }
    ];

    let animationId: number;
    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      const cx = w * 0.72;
      const cy = h * 0.5;
      const maxR = Math.min(w, h) * 0.48;

      // Draw faint concentric range rings
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
      ctx.lineWidth = 1;
      [0.25, 0.5, 0.75, 1.0].forEach((ratio) => {
        ctx.beginPath();
        ctx.arc(cx, cy, maxR * ratio, 0, Math.PI * 2);
        ctx.stroke();
      });

      // Crosshairs
      ctx.beginPath();
      ctx.moveTo(cx - maxR, cy);
      ctx.lineTo(cx + maxR, cy);
      ctx.moveTo(cx, cy - maxR);
      ctx.lineTo(cx, cy + maxR);
      ctx.stroke();

      // Sweeping radar beam (pie slice gradient)
      angle = (angle + 0.015) % (Math.PI * 2);
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, maxR, angle - 0.35, angle);
      ctx.closePath();
      const sweepGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, maxR);
      sweepGrad.addColorStop(0, 'rgba(45, 212, 191, 0.02)');
      sweepGrad.addColorStop(1, 'rgba(45, 212, 191, 0.12)');
      ctx.fillStyle = sweepGrad;
      ctx.fill();
      ctx.restore();

      // Sweep leading line
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(angle) * maxR, cy + Math.sin(angle) * maxR);
      ctx.strokeStyle = 'rgba(45, 212, 191, 0.35)';
      ctx.lineWidth = 1.2;
      ctx.stroke();

      // Blips
      blips.forEach((b) => {
        const bx = cx + Math.cos(b.theta) * (maxR * b.r);
        const by = cy + Math.sin(b.theta) * (maxR * b.r);
        
        // Check angle proximity for sweep illumination
        const diff = (angle - b.theta + Math.PI * 2) % (Math.PI * 2);
        const bright = diff < 0.5 ? 1 : 0.25;

        ctx.fillStyle = `rgba(45, 212, 191, ${bright})`;
        ctx.beginPath();
        ctx.arc(bx, by, b.size, 0, Math.PI * 2);
        ctx.fill();

        if (diff < 0.5) {
          ctx.strokeStyle = `rgba(45, 212, 191, ${0.4 * (1 - diff * 2)})`;
          ctx.beginPath();
          ctx.arc(bx, by, b.size * 3, 0, Math.PI * 2);
          ctx.stroke();
        }
      });

      animationId = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationId);
    };
  }, []);

  const handleLaunch = () => {
    const pt = document.getElementById('pageTransition');
    if (pt) pt.classList.add('active');
    setTimeout(() => {
      window.location.href = '/portal';
    }, 280);
  };

  return (
    <section className="hero container border-b">
      <canvas id="heroCanvas" ref={canvasRef}></canvas>
      <div className="hero-inner grid-5">
        <div className="b-dot bl"></div><div className="b-dot br"></div>
        <div className="hero-copy">
          <div className="hc-top">
            <div className="b-dot br"></div>
            <div className="hero-badge-strip">
              <span className="hero-tag-chip">
                <Shield size={12} color="var(--status-ok)" />
                <span>SIH 26168 // ISRO DOS DOMAIN</span>
              </span>
              <span className="hero-status-live">
                <span className="pulse-dot"></span>
                <span>15-STATE ES-EKF READY</span>
              </span>
            </div>
            <h1 className="hero-title rev d1 in" style={{ marginBottom: 0 }}>
              Navigation That Never Stops
            </h1>
          </div>
          <div className="hc-mid">
            <div className="b-dot br"></div>
            <p className="hero-sub rev d2 in">
              AERIS uses onboard inertial sensors and Error-State Kalman Filters to maintain sub-meter dead reckoning navigation when GPS signals are jammed, spoofed, or lost in tunnels and urban canyons.
            </p>
          </div>
          <div className="hc-bot">
            <div className="hc-btn-cell" style={{ borderRight: '1px solid var(--line)' }} onClick={handleLaunch}>
              <button className="solid-hero-btn">
                <span>LAUNCH GNSS COCKPIT</span>
                <ArrowRight size={14} />
              </button>
            </div>
            <div className="hc-btn-cell">
              <a href="#problem" className="solid-hero-link">SYSTEM SPECS ↓</a>
            </div>
          </div>
        </div>

        <div className="hero-vis">
          <div className="hero-top-spacer"></div>
          <div className="hero-video-box rev d3 in">
            <div className="b-dot bl"></div><div className="b-dot br"></div>
            <video 
              src={homeVideo} 
              autoPlay 
              loop 
              muted 
              playsInline 
              disablePictureInPicture
              className="hero-video"
            />
          </div>

          {/* Solid Defense Telemetry Terminal Card */}
          <div className="hero-telemetry rev d4 in">
            <div className="telemetry-terminal-card">
              <div className="terminal-header">
                <div className="terminal-title">
                  <Terminal size={12} color="var(--status-ok)" />
                  <span>ONBOARD SENSOR BUS // TELEMETRY STREAM</span>
                </div>
                <div className="terminal-freq">100 HZ</div>
              </div>

              <div className="terminal-grid">
                <div className="term-cell">
                  <span className="term-k">ESTIMATOR</span>
                  <span className="term-v ok">15-STATE ES-EKF</span>
                </div>
                <div className="term-cell">
                  <span className="term-k">IMU FRAMES</span>
                  <span className="term-v data">{imuCount.toLocaleString()}</span>
                </div>
                <div className="term-cell">
                  <span className="term-k">FIX ORIGIN</span>
                  <span className="term-v">52.370°N, 1.254°W</span>
                </div>
                <div className="term-cell">
                  <span className="term-k">OUTAGE TOLERANCE</span>
                  <span className="term-v warn">60.0s UNCONSTRAINED</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

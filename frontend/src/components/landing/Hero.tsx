import React, { useEffect, useRef } from 'react';
import homeVideo from '../../assets/home-video.mp4';

export const Hero: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const ctx = cv.getContext('2d');
    if (!ctx) return;
    
    let w: number, h: number;
    const pts: {x:number, y:number, vx:number, vy:number}[] = [];
    
    const resize = () => {
      w = cv.width = cv.offsetWidth;
      h = cv.height = cv.offsetHeight;
    };
    resize();
    window.addEventListener('resize', resize);
    
    for (let i = 0; i < 40; i++) {
      pts.push({
        x: Math.random() * 100,
        y: Math.random() * 100,
        vx: (Math.random() - 0.5) * 0.2,
        vy: (Math.random() - 0.5) * 0.2
      });
    }

    let animationId: number;
    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = 'rgba(255,255,255,0.1)';
      pts.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > 100) p.vx *= -1;
        if (p.y < 0 || p.y > 100) p.vy *= -1;
        ctx.beginPath();
        ctx.arc((p.x / 100) * w, (p.y / 100) * h, 1, 0, Math.PI * 2);
        ctx.fill();
      });
      animationId = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationId);
    };
  }, []);

  return (
    <section className="hero container border-b">
      <canvas id="heroCanvas" ref={canvasRef}></canvas>
      <div className="hero-inner grid-5">
        <div className="b-dot bl"></div><div className="b-dot br"></div>
        <div className="hero-copy">
          <div className="hc-top">
            <div className="b-dot br"></div>
            <h1 className="hero-title rev d1 in" style={{ marginBottom: 0 }}>Navigation That Never Stops</h1>
          </div>
          <div className="hc-mid">
            <div className="b-dot br"></div>
            <p className="hero-sub rev d2 in">
              AERIS uses onboard inertial sensors and AI to maintain precise navigation when GPS signals fail in tunnels, urban canyons, or jammed environments.
            </p>
          </div>
          <div className="hc-bot">
            <div className="hc-btn-cell" style={{ borderRight: '1px solid var(--line)' }} onClick={() => {
              const pt = document.getElementById('pageTransition');
              if (pt) pt.classList.add('active');
              setTimeout(() => {
                window.location.href = '/portal';
              }, 320);
            }}>
              <span>LAUNCH DEMO</span>
            </div>
            <div className="hc-btn-cell">
              <a href="#problem">LEARN MORE ↓</a>
            </div>
          </div>
        </div>
        <div className="hero-vis">
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
          <div className="hero-telemetry rev d4 in">
          </div>
        </div>
      </div>
    </section>
  );
};

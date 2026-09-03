export const drawVehicleMarker = (
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  heading: number,
  color: string,
  isOutage: boolean = false
) => {
  ctx.save();

  // If in outage, draw active emergency beacon pulse ring
  if (isOutage) {
    const timeSec = performance.now() / 1000;
    const pulsePhase = (timeSec * 1.5) % 1;
    const pulseR = 10 + pulsePhase * 18;
    const pulseAlpha = (1 - pulsePhase) * 0.75;

    ctx.strokeStyle = `rgba(240, 128, 30, ${pulseAlpha})`;
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(x, y, pulseR, 0, Math.PI * 2);
    ctx.stroke();
  }

  // Draw arrow vehicle marker
  ctx.translate(x, y);
  ctx.rotate(heading);
  ctx.beginPath();
  ctx.moveTo(11, 0);
  ctx.lineTo(-7, 6.5);
  ctx.lineTo(-3.5, 0);
  ctx.lineTo(-7, -6.5);
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.shadowBlur = 12;
  ctx.shadowColor = color;
  ctx.fill();
  ctx.restore();
};

export const drawVehicleMarker = (
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  heading: number,
  color: string,
  label?: string,
  isOutage: boolean = false,
  showHalo: boolean = true,
  badgeOffset?: { dx: number; dy: number }
) => {
  ctx.save();

  // 1. Permanent Locator Halo Ring (for spatial presence)
  if (showHalo) {
    ctx.beginPath();
    ctx.arc(x, y, 22, 0, Math.PI * 2);
    ctx.strokeStyle = isOutage ? 'rgba(240, 128, 30, 0.45)' : (color === '#A855F7' ? 'rgba(168, 85, 247, 0.45)' : 'rgba(45, 212, 191, 0.4)');
    ctx.lineWidth = 1.4;
    ctx.setLineDash([4, 4]);
    ctx.stroke();
    ctx.setLineDash([]);

    // 2. Active Pulse Wave (radar beacon)
    const timeSec = performance.now() / 1000;
    const pulseSpeed = isOutage ? 2.5 : 1.2;
    const pulsePhase = (timeSec * pulseSpeed) % 1;
    const maxR = isOutage ? 44 : 32;
    const pulseR = 10 + pulsePhase * (maxR - 10);
    const pulseAlpha = (1 - pulsePhase) * (isOutage ? 0.9 : 0.55);

    ctx.beginPath();
    ctx.arc(x, y, pulseR, 0, Math.PI * 2);
    ctx.strokeStyle = isOutage ? `rgba(229, 72, 77, ${pulseAlpha})` : (color === '#A855F7' ? `rgba(168, 85, 247, ${pulseAlpha})` : `rgba(45, 212, 191, ${pulseAlpha})`);
    ctx.lineWidth = isOutage ? 2 : 1.4;
    ctx.stroke();
  }

  // 3. Move to vehicle location and rotate to vehicle orientation
  ctx.translate(x, y);
  ctx.rotate(heading);

  // 4. Forward Velocity Vector Line (tactical projection)
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(17, 0);
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // 5. Tactical Chevron Arrow
  ctx.beginPath();
  ctx.moveTo(10, 0);      // Arrow tip
  ctx.lineTo(-7, 6);      // Right wing
  ctx.lineTo(-3, 0);      // Inner notch
  ctx.lineTo(-7, -6);     // Left wing
  ctx.closePath();

  // Contrast Border (Solid black border makes it 100% visible on any background)
  ctx.strokeStyle = '#050508';
  ctx.lineWidth = 2.0;
  ctx.lineJoin = 'round';
  ctx.stroke();

  // Vibrant Fill with glow
  ctx.fillStyle = color;
  ctx.shadowBlur = 8;
  ctx.shadowColor = color;
  ctx.fill();

  // 6. Center Cockpit Core Dot
  ctx.beginPath();
  ctx.arc(0, 0, 1.5, 0, Math.PI * 2);
  ctx.fillStyle = '#FFFFFF';
  ctx.shadowBlur = 0;
  ctx.fill();

  ctx.restore();

  // 7. Tactical Identifier Badge (rendered upright, not rotated)
  if (label) {
    ctx.save();
    ctx.font = 'bold 9px "JetBrains Mono", monospace';
    const tagPadding = 4;
    const tagText = label.toUpperCase();
    const textMetrics = ctx.measureText(tagText);
    const tagW = textMetrics.width + tagPadding * 2;
    const tagH = 14;
    const tagX = x + (badgeOffset?.dx ?? 16);
    const tagY = y + (badgeOffset?.dy ?? -18);

    // Badge background box
    ctx.fillStyle = '#08080C';
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(tagX, tagY, tagW, tagH, 2);
    ctx.fill();
    ctx.stroke();

    // Badge text
    ctx.fillStyle = color;
    ctx.textBaseline = 'middle';
    ctx.fillText(tagText, tagX + tagPadding, tagY + tagH / 2);
    ctx.restore();
  }
};

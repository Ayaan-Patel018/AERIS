export const drawTrajectory = (
  ctx: CanvasRenderingContext2D,
  pts: {x: number, y: number}[],
  color: string,
  width: number,
  isDashed = false
) => {
  if (pts.length < 2) return;
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  if (isDashed) {
    ctx.setLineDash([5, 5]);
  } else {
    ctx.setLineDash([]);
  }
  ctx.moveTo(pts[0].x, pts[0].y);
  for (let i = 1; i < pts.length; i++) {
    ctx.lineTo(pts[i].x, pts[i].y);
  }
  ctx.stroke();
  ctx.setLineDash([]); // reset
};

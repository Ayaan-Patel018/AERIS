export const drawUncertaintyCircle = (
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  radius: number,
  color: string
) => {
  if (radius <= 0) return;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = color.replace('.15', '.4');
  ctx.lineWidth = 1;
  ctx.stroke();
};

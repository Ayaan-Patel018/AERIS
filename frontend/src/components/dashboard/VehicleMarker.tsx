export const drawVehicleMarker = (
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  heading: number,
  color: string
) => {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(heading);
  ctx.beginPath();
  ctx.moveTo(10, 0);
  ctx.lineTo(-6, 6);
  ctx.lineTo(-3, 0);
  ctx.lineTo(-6, -6);
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.fill();
  ctx.shadowBlur = 10;
  ctx.shadowColor = color;
  ctx.fill();
  ctx.restore();
};

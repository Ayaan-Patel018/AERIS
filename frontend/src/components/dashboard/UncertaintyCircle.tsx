/**
 * UncertaintyCircle.tsx — Mathematical 2σ Covariance Ellipse & Uncertainty Circle
 *
 * Implements:
 * 1. drawCovarianceEllipse: Honest 2σ confidence ellipse from the 2×2 East-North
 *    covariance block:
 *      Σ_EN = [[cov_xx, cov_xy],
 *              [cov_xy, cov_yy]]  (m²)
 *    Eigendecomposition yields principal axes (semi-major a = 2√λ₁, semi-minor b = 2√λ₂)
 *    and orientation angle θ. Under non-holonomic constraints (NHC), lateral error is
 *    bounded while forward error drifts, creating a realistic elongated error ellipse.
 *
 * 2. drawUncertaintyCircle: Isotropic fallback circle based on scalar radius.
 */

export const drawCovarianceEllipse = (
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  cov_xx: number,
  cov_yy: number,
  cov_xy: number,
  metresToPixels: (m: number) => number,
  color: string,
  sigma: number = 2.0
) => {
  // If covariance is invalid or degenerate, return
  if (isNaN(cov_xx) || isNaN(cov_yy) || isNaN(cov_xy) || (cov_xx <= 0 && cov_yy <= 0)) {
    return;
  }

  // 1. Analytical eigendecomposition of 2×2 symmetric covariance matrix
  //    λ = (tr ± sqrt(tr² - 4·det)) / 2
  const tr = cov_xx + cov_yy;
  const det = cov_xx * cov_yy - cov_xy * cov_xy;
  const disc = Math.max(0, (tr * tr) / 4 - det);
  const sqrtDisc = Math.sqrt(disc);

  const lambda1 = Math.max(0, tr / 2 + sqrtDisc); // Major eigenvalue (variance along major axis)
  const lambda2 = Math.max(0, tr / 2 - sqrtDisc); // Minor eigenvalue (variance along minor axis)

  // 2. Semi-axes in metres scaled by confidence level (sigma=2 gives ~95.4% confidence region)
  const aMeters = sigma * Math.sqrt(lambda1);
  const bMeters = sigma * Math.sqrt(lambda2);

  // Convert to canvas pixel dimensions
  const aPx = Math.max(metresToPixels(aMeters), 3);
  const bPx = Math.max(metresToPixels(bMeters), 3);

  // 3. Eigenvector angle of major axis in ENU navigation frame (East = +x, North = +y)
  //    v₁ corresponds to eigenvalue lambda1:
  //    (cov_xx - lambda1)*v_x + cov_xy*v_y = 0  =>  angle = atan2(lambda1 - cov_xx, cov_xy) or atan2(2*cov_xy, cov_xx - cov_yy)/2
  let enuAngle = 0;
  if (Math.abs(cov_xy) > 1e-7 || Math.abs(cov_xx - cov_yy) > 1e-7) {
    enuAngle = 0.5 * Math.atan2(2 * cov_xy, cov_xx - cov_yy);
  }

  // In HTML canvas coordinates: East (+X) is right, North (+Y) is UP.
  // But canvas Y increases downwards, so a positive ENU angle (counter-clockwise from East)
  // corresponds to a negative rotation in canvas space.
  const canvasAngle = -enuAngle;

  // 4. Render oriented 2σ covariance ellipse
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(canvasAngle);

  ctx.beginPath();
  ctx.ellipse(0, 0, aPx, bPx, 0, 0, Math.PI * 2);

  // Fill translucent uncertainty glow
  ctx.fillStyle = color;
  ctx.fill();

  // Highlight border with matching accent
  ctx.strokeStyle = color.replace(/[\d.]+\)$/, '0.65)');
  ctx.lineWidth = 1.4;
  ctx.stroke();

  // Subtle directional major axis indicator line inside ellipse
  if (aPx > 12) {
    ctx.beginPath();
    ctx.setLineDash([2, 3]);
    ctx.moveTo(-aPx * 0.75, 0);
    ctx.lineTo(aPx * 0.75, 0);
    ctx.strokeStyle = color.replace(/[\d.]+\)$/, '0.45)');
    ctx.lineWidth = 1.0;
    ctx.stroke();
    ctx.setLineDash([]);
  }

  ctx.restore();
};

export const drawUncertaintyCircle = (
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  radius: number,
  color: string
) => {
  if (radius <= 0 || isNaN(radius)) return;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = color.replace(/[\d.]+\)$/, '0.45)');
  ctx.lineWidth = 1;
  ctx.stroke();
};

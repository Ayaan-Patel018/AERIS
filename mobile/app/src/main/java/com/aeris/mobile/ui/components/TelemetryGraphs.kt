package com.aeris.mobile.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.domain.model.GnssStatus
import com.aeris.mobile.domain.model.OutageWindow
import com.aeris.mobile.domain.model.TrajectoryPoint
import com.aeris.mobile.ui.theme.Aeris

/**
 * Three synchronized telemetry curves per M07 §4:
 * 1. Position Uncertainty (1σ semi-major, m)
 * 2. Vehicle Speed (km/h)
 * 3. Vehicle Heading (deg)
 */
@Composable
fun TelemetryGraphs(
    points: List<TrajectoryPoint>,
    outages: List<OutageWindow>,
    currentFraction: Float,
    durationSec: Double,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(colors.paper)
            .border(1.dp, colors.harbor, RoundedCornerShape(16.dp))
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Section Header
        Text(
            text = "TELEMETRY OVER TIME",
            color = colors.ink3,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.8.sp
        )

        // 1. Uncertainty Graph (The Hero Metric)
        SingleGraph(
            title = "Position Uncertainty (1σ, metres)",
            points = points,
            outages = outages,
            durationSec = durationSec,
            currentFraction = currentFraction,
            valueExtractor = { it.sigma ?: 0.0 },
            strokeColor = colors.amber,
            fillColor = colors.amberSoft.copy(alpha = 0.5f),
        )

        // 2. Speed Graph
        SingleGraph(
            title = "Speed (km/h)",
            points = points,
            outages = outages,
            durationSec = durationSec,
            currentFraction = currentFraction,
            valueExtractor = { (it.speedMps ?: 0.0) * 3.6 },
            strokeColor = colors.cobalt,
            fillColor = colors.cobaltSoft.copy(alpha = 0.4f),
        )

        // 3. Heading Graph
        SingleGraph(
            title = "Heading (degrees)",
            points = points,
            outages = outages,
            durationSec = durationSec,
            currentFraction = currentFraction,
            valueExtractor = { it.headingDeg ?: 0.0 },
            strokeColor = colors.slate,
            fillColor = Color.Transparent,
        )
    }
}

@Composable
private fun SingleGraph(
    title: String,
    points: List<TrajectoryPoint>,
    outages: List<OutageWindow>,
    durationSec: Double,
    currentFraction: Float,
    valueExtractor: (TrajectoryPoint) -> Double,
    strokeColor: Color,
    fillColor: Color,
) {
    val colors = Aeris.colors

    Column(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = title,
                color = colors.ink2,
                fontSize = 11.5.sp,
                fontWeight = FontWeight.SemiBold
            )
        }

        Spacer(modifier = Modifier.height(6.dp))

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(64.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(colors.harbor2.copy(alpha = 0.5f))
        ) {
            Canvas(modifier = Modifier.matchParentSize()) {
                val w = size.width
                val h = size.height

                // 1. Draw outage band backdrops
                if (durationSec > 0.0) {
                    for (outage in outages) {
                        val sFrac = (outage.startSec / durationSec).toFloat().coerceIn(0f, 1f)
                        val eFrac = (outage.endSec / durationSec).toFloat().coerceIn(0f, 1f)
                        drawRect(
                            color = colors.amberSoft.copy(alpha = 0.7f),
                            topLeft = Offset(sFrac * w, 0f),
                            size = Size((eFrac - sFrac) * w, h)
                        )
                    }
                }

                // 2. Draw telemetry curve
                if (points.size >= 2) {
                    val maxVal = points.maxOfOrNull { valueExtractor(it) }?.coerceAtLeast(1.0) ?: 1.0

                    // Decimate if many points for high 60fps performance
                    val step = (points.size / 200).coerceAtLeast(1)
                    val sampled = points.filterIndexed { index, _ -> index % step == 0 || index == points.lastIndex }

                    val linePath = Path()
                    val fillPath = Path()

                    fillPath.moveTo(0f, h)

                    for (i in sampled.indices) {
                        val pt = sampled[i]
                        val x = if (durationSec > 0) (pt.timestampSec / durationSec).toFloat() * w else (i.toFloat() / (sampled.size - 1)) * w
                        val y = h - ((valueExtractor(pt) / maxVal).toFloat() * (h - 8.dp.toPx()))

                        if (i == 0) {
                            linePath.moveTo(x, y)
                            fillPath.lineTo(x, y)
                        } else {
                            linePath.lineTo(x, y)
                            fillPath.lineTo(x, y)
                        }
                    }

                    fillPath.lineTo(w, h)
                    fillPath.close()

                    if (fillColor != Color.Transparent) {
                        drawPath(fillPath, color = fillColor)
                    }
                    drawPath(linePath, color = strokeColor, style = Stroke(width = 1.5.dp.toPx()))
                }

                // 3. Playhead cursor
                val playheadX = (w * currentFraction).coerceIn(0f, w)
                drawLine(
                    color = colors.ink,
                    start = Offset(playheadX, 0f),
                    end = Offset(playheadX, h),
                    strokeWidth = 1.5.dp.toPx()
                )
            }
        }
    }
}

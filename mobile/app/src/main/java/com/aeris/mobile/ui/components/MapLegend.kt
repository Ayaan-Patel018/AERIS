package com.aeris.mobile.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import com.aeris.mobile.ui.theme.AerisGrey10
import com.aeris.mobile.ui.theme.AerisGrey50
import com.aeris.mobile.ui.theme.AerisGrey70
import com.aeris.mobile.ui.theme.AerisWhite

/**
 * Small on-map legend explaining the three route visual treatments.
 *
 * Since the design is monochrome, the polyline states are distinguished
 * by line style and marker shape rather than colour:
 * 1. **Solid line + filled marker** — GNSS locked.
 * 2. **Dashed line + hollow marker** — dead reckoning.
 * 3. **Dashed line + double-ring marker** — low confidence / anomaly.
 */
@Composable
fun MapLegend(modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(AerisGrey10.copy(alpha = 0.85f))
            .padding(10.dp),
    ) {
        LegendItem(type = LegendType.GPS_LOCKED, label = "GPS locked")
        Spacer(modifier = Modifier.height(4.dp))
        LegendItem(type = LegendType.DEAD_RECKONING, label = "Estimating")
        Spacer(modifier = Modifier.height(4.dp))
        LegendItem(type = LegendType.LOW_CONFIDENCE, label = "Low confidence")
    }
}

private enum class LegendType { GPS_LOCKED, DEAD_RECKONING, LOW_CONFIDENCE }

@Composable
private fun LegendItem(type: LegendType, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Canvas(modifier = Modifier.size(width = 28.dp, height = 12.dp)) {
            drawLegendSample(type)
        }
        Spacer(modifier = Modifier.width(6.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = AerisGrey70,
        )
    }
}

private fun DrawScope.drawLegendSample(type: LegendType) {
    val y = size.height / 2
    val markerRadius = 4f

    when (type) {
        LegendType.GPS_LOCKED -> {
            // Solid line
            drawLine(
                color = Color.White,
                start = Offset(0f, y),
                end = Offset(size.width, y),
                strokeWidth = 2f,
            )
            // Filled circle marker
            drawCircle(
                color = Color.White,
                radius = markerRadius,
                center = Offset(size.width - markerRadius - 2f, y),
            )
        }
        LegendType.DEAD_RECKONING -> {
            // Dashed line
            drawLine(
                color = Color.White.copy(alpha = 0.7f),
                start = Offset(0f, y),
                end = Offset(size.width, y),
                strokeWidth = 2f,
                pathEffect = PathEffect.dashPathEffect(floatArrayOf(6f, 4f)),
            )
            // Hollow circle marker
            drawCircle(
                color = Color.White.copy(alpha = 0.7f),
                radius = markerRadius,
                center = Offset(size.width - markerRadius - 2f, y),
                style = Stroke(width = 1.5f),
            )
        }
        LegendType.LOW_CONFIDENCE -> {
            // Dashed line
            drawLine(
                color = AerisGrey50,
                start = Offset(0f, y),
                end = Offset(size.width, y),
                strokeWidth = 2f,
                pathEffect = PathEffect.dashPathEffect(floatArrayOf(4f, 4f)),
            )
            // Double-ring marker
            val cx = size.width - markerRadius - 2f
            drawCircle(
                color = AerisGrey50,
                radius = markerRadius + 2f,
                center = Offset(cx, y),
                style = Stroke(width = 1f),
            )
            drawCircle(
                color = AerisGrey50,
                radius = markerRadius,
                center = Offset(cx, y),
                style = Stroke(width = 1.5f),
            )
        }
    }
}

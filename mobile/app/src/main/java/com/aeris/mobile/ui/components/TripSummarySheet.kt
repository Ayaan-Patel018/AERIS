package com.aeris.mobile.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.service.RoutePoint
import com.aeris.mobile.ui.theme.AerisGrey30
import com.aeris.mobile.ui.theme.AerisGrey50

/**
 * Trip summary overlaid card shown after tracking stops.
 */
@Composable
fun TripSummarySheet(
    routePoints: List<RoutePoint>,
    distanceTraveledMeters: Double,
    totalGnssOutageSec: Long,
    maxDriftMeters: Double,
    averageConfidence: Double,
    onSaveTrip: () -> Unit = {},
    onDismiss: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
            .background(MaterialTheme.colorScheme.surface)
            .padding(horizontal = 24.dp)
            .padding(top = 16.dp, bottom = 24.dp)
            .height(500.dp) // Fixed height to allow scrolling
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = "Trip complete",
                style = MaterialTheme.typography.displaySmall,
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.Bold,
            )

            Spacer(modifier = Modifier.height(32.dp))

            // ── Route timeline strip ────────────────────────────────────────
            Text(
                text = "ROUTE HISTORY",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.align(Alignment.Start),
            )
            Spacer(modifier = Modifier.height(8.dp))
            RouteTimelineStrip(
                routePoints = routePoints,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(24.dp)
                    .clip(RoundedCornerShape(4.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant),
            )

            Spacer(modifier = Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text("Start", style = MaterialTheme.typography.labelSmall, color = AerisGrey30)
                Text("End", style = MaterialTheme.typography.labelSmall, color = AerisGrey30)
            }

            Spacer(modifier = Modifier.height(40.dp))

            // ── Stats ───────────────────────────────────────────────────────
            StatRow(
                label = "Total distance",
                value = formatDistance(distanceTraveledMeters),
            )
            StatRow(
                label = "Time without GNSS",
                value = formatDuration(totalGnssOutageSec),
            )
            StatRow(
                label = "Estimated max drift",
                value = "%.1f m".format(maxDriftMeters),
            )
            StatRow(
                label = "Average confidence",
                value = "%.0f%%".format(averageConfidence),
            )

            Spacer(modifier = Modifier.height(56.dp))

            // ── Save trip action ────────────────────────────────────────────
            Text(
                text = "Save trip",
                style = MaterialTheme.typography.labelLarge.copy(
                    color = MaterialTheme.colorScheme.onSurface,
                    textDecoration = TextDecoration.Underline,
                    letterSpacing = 1.sp,
                ),
                modifier = Modifier.clickable { onSaveTrip() },
            )

            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = "Dismiss",
                style = MaterialTheme.typography.labelMedium.copy(
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                ),
                modifier = Modifier.clickable { onDismiss() },
            )

            Spacer(modifier = Modifier.height(48.dp))
        }
    }
}

@Composable
private fun StatRow(label: String, value: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 12.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

@Composable
private fun RouteTimelineStrip(
    routePoints: List<RoutePoint>,
    modifier: Modifier = Modifier,
) {
    val primaryColor = MaterialTheme.colorScheme.primary
    val mutedColor = AerisGrey50

    Canvas(modifier = modifier) {
        if (routePoints.isEmpty()) return@Canvas

        val segmentWidth = size.width / routePoints.size.coerceAtLeast(1)
        val y = size.height / 2

        routePoints.forEachIndexed { index, point ->
            val x = index * segmentWidth
            val color: Color
            val pathEffect: PathEffect?

            when {
                point.isGnssLocked && point.confidence >= 60 -> {
                    color = primaryColor
                    pathEffect = null
                }
                point.confidence < 40 -> {
                    color = mutedColor
                    pathEffect = PathEffect.dashPathEffect(floatArrayOf(3f, 3f))
                }
                else -> {
                    color = primaryColor.copy(alpha = 0.5f)
                    pathEffect = PathEffect.dashPathEffect(floatArrayOf(6f, 3f))
                }
            }

            drawLine(
                color = color,
                start = Offset(x, y),
                end = Offset(x + segmentWidth, y),
                strokeWidth = size.height * 0.6f,
                pathEffect = pathEffect,
            )
        }
    }
}

private fun formatDistance(metres: Double): String = when {
    metres < 1000 -> "%.0f m".format(metres)
    else -> "%.2f km".format(metres / 1000)
}

private fun formatDuration(seconds: Long): String {
    val mins = seconds / 60
    val secs = seconds % 60
    return if (mins > 0) "${mins}m ${secs}s" else "${secs}s"
}

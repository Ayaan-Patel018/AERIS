package com.aeris.mobile.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowForward
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.service.TrackingState
import com.aeris.mobile.ui.theme.AerisGrey10
import com.aeris.mobile.ui.theme.AerisGrey15
import com.aeris.mobile.ui.theme.AerisGrey30
import com.aeris.mobile.ui.theme.AerisGrey50
import com.aeris.mobile.ui.theme.AerisGrey70
import com.aeris.mobile.ui.theme.AerisGrey90

/**
 * Bottom sheet content for the navigation screen.
 *
 * **With active route:** shows a compact navigation card (destination, ETA, distance)
 * followed by sensor stats and IMU bars.
 * **Without route:** shows sensor stats and IMU bars only.
 *
 * All colours are strictly monochrome — white / grey variants only.
 */
@Composable
fun NavigationBottomPanel(
    trackingState: TrackingState,
    isNavigating: Boolean,
    isRouteFetching: Boolean,
    destinationName: String?,
    etaMinutes: Int?,
    remainingMeters: Double?,
    onStopNavigation: () -> Unit,
    onStopTracking: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp)
            .padding(bottom = 28.dp),
    ) {
        Spacer(modifier = Modifier.height(8.dp))

        // ── Route fetching indicator ──────────────────────────────────────
        if (isRouteFetching) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(bottom = 16.dp),
            ) {
                CircularProgressIndicator(
                    color = AerisGrey70,
                    modifier = Modifier.size(16.dp),
                    strokeWidth = 2.dp,
                )
                Spacer(modifier = Modifier.width(12.dp))
                Text(
                    text = "Calculating route…",
                    style = MaterialTheme.typography.bodySmall,
                    color = AerisGrey50,
                    letterSpacing = 0.3.sp,
                )
            }
        }

        // ── Navigation card ───────────────────────────────────────────────
        AnimatedVisibility(
            visible = isNavigating && destinationName != null,
            enter = expandVertically() + fadeIn(tween(250)),
            exit = shrinkVertically() + fadeOut(tween(200)),
        ) {
            Column {
                NavigationCard(
                    destinationName = destinationName ?: "",
                    etaMinutes = etaMinutes,
                    remainingMeters = remainingMeters,
                    currentSpeedKmh = trackingState.currentSpeedKmh,
                    onStop = onStopNavigation,
                )
                Spacer(modifier = Modifier.height(20.dp))
            }
        }

        // ── Sensor status row ─────────────────────────────────────────────
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            GpsChip(
                isGnssLocked = trackingState.isGnssAvailable,
                modifier = Modifier.weight(1f),
            )
            ConfidenceChip(
                confidence = trackingState.confidence,
                modifier = Modifier.weight(1f),
            )
            ModeChip(
                motionMode = trackingState.motionMode.name
                    .lowercase().replaceFirstChar { it.uppercase() },
                modifier = Modifier.weight(1f),
            )
        }

        Spacer(modifier = Modifier.height(22.dp))

        // ── Divider ───────────────────────────────────────────────────────
        HorizontalDivider(color = AerisGrey15, thickness = 1.dp)
        Spacer(modifier = Modifier.height(18.dp))

        // ── Section label ─────────────────────────────────────────────────
        Text(
            text = "LIVE TELEMETRY",
            style = MaterialTheme.typography.labelMedium,
            color = AerisGrey50,
            letterSpacing = 1.8.sp,
        )
        Spacer(modifier = Modifier.height(12.dp))

        // ── IMU bars ──────────────────────────────────────────────────────
        ImuSensorGroup(
            title = "Accel  m/s²",
            readings = trackingState.currentAccel,
            maxValue = 20.0,
            colors = listOf(AerisGrey90, AerisGrey70, AerisGrey50),
        )
        Spacer(modifier = Modifier.height(10.dp))
        ImuSensorGroup(
            title = "Gyro  rad/s",
            readings = trackingState.currentGyro,
            maxValue = 5.0,
            colors = listOf(AerisGrey90, AerisGrey70, AerisGrey50),
        )

        Spacer(modifier = Modifier.height(26.dp))

        // ── End session ───────────────────────────────────────────────────
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(Color(0xFFE53935).copy(alpha = 0.15f))
                .border(1.dp, Color(0xFFE53935).copy(alpha = 0.3f), RoundedCornerShape(16.dp))
                .clickable {
                    if (isNavigating) onStopNavigation()
                    onStopTracking()
                }
                .padding(horizontal = 20.dp, vertical = 16.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                imageVector = Icons.Default.Close,
                contentDescription = "Stop",
                tint = Color(0xFFE53935),
                modifier = Modifier.size(20.dp)
            )
            Spacer(modifier = Modifier.width(10.dp))
            Text(
                text = if (isNavigating) "Stop Navigation & Trip" else "End Trip & Save",
                style = MaterialTheme.typography.titleMedium,
                color = Color(0xFFE53935),
                fontWeight = FontWeight.Bold,
            )
        }
    }
}

// ── Navigation card ───────────────────────────────────────────────────────────

@Composable
private fun NavigationCard(
    destinationName: String,
    etaMinutes: Int?,
    remainingMeters: Double?,
    currentSpeedKmh: Float,
    onStop: () -> Unit,
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(AerisGrey15)
            .border(
                width = 1.dp,
                color = AerisGrey30,
                shape = RoundedCornerShape(16.dp),
            )
            .padding(horizontal = 18.dp, vertical = 14.dp),
    ) {
        Column {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "NAVIGATING TO",
                        style = MaterialTheme.typography.labelSmall,
                        color = AerisGrey50,
                        letterSpacing = 1.5.sp,
                    )
                    Spacer(modifier = Modifier.height(3.dp))
                    Text(
                        text = destinationName.split(",").first().trim(),
                        style = MaterialTheme.typography.titleMedium,
                        color = Color.White,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Spacer(modifier = Modifier.width(12.dp))
                Box(
                    modifier = Modifier
                        .size(30.dp)
                        .clip(CircleShape)
                        .background(AerisGrey30)
                        .clickable(onClick = onStop),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        imageVector = Icons.Default.Close,
                        contentDescription = "Cancel route",
                        tint = AerisGrey70,
                        modifier = Modifier.size(14.dp),
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            Row(horizontalArrangement = Arrangement.spacedBy(28.dp)) {
                if (etaMinutes != null) {
                    NavStat(
                        value = "$etaMinutes min",
                        label = "ETA",
                    )
                }
                if (remainingMeters != null) {
                    NavStat(
                        value = if (remainingMeters >= 1000)
                            "${"%.1f".format(remainingMeters / 1000)} km"
                        else
                            "${remainingMeters.toInt()} m",
                        label = "Remaining",
                    )
                }
                NavStat(
                    value = "${currentSpeedKmh.toInt()} km/h",
                    label = "Speed",
                )
            }
        }
    }
}

@Composable
private fun NavStat(value: String, label: String) {
    Column {
        Text(
            text = value,
            style = MaterialTheme.typography.headlineSmall,
            color = Color.White,
            fontWeight = FontWeight.Bold,
        )
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = AerisGrey50,
            letterSpacing = 0.5.sp,
        )
    }
}

// ── Status chips ──────────────────────────────────────────────────────────────

@Composable
private fun GpsChip(isGnssLocked: Boolean, modifier: Modifier = Modifier) {
    val infiniteTransition = rememberInfiniteTransition(label = "gps")
    val scale by infiniteTransition.animateFloat(
        initialValue = 0.8f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(700, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "gps_scale",
    )

    Row(
        modifier = modifier
            .clip(RoundedCornerShape(10.dp))
            .background(AerisGrey15)
            .padding(horizontal = 12.dp, vertical = 9.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        Box(
            modifier = Modifier
                .size(7.dp)
                .scale(if (isGnssLocked) scale else 1f)
                .clip(CircleShape)
                .background(if (isGnssLocked) Color.White else AerisGrey50),
        )
        Spacer(modifier = Modifier.width(7.dp))
        Text(
            text = if (isGnssLocked) "GPS" else "DR",
            style = MaterialTheme.typography.labelSmall,
            color = if (isGnssLocked) Color.White else AerisGrey70,
            fontWeight = FontWeight.SemiBold,
            letterSpacing = 0.5.sp,
        )
    }
}

@Composable
private fun ConfidenceChip(confidence: Int, modifier: Modifier = Modifier) {
    val textColor = when {
        confidence >= 75 -> Color.White
        confidence >= 50 -> AerisGrey90
        else -> AerisGrey70
    }
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(10.dp))
            .background(AerisGrey15)
            .padding(horizontal = 12.dp, vertical = 9.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        Text(
            text = "$confidence%",
            style = MaterialTheme.typography.labelSmall,
            color = textColor,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

@Composable
private fun ModeChip(motionMode: String, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(10.dp))
            .background(AerisGrey15)
            .padding(horizontal = 12.dp, vertical = 9.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        Text(
            text = motionMode,
            style = MaterialTheme.typography.labelSmall,
            color = AerisGrey70,
            fontWeight = FontWeight.Medium,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

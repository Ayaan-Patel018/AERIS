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
    isSimulationMode: Boolean = false,
    simFusedPoint: com.aeris.mobile.core.simulation.TrajectoryPoint? = null,
    simGnssPoint: com.aeris.mobile.core.simulation.TrajectoryPoint? = null,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp)
            .padding(bottom = 28.dp),
    ) {
        Spacer(modifier = Modifier.height(8.dp))

        if (isSimulationMode) {
            SimulationTelemetryPanel(simFusedPoint = simFusedPoint, simGnssPoint = simGnssPoint)
            return@Column
        }

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

// ── Simulation Telemetry Panel ────────────────────────────────────────────────
// Entirely separate from navigation / destination logic.
// Mirrors the AERIS frontend Sidebar design — grouped telemetry rows.

private val AerisOrange = Color(0xFFF0801E)
private val GnssTeal = Color(0xFF2DD4BF)
private val GnssRed = Color(0xFFE5484D)
private val OkGreen = Color(0xFF4CAF50)
private val WarnAmber = Color(0xFFFFC107)

@Composable
fun SimulationTelemetryPanel(
    simFusedPoint: com.aeris.mobile.core.simulation.TrajectoryPoint?,
    simGnssPoint: com.aeris.mobile.core.simulation.TrajectoryPoint?,
) {
    val isGnssOutage = simFusedPoint?.isGnssHealthy == false

    // Kinematics derived from fused point
    val heading = simFusedPoint?.heading ?: 0.0
    val cardinal = run {
        val dirs = listOf("N", "NE", "E", "SE", "S", "SW", "W", "NW")
        dirs[(((heading / 45).toInt()) % 8 + 8) % 8]
    }

    Column(modifier = Modifier.fillMaxWidth()) {

        // ── GROUP 1: FILTER / ESTIMATOR ──────────────────────────────────────
        SimGroup(title = "FILTER / ESTIMATOR") {
            SimRow(label = "GNSS State") {
                val text = if (isGnssOutage) "OUTAGE" else "LOCKED"
                val color = if (isGnssOutage) WarnAmber else OkGreen
                Text(text, color = color, fontSize = 11.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp)
            }
            SimRow(label = "RF Signal") {
                Row(horizontalArrangement = Arrangement.spacedBy(3.dp), verticalAlignment = Alignment.CenterVertically) {
                    val bars = if (isGnssOutage) 0 else 5
                    repeat(5) { i ->
                        Box(
                            modifier = Modifier
                                .width(5.dp)
                                .height((6 + i * 3).dp)
                                .clip(RoundedCornerShape(1.dp))
                                .background(if (i < bars) Color.White else AerisGrey30)
                        )
                    }
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        if (isGnssOutage) "0/5" else "5/5",
                        color = if (isGnssOutage) WarnAmber else Color.White,
                        fontSize = 11.sp, fontWeight = FontWeight.SemiBold
                    )
                }
            }
            SimRow(label = "Satellite Fix") {
                Text(
                    if (isGnssOutage) "SEARCHING (0 SATS)" else "LOCKED (11 SATS)",
                    color = if (isGnssOutage) WarnAmber else AerisGrey70,
                    fontSize = 11.sp
                )
            }
            SimRow(label = "Mode") {
                Text(
                    if (isGnssOutage) "DEAD RECKONING" else "InES-EKF FUSED",
                    color = AerisOrange, fontSize = 11.sp, fontWeight = FontWeight.SemiBold
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // ── GROUP 2: KINEMATICS ───────────────────────────────────────────────
        SimGroup(title = "KINEMATICS") {
            SimRow(label = "Heading") {
                Text(
                    "${"%.1f".format(heading)}°  $cardinal",
                    color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.SemiBold
                )
            }
            if (isGnssOutage) {
                SimRow(label = "Fused vs GNSS Drift") {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("AERIS", color = AerisOrange, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        Text("  vs  ", color = AerisGrey50, fontSize = 10.sp)
                        Text("RAW GNSS", color = GnssRed, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // ── GROUP 3: TRAJECTORY LAYERS ────────────────────────────────────────
        SimGroup(title = "TRAJECTORY LAYERS") {
            SimRow(label = "AERIS InES-EKF") {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(modifier = Modifier.size(10.dp).clip(CircleShape).background(AerisOrange))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("ACTIVE", color = AerisOrange, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                }
            }
            SimRow(label = "Raw GNSS") {
                val gnssColor = if (isGnssOutage) GnssRed else GnssTeal
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(modifier = Modifier.size(10.dp).clip(CircleShape).background(gnssColor))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(if (isGnssOutage) "OUTAGE" else "ACTIVE", color = gnssColor, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
                }
            }
            SimRow(label = "Update Rate") {
                Text("10 Hz  (100 Hz IMU)", color = AerisGrey70, fontSize = 11.sp)
            }
        }

        Spacer(modifier = Modifier.height(20.dp))
    }
}

@Composable
private fun SimGroup(title: String, content: @Composable () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(14.dp))
            .background(AerisGrey15)
            .padding(horizontal = 16.dp, vertical = 14.dp)
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.labelSmall,
            color = AerisGrey50,
            letterSpacing = 1.6.sp,
            fontWeight = FontWeight.Bold,
        )
        Spacer(modifier = Modifier.height(10.dp))
        content()
    }
}

@Composable
private fun SimRow(label: String, value: @Composable () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 5.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, color = AerisGrey50, fontSize = 11.sp, letterSpacing = 0.3.sp)
        value()
    }
}

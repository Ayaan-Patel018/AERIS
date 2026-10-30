package com.aeris.mobile.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.domain.model.OutageWindow
import com.aeris.mobile.domain.model.TrajectoryPoint
import com.aeris.mobile.ui.components.GnssSignalState
import com.aeris.mobile.ui.components.SignalChip
import com.aeris.mobile.ui.theme.NightColors
import com.aeris.mobile.util.Formatters
import kotlin.math.roundToInt

/**
 * In-car landscape Dash Mode glance display updated per R5 § 4.
 *
 * Replaces legacy media bar with thin progress rail and pause button at lower right.
 * Features persistent "Playing recorded drive" chip, 16-point cardinal rose, and sentence-case labels.
 */
@Composable
fun DashModeScreen(
    currentPoint: TrajectoryPoint?,
    currentFraction: Float,
    durationSec: Double,
    isPlaying: Boolean,
    activeOutage: OutageWindow?,
    driveId: String = "S3b",
    onTogglePlayPause: () -> Unit,
    onExitDashMode: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = NightColors // Always high-contrast night palette

    // Border, chip and colours key on the outages[] window, not on the frame status
    val isOutage = activeOutage != null
    val speedKmh = currentPoint?.speedMps?.let { (it * 3.6).roundToInt().toString() } ?: "—"
    val uncertaintyM = currentPoint?.sigmaMajorM

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(colors.chalk)
            .then(
                if (isOutage) Modifier.border(3.dp, colors.amber) else Modifier
            )
            .padding(24.dp)
    ) {
        // Top row: Persistent chip "Playing recorded drive" | Signal Chip | Close Button per R5 § 4
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                // Persistent chip per R5 § 4
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(14.dp))
                        .background(colors.paper)
                        .border(1.dp, colors.harbor, RoundedCornerShape(14.dp))
                        .padding(horizontal = 10.dp, vertical = 5.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.PlayArrow,
                            contentDescription = null,
                            tint = colors.ink2,
                            modifier = Modifier.size(12.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Playing recorded drive • $driveId",
                            color = colors.ink2,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
                Spacer(modifier = Modifier.width(12.dp))
                SignalChip(
                    signalState = if (isOutage) GnssSignalState.DEAD_RECKONING else GnssSignalState.LOCKED
                )
            }

            Box(
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .background(colors.paper)
                    .clickable(role = Role.Button, onClick = onExitDashMode)
                    .semantics { role = Role.Button },
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Close,
                    contentDescription = "Exit Dash Mode",
                    tint = colors.ink,
                    modifier = Modifier.size(18.dp)
                )
            }
        }

        // Center row: Huge Speed Readout on Left | Uncertainty & Heading on Right (sentence case per R6 § 3.4)
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.Center),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Speed
            Column {
                Row(verticalAlignment = Alignment.Bottom) {
                    Text(
                        text = speedKmh,
                        color = colors.ink,
                        fontSize = 80.sp,
                        fontWeight = FontWeight.Black,
                        lineHeight = 84.sp
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "km/h",
                        color = colors.ink2,
                        fontSize = 24.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }

            // Uncertainty & Heading (Sentence case)
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = "Position uncertainty, 1σ",
                    color = colors.ink2,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = if (uncertaintyM != null) "±${Formatters.formatMeters(uncertaintyM)}" else "—",
                    color = if (isOutage) colors.amberLine else colors.teal,
                    fontSize = 32.sp,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(10.dp))
                val headingDeg = currentPoint?.headingDeg
                Text(
                    text = if (headingDeg != null) {
                        "Heading ${headingDeg.roundToInt() % 360}° ${Formatters.cardinal16(headingDeg)}"
                    } else "Heading —",
                    color = colors.ink2,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Medium
                )
            }
        }

        // Bottom row: Thin progress rail with pause button at lower right per R5 § 4
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Thin progress rail (6 dp)
            Box(
                modifier = Modifier
                    .weight(1f)
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp))
                    .background(colors.harbor)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth(currentFraction)
                        .height(6.dp)
                        .background(if (isOutage) colors.amberLine else colors.cobalt)
                )
            }

            Spacer(modifier = Modifier.width(16.dp))

            // Pause/Play Button at lower right
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(CircleShape)
                    .background(colors.ink)
                    .clickable(onClick = onTogglePlayPause),
                contentAlignment = Alignment.Center
            ) {
                if (isPlaying) {
                    Row(horizontalArrangement = Arrangement.spacedBy(3.dp)) {
                        Box(modifier = Modifier.size(width = 3.dp, height = 14.dp).background(colors.paper))
                        Box(modifier = Modifier.size(width = 3.dp, height = 14.dp).background(colors.paper))
                    }
                } else {
                    Icon(
                        imageVector = Icons.Default.PlayArrow,
                        contentDescription = "Play",
                        tint = colors.paper,
                        modifier = Modifier.size(22.dp)
                    )
                }
            }
        }
    }
}

package com.aeris.mobile.ui.sheet

import androidx.compose.animation.core.animateFloatAsState
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.model.OutageWindow
import com.aeris.mobile.domain.model.TrajectoryPoint
import com.aeris.mobile.ui.components.AerisButton
import com.aeris.mobile.ui.components.AerisButtonVariant
import com.aeris.mobile.ui.components.StatusHud
import com.aeris.mobile.ui.components.TelemetryGraphs
import com.aeris.mobile.ui.components.TimelineScrubber
import com.aeris.mobile.ui.theme.Aeris

enum class SheetSnap {
    PEEK,
    HALF,
    FULL
}

/**
 * 3-height Bottom Sheet container per M06 §1 & §2.
 */
@Composable
fun DriveBottomSheet(
    drive: Drive?,
    currentPoint: TrajectoryPoint?,
    activeOutage: OutageWindow?,
    currentFraction: Float,
    isPlaying: Boolean,
    playbackSpeed: Float,
    sheetSnap: SheetSnap,
    onSnapChange: (SheetSnap) -> Unit,
    onSeekFraction: (Float) -> Unit,
    onTogglePlayPause: () -> Unit,
    onCycleSpeed: () -> Unit,
    onJumpOutage: () -> Unit,
    onSelectOutage: (OutageWindow) -> Unit,
    onOpenAboutRun: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors

    val targetHeight = when (sheetSnap) {
        SheetSnap.PEEK -> 140.dp
        SheetSnap.HALF -> 380.dp
        SheetSnap.FULL -> 640.dp
    }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .height(targetHeight)
            .shadow(16.dp, RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp), ambientColor = colors.ink.copy(alpha = 0.15f))
            .clip(RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp))
            .background(colors.paper)
            .border(1.dp, colors.harbor, RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp))
            .padding(horizontal = 20.dp)
            .padding(top = 10.dp, bottom = 16.dp)
    ) {
        // Drag Handle
        Box(
            modifier = Modifier
                .align(Alignment.CenterHorizontally)
                .width(36.dp)
                .height(4.dp)
                .clip(RoundedCornerShape(2.dp))
                .background(colors.harbor)
                .clickable {
                    val nextSnap = when (sheetSnap) {
                        SheetSnap.PEEK -> SheetSnap.HALF
                        SheetSnap.HALF -> SheetSnap.FULL
                        SheetSnap.FULL -> SheetSnap.PEEK
                    }
                    onSnapChange(nextSnap)
                }
        )

        Spacer(modifier = Modifier.height(12.dp))

        // Playback row & scrubber (Always visible at Peek, Half, and Full)
        TimelineScrubber(
            currentFraction = currentFraction,
            durationSec = drive?.meta?.durationSec ?: 0.0,
            outages = drive?.outages ?: emptyList(),
            isPlaying = isPlaying,
            speed = playbackSpeed,
            onSeekFraction = onSeekFraction,
            onTogglePlayPause = onTogglePlayPause,
            onCycleSpeed = onCycleSpeed,
            onJumpOutage = onJumpOutage,
        )

        // Expanded content for Half and Full
        if (sheetSnap != SheetSnap.PEEK) {
            Spacer(modifier = Modifier.height(14.dp))

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                // Status HUD
                StatusHud(
                    point = currentPoint,
                    totalDurationSec = drive?.meta?.durationSec ?: 0.0,
                )

                if (sheetSnap == SheetSnap.FULL) {
                    // Drive header info
                    DriveHeaderCard(drive = drive)

                    // Outages list
                    OutageListCard(
                        outages = drive?.outages ?: emptyList(),
                        onSelectOutage = onSelectOutage
                    )

                    // Telemetry graphs
                    TelemetryGraphs(
                        points = drive?.points ?: emptyList(),
                        outages = drive?.outages ?: emptyList(),
                        currentFraction = currentFraction,
                        durationSec = drive?.meta?.durationSec ?: 0.0,
                    )

                    // Baseline comparison card
                    ComparisonCard(
                        outage = activeOutage ?: drive?.outages?.firstOrNull(),
                        baselinePoints = drive?.baselinePoints ?: emptyList()
                    )

                    // Results card
                    ResultsCard(metrics = drive?.metrics)

                    // About this run trust row
                    AboutRunTrustRow(onClick = onOpenAboutRun)
                }
            }
        }
    }
}

@Composable
private fun DriveHeaderCard(drive: Drive?) {
    val colors = Aeris.colors
    val meta = drive?.meta ?: return

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(colors.harbor2.copy(alpha = 0.5f))
            .padding(16.dp)
    ) {
        Text(
            text = meta.name,
            color = colors.ink,
            fontSize = 17.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(modifier = Modifier.height(4.dp))
        val distanceKm = meta.totalDistanceMeters / 1000.0
        val durationMin = meta.durationSec / 60.0
        Text(
            text = String.format("%.1f min · %.2f km · %d satellite loss events", durationMin, distanceKm, meta.outageCount),
            color = colors.ink2,
            fontSize = 13.sp
        )
    }
}

@Composable
private fun OutageListCard(
    outages: List<OutageWindow>,
    onSelectOutage: (OutageWindow) -> Unit,
) {
    val colors = Aeris.colors

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(colors.paper)
            .border(1.dp, colors.harbor, RoundedCornerShape(16.dp))
            .padding(16.dp)
    ) {
        Text(
            text = "SATELLITE LOSS EVENTS (${outages.size})",
            color = colors.ink3,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.8.sp
        )
        Spacer(modifier = Modifier.height(10.dp))

        if (outages.isEmpty()) {
            Text(
                text = "No satellite loss in this drive.",
                color = colors.ink2,
                fontSize = 13.sp
            )
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                outages.forEach { outage ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(10.dp))
                            .background(colors.amberSoft.copy(alpha = 0.5f))
                            .border(1.dp, colors.amber.copy(alpha = 0.3f), RoundedCornerShape(10.dp))
                            .clickable { onSelectOutage(outage) }
                            .padding(horizontal = 12.dp, vertical = 10.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text(
                                text = "GNSS Outage (${outage.id})",
                                color = colors.ink,
                                fontSize = 13.5.sp,
                                fontWeight = FontWeight.Bold
                            )
                            val startMin = outage.startSec.toInt() / 60
                            val startS = outage.startSec.toInt() % 60
                            Text(
                                text = String.format("Starts at %02d:%02d · Duration %.0fs", startMin, startS, outage.durationSec),
                                color = colors.ink2,
                                fontSize = 12.sp
                            )
                        }
                        Text(
                            text = String.format("±%.1f m max", outage.maxUncertaintyMeters),
                            color = colors.amber,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun AboutRunTrustRow(onClick: () -> Unit) {
    val colors = Aeris.colors
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(colors.harbor2.copy(alpha = 0.6f))
            .clickable(role = Role.Button, onClick = onClick)
            .padding(14.dp)
            .semantics {
                role = Role.Button
                contentDescription = "About this run trust details"
            },
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = Icons.Default.Info,
                contentDescription = null,
                tint = colors.cobalt,
                modifier = Modifier.size(18.dp)
            )
            Spacer(modifier = Modifier.width(10.dp))
            Text(
                text = "About this run (Trust ledger)",
                color = colors.ink,
                fontSize = 13.5.sp,
                fontWeight = FontWeight.SemiBold
            )
        }
        Text(
            text = "View details →",
            color = colors.cobalt,
            fontSize = 12.5.sp,
            fontWeight = FontWeight.Bold
        )
    }
}

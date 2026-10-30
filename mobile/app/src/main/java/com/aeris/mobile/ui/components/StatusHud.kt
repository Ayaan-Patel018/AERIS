package com.aeris.mobile.ui.components

import androidx.compose.animation.AnimatedVisibility
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
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.domain.model.GnssStatus
import com.aeris.mobile.domain.model.TrajectoryPoint
import com.aeris.mobile.ui.theme.Aeris
import com.aeris.mobile.util.Formatters
import kotlin.math.roundToInt

/**
 * Status HUD card per R1 & R6 § 3.
 *
 * Displays live telemetry using sentence-case labels and unified formatters:
 * - Signal status (SignalChip)
 * - Speed (e.g. "38 km/h")
 * - Heading with 16-point rose (e.g. "291° WNW")
 * - Position uncertainty (e.g. "±14 m, 1σ")
 */
@Composable
fun StatusHud(
    point: TrajectoryPoint?,
    totalDurationSec: Double,
    use95Percent: Boolean = false,
    useMps: Boolean = false,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors

    val status = point?.status ?: GnssStatus.UNKNOWN
    val signalState = when (status) {
        GnssStatus.HEALTHY -> GnssSignalState.LOCKED
        GnssStatus.OUTAGE -> GnssSignalState.DEAD_RECKONING
        GnssStatus.DEGRADED -> GnssSignalState.DEGRADED
        GnssStatus.UNKNOWN -> GnssSignalState.UNKNOWN
    }

    val speedDisplay = if (point?.speedMps != null) {
        if (useMps) {
            String.format(java.util.Locale.getDefault(), "%.1f m/s", point.speedMps)
        } else {
            Formatters.formatSpeedKmh(point.speedMps)
        }
    } else "—"

    val headingDisplay = if (point?.headingDeg != null) {
        val deg = ((point.headingDeg % 360.0 + 360.0) % 360.0).roundToInt()
        val cardinal = Formatters.cardinal16(point.headingDeg)
        "$deg° $cardinal"
    } else "—"

    val uncertaintyValue = if (point?.sigma != null) {
        val scale = if (use95Percent) 2.4477 else 1.0
        val valM = point.sigma * scale
        "±${Formatters.formatMeters(valM)}"
    } else "—"

    val timeCurrentSec = point?.timestampSec ?: 0.0
    val timeFormatted = "${Formatters.formatMmSs(timeCurrentSec)} / ${Formatters.formatMmSs(totalDurationSec)}"

    Column(
        modifier = modifier
            .fillMaxWidth()
            .shadow(4.dp, RoundedCornerShape(16.dp), ambientColor = colors.ink.copy(alpha = 0.08f))
            .clip(RoundedCornerShape(16.dp))
            .background(colors.paper)
            .border(1.dp, colors.harbor, RoundedCornerShape(16.dp))
            .padding(16.dp)
    ) {
        // Top row: Signal status chip + Time
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            SignalChip(signalState = signalState)
            Text(
                text = timeFormatted,
                color = colors.ink2,
                fontSize = 12.5.sp,
                fontWeight = FontWeight.Medium,
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Three-column readout: Speed | Heading | Uncertainty (Sentence-case labels)
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top
        ) {
            // Speed
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "Speed",
                    color = colors.ink3,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = speedDisplay,
                    color = colors.ink,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                )
            }

            // Heading
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "Heading",
                    color = colors.ink3,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = headingDisplay,
                    color = colors.ink,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                )
            }

            // Uncertainty
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = if (use95Percent) "Position uncertainty (95%)" else "Position uncertainty (1σ)",
                    color = colors.ink3,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = uncertaintyValue,
                    color = if (signalState == GnssSignalState.DEAD_RECKONING) colors.amber else colors.ink,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
    }
}

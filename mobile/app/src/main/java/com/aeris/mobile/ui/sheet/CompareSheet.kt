package com.aeris.mobile.ui.sheet

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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.SheetState
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.model.OutageWindow
import com.aeris.mobile.domain.playback.DriveMoments
import com.aeris.mobile.util.Formatters
import com.aeris.mobile.ui.theme.Aeris

/**
 * Compare Sheet for one outage window. Every number comes from the export or the metrics asset:
 * - corrections[].jump_m after the window ("from the new fix" = the correction at the first fix after it);
 * - outages[] (withheld fixes, last fix / first fix after);
 * - the scorer's metrics, labelled as scoring (VBOX reference, development drive, in-sample).
 * No error is computed in the app; there is no hold-last-fix row because the metrics asset has no such number.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CompareSheet(
    outage: OutageWindow?,
    drive: Drive,
    onPlayMoment: (Double) -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
    sheetState: SheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
) {
    val colors = Aeris.colors

    if (outage == null) return

    val durationSec = (outage.endSec - outage.startSec).coerceAtLeast(0.0)
    val newFixJump = DriveMoments.firstCorrectionAfter(drive, outage)
    val later = DriveMoments.correctionsAfter(drive, outage).filter { it != newFixJump }
    val metrics = drive.metrics
    val us = java.util.Locale.US

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = colors.paper,
        dragHandle = {
            Box(
                modifier = Modifier
                    .padding(top = 10.dp, bottom = 6.dp)
                    .width(36.dp)
                    .height(4.dp)
                    .clip(RoundedCornerShape(2.dp))
                    .background(colors.harbor)
            )
        },
        modifier = modifier
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp, vertical = 8.dp)
                .padding(bottom = 24.dp)
        ) {
            Text(
                text = "After the outage",
                color = colors.ink,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = "GNSS ${outage.kind ?: ""} outage at ${Formatters.formatMmSs(outage.startSec)} • lasted ${durationSec.toInt()} s",
                color = colors.ink2,
                fontSize = 13.sp
            )

            Spacer(modifier = Modifier.height(18.dp))

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(14.dp))
                    .background(colors.chalk)
                    .border(1.dp, colors.harbor, RoundedCornerShape(14.dp))
                    .padding(14.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // Row 1: the jump from the new fix (corrections[].jump_m)
                CompareTableRow(
                    sourceLabel = "AERIS jump at the new fix",
                    indicatorColor = colors.cobalt,
                    errorValue = newFixJump?.let { String.format(us, "%.1f m", it.jumpM) } ?: "—",
                    trackedValue = newFixJump?.let { "${Formatters.formatMmSs(it.tSec)} • ${it.cause.replace('_', ' ')}" } ?: "no correction",
                    isPrimary = true
                )

                // Later corrections after the window (e.g. a replay)
                later.forEach { c ->
                    HorizontalDivider(thickness = 0.5.dp, color = colors.harbor)
                    CompareTableRow(
                        sourceLabel = "Later correction",
                        indicatorColor = colors.amberLine,
                        errorValue = String.format(us, "%.1f m", c.jumpM),
                        trackedValue = "${Formatters.formatMmSs(c.tSec)} • ${c.cause.replace('_', ' ')}",
                        isPrimary = false
                    )
                }

                HorizontalDivider(thickness = 0.5.dp, color = colors.harbor)

                // Phone GNSS during the window (outages[])
                CompareTableRow(
                    sourceLabel = "Phone GNSS",
                    indicatorColor = colors.teal,
                    errorValue = outage.withheldFixCount?.let { "$it fixes withheld" } ?: "—",
                    trackedValue = "last fix ${outage.lastFixSec?.let { Formatters.formatMmSs(it) } ?: "—"} • " +
                        "next ${outage.firstFixAfterSec?.let { Formatters.formatMmSs(it) } ?: "—"}",
                    isPrimary = false
                )

                // Scoring, only from the metrics asset
                if (metrics != null) {
                    HorizontalDivider(thickness = 0.5.dp, color = colors.harbor)
                    CompareTableRow(
                        sourceLabel = "Scoring (VBOX reference)",
                        indicatorColor = colors.slate,
                        errorValue = metrics.endErrorMeters?.let { String.format(us, "end error %.1f m", it) } ?: "—",
                        trackedValue = String.format(us, "mean %.1f m • in-sample", metrics.meanErrorMeters),
                        isPrimary = false
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            Text(
                text = newFixJump?.let {
                    String.format(us, "When GNSS returned, the first fix moved AERIS %.1f m; the app draws that step dashed, never as driving.", it.jumpM)
                } ?: "No correction after this outage.",
                color = colors.ink,
                fontSize = 13.sp,
                lineHeight = 18.sp
            )

            Spacer(modifier = Modifier.height(20.dp))

            // Action: Play this moment (starts playback 5 s before the outage)
            Button(
                onClick = {
                    onPlayMoment((outage.startSec - 5.0).coerceAtLeast(0.0))
                    onDismiss()
                },
                colors = ButtonDefaults.buttonColors(
                    containerColor = colors.ink,
                    contentColor = colors.paper
                ),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.PlayArrow,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Play this moment",
                    fontSize = 14.5.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        }
    }
}

@Composable
private fun CompareTableRow(
    sourceLabel: String,
    indicatorColor: Color,
    errorValue: String,
    trackedValue: String,
    isPrimary: Boolean,
) {
    val colors = Aeris.colors

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(indicatorColor)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = sourceLabel,
                color = colors.ink,
                fontSize = 13.sp,
                fontWeight = if (isPrimary) FontWeight.Bold else FontWeight.Medium
            )
        }

        Column(horizontalAlignment = Alignment.End) {
            Text(
                text = errorValue,
                color = if (isPrimary) colors.cobalt else colors.ink,
                fontSize = 12.5.sp,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                text = trackedValue,
                color = colors.ink3,
                fontSize = 11.sp
            )
        }
    }
}

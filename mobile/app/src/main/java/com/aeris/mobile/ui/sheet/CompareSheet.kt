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
import com.aeris.mobile.domain.math.EventDetector
import com.aeris.mobile.domain.model.OutageWindow
import com.aeris.mobile.domain.model.TrajectoryPoint
import com.aeris.mobile.ui.theme.Aeris

/**
 * Compare Sheet ("If we hadn't tracked") matching R5 § 6.
 *
 * Opened from Trip detail comparison row or from an outage moment card's long-press.
 * Shows outage comparison metrics: AERIS vs Hold last fix vs Raw satellite fixes,
 * with plain-language summary and "Play this moment" button.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CompareSheet(
    outage: OutageWindow?,
    onPlayMoment: (Double) -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
    sheetState: SheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
) {
    val colors = Aeris.colors

    if (outage == null) return

    val aerisDisplacement = EventDetector.haversineDistanceMeters(
        outage.startPoint.lat, outage.startPoint.lon,
        outage.endPoint.lat, outage.endPoint.lon
    )
    val holdLastFixError = aerisDisplacement
    val aerisEndUncertainty = outage.endPoint.sigma ?: outage.maxUncertaintyMeters
    val durationSec = (outage.endSec - outage.startSec).coerceAtLeast(0.0)

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
                text = "If we hadn't tracked",
                color = colors.ink,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = "GNSS outage at ${String.format("%02d:%02d", (outage.startSec / 60).toInt(), (outage.startSec % 60).toInt())} • lasted ${durationSec.toInt()} s",
                color = colors.ink2,
                fontSize = 13.sp
            )

            Spacer(modifier = Modifier.height(18.dp))

            // 3-Row Comparison Table per R5 § 6 & M06 § 6
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(14.dp))
                    .background(colors.chalk)
                    .border(1.dp, colors.harbor, RoundedCornerShape(14.dp))
                    .padding(14.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // Row 1: AERIS Dead Reckoning
                CompareTableRow(
                    sourceLabel = "AERIS Dead Reckoning",
                    indicatorColor = colors.cobalt,
                    errorValue = String.format("±%.1f m (1σ)", aerisEndUncertainty),
                    trackedValue = String.format("%.0f m tracked", aerisDisplacement),
                    isPrimary = true
                )

                HorizontalDivider(thickness = 0.5.dp, color = colors.harbor)

                // Row 2: Hold last fix (Baseline)
                CompareTableRow(
                    sourceLabel = "Baseline (Hold last fix)",
                    indicatorColor = colors.slate,
                    errorValue = String.format("%.0f m drift", holdLastFixError),
                    trackedValue = "0 m (frozen)",
                    isPrimary = false
                )

                HorizontalDivider(thickness = 0.5.dp, color = colors.harbor)

                // Row 3: Raw satellite fixes
                CompareTableRow(
                    sourceLabel = "Raw satellite fixes",
                    indicatorColor = colors.teal,
                    errorValue = "No fix (0 sats)",
                    trackedValue = "Unavailable",
                    isPrimary = false
                )
            }

            Spacer(modifier = Modifier.height(14.dp))

            // Plain-language single sentence explanation per R5 § 6
            Text(
                text = String.format(
                    "AERIS was %.1f m from the new fix after the satellite loss; holding the last fix would have left it %.0f m away.",
                    aerisEndUncertainty,
                    holdLastFixError
                ),
                color = colors.ink,
                fontSize = 13.sp,
                lineHeight = 18.sp
            )

            Spacer(modifier = Modifier.height(20.dp))

            // Action: Play this moment (starts playback 5s before outage per R5 § 6)
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

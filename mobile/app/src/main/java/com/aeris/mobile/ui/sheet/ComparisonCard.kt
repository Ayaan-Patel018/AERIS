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
import androidx.compose.material3.Text
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
 * Baseline comparison card ("If we hadn't tracked") per M06 §6.
 */
@Composable
fun ComparisonCard(
    outage: OutageWindow?,
    baselinePoints: List<TrajectoryPoint>,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors

    if (outage == null) return

    // Calculate displacement for AERIS during the outage
    val aerisDisplacement = EventDetector.haversineDistanceMeters(
        outage.startPoint.lat, outage.startPoint.lon,
        outage.endPoint.lat, outage.endPoint.lon
    )

    // Baseline "hold last fix" stays at outage start point
    // Its error at the end of the outage is the distance from startPoint to endPoint
    val holdLastFixError = aerisDisplacement
    val aerisEndUncertainty = outage.endPoint.sigma ?: (outage.maxUncertaintyMeters)

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(colors.paper)
            .border(1.dp, colors.harbor, RoundedCornerShape(16.dp))
            .padding(16.dp)
    ) {
        Text(
            text = "BASELINE COMPARISON",
            color = colors.ink3,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.8.sp
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = "If we hadn't tracked (GNSS-denied)",
            color = colors.ink,
            fontSize = 15.sp,
            fontWeight = FontWeight.Bold
        )

        Spacer(modifier = Modifier.height(14.dp))

        // Row 1: AERIS Dead Reckoning
        ComparisonRow(
            label = "AERIS Dead Reckoning",
            color = colors.cobalt,
            separationText = String.format("±%.1f m uncertainty", aerisEndUncertainty),
            detailText = String.format("%.0f m tracked", aerisDisplacement)
        )

        Spacer(modifier = Modifier.height(10.dp))

        // Row 2: Baseline Hold Last Fix
        ComparisonRow(
            label = "Baseline (Hold last fix)",
            color = colors.slate,
            separationText = String.format("%.1f m drift", holdLastFixError),
            detailText = "0 m tracked (frozen)"
        )

        Spacer(modifier = Modifier.height(14.dp))

        // Plain-language summary
        val summaryText = String.format(
            "Holding the last fix would have left the vehicle %.0f m behind; AERIS continuously tracked within ±%.1f m.",
            holdLastFixError,
            aerisEndUncertainty
        )
        Text(
            text = summaryText,
            color = colors.ink2,
            fontSize = 12.5.sp,
            lineHeight = 17.sp,
        )
    }
}

@Composable
private fun ComparisonRow(
    label: String,
    color: Color,
    separationText: String,
    detailText: String,
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
                    .size(10.dp)
                    .clip(CircleShape)
                    .background(color)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = label,
                color = colors.ink,
                fontSize = 13.5.sp,
                fontWeight = FontWeight.SemiBold
            )
        }

        Column(horizontalAlignment = Alignment.End) {
            Text(
                text = separationText,
                color = colors.ink,
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = detailText,
                color = colors.ink3,
                fontSize = 11.sp,
            )
        }
    }
}

package com.aeris.mobile.ui.sheet

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.domain.model.DriveMetrics
import com.aeris.mobile.ui.theme.Aeris

/**
 * Performance and verification results card per M06 §7.
 */
@Composable
fun ResultsCard(
    metrics: DriveMetrics?,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(colors.paper)
            .border(1.dp, colors.harbor, RoundedCornerShape(16.dp))
            .padding(16.dp)
    ) {
        Text(
            text = "EVALUATION METRICS",
            color = colors.ink3,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.8.sp
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = "Filter Accuracy & Drift",
            color = colors.ink,
            fontSize = 15.sp,
            fontWeight = FontWeight.Bold
        )

        Spacer(modifier = Modifier.height(14.dp))

        if (metrics == null) {
            Text(
                text = "Performance metrics unavailable for this drive.",
                color = colors.ink3,
                fontSize = 13.sp
            )
        } else {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                MetricColumn(
                    label = "MAX DRIFT",
                    value = String.format("%.1f m", metrics.maxDriftMeters)
                )
                MetricColumn(
                    label = "MEAN ERROR",
                    value = String.format("%.1f m", metrics.meanErrorMeters)
                )
                MetricColumn(
                    label = "OUTAGE TIME",
                    value = String.format("%.0f s", metrics.totalOutageDurationSec)
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = "Provenance: ${metrics.provenance}",
                color = colors.ink3,
                fontSize = 11.sp,
            )
        }
    }
}

@Composable
private fun MetricColumn(
    label: String,
    value: String,
) {
    val colors = Aeris.colors
    Column {
        Text(
            text = label,
            color = colors.ink3,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.5.sp
        )
        Spacer(modifier = Modifier.height(2.dp))
        Text(
            text = value,
            color = colors.ink,
            fontSize = 16.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}

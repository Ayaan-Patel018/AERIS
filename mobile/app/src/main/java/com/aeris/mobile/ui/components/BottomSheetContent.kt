package com.aeris.mobile.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.aeris.mobile.core.filter.MotionMode
import com.aeris.mobile.service.SensorHealth
import com.aeris.mobile.service.SensorStatus
import com.aeris.mobile.ui.theme.AERISTheme
import com.aeris.mobile.ui.theme.AerisGrey10
import com.aeris.mobile.ui.theme.AerisGrey15
import com.aeris.mobile.ui.theme.AerisGrey30
import com.aeris.mobile.ui.theme.AerisGrey50
import com.aeris.mobile.ui.theme.AerisGrey70
import com.aeris.mobile.ui.theme.AerisGrey90
import com.aeris.mobile.ui.theme.AerisWhite

/**
 * Content of the expandable bottom sheet on the navigation screen.
 *
 * **Collapsed** (default): state label, context line, three stats.
 * **Expanded**: adds per-mode probability bars and sensor health.
 * **Alert**: plain-language warning when confidence is very low.
 */
@Composable
fun BottomSheetContent(
    stateLabel: String,
    contextLine: String,
    confidence: Int,
    distanceToDestination: String,
    eta: String,
    isExpanded: Boolean,
    alertMessage: String?,
    modeProbabilities: Map<MotionMode, Float>,
    sensorHealth: SensorHealth,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(AerisGrey10)
            .padding(horizontal = 20.dp, vertical = 16.dp),
    ) {
        // ── Drag handle ─────────────────────────────────────────────────
        Box(
            modifier = Modifier
                .align(Alignment.CenterHorizontally)
                .width(32.dp)
                .height(4.dp)
                .clip(RoundedCornerShape(2.dp))
                .background(AerisGrey30),
        )
        Spacer(modifier = Modifier.height(16.dp))

        // ── State label ─────────────────────────────────────────────────
        Text(
            text = stateLabel,
            style = MaterialTheme.typography.headlineMedium,
            color = AerisWhite,
            fontWeight = FontWeight.SemiBold,
        )
        Spacer(modifier = Modifier.height(4.dp))

        // ── Context line ────────────────────────────────────────────────
        Text(
            text = contextLine,
            style = MaterialTheme.typography.bodyMedium,
            color = AerisGrey70,
        )
        Spacer(modifier = Modifier.height(20.dp))

        // ── Three stats ─────────────────────────────────────────────────
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            StatItem(label = "Distance", value = distanceToDestination)
            StatItem(label = "Confidence", value = "${confidence}%")
            StatItem(label = "ETA", value = eta)
        }

        // ── Alert message ───────────────────────────────────────────────
        if (alertMessage != null) {
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = alertMessage,
                style = MaterialTheme.typography.bodySmall,
                color = AerisGrey90,
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(8.dp))
                    .background(AerisGrey15)
                    .padding(12.dp),
            )
        }

        // ── Expanded section ────────────────────────────────────────────
        AnimatedVisibility(
            visible = isExpanded,
            enter = expandVertically(),
            exit = shrinkVertically(),
        ) {
            Column {
                Spacer(modifier = Modifier.height(20.dp))

                // Mode probability bars
                Text(
                    text = "MOTION MODE",
                    style = MaterialTheme.typography.labelSmall,
                    color = AerisGrey50,
                )
                Spacer(modifier = Modifier.height(8.dp))
                modeProbabilities.forEach { (mode, probability) ->
                    ModeProbabilityBar(
                        label = mode.name.lowercase()
                            .replaceFirstChar { it.uppercase() },
                        probability = probability,
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Sensor health indicators
                Text(
                    text = "SENSOR HEALTH",
                    style = MaterialTheme.typography.labelSmall,
                    color = AerisGrey50,
                )
                Spacer(modifier = Modifier.height(8.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    SensorHealthIndicator("GNSS", sensorHealth.gnss)
                    SensorHealthIndicator("IMU", sensorHealth.imu)
                    SensorHealthIndicator("Baro", sensorHealth.baro)
                }
            }
        }
    }
}

@Composable
private fun StatItem(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = value,
            style = MaterialTheme.typography.headlineSmall,
            color = AerisWhite,
            fontWeight = FontWeight.SemiBold,
        )
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = AerisGrey50,
        )
    }
}

@Composable
private fun ModeProbabilityBar(label: String, probability: Float) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = AerisGrey70,
            modifier = Modifier.width(80.dp),
        )
        Box(
            modifier = Modifier
                .weight(1f)
                .height(6.dp)
                .clip(RoundedCornerShape(3.dp))
                .background(AerisGrey15),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth(probability.coerceIn(0f, 1f))
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp))
                    .background(AerisWhite.copy(alpha = 0.7f)),
            )
        }
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = "${(probability * 100).toInt()}%",
            style = MaterialTheme.typography.labelSmall,
            color = AerisGrey50,
            modifier = Modifier.width(36.dp),
        )
    }
}

@Composable
private fun SensorHealthIndicator(name: String, status: SensorStatus) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        val dotColor = when (status) {
            SensorStatus.ACTIVE -> AerisWhite
            SensorStatus.DEGRADED -> AerisGrey50
            SensorStatus.UNAVAILABLE -> AerisGrey30
        }
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(dotColor),
        )
        Spacer(modifier = Modifier.width(6.dp))
        Text(
            text = name,
            style = MaterialTheme.typography.labelSmall,
            color = AerisGrey70,
        )
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF1A1A1A)
@Composable
private fun BottomSheetPreview() {
    AERISTheme {
        BottomSheetContent(
            stateLabel = "Estimated position",
            contextLine = "GPS signal lost 0:42 ago — still tracking",
            confidence = 72,
            distanceToDestination = "--",
            eta = "--",
            isExpanded = true,
            alertMessage = null,
            modeProbabilities = mapOf(
                MotionMode.STOPPED to 0f,
                MotionMode.CRUISING to 1f,
                MotionMode.TURNING to 0f,
                MotionMode.BRAKING to 0f,
            ),
            sensorHealth = SensorHealth(
                SensorStatus.DEGRADED,
                SensorStatus.ACTIVE,
                SensorStatus.ACTIVE,
            ),
        )
    }
}

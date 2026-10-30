package com.aeris.mobile.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowForward
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.aeris.mobile.service.TrackingState
import kotlin.math.absoluteValue

@Composable
fun ImuBottomSheetContent(
    trackingState: TrackingState,
    onStopTracking: () -> Unit,
    modifier: Modifier = Modifier
) {
    val stateLabel = if (trackingState.isGnssAvailable) "GPS locked" else "Estimated position"
    val etaString = "--"
    val isGnssLocked = trackingState.isGnssAvailable
    val confidence = trackingState.confidence

    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp)
            .padding(bottom = 24.dp)
    ) {
        // Handle for bottom sheet
        Box(
            modifier = Modifier
                .width(40.dp)
                .height(4.dp)
                .clip(RoundedCornerShape(2.dp))
                .background(MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f))
                .align(Alignment.CenterHorizontally)
        )
        
        Spacer(modifier = Modifier.height(16.dp))

        // Top section (similar to FloatingBottomCard)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = Icons.Default.CheckCircle,
                contentDescription = null,
                tint = if (isGnssLocked) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = stateLabel,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.Medium
            )
        }
        Spacer(modifier = Modifier.height(24.dp))

        Text(
            text = "Tracking Data",
            style = MaterialTheme.typography.displayMedium,
            color = MaterialTheme.colorScheme.onSurface,
            fontWeight = FontWeight.Bold
        )
        
        Spacer(modifier = Modifier.height(8.dp))

        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = "${confidence}% Confidence",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(modifier = Modifier.width(16.dp))
            Text(
                text = "$etaString ETA",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        Spacer(modifier = Modifier.height(32.dp))

        // Expanded IMU Visuals
        Text(
            text = "Live IMU Telemetry",
            style = MaterialTheme.typography.titleLarge,
            color = MaterialTheme.colorScheme.onSurface,
            fontWeight = FontWeight.SemiBold
        )
        
        Spacer(modifier = Modifier.height(16.dp))

        // Accelerometer
        ImuSensorGroup(
            title = "Accelerometer (m/s²)",
            readings = trackingState.currentAccel,
            maxValue = 20.0,
            colors = listOf(Color(0xFFE57373), Color(0xFF81C784), Color(0xFF64B5F6))
        )
        
        Spacer(modifier = Modifier.height(16.dp))

        // Gyroscope
        ImuSensorGroup(
            title = "Gyroscope (rad/s)",
            readings = trackingState.currentGyro,
            maxValue = 5.0,
            colors = listOf(Color(0xFFFFB74D), Color(0xFFBA68C8), Color(0xFF4DB6AC))
        )

        Spacer(modifier = Modifier.height(32.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "End tracking session",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            
            IconButton(
                onClick = onStopTracking,
                modifier = Modifier
                    .size(56.dp)
                    .background(MaterialTheme.colorScheme.onSurface, shape = androidx.compose.foundation.shape.CircleShape)
            ) {
                Icon(
                    imageVector = Icons.Default.ArrowForward,
                    contentDescription = "Stop",
                    tint = MaterialTheme.colorScheme.surface
                )
            }
        }
    }
}

@Composable
fun ImuSensorGroup(
    title: String,
    readings: List<Double>,
    maxValue: Double,
    colors: List<Color>
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
            .padding(16.dp)
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(14.dp))
        
        val labels = listOf("X", "Y", "Z")
        for (i in 0 until 3) {
            val reading = if (i < readings.size) readings[i] else 0.0
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)
            ) {
                Text(
                    text = labels[i],
                    style = MaterialTheme.typography.titleSmall,
                    color = colors[i],
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.width(20.dp)
                )
                
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .height(8.dp)
                        .clip(RoundedCornerShape(4.dp))
                        .background(MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.2f))
                ) {
                    val fraction = (reading.absoluteValue / maxValue).coerceIn(0.0, 1.0).toFloat()
                    val alignment = if (reading >= 0) Alignment.CenterStart else Alignment.CenterEnd
                    Box(
                        modifier = Modifier
                            .fillMaxWidth(fraction)
                            .height(8.dp)
                            .background(colors[i])
                            .align(alignment)
                    )
                }
                
                Text(
                    text = String.format("%.2f", reading),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface,
                    fontWeight = FontWeight.Medium,
                    modifier = Modifier.width(48.dp).padding(start = 8.dp),
                    textAlign = androidx.compose.ui.text.style.TextAlign.End
                )
            }
        }
    }
}

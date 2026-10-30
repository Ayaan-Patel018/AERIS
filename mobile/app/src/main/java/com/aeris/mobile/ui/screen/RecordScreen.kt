package com.aeris.mobile.ui.screen

import android.content.Context
import androidx.compose.animation.animateColorAsState
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
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.service.SensorRecorderService
import com.aeris.mobile.ui.theme.Aeris

/**
 * Drive recording screen per M08 §1.
 *
 * Records raw motion sensors and satellite fixes to CSV matching backend data_loader.py.
 */
@Composable
fun RecordScreen(
    onNavigateBack: () -> Unit,
    onNavigateTab: (com.aeris.mobile.ui.components.AerisNavTab) -> Unit = {},
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val colors = Aeris.colors
    val status by SensorRecorderService.status.collectAsState()

    Box(modifier = modifier.fillMaxSize().background(colors.chalk)) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp)
                .padding(bottom = 76.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween
        ) {
        // Top header
        Column(modifier = Modifier.fillMaxWidth()) {
            Text(
                text = "Record a drive",
                color = colors.ink,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Log raw phone motion sensors and satellite fixes for offline processing.",
                color = colors.ink2,
                fontSize = 13.5.sp,
                lineHeight = 18.sp
            )
        }

        // Status Card
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(colors.paper)
                .border(1.dp, colors.harbor, RoundedCornerShape(16.dp))
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // Readiness badge
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(10.dp)
                        .clip(CircleShape)
                        .background(if (status.isRecording) colors.amber else colors.teal)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = if (status.isRecording) "Recording in progress" else "Ready to record",
                    color = colors.ink,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold
                )
            }

            // Sensor streaming status
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = "Sensors (Accel + Gyro)", color = colors.ink2, fontSize = 13.sp)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.Check,
                        contentDescription = null,
                        tint = colors.teal,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(text = "Active (~100 Hz)", color = colors.ink, fontSize = 12.5.sp, fontWeight = FontWeight.Medium)
                }
            }

            // Real Satellites from this phone
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = "Satellites (from this phone)", color = colors.ink2, fontSize = 13.sp)
                Text(
                    text = "${status.satellitesUsed} in fix",
                    color = colors.ink,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold
                )
            }

            // Fix accuracy
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = "GNSS Fix Accuracy", color = colors.ink2, fontSize = 13.sp)
                val accText = if (status.fixAccuracyMeters != null) String.format("±%.1f m", status.fixAccuracyMeters) else "Acquiring…"
                Text(
                    text = accText,
                    color = colors.ink,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold
                )
            }

            if (status.isRecording) {
                // Live metrics row
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    val m = status.elapsedSec / 60
                    val s = status.elapsedSec % 60
                    val kb = status.bytesWritten / 1024
                    Text(
                        text = String.format("Time: %02d:%02d", m, s),
                        color = colors.amber,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "$kb KB written",
                        color = colors.ink2,
                        fontSize = 12.5.sp,
                    )
                }
            }
        }

        // Center 72 dp round record button
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                modifier = Modifier
                    .size(76.dp)
                    .clip(CircleShape)
                    .background(if (status.isRecording) colors.amberSoft else colors.harbor2)
                    .border(2.dp, if (status.isRecording) colors.amber else colors.harbor, CircleShape)
                    .clickable(role = Role.Button) {
                        if (status.isRecording) {
                            SensorRecorderService.stop(context)
                        } else {
                            SensorRecorderService.start(context)
                        }
                    }
                    .semantics {
                        role = Role.Button
                        contentDescription = if (status.isRecording) "Stop recording" else "Start recording"
                    },
                contentAlignment = Alignment.Center
            ) {
                if (status.isRecording) {
                    // Square Stop glyph
                    Box(
                        modifier = Modifier
                            .size(24.dp)
                            .clip(RoundedCornerShape(4.dp))
                            .background(colors.amber)
                    )
                } else {
                    // Circle Record glyph
                    Box(
                        modifier = Modifier
                            .size(28.dp)
                            .clip(CircleShape)
                            .background(colors.ink)
                    )
                }
            }
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                text = if (status.isRecording) "Tap to Stop & Save" else "Tap to Record",
                color = colors.ink2,
                fontSize = 13.sp,
                fontWeight = FontWeight.Medium
            )
        }

        // Honest disclaimer
        Text(
            text = "Record mode logs raw device sensors. AERIS dead reckoning runs offline on the backend.",
            color = colors.ink3,
            fontSize = 11.5.sp,
            textAlign = androidx.compose.ui.text.style.TextAlign.Center,
            lineHeight = 16.sp,
            modifier = Modifier.padding(horizontal = 16.dp)
        )
    }

        // Bottom Navigation Bar
        com.aeris.mobile.ui.components.AerisBottomNav(
            selectedTab = com.aeris.mobile.ui.components.AerisNavTab.RECORD,
            onTabSelected = onNavigateTab,
            modifier = Modifier.align(Alignment.BottomCenter)
        )
    }
}

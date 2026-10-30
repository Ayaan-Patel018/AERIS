package com.aeris.mobile.ui.screen

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
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.aeris.mobile.ui.theme.Aeris

/**
 * Settings dialog per M09 §5.
 */
@Composable
fun SettingsDialog(
    isNightTheme: Boolean,
    onToggleNightTheme: (Boolean) -> Unit,
    use95PercentUncertainty: Boolean,
    onToggle95Percent: (Boolean) -> Unit,
    showReferenceTrack: Boolean,
    onToggleReferenceTrack: (Boolean) -> Unit,
    useMpsUnits: Boolean,
    onToggleUnits: (Boolean) -> Unit,
    onDismiss: () -> Unit,
) {
    val colors = Aeris.colors

    Dialog(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(24.dp))
                .background(colors.paper)
                .border(1.dp, colors.harbor, RoundedCornerShape(24.dp))
                .padding(24.dp)
                .verticalScroll(rememberScrollState())
        ) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Settings",
                    color = colors.ink,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold
                )
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(CircleShape)
                        .background(colors.harbor2)
                        .clickable(role = Role.Button, onClick = onDismiss)
                        .semantics { role = Role.Button },
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Close,
                        contentDescription = "Close",
                        tint = colors.ink,
                        modifier = Modifier.size(18.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(20.dp))

            // Dark Mode toggle
            SettingSwitchRow(
                title = "Dark appearance",
                subtitle = "Force night mode map and high-contrast UI",
                checked = isNightTheme,
                onCheckedChange = onToggleNightTheme
            )

            HorizontalDivider(color = colors.harbor, modifier = Modifier.padding(vertical = 12.dp))

            // 95% Confidence Ellipse toggle
            SettingSwitchRow(
                title = "95% Confidence region",
                subtitle = "Scale error ellipse to 95% 2-DoF (default is 1σ)",
                checked = use95PercentUncertainty,
                onCheckedChange = onToggle95Percent
            )

            HorizontalDivider(color = colors.harbor, modifier = Modifier.padding(vertical = 12.dp))

            // Speed units (km/h vs m/s)
            SettingSwitchRow(
                title = "Use m/s speed units",
                subtitle = "Display velocity in m/s instead of km/h",
                checked = useMpsUnits,
                onCheckedChange = onToggleUnits
            )

            HorizontalDivider(color = colors.harbor, modifier = Modifier.padding(vertical = 12.dp))

            // Reference track (Ground truth debug toggle)
            SettingSwitchRow(
                title = "Show reference track",
                subtitle = "Reference — not used by AERIS (scoring only)",
                checked = showReferenceTrack,
                onCheckedChange = onToggleReferenceTrack
            )

            HorizontalDivider(color = colors.harbor, modifier = Modifier.padding(vertical = 12.dp))

            // Live positioning (Honest disabled placeholder per M08 §5)
            Column(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "Live positioning",
                    color = colors.ink3,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = "Requires on-device real-time filter deployment (Tier 3).",
                    color = colors.ink3,
                    fontSize = 12.sp
                )
            }

            Spacer(modifier = Modifier.height(20.dp))

            // Privacy notice per V0 § 4
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(colors.harbor2)
                    .padding(12.dp)
            ) {
                Column {
                    Text(
                        text = "Privacy Notice",
                        color = colors.ink,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "• Leaves device: Map tile requests for the visible area, search text with approximate location bias, and route endpoints for directions.\n• Never leaves device: Recorded sensor data, AERIS tracks, reference tracks, trip metrics, and drive history. No analytics or telemetry.",
                        color = colors.ink2,
                        fontSize = 11.sp,
                        lineHeight = 15.sp
                    )
                }
            }
        }
    }
}

@Composable
private fun SettingSwitchRow(
    title: String,
    subtitle: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
) {
    val colors = Aeris.colors
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                color = colors.ink,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = subtitle,
                color = colors.ink2,
                fontSize = 12.sp,
                lineHeight = 16.sp
            )
        }
        Spacer(modifier = Modifier.width(12.dp))
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = SwitchDefaults.colors(
                checkedThumbColor = colors.paper,
                checkedTrackColor = colors.cobalt,
                uncheckedThumbColor = colors.ink3,
                uncheckedTrackColor = colors.harbor2,
            )
        )
    }
}

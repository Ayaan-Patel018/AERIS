package com.aeris.mobile.ui.components

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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.ui.theme.Aeris

enum class AerisNavTab(val label: String) {
    EXPLORE("Explore"),
    TRIPS("Trips"),
    RECORD("Record")
}

/**
 * Three-tab bottom navigation bar matching Mockup 00 Screen 1 & R1 § 3.
 */
@Composable
fun AerisBottomNav(
    selectedTab: AerisNavTab,
    onTabSelected: (AerisNavTab) -> Unit,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors

    Box(
        modifier = modifier
            .fillMaxWidth()
            .shadow(12.dp, ambientColor = colors.ink.copy(alpha = 0.08f))
            .background(colors.paper)
            .border(width = 1.dp, color = colors.harbor)
            .padding(vertical = 8.dp, horizontal = 24.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceAround,
            verticalAlignment = Alignment.CenterVertically
        ) {
            AerisNavTab.entries.forEach { tab ->
                val isSelected = tab == selectedTab

                Column(
                    modifier = Modifier
                        .clickable(role = Role.Tab) { onTabSelected(tab) }
                        .padding(horizontal = 16.dp, vertical = 4.dp)
                        .semantics {
                            role = Role.Tab
                            selected = isSelected
                            contentDescription = "${tab.label} tab"
                        },
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    // Pill highlight for active tab
                    Box(
                        modifier = Modifier
                            .size(width = 48.dp, height = 30.dp)
                            .clip(RoundedCornerShape(15.dp))
                            .background(if (isSelected) colors.cobaltSoft else androidx.compose.ui.graphics.Color.Transparent),
                        contentAlignment = Alignment.Center
                    ) {
                        when (tab) {
                            AerisNavTab.EXPLORE -> {
                                // Compass icon
                                Box(
                                    modifier = Modifier
                                        .size(18.dp)
                                        .clip(androidx.compose.foundation.shape.CircleShape)
                                        .border(2.dp, if (isSelected) colors.cobalt else colors.ink2, androidx.compose.foundation.shape.CircleShape)
                                )
                            }
                            AerisNavTab.TRIPS -> {
                                // Route / nodes icon
                                Box(
                                    modifier = Modifier
                                        .size(16.dp)
                                        .border(2.dp, if (isSelected) colors.cobalt else colors.ink2, RoundedCornerShape(4.dp))
                                )
                            }
                            AerisNavTab.RECORD -> {
                                // Concentric record target
                                Box(
                                    modifier = Modifier
                                        .size(16.dp)
                                        .clip(androidx.compose.foundation.shape.CircleShape)
                                        .background(if (isSelected) colors.cobalt else colors.ink2)
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(2.dp))

                    Text(
                        text = tab.label,
                        color = if (isSelected) colors.ink else colors.ink3,
                        fontSize = 11.5.sp,
                        fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal,
                    )
                }
            }
        }
    }
}

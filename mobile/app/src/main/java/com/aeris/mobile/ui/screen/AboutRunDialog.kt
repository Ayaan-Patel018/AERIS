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
 * About This Run (Trust Ledger) dialog per M06 §5.
 */
@Composable
fun AboutRunDialog(onDismiss: () -> Unit) {
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
                Column {
                    Text(
                        text = "Trust Ledger",
                        color = colors.ink,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = "How this track was computed",
                        color = colors.ink2,
                        fontSize = 12.5.sp
                    )
                }

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

            LedgerItem("Filter Algorithm", "15-state Error-State EKF (EsEkf)")
            LedgerItem("Inertial Inputs", "Phone Accelerometer & Gyroscope (~100 Hz)")
            LedgerItem("Satellite Updates", "1 Hz GNSS position fixes")
            LedgerItem("Reference Used as Input", "No (Strictly independent)", highlightCobalt = true)
            LedgerItem("Map Matching", "None (Dead reckoning from motion sensors alone)")
            LedgerItem("Evaluation Scenario", "Warwick Campus S3b (60s GNSS outage)")
            LedgerItem("Problem Statement", "SIH 2026 — ISRO Statement 26168")

            Spacer(modifier = Modifier.height(16.dp))

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(12.dp))
                    .background(colors.harbor2)
                    .padding(12.dp)
            ) {
                Text(
                    text = "AERIS computes position without relying on pre-surveyed ground truth or simulation aid.",
                    color = colors.ink2,
                    fontSize = 11.5.sp,
                    lineHeight = 16.sp
                )
            }
        }
    }
}

@Composable
private fun LedgerItem(label: String, value: String, highlightCobalt: Boolean = false) {
    val colors = Aeris.colors
    Column(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
        Text(
            text = label.uppercase(),
            color = colors.ink3,
            fontSize = 10.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.5.sp
        )
        Spacer(modifier = Modifier.height(2.dp))
        Text(
            text = value,
            color = if (highlightCobalt) colors.cobalt else colors.ink,
            fontSize = 13.5.sp,
            fontWeight = FontWeight.SemiBold
        )
        HorizontalDivider(color = colors.harbor.copy(alpha = 0.5f), modifier = Modifier.padding(top = 8.dp))
    }
}

package com.aeris.mobile.ui.screen

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.ui.components.AerisButton
import com.aeris.mobile.ui.components.AerisButtonVariant
import com.aeris.mobile.ui.theme.Aeris

enum class StageStatus {
    PENDING,
    ACTIVE,
    DONE,
    FAILED,
}

data class LoadingStage(
    val label: String,
    val status: StageStatus,
)

/**
 * In-app loading screen per M04 §2.
 *
 * Shows real progress of:
 * 1. Reading drive data
 * 2. Preparing the map
 * 3. Building the path
 */
@Composable
fun LoadingScreen(
    stages: List<LoadingStage>,
    driveId: String?,
    errorMessage: String? = null,
    onRetry: () -> Unit = {},
    onContinueWithoutMap: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(colors.chalk),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier
                .widthIn(max = 320.dp)
                .padding(24.dp)
        ) {
            // Wordmark and Brand
            Text(
                text = "AERIS",
                color = colors.ink,
                fontSize = 32.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 2.sp,
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = "Navigation that keeps working without satellites.",
                color = colors.ink2,
                fontSize = 14.sp,
                lineHeight = 20.sp,
                modifier = Modifier.padding(horizontal = 8.dp),
                textAlign = androidx.compose.ui.text.style.TextAlign.Center
            )

            Spacer(modifier = Modifier.height(32.dp))

            if (errorMessage != null) {
                // Error card
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(16.dp))
                        .background(colors.paper)
                        .border(1.dp, colors.signalRed.copy(alpha = 0.3f), RoundedCornerShape(16.dp))
                        .padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(
                        imageVector = Icons.Default.Warning,
                        contentDescription = null,
                        tint = colors.signalRed,
                        modifier = Modifier.size(28.dp)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Data unavailable",
                        color = colors.ink,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = errorMessage,
                        color = colors.ink2,
                        fontSize = 13.sp,
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    AerisButton(
                        text = "Retry",
                        onClick = onRetry,
                        compact = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    if (onContinueWithoutMap != null) {
                        Spacer(modifier = Modifier.height(8.dp))
                        AerisButton(
                            text = "Continue without map",
                            onClick = onContinueWithoutMap,
                            variant = AerisButtonVariant.OUTLINED,
                            compact = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
            } else {
                // Stage list
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(16.dp))
                        .background(colors.paper)
                        .border(1.dp, colors.harbor, RoundedCornerShape(16.dp))
                        .padding(horizontal = 20.dp, vertical = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    stages.forEach { stage ->
                        StageRow(stage = stage)
                    }
                }

                if (driveId != null) {
                    Spacer(modifier = Modifier.height(20.dp))
                    Text(
                        text = "Drive: $driveId",
                        color = colors.ink3,
                        fontSize = 12.sp,
                    )
                }
            }
        }
    }
}

@Composable
private fun StageRow(stage: LoadingStage) {
    val colors = Aeris.colors

    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth()
    ) {
        when (stage.status) {
            StageStatus.PENDING -> {
                Box(
                    modifier = Modifier
                        .size(18.dp)
                        .border(1.5.dp, colors.harbor, CircleShape)
                )
            }
            StageStatus.ACTIVE -> {
                CircularProgressIndicator(
                    modifier = Modifier.size(18.dp),
                    strokeWidth = 2.dp,
                    color = colors.cobalt
                )
            }
            StageStatus.DONE -> {
                Box(
                    modifier = Modifier
                        .size(18.dp)
                        .clip(CircleShape)
                        .background(colors.cobalt),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Check,
                        contentDescription = null,
                        tint = colors.paper,
                        modifier = Modifier.size(12.dp)
                    )
                }
            }
            StageStatus.FAILED -> {
                Box(
                    modifier = Modifier
                        .size(18.dp)
                        .clip(CircleShape)
                        .background(colors.signalRed),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Warning,
                        contentDescription = null,
                        tint = colors.paper,
                        modifier = Modifier.size(12.dp)
                    )
                }
            }
        }

        Spacer(modifier = Modifier.width(14.dp))

        Text(
            text = stage.label,
            color = if (stage.status == StageStatus.PENDING) colors.ink3 else colors.ink,
            fontSize = 13.5.sp,
            fontWeight = if (stage.status == StageStatus.ACTIVE) FontWeight.SemiBold else FontWeight.Normal,
        )
    }
}

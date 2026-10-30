package com.aeris.mobile.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.R
import com.aeris.mobile.ui.theme.Aeris

/**
 * Banner mode: Active Outage or Reacquisition confirmation.
 */
sealed interface BannerState {
    data class Outage(val elapsedSec: Double, val uncertaintyM: Double) : BannerState
    data class Reacquisition(val separationMeters: Double) : BannerState
}

/**
 * Prominent alert banner rendered at the top of the map view when an outage occurs or resolves.
 *
 * Adheres to M02 & M06:
 * - AmberSoft background, Amber border during dead reckoning.
 * - TealSoft background, Teal border upon re-acquisition.
 * - Text uses high-contrast ink (never white on amber).
 * - Declares LiveRegionMode.Polite for screen readers.
 */
@Composable
fun OutageBanner(
    bannerState: BannerState?,
    modifier: Modifier = Modifier,
) {
    val colors = Aeris.colors

    AnimatedVisibility(
        visible = bannerState != null,
        enter = fadeIn() + expandVertically(),
        exit = fadeOut() + shrinkVertically(),
        modifier = modifier.fillMaxWidth()
    ) {
        if (bannerState == null) return@AnimatedVisibility

        when (bannerState) {
            is BannerState.Outage -> {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 6.dp)
                        .shadow(8.dp, RoundedCornerShape(16.dp), ambientColor = colors.ink.copy(alpha = 0.12f))
                        .clip(RoundedCornerShape(16.dp))
                        .background(colors.amberSoft)
                        .border(1.5.dp, colors.amber, RoundedCornerShape(16.dp))
                        .padding(horizontal = 16.dp, vertical = 12.dp)
                        .semantics { liveRegion = LiveRegionMode.Polite }
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            text = stringResource(R.string.outage_banner_title),
                            color = colors.ink,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold,
                        )
                        val elapsedText = String.format("+%.1fs", bannerState.elapsedSec)
                        Text(
                            text = elapsedText,
                            color = colors.amber,
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                    Spacer(modifier = Modifier.height(3.dp))
                    Text(
                        text = stringResource(R.string.outage_banner_subtitle),
                        color = colors.ink2,
                        fontSize = 12.5.sp,
                        lineHeight = 16.sp,
                    )
                }
            }
            is BannerState.Reacquisition -> {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 6.dp)
                        .shadow(8.dp, RoundedCornerShape(16.dp), ambientColor = colors.ink.copy(alpha = 0.12f))
                        .clip(RoundedCornerShape(16.dp))
                        .background(colors.tealSoft)
                        .border(1.5.dp, colors.teal, RoundedCornerShape(16.dp))
                        .padding(horizontal = 16.dp, vertical = 12.dp)
                        .semantics { liveRegion = LiveRegionMode.Polite }
                ) {
                    Text(
                        text = stringResource(R.string.reacquisition_banner_title),
                        color = colors.ink,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(modifier = Modifier.height(3.dp))
                    Text(
                        text = stringResource(
                            R.string.reacquisition_distance_format,
                            bannerState.separationMeters
                        ),
                        color = colors.ink2,
                        fontSize = 12.5.sp,
                    )
                }
            }
        }
    }
}

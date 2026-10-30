package com.aeris.mobile.ui.components

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.aeris.mobile.ui.theme.AERISTheme
import com.aeris.mobile.ui.theme.AerisGrey10
import com.aeris.mobile.ui.theme.AerisGrey15
import com.aeris.mobile.ui.theme.AerisGrey50
import com.aeris.mobile.ui.theme.AerisGrey70
import com.aeris.mobile.ui.theme.AerisWhite

/**
 * Floating status pill anchored at the top of the map.
 *
 * Shows a small indicator dot (white = GNSS locked, grey = dead reckoning)
 * and a one-line status label.
 *
 * @param isGnssLocked Whether GNSS is currently available.
 * @param statusText   One-line status string.
 */
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material3.Icon
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.fillMaxWidth

@Composable
fun StatusPill(
    isGnssLocked: Boolean,
    statusText: String,
    modifier: Modifier = Modifier,
) {
    val dotColor by animateColorAsState(
        targetValue = if (isGnssLocked) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
        label = "dot",
    )
    
    // Mimic the large floating pill in the target design
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp),
        horizontalArrangement = Arrangement.Center
    ) {
        Row(
            modifier = Modifier
                .clip(RoundedCornerShape(32.dp))
                .background(androidx.compose.ui.graphics.Color(0x22FFFFFF))
                .border(1.dp, androidx.compose.ui.graphics.Color(0x33FFFFFF), RoundedCornerShape(32.dp))
                .padding(horizontal = 20.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                imageVector = Icons.Default.LocationOn,
                contentDescription = null,
                tint = dotColor,
                modifier = Modifier.size(20.dp)
            )
            Spacer(modifier = Modifier.width(12.dp))
            Text(
                text = statusText,
                style = MaterialTheme.typography.titleMedium,
                color = androidx.compose.ui.graphics.Color.White,
            )
        }
    }
}

@Preview
@Composable
private fun StatusPillPreview() {
    AERISTheme {
        StatusPill(isGnssLocked = false, statusText = "Estimating position")
    }
}

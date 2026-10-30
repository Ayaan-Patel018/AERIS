package com.aeris.mobile.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.Spacer
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.font.FontWeight
import com.aeris.mobile.ui.theme.AERISTheme

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue

/**
 * Launch / welcome screen — the first thing the user sees.
 *
 * @param onGetStarted Called when the user initiates tracking.
 */
@Composable
fun LaunchScreen(onGetStarted: () -> Unit = {}) {
    var visible by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        visible = true
        kotlinx.coroutines.delay(2500)
        onGetStarted()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier.padding(horizontal = 24.dp)
        ) {
            // ── Logo & Brand ────────────────────────────────────────────
            AnimatedVisibility(
                visible = visible,
                enter = fadeIn(animationSpec = tween(800, delayMillis = 100)) + slideInVertically(animationSpec = tween(800, delayMillis = 100), initialOffsetY = { it / 2 })
            ) {
                // Load aeris(1).svg from assets via Coil SVG decoder.
                // The SVG has a white background; we invert it to white-on-black.
                coil.compose.AsyncImage(
                    model = coil.request.ImageRequest.Builder(androidx.compose.ui.platform.LocalContext.current)
                        .data("file:///android_asset/aeris_wordmark.svg")
                        .decoderFactory(coil.decode.SvgDecoder.Factory())
                        .build(),
                    contentDescription = "Aeris Wordmark",
                    colorFilter = androidx.compose.ui.graphics.ColorFilter.colorMatrix(
                        androidx.compose.ui.graphics.ColorMatrix(
                            floatArrayOf(
                                -1f,  0f,  0f, 0f, 255f,
                                 0f, -1f,  0f, 0f, 255f,
                                 0f,  0f, -1f, 0f, 255f,
                                 0f,  0f,  0f, 1f,   0f,
                            )
                        )
                    ),
                    modifier = Modifier
                        .fillMaxWidth(0.75f)
                        .aspectRatio(106f / 60f)
                )
            }

            Spacer(modifier = Modifier.height(56.dp))

            // ── Tagline ─────────────────────────────────────────────────
            AnimatedVisibility(
                visible = visible,
                enter = fadeIn(animationSpec = tween(800, delayMillis = 400)) + slideInVertically(animationSpec = tween(800, delayMillis = 400), initialOffsetY = { it / 2 })
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(
                        text = "Navigate the Unknown.",
                        style = MaterialTheme.typography.titleLarge.copy(
                            color = Color.White,
                            fontWeight = FontWeight.Normal,
                            letterSpacing = 1.sp,
                        ),
                    )
                    
                    Spacer(modifier = Modifier.height(16.dp))

                    Text(
                        text = "Precision dead-reckoning when GNSS fails.",
                        style = MaterialTheme.typography.bodyMedium.copy(
                            color = Color.White.copy(alpha = 0.6f),
                            letterSpacing = 0.5.sp,
                        ),
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center
                    )
                }
            }

            Spacer(modifier = Modifier.height(56.dp))
        }
    }
}

// ── Preview ─────────────────────────────────────────────────────────────

@Preview(showBackground = true, backgroundColor = 0xFF000000)
@Composable
private fun LaunchScreenPreview() {
    AERISTheme {
        LaunchScreen()
    }
}

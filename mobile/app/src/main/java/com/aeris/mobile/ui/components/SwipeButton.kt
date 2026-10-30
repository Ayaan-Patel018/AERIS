package com.aeris.mobile.ui.components

import androidx.compose.animation.core.Animatable
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import kotlin.math.roundToInt

@Composable
fun SwipeButton(
    text: String = "Swipe to begin",
    onSwipeComplete: () -> Unit,
    modifier: Modifier = Modifier
) {
    var width by remember { mutableFloatStateOf(0f) }
    val trackHeightDp = 58.dp
    val thumbSizeDp = 46.dp
    val thumbPaddingDp = 6.dp
    
    val thumbSizePx = with(LocalDensity.current) { (thumbSizeDp + thumbPaddingDp * 2).toPx() }
    
    val offsetX = remember { Animatable(0f) }
    var isComplete by remember { mutableStateOf(false) }
    val coroutineScope = rememberCoroutineScope()

    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(trackHeightDp)
            .clip(CircleShape)
            .background(Color(0xFF151517)) // Premium dark grey
            .onSizeChanged { width = it.width.toFloat() }
    ) {
        // Background Text
        val textAlpha = 1f - (offsetX.value / ((width - thumbSizePx).coerceAtLeast(1f) * 0.5f)).coerceIn(0f, 1f)
        Text(
            text = text,
            style = MaterialTheme.typography.labelLarge.copy(
                letterSpacing = 1.sp,
                fontWeight = FontWeight.Medium
            ),
            color = Color.White.copy(alpha = 0.5f),
            modifier = Modifier
                .align(Alignment.Center)
                .alpha(textAlpha)
        )

        // Draggable Thumb
        Box(
            modifier = Modifier
                .offset { IntOffset(offsetX.value.roundToInt(), 0) }
                .padding(thumbPaddingDp)
                .size(thumbSizeDp)
                .clip(CircleShape)
                .background(Color.White)
                .pointerInput(Unit) {
                    detectHorizontalDragGestures(
                        onDragEnd = {
                            coroutineScope.launch {
                                val maxDrag = width - thumbSizePx
                                if (offsetX.value > maxDrag * 0.65f && !isComplete) {
                                    isComplete = true
                                    offsetX.animateTo(maxDrag)
                                    onSwipeComplete()
                                } else {
                                    offsetX.animateTo(0f)
                                }
                            }
                        },
                        onHorizontalDrag = { change, dragAmount ->
                            if (isComplete) return@detectHorizontalDragGestures
                            change.consume()
                            coroutineScope.launch {
                                val maxDrag = width - thumbSizePx
                                val newOffset = (offsetX.value + dragAmount).coerceIn(0f, maxDrag)
                                offsetX.snapTo(newOffset)
                            }
                        }
                    )
                },
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                contentDescription = "Swipe Arrow",
                tint = Color.Black,
                modifier = Modifier.size(24.dp)
            )
        }
    }
}

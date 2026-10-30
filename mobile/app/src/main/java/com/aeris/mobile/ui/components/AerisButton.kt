package com.aeris.mobile.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonColors
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aeris.mobile.ui.theme.Aeris

enum class AerisButtonVariant {
    FILLED,
    TONAL,
    OUTLINED,
    TEXT,
}

/**
 * Standard Aeris button component per M02 specification.
 *
 * Radius: 12 dp
 * Height: 48 dp (or compact 40 dp)
 * Minimum touch target: 48x48 dp
 * Accessible touch targets, font-scale tolerant.
 */
@Composable
fun AerisButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    variant: AerisButtonVariant = AerisButtonVariant.FILLED,
    enabled: Boolean = true,
    compact: Boolean = false,
    tag: String = "AerisButton",
    trailingIcon: @Composable (() -> Unit)? = null,
) {
    val colors = Aeris.colors
    val height = if (compact) 40.dp else 48.dp
    val shape = RoundedCornerShape(12.dp)
    val interactionSource = remember { MutableInteractionSource() }

    val contentPadding = PaddingValues(
        horizontal = if (compact) 16.dp else 20.dp,
        vertical = if (compact) 8.dp else 12.dp
    )

    when (variant) {
        AerisButtonVariant.FILLED -> {
            Button(
                onClick = onClick,
                enabled = enabled,
                shape = shape,
                colors = ButtonDefaults.buttonColors(
                    containerColor = colors.ink,
                    contentColor = colors.paper,
                    disabledContainerColor = colors.harbor2,
                    disabledContentColor = colors.ink3
                ),
                contentPadding = contentPadding,
                interactionSource = interactionSource,
                modifier = modifier
                    .defaultMinSize(minWidth = 48.dp, minHeight = 48.dp)
                    .height(height)
                    .testTag(tag),
            ) {
                Text(
                    text = text,
                    fontSize = if (compact) 13.sp else 14.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                trailingIcon?.invoke()
            }
        }
        AerisButtonVariant.TONAL -> {
            Button(
                onClick = onClick,
                enabled = enabled,
                shape = shape,
                colors = ButtonDefaults.buttonColors(
                    containerColor = colors.harbor2,
                    contentColor = colors.ink,
                    disabledContainerColor = colors.harbor2.copy(alpha = 0.5f),
                    disabledContentColor = colors.ink3
                ),
                contentPadding = contentPadding,
                interactionSource = interactionSource,
                modifier = modifier
                    .defaultMinSize(minWidth = 48.dp, minHeight = 48.dp)
                    .height(height)
                    .testTag(tag),
            ) {
                Text(
                    text = text,
                    fontSize = if (compact) 13.sp else 14.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                trailingIcon?.invoke()
            }
        }
        AerisButtonVariant.OUTLINED -> {
            OutlinedButton(
                onClick = onClick,
                enabled = enabled,
                shape = shape,
                border = BorderStroke(1.dp, if (enabled) colors.harbor else colors.harbor2),
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = colors.ink,
                    disabledContentColor = colors.ink3
                ),
                contentPadding = contentPadding,
                interactionSource = interactionSource,
                modifier = modifier
                    .defaultMinSize(minWidth = 48.dp, minHeight = 48.dp)
                    .height(height)
                    .testTag(tag),
            ) {
                Text(
                    text = text,
                    fontSize = if (compact) 13.sp else 14.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                trailingIcon?.invoke()
            }
        }
        AerisButtonVariant.TEXT -> {
            TextButton(
                onClick = onClick,
                enabled = enabled,
                shape = shape,
                colors = ButtonDefaults.textButtonColors(
                    contentColor = colors.ink,
                    disabledContentColor = colors.ink3
                ),
                contentPadding = contentPadding,
                interactionSource = interactionSource,
                modifier = modifier
                    .defaultMinSize(minWidth = 48.dp, minHeight = 48.dp)
                    .height(height)
                    .testTag(tag),
            ) {
                Text(
                    text = text,
                    fontSize = if (compact) 13.sp else 14.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                trailingIcon?.invoke()
            }
        }
    }
}

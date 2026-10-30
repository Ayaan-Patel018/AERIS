package com.aeris.mobile.ui.theme

import android.app.Activity
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

/**
 * Maps Day AerisColors to Material 3 LightColorScheme.
 */
private fun lightAerisColorScheme(colors: AerisColors) = lightColorScheme(
    primary = colors.ink,
    onPrimary = colors.chalk,
    primaryContainer = colors.harbor2,
    onPrimaryContainer = colors.ink,
    secondary = colors.ink2,
    onSecondary = colors.chalk,
    secondaryContainer = colors.cobaltSoft,
    onSecondaryContainer = colors.cobalt,
    tertiary = colors.teal,
    onTertiary = colors.paper,
    tertiaryContainer = colors.tealSoft,
    onTertiaryContainer = colors.ink,
    background = colors.chalk,
    onBackground = colors.ink,
    surface = colors.paper,
    onSurface = colors.ink,
    surfaceVariant = colors.harbor2,
    onSurfaceVariant = colors.ink2,
    outline = colors.harbor,
    outlineVariant = colors.harbor2,
    error = colors.signalRed,
    onError = colors.paper,
    errorContainer = colors.signalRedSoft,
    onErrorContainer = colors.signalRed,
)

/**
 * Maps Night AerisColors to Material 3 DarkColorScheme.
 */
private fun darkAerisColorScheme(colors: AerisColors) = darkColorScheme(
    primary = colors.ink,
    onPrimary = colors.chalk,
    primaryContainer = colors.harbor2,
    onPrimaryContainer = colors.ink,
    secondary = colors.ink2,
    onSecondary = colors.chalk,
    secondaryContainer = colors.cobaltSoft,
    onSecondaryContainer = colors.cobalt,
    tertiary = colors.teal,
    onTertiary = colors.chalk,
    tertiaryContainer = colors.tealSoft,
    onTertiaryContainer = colors.ink,
    background = colors.chalk,
    onBackground = colors.ink,
    surface = colors.paper,
    onSurface = colors.ink,
    surfaceVariant = colors.harbor2,
    onSurfaceVariant = colors.ink2,
    outline = colors.harbor,
    outlineVariant = colors.harbor2,
    error = colors.signalRed,
    onError = colors.chalk,
    errorContainer = colors.signalRedSoft,
    onErrorContainer = colors.signalRed,
)

/**
 * Root Compose theme for the AERIS application.
 *
 * Provides [AerisColors] via [LocalAerisColors] and sets up Material3
 * ColorScheme, Typography, and edge-to-edge system bar appearance.
 */
@Composable
fun AERISTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val aerisColors = if (darkTheme) NightColors else DayColors
    val materialScheme = if (darkTheme) {
        darkAerisColorScheme(aerisColors)
    } else {
        lightAerisColorScheme(aerisColors)
    }

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = aerisColors.chalk.toArgb()
            window.navigationBarColor = aerisColors.chalk.toArgb()
            val insetsController = WindowCompat.getInsetsController(window, view)
            insetsController.isAppearanceLightStatusBars = !darkTheme
            insetsController.isAppearanceLightNavigationBars = !darkTheme
        }
    }

    CompositionLocalProvider(
        LocalAerisColors provides aerisColors,
    ) {
        MaterialTheme(
            colorScheme = materialScheme,
            typography = AerisTypography,
            content = content,
        )
    }
}

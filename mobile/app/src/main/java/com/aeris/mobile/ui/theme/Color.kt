package com.aeris.mobile.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

/**
 * Aeris semantic design system tokens per M02 specification.
 *
 * Colours are named strictly for what they mean:
 * - ink / ink2 / ink3: Text and typography hierarchy
 * - chalk: Primary app canvas background
 * - paper: Cards, bottom sheets, floating dialogs
 * - harbor / harbor2: Hairlines, subtle dividing borders, skeletons
 * - cobalt: AERIS dead reckoning estimate (never reused for generic UI buttons)
 * - cobaltSoft: AERIS tint for selected rows and chips
 * - amber: Dead reckoning, outage indicator, uncertainty corridor fill
 * - amberSoft: Outage banner fill, warning pill container
 * - teal: GNSS satellite fix locked, raw GPS fix points
 * - tealSoft: GNSS locked pill container
 * - slate: Ground truth reference and baseline comparison paths
 * - signalRed / signalRedSoft: Error states only
 */
@Immutable
data class AerisColors(
    val ink: Color,
    val ink2: Color,
    val ink3: Color,
    val chalk: Color,
    val paper: Color,
    val harbor: Color,
    val harbor2: Color,
    val cobalt: Color,
    val cobaltSoft: Color,
    val amber: Color,
    val amberLine: Color,
    val amberSoft: Color,
    val teal: Color,
    val tealSoft: Color,
    val slate: Color,
    val signalRed: Color,
    val signalRedSoft: Color,
)

val DayColors = AerisColors(
    ink = Color(0xFF16212B),
    ink2 = Color(0xFF4A5866),
    ink3 = Color(0xFF7A8794),
    chalk = Color(0xFFF5F7F6),
    paper = Color(0xFFFFFFFF),
    harbor = Color(0xFFE3E9EC),
    harbor2 = Color(0xFFEEF2F4),
    cobalt = Color(0xFF2D5BFF),
    cobaltSoft = Color(0xFFE6ECFF),
    amber = Color(0xFFE8930C),
    amberLine = Color(0xFFB26A00),
    amberSoft = Color(0xFFFDF1DC),
    teal = Color(0xFF0E9F8E),
    tealSoft = Color(0xFFDDF4F0),
    slate = Color(0xFF8493A0),
    signalRed = Color(0xFFD64545),
    signalRedSoft = Color(0xFFFBE7E7),
)

val NightColors = AerisColors(
    ink = Color(0xFFE8EEF2),
    ink2 = Color(0xFFA9B6C1),
    ink3 = Color(0xFF76848F),
    chalk = Color(0xFF0C1319),
    paper = Color(0xFF151E26),
    harbor = Color(0xFF26333E),
    harbor2 = Color(0xFF1D2933),
    cobalt = Color(0xFF6D8BFF),
    cobaltSoft = Color(0xFF1C2748),
    amber = Color(0xFFF2A93B),
    amberLine = Color(0xFFF2A93B),
    amberSoft = Color(0xFF3A2C12),
    teal = Color(0xFF2BC4B1),
    tealSoft = Color(0xFF12332F),
    slate = Color(0xFF7D8D9A),
    signalRed = Color(0xFFF06A6A),
    signalRedSoft = Color(0xFF3B1B1B),
)

val LocalAerisColors = staticCompositionLocalOf<AerisColors> {
    error("No AerisColors provided. Did you wrap your composable in AERISTheme?")
}

object Aeris {
    val colors: AerisColors
        @Composable
        get() = LocalAerisColors.current
}

// ── Backwards-compatible grayscale definitions ───────────────────────────
val AerisBlack = Color(0xFF000000)
val AerisWhite = Color(0xFFFFFFFF)
val AerisGrey90 = Color(0xFFE5E5E5)
val AerisGrey70 = Color(0xFFB3B3B3)
val AerisGrey50 = Color(0xFF808080)
val AerisGrey30 = Color(0xFF4D4D4D)
val AerisGrey15 = Color(0xFF262626)
val AerisGrey10 = Color(0xFF1A1A1A)


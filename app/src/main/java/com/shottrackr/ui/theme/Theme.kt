package com.shottrackr.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val DarkColorScheme = darkColorScheme(
    background = DeepCharcoal,
    surface = DarkGrey,
    primary = BasketballOrange,
    onPrimary = OffWhite,
    onBackground = OffWhite,
    onSurface = OffWhite,
    secondary = MutedGrey
)

@Composable
fun ShotTrackrTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkColorScheme,
        // Typography can be added here later
        content = content
    )
}
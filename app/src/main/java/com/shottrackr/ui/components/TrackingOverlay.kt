package com.shottrackr.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import com.shottrackr.engine.FrameResult
import com.shottrackr.ui.theme.BasketballOrange

@Composable
fun TrackingOverlay(
    frameResult: FrameResult?,
    modifier: Modifier = Modifier
) {
    Canvas(modifier = modifier.fillMaxSize()) {
        if (frameResult == null) return@Canvas

        val scaleX = size.width / 640f // Assuming YOLO 640x640 input
        val scaleY = size.height / 640f

        if (frameResult.ballTracked) {
            val cx = frameResult.ballX * scaleX
            val cy = frameResult.ballY * scaleY

            drawCircle(
                color = BasketballOrange,
                radius = 16f,
                center = Offset(cx, cy)
            )
        }
    }
}
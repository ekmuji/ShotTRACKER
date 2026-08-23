package com.shottrackr.ui.workout

import android.graphics.Bitmap
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shottrackr.engine.FrameResult
import com.shottrackr.ui.components.CameraPreviewLayer
import com.shottrackr.ui.components.TrackingOverlay
import com.shottrackr.ui.theme.ShotTrackrTheme
import kotlinx.coroutines.delay

@Composable
fun WorkoutScreen(
    uiState: WorkoutUiState,
    frameResult: FrameResult?,
    onFrameCaptured: (Bitmap) -> Unit
) {
    Box(modifier = Modifier.fillMaxSize().background(Color.Black)) {

        // 1. CameraX Layer
        CameraPreviewLayer(onFrame = onFrameCaptured)

        // 2. Tracking Dot Layer
        TrackingOverlay(frameResult = frameResult)

        // 3. Floating HUD Layer
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // Status Badge
            Text(
                text = uiState.trackingStatus.name.replace("_", " "),
                color = if (uiState.trackingStatus == TrackingStatus.TRACKING) Color(0xFF4ADE80) else Color(0xFFFF8A3D),
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp
            )

            // Bottom Scoreboard
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Bottom
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(32.dp)) {
                    StatDisplay("MAKES", uiState.makes.toString(), Color(0xFF4ADE80))
                    StatDisplay("MISSES", uiState.misses.toString(), Color.White)
                }

                Text(
                    text = uiState.percentage,
                    fontSize = 80.sp,
                    fontWeight = FontWeight.Black,
                    color = Color(0xFFFF8A3D) // Basketball Orange
                )
            }
        }

        // 4. Transient Shot Animation
        if (uiState.latestShot != null) {
            TransientShotAnimation(uiState.latestShot)
        }
    }
}

@Composable
fun StatDisplay(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(text = value, fontSize = 56.sp, fontWeight = FontWeight.Bold, color = color)
        Text(text = label, fontSize = 14.sp, color = Color.LightGray)
    }
}

@Composable
fun TransientShotAnimation(shotResult: ShotResult) {
    var visible by remember { mutableStateOf(true) }

    LaunchedEffect(shotResult) {
        visible = true
        delay(1500)
        visible = false
    }

    AnimatedVisibility(
        visible = visible,
        enter = scaleIn(initialScale = 0.5f) + fadeIn(),
        exit = scaleOut(targetScale = 1.2f) + fadeOut(),
        modifier = Modifier.fillMaxSize()
    ) {
        Box(contentAlignment = Alignment.Center) {
            val text = if (shotResult == ShotResult.MADE) "✓ MADE" else "MISS"
            val color = if (shotResult == ShotResult.MADE) Color(0xFF4ADE80) else Color.White

            Text(
                text = text,
                fontSize = 72.sp,
                fontWeight = FontWeight.Black,
                color = color,
                modifier = Modifier
                    .background(Color(0x99000000), shape = MaterialTheme.shapes.large)
                    .padding(32.dp)
            )
        }
    }
}

// --- COMPOSE PREVIEWS ---

@Preview(
    name = "Live Workout HUD (Landscape)",
    device = "spec:width=1280dp,height=720dp,orientation=landscape",
    showBackground = true
)
@Composable
fun WorkoutScreenPreview() {
    ShotTrackrTheme {
        WorkoutScreen(
            uiState = WorkoutUiState(
                makes = 12,
                misses = 8,
                totalShots = 20,
                percentage = "60%",
                trackingStatus = TrackingStatus.TRACKING,
                latestShot = ShotResult.MADE
            ),
            frameResult = FrameResult(
                totalMakes = 12,
                totalShots = 20,
                justMadeShot = true,
                justMissedShot = false,
                hoopTracked = true,
                ballTracked = true,
                ballX = 320f,
                ballY = 200f,
                ballW = 30f,
                ballH = 30f,
                hoopX = 320f,
                hoopY = 150f,
                hoopW = 80f,
                hoopH = 20f
            ),
            onFrameCaptured = {}
        )
    }
}
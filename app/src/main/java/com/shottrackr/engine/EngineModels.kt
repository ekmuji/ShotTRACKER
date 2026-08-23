package com.shottrackr.engine


enum class ShotResult {
    SHOT_NONE,
    SHOT_MADE,
    SHOT_MISSED
}

data class FrameResult(
    val totalMakes: Int,
    val totalShots: Int,
    val justMadeShot: Boolean,
    val justMissedShot: Boolean,
    val hoopTracked: Boolean,
    val ballTracked: Boolean,
    val ballX: Float,
    val ballY: Float,
    val ballW: Float,
    val ballH: Float,
    val hoopX: Float,
    val hoopY: Float,
    val hoopW: Float,
    val hoopH: Float
)
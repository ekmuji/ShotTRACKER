package com.shottrackr.ui.workout

enum class ShotResult {
    MADE, MISSED
}

enum class TrackingStatus {
    TRACKING, FINDING_RIM, MOVE_CAMERA
}

data class WorkoutUiState(
    val makes: Int = 0,
    val misses: Int = 0,
    val totalShots: Int = 0,
    val percentage: String = "0%",
    val trackingStatus: TrackingStatus = TrackingStatus.TRACKING,
    val latestShot: ShotResult? = null
)
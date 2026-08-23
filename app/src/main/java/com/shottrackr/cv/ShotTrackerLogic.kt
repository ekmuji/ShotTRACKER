package com.shottrackr.cv

import android.os.SystemClock

class ShotTrackerLogic {

    // SwishAI Configuration
    private val SHOT_COOLDOWN_MS = 1500L
    private val BASKET_COOLDOWN_MS = 2000L

    // SwishAI Thresholds
    private val THRESHOLDS = mapOf(
        0 to 0.60f, // Ball
        1 to 0.25f, // Ball in Basket
        2 to 0.70f, // Player
        3 to 0.70f, // Basket
        4 to 0.77f  // Player Shooting
    )

    // State
    var shotsAttempted = 0
        private set
    var basketsMade = 0
        private set

    private var lastShotTime = 0L
    private var lastBasketTime = 0L

    fun processDetection(cls: Int, conf: Float): DetectionEvent? {
        val threshold = THRESHOLDS[cls] ?: 0.3f
        if (conf < threshold) return null

        val currentTime = SystemClock.elapsedRealtime()

        return when (cls) {
            4 -> registerShot(currentTime)
            1 -> registerBasket(currentTime)
            else -> null
        }
    }

    private fun registerShot(currentTime: Long): DetectionEvent? {
        if (currentTime - lastShotTime >= SHOT_COOLDOWN_MS) {
            shotsAttempted++
            lastShotTime = currentTime
            return DetectionEvent.SHOT_TAKEN
        }
        return null
    }

    private fun registerBasket(currentTime: Long): DetectionEvent? {
        if (currentTime - lastBasketTime >= BASKET_COOLDOWN_MS) {

            // Auto-add shot if a basket is detected but no shot was registered
            if (currentTime - lastShotTime > (SHOT_COOLDOWN_MS * 2)) {
                shotsAttempted++
                lastShotTime = currentTime
            }

            basketsMade++
            lastBasketTime = currentTime
            return DetectionEvent.BASKET_MADE
        }
        return null
    }
}

enum class DetectionEvent {
    SHOT_TAKEN, BASKET_MADE
}
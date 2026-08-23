package com.shottrackr.engine

class TrackerBridge {
    private var nativeHandle: Long = 0

    init {
        System.loadLibrary("tracker_engine")
    }

    fun create(fps: Float) {
        if (nativeHandle == 0L) nativeHandle = nativeCreate(fps)
    }

    fun destroy() {
        if (nativeHandle != 0L) {
            nativeDestroy(nativeHandle)
            nativeHandle = 0L
        }
    }

    fun resetSession() {
        if (nativeHandle != 0L) nativeResetSession(nativeHandle)
    }

    fun update(
        timestampMs: Long,
        ballDetected: Boolean, ballCx: Float, ballCy: Float, ballW: Float, ballH: Float, ballConf: Float,
        hoopDetected: Boolean, hoopCx: Float, hoopCy: Float, hoopW: Float, hoopH: Float, hoopConf: Float,
        ballInBasketDetected: Boolean,
        playerShootingDetected: Boolean
    ): FrameResult? {
        if (nativeHandle == 0L) return null
        return nativeUpdate(
            nativeHandle, timestampMs,
            ballDetected, ballCx, ballCy, ballW, ballH, ballConf,
            hoopDetected, hoopCx, hoopCy, hoopW, hoopH, hoopConf,
            ballInBasketDetected, playerShootingDetected
        )
    }

    private external fun nativeDestroy(handle: Long)
    private external fun nativeResetSession(handle: Long)

    private external fun nativeUpdate(
        handle: Long, timestampMs: Long,
        ballDetected: Boolean, ballCx: Float, ballCy: Float, ballW: Float, ballH: Float, ballConf: Float,
        hoopDetected: Boolean, hoopCx: Float, hoopCy: Float, hoopW: Float, hoopH: Float, hoopConf: Float,
        ballInBasketDetected: Boolean, playerShootingDetected: Boolean
    ): FrameResult

    companion object {
        @JvmStatic
        private external fun nativeCreate(fps: Float): Long
    }
}
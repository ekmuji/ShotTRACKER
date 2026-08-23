package com.shottrackr.ml

import android.content.Context
import android.graphics.Bitmap
import android.media.MediaMetadataRetriever
import android.net.Uri
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class VideoProcessor(private val context: Context, private val detector: ShotDetector) {

    suspend fun analyzeVideo(videoUri: Uri, onFrameProcessed: (List<Detection>) -> Unit) {
        withContext(Dispatchers.IO) {
            val retriever = MediaMetadataRetriever()
            try {
                retriever.setDataSource(context, videoUri)
                val durationStr = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)
                val durationMs = durationStr?.toLongOrNull() ?: 0L

                // Process at 15 frames per second to balance speed and accuracy
                val intervalMs = 1000L / 15L

                for (timeMs in 0 until durationMs step intervalMs) {
                    // Extract frame at specific microsecond
                    val frameBitmap: Bitmap? = retriever.getFrameAtTime(
                        timeMs * 1000,
                        MediaMetadataRetriever.OPTION_CLOSEST
                    )

                    frameBitmap?.let {
                        val detections = detector.detect(it)
                        onFrameProcessed(detections)
                    }
                }
            } finally {
                retriever.release()
            }
        }
    }
}
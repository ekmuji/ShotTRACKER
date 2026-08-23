package com.shottrackr.ml

import android.content.Context
import android.graphics.Bitmap
import org.tensorflow.lite.Interpreter
import org.tensorflow.lite.gpu.CompatibilityList
import org.tensorflow.lite.gpu.GpuDelegate
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.channels.FileChannel

data class Detection(
    val classId: Int, // 0=Ball, 1=BallInBasket, 2=Player, 3=Basket, 4=PlayerShooting
    val centerX: Float,
    val centerY: Float,
    val width: Float,
    val height: Float,
    val confidence: Float
)

class ShotDetector(private val context: Context) : AutoCloseable {

    private var interpreter: Interpreter? = null

    // Updated for YOLO11s 640x640 model
    private val inputSize = 640
    private val numClasses = 5
    private val numElements = 9 // 4 box coordinates + 5 classes
    private val numAnchors = 8400 // 640x640 grid generates 8400 predictions

    // SwishAI Thresholds
    private val thresholds = mapOf(
        0 to 0.50f, // Ball
        1 to 0.25f, // Ball in Basket
        2 to 0.70f, // Player
        3 to 0.25f, // Basket
        4 to 0.77f  // Player Shooting
    )

    init {
        val compatList = CompatibilityList()
        val options = Interpreter.Options().apply {
            if (compatList.isDelegateSupportedOnThisDevice) {
                addDelegate(GpuDelegate())
            } else {
                numThreads = 4
            }
        }
        interpreter = Interpreter(loadModelFile("shot_detector.tflite"), options)
    }

    private fun loadModelFile(modelName: String): ByteBuffer {
        val fileDescriptor = context.assets.openFd(modelName)
        val inputStream = FileInputStream(fileDescriptor.fileDescriptor)
        val fileChannel = inputStream.channel
        return fileChannel.map(FileChannel.MapMode.READ_ONLY, fileDescriptor.startOffset, fileDescriptor.declaredLength)
    }

    @Synchronized
    fun detect(bitmap: Bitmap): List<Detection> {
        if (interpreter == null) return emptyList()

        val resizedBitmap = Bitmap.createScaledBitmap(bitmap, inputSize, inputSize, false)
        val byteBuffer = convertBitmapToByteBuffer(resizedBitmap)

        // New Output Tensor Shape: [1, 9, 8400]
        val output = Array(1) { Array(numElements) { FloatArray(numAnchors) } }
        interpreter?.run(byteBuffer, output)

        return parseOutput(output[0], bitmap.width.toFloat(), bitmap.height.toFloat())
    }

    private fun convertBitmapToByteBuffer(bitmap: Bitmap): ByteBuffer {
        val byteBuffer = ByteBuffer.allocateDirect(4 * inputSize * inputSize * 3)
        byteBuffer.order(ByteOrder.nativeOrder())

        val intValues = IntArray(inputSize * inputSize)
        bitmap.getPixels(intValues, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)

        var pixel = 0
        for (i in 0 until inputSize) {
            for (j in 0 until inputSize) {
                val valInt = intValues[pixel++]
                byteBuffer.putFloat(((valInt shr 16) and 0xFF) / 255.0f)
                byteBuffer.putFloat(((valInt shr 8) and 0xFF) / 255.0f)
                byteBuffer.putFloat((valInt and 0xFF) / 255.0f)
            }
        }
        return byteBuffer
    }

    private fun parseOutput(output: Array<FloatArray>, origW: Float, origH: Float): List<Detection> {
        val detections = mutableListOf<Detection>()
        val scaleX = origW / inputSize
        val scaleY = origH / inputSize

        for (i in 0 until numAnchors) {
            // Loop through the 5 class probabilities starting at index 4
            for (c in 0 until numClasses) {
                val confidence = output[4 + c][i]
                val threshold = thresholds[c] ?: 0.3f

                if (confidence > threshold) {
                    detections.add(
                        Detection(
                            classId = c,
                            centerX = output[0][i] * scaleX,
                            centerY = output[1][i] * scaleY,
                            width = output[2][i] * scaleX,
                            height = output[3][i] * scaleY,
                            confidence = confidence
                        )
                    )
                }
            }
        }

        return filterBestDetections(detections)
    }

    private fun filterBestDetections(allDetections: List<Detection>): List<Detection> {
        val bestDetections = mutableListOf<Detection>()
        // Return only the highest confidence detection per class per frame
        for (i in 0 until numClasses) {
            val bestForClass = allDetections.filter { it.classId == i }.maxByOrNull { it.confidence }
            if (bestForClass != null) {
                bestDetections.add(bestForClass)
            }
        }
        return bestDetections
    }

    @Synchronized
    override fun close() {
        interpreter?.close()
        interpreter = null
    }
}
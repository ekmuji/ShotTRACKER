package com.shottrackr.camera

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Matrix
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import java.util.concurrent.Executors

class CameraService(private val context: Context) {

    fun interface FrameCallback {
        fun onFrame(bitmap: Bitmap, width: Int, height: Int, frameIndex: Int)
    }

    private inner class BitmapPool(w: Int, h: Int) {
        private val slots = Array(2) { Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888) }
        private var idx = 0
        fun acquire(): Bitmap = slots[idx].also { idx = (idx + 1) % 2 }
    }

    private val analysisExecutor = Executors.newSingleThreadExecutor()
    private var cameraProvider: ProcessCameraProvider? = null
    private var pool: BitmapPool? = null
    private var rotationMatrix: Matrix? = null
    private var lastRotation = Int.MIN_VALUE
    private var frameIndex = 0

    fun start(
        lifecycleOwner: LifecycleOwner,
        previewView: PreviewView,
        lensFacing: Int = CameraSelector.LENS_FACING_BACK,
        callback: FrameCallback,
    ) {
        ProcessCameraProvider.getInstance(context).also { future ->
            future.addListener({
                cameraProvider = future.get()
                bind(lifecycleOwner, previewView, lensFacing, callback)
            }, ContextCompat.getMainExecutor(context))
        }
    }

    fun stop() {
        cameraProvider?.unbindAll()
        frameIndex = 0
    }

    private fun bind(
        lifecycleOwner: LifecycleOwner,
        previewView: PreviewView,
        lensFacing: Int,
        callback: FrameCallback,
    ) {
        val selector = CameraSelector.Builder().requireLensFacing(lensFacing).build()
        val preview  = Preview.Builder().build()
            .also { it.setSurfaceProvider(previewView.surfaceProvider) }

        val analysis = ImageAnalysis.Builder()
            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
            .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
            .build()
            .also { useCase ->
                useCase.setAnalyzer(analysisExecutor) { proxy ->
                    processProxy(proxy, callback)
                }
            }

        cameraProvider?.unbindAll()
        cameraProvider?.bindToLifecycle(lifecycleOwner, selector, preview, analysis)
    }

    private fun processProxy(proxy: ImageProxy, callback: FrameCallback) {
        val w = proxy.width
        val h = proxy.height

        if (pool == null) pool = BitmapPool(w, h)

        val dest = pool!!.acquire()
        val plane = proxy.planes[0]
        dest.copyPixelsFromBuffer(plane.buffer)
        proxy.close()

        val degrees = proxy.imageInfo.rotationDegrees
        if (degrees != lastRotation) {
            rotationMatrix = if (degrees == 0) null
            else Matrix().apply { postRotate(degrees.toFloat()) }
            lastRotation = degrees
        }

        val rotated = rotationMatrix?.let {
            Bitmap.createBitmap(dest, 0, 0, dest.width, dest.height, it, false)
        } ?: dest

        callback.onFrame(rotated, rotated.width, rotated.height, frameIndex++)
    }
}
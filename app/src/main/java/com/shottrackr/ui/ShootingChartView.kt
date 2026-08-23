package com.shottrackr.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.util.AttributeSet
import android.view.View

class ShootingChartView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : View(context, attrs) {

    private val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color       = Color.parseColor("#FF6B35")
        style       = Paint.Style.STROKE
        strokeWidth = 3f
        strokeJoin  = Paint.Join.ROUND
        strokeCap   = Paint.Cap.ROUND
    }
    private val dotPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#FF6B35")
        style = Paint.Style.FILL
    }
    private val gridPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color       = Color.parseColor("#33FFFFFF")
        style       = Paint.Style.STROKE
        strokeWidth = 1f
    }
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color    = Color.parseColor("#AAFFFFFF")
        textSize = 28f
        textAlign = Paint.Align.RIGHT
    }

    private var points: List<Pair<Int, Float>> = emptyList()
    private val path = Path()

    private val padL = 60f; private val padR = 20f
    private val padT = 20f; private val padB = 40f

    fun setData(data: List<Pair<Int, Float>>) {
        points = data
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (points.size < 2) {
            drawEmptyMessage(canvas)
            return
        }

        val chartW = width  - padL - padR
        val chartH = height - padT - padB

        for (pct in listOf(25f, 50f, 75f, 100f)) {
            val y = padT + chartH * (1f - pct / 100f)
            canvas.drawLine(padL, y, padL + chartW, y, gridPaint)
            canvas.drawText("${pct.toInt()}%", padL - 4f, y + 10f, labelPaint)
        }

        path.reset()
        points.forEachIndexed { i, (_, pct) ->
            val x = padL + chartW * (i / (points.size - 1).toFloat())
            val y = padT + chartH * (1f - pct / 100f)
            if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        canvas.drawPath(path, linePaint)

        points.forEachIndexed { i, (_, pct) ->
            val x = padL + chartW * (i / (points.size - 1).toFloat())
            val y = padT + chartH * (1f - pct / 100f)
            canvas.drawCircle(x, y, 6f, dotPaint)
        }
    }

    private val emptyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color     = Color.parseColor("#55FFFFFF")
        textSize  = 36f
        textAlign = Paint.Align.CENTER
    }

    private fun drawEmptyMessage(canvas: Canvas) {
        canvas.drawText(
            "Complete sessions to see trend",
            width / 2f, height / 2f, emptyPaint
        )
    }
}
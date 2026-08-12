"""
Basketball Detector
===================
Detects a basketball in a video frame using two complementary strategies:

  1. HSV colour segmentation  — isolates the orange/tan colour range of a
     regulation basketball and finds the largest circular blob.
  2. Hough Circle Transform   — runs on a preprocessed grey frame to catch
     balls whose colour is out of the expected range (poor lighting, worn ball).

The two candidates are merged: if both fire and agree within a tolerance their
centroid/radius are averaged; otherwise the higher-confidence detection wins.
"""

from __future__ import annotations

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class BallDetection:
    """A single basketball detection in one frame."""
    x: float          # centre x (pixels)
    y: float          # centre y (pixels)
    radius: float     # approximate radius (pixels)
    confidence: float # 0.0 – 1.0
    method: str       # "color" | "hough" | "merged"

    @property
    def center(self) -> tuple[float, float]:
        return (self.x, self.y)

    @property
    def area(self) -> float:
        return np.pi * self.radius ** 2


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

class BallDetector:
    """Detect a basketball in a single BGR frame."""

    # --- HSV colour bounds for a regulation NBA/NCAA ball ----------------
    # Two ranges because orange wraps near H=0/180 in OpenCV's 0-179 scale.
    HSV_LOWER_1 = np.array([0,  100, 100], dtype=np.uint8)
    HSV_UPPER_1 = np.array([25, 255, 255], dtype=np.uint8)
    HSV_LOWER_2 = np.array([160, 100, 100], dtype=np.uint8)
    HSV_UPPER_2 = np.array([179, 255, 255], dtype=np.uint8)

    def __init__(
        self,
        min_radius: int = 10,
        max_radius: int = 80,
        min_circularity: float = 0.70,
        hough_dp: float = 1.2,
        hough_min_dist: int = 50,
        debug: bool = False,
    ):
        self.min_radius = min_radius
        self.max_radius = max_radius
        self.min_circularity = min_circularity
        self.hough_dp = hough_dp
        self.hough_min_dist = hough_min_dist
        self.debug = debug

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, frame: np.ndarray) -> Optional[BallDetection]:
        """Return the best BallDetection for *frame*, or None."""
        color_det = self._detect_by_color(frame)
        hough_det = self._detect_by_hough(frame)
        return self._merge(color_det, hough_det)

    # ------------------------------------------------------------------
    # Strategy 1 – colour segmentation
    # ------------------------------------------------------------------

    def _detect_by_color(self, frame: np.ndarray) -> Optional[BallDetection]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, self.HSV_LOWER_1, self.HSV_UPPER_1)
        mask2 = cv2.inRange(hsv, self.HSV_LOWER_2, self.HSV_UPPER_2)
        mask = cv2.bitwise_or(mask1, mask2)

        # Morphological clean-up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        best: Optional[BallDetection] = None
        best_score = -1.0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < np.pi * self.min_radius ** 2:
                continue
            perimeter = cv2.arcLength(cnt, closed=True)
            if perimeter == 0:
                continue
            circularity = 4 * np.pi * area / (perimeter ** 2)
            if circularity < self.min_circularity:
                continue

            (cx, cy), radius = cv2.minEnclosingCircle(cnt)
            if not (self.min_radius <= radius <= self.max_radius):
                continue

            # Score = circularity * normalised area (prefer bigger balls)
            score = circularity * min(area / (np.pi * self.max_radius ** 2), 1.0)
            if score > best_score:
                best_score = score
                best = BallDetection(
                    x=float(cx), y=float(cy), radius=float(radius),
                    confidence=float(np.clip(score, 0, 1)),
                    method="color",
                )

        return best

    # ------------------------------------------------------------------
    # Strategy 2 – Hough circles
    # ------------------------------------------------------------------

    def _detect_by_hough(self, frame: np.ndarray) -> Optional[BallDetection]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)

        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=self.hough_dp,
            minDist=self.hough_min_dist,
            param1=100,
            param2=30,
            minRadius=self.min_radius,
            maxRadius=self.max_radius,
        )
        if circles is None:
            return None

        circles = np.round(circles[0]).astype(int)
        # Pick the circle with the most orange pixels inside it
        best: Optional[BallDetection] = None
        best_orange = -1

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, self.HSV_LOWER_1, self.HSV_UPPER_1)
        mask2 = cv2.inRange(hsv, self.HSV_LOWER_2, self.HSV_UPPER_2)
        orange_mask = cv2.bitwise_or(mask1, mask2)

        h, w = frame.shape[:2]
        for (cx, cy, r) in circles:
            roi_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.circle(roi_mask, (cx, cy), r, 255, -1)
            orange_pixels = cv2.countNonZero(cv2.bitwise_and(orange_mask, roi_mask))
            total_pixels   = cv2.countNonZero(roi_mask)
            orange_ratio   = orange_pixels / max(total_pixels, 1)

            if orange_pixels > best_orange:
                best_orange = orange_pixels
                confidence  = float(np.clip(0.4 + orange_ratio * 0.6, 0, 1))
                best = BallDetection(
                    x=float(cx), y=float(cy), radius=float(r),
                    confidence=confidence, method="hough",
                )

        return best

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    def _merge(
        self,
        color_det: Optional[BallDetection],
        hough_det: Optional[BallDetection],
    ) -> Optional[BallDetection]:
        if color_det is None and hough_det is None:
            return None
        if color_det is None:
            return hough_det
        if hough_det is None:
            return color_det

        dist = np.hypot(color_det.x - hough_det.x, color_det.y - hough_det.y)
        tolerance = (color_det.radius + hough_det.radius) * 0.6

        if dist < tolerance:
            # Weighted average by confidence
            w1, w2 = color_det.confidence, hough_det.confidence
            total = w1 + w2
            return BallDetection(
                x      = (color_det.x      * w1 + hough_det.x      * w2) / total,
                y      = (color_det.y      * w1 + hough_det.y      * w2) / total,
                radius = (color_det.radius * w1 + hough_det.radius * w2) / total,
                confidence = min(1.0, (w1 + w2) / 1.5),
                method = "merged",
            )

        # Detections disagree — trust the more confident one
        return color_det if color_det.confidence >= hough_det.confidence else hough_det


# ---------------------------------------------------------------------------
# Visualisation helper
# ---------------------------------------------------------------------------

def draw_ball(frame: np.ndarray, det: Optional[BallDetection]) -> np.ndarray:
    """Draw detection overlay onto *frame* (in-place copy)."""
    out = frame.copy()
    if det is None:
        return out
    cx, cy, r = int(det.x), int(det.y), int(det.radius)
    colour = (0, 165, 255)  # BGR orange
    cv2.circle(out, (cx, cy), r, colour, 2)
    cv2.circle(out, (cx, cy), 3, colour, -1)
    label = f"{det.method} {det.confidence:.2f}"
    cv2.putText(out, label, (cx - r, cy - r - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, colour, 1, cv2.LINE_AA)
    return out

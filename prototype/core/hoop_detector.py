"""
Hoop Detector
=============
Detects a basketball hoop rim in a frame.

The rim appears as an orange ellipse (viewed at an angle) or circle (straight-on).
Detection pipeline:

  1. Edge detection on an HSV-filtered mask to isolate orange structure.
  2. Hough Circle / Ellipse fitting on the edge image.
  3. Geometric filter: the hoop must be wider than it is tall (foreshortening),
     must be at a plausible height in the frame, and must be larger than the ball.

Because the hoop is stationary (fixed to a pole), the detector also maintains a
*stabilised* position via exponential moving average so that brief occlusions
don't cause jitter in downstream logic.
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
class HoopDetection:
    """A single hoop detection in one frame."""
    x: float          # centre x of the rim
    y: float          # centre y of the rim
    width: float      # horizontal diameter (pixels) — wider due to foreshortening
    height: float     # vertical diameter  (pixels) — smaller
    confidence: float # 0.0 – 1.0

    @property
    def center(self) -> tuple[float, float]:
        return (self.x, self.y)

    @property
    def radius(self) -> float:
        """Effective radius (average of semi-axes)."""
        return (self.width + self.height) / 4.0

    @property
    def inner_zone(self) -> tuple[float, float, float, float]:
        """Bounding box (x1,y1,x2,y2) of the hoop opening — used for made-shot detection."""
        hw, hh = self.width / 2, self.height / 2
        return (self.x - hw, self.y - hh, self.x + hw, self.y + hh)


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

class HoopDetector:
    """Detect the basketball hoop rim in a single BGR frame."""

    # HSV range for the orange metallic rim / backboard highlight
    HSV_LOWER = np.array([5, 60, 60],  dtype=np.uint8)
    HSV_UPPER = np.array([30, 255, 255], dtype=np.uint8)

    # EMA smoothing factor for the stabilised position (0 = frozen, 1 = no smoothing)
    ALPHA = 0.25

    def __init__(
        self,
        min_radius: int = 25,
        max_radius: int = 200,
        aspect_ratio_range: tuple[float, float] = (1.1, 4.0),
        min_frame_height_frac: float = 0.10,
        max_frame_height_frac: float = 0.75,
        debug: bool = False,
    ):
        self.min_radius = min_radius
        self.max_radius = max_radius
        self.aspect_lo, self.aspect_hi = aspect_ratio_range
        self.min_frac = min_frame_height_frac
        self.max_frac = max_frame_height_frac
        self.debug = debug

        # Stabilised (EMA) hoop position
        self._stable: Optional[HoopDetection] = None
        self._frames_since_seen: int = 0
        self._MAX_INVISIBLE = 30   # frames before we forget the hoop

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, frame: np.ndarray, use_stable: bool = True) -> Optional[HoopDetection]:
        """
        Detect the hoop in *frame*.

        If *use_stable* is True and we have a recent stabilised position, that
        is blended with the raw detection (or returned alone on a miss).
        """
        raw = self._raw_detect(frame)
        if raw is not None:
            self._frames_since_seen = 0
            if use_stable and self._stable is not None:
                self._stable = self._ema(self._stable, raw)
            else:
                self._stable = raw
        else:
            self._frames_since_seen += 1
            if self._frames_since_seen > self._MAX_INVISIBLE:
                self._stable = None   # stale — force re-detection

        return self._stable

    def reset(self) -> None:
        self._stable = None
        self._frames_since_seen = 0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _raw_detect(self, frame: np.ndarray) -> Optional[HoopDetection]:
        h, w = frame.shape[:2]
        min_y = int(h * self.min_frac)
        max_y = int(h * self.max_frac)

        # --- Build edge image from orange mask ---------------------------
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.HSV_LOWER, self.HSV_UPPER)

        # Also include white/grey backboard area to help detect rim against board
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, bright_mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        mask = cv2.bitwise_or(mask, bright_mask)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.dilate(mask, kernel, iterations=1)
        edges = cv2.Canny(mask, 50, 150)

        # Restrict to plausible vertical region
        search_mask = np.zeros_like(edges)
        search_mask[min_y:max_y, :] = 255
        edges = cv2.bitwise_and(edges, search_mask)

        # --- Hough circles on edge image ---------------------------------
        # We intentionally use a large dp to be tolerant of the elliptical rim
        circles = cv2.HoughCircles(
            edges,
            cv2.HOUGH_GRADIENT,
            dp=1.5,
            minDist=w // 4,
            param1=50,
            param2=20,
            minRadius=self.min_radius,
            maxRadius=self.max_radius,
        )

        candidates: list[HoopDetection] = []

        if circles is not None:
            for (cx, cy, r) in np.round(circles[0]).astype(int):
                # The circle finder gives us an isotropic estimate; the real rim
                # is foreshortened, so treat vertical radius as ~50–80% of horizontal.
                est_width  = float(r * 2)
                est_height = float(r * 2 * 0.6)   # typical foreshortening estimate
                if not (min_y <= cy <= max_y):
                    continue
                candidates.append(HoopDetection(
                    x=float(cx), y=float(cy),
                    width=est_width, height=est_height,
                    confidence=0.6,
                ))

        # --- Contour-based fallback --------------------------------------
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if len(cnt) < 5:
                continue
            area = cv2.contourArea(cnt)
            if area < np.pi * self.min_radius ** 2:
                continue

            # Fit ellipse
            try:
                (cx, cy), (mw, mh), angle = cv2.fitEllipse(cnt)
            except cv2.error:
                continue

            if not (min_y <= cy <= max_y):
                continue
            if mw < mh:   # ensure mw is the major axis
                mw, mh = mh, mw
            aspect = mw / max(mh, 1e-3)
            if not (self.aspect_lo <= aspect <= self.aspect_hi):
                continue
            r = mw / 2
            if not (self.min_radius <= r <= self.max_radius):
                continue

            # Score by how ellipse-like the contour is
            ellipse_area = np.pi * (mw / 2) * (mh / 2)
            fill = min(area / max(ellipse_area, 1), 1.0)
            confidence = float(np.clip(0.5 + fill * 0.5, 0, 1))

            candidates.append(HoopDetection(
                x=float(cx), y=float(cy),
                width=float(mw), height=float(mh),
                confidence=confidence,
            ))

        if not candidates:
            return None

        return max(candidates, key=lambda d: d.confidence)

    def _ema(self, prev: HoopDetection, curr: HoopDetection) -> HoopDetection:
        a = self.ALPHA
        return HoopDetection(
            x          = prev.x      * (1 - a) + curr.x      * a,
            y          = prev.y      * (1 - a) + curr.y      * a,
            width      = prev.width  * (1 - a) + curr.width  * a,
            height     = prev.height * (1 - a) + curr.height * a,
            confidence = max(prev.confidence, curr.confidence),
        )


# ---------------------------------------------------------------------------
# Visualisation helper
# ---------------------------------------------------------------------------

def draw_hoop(frame: np.ndarray, det: Optional[HoopDetection]) -> np.ndarray:
    out = frame.copy()
    if det is None:
        return out
    cx, cy = int(det.x), int(det.y)
    rw, rh = int(det.width / 2), int(det.height / 2)
    colour = (0, 255, 0)   # green
    cv2.ellipse(out, (cx, cy), (rw, rh), 0, 0, 360, colour, 2)
    cv2.circle(out, (cx, cy), 4, colour, -1)
    label = f"hoop {det.confidence:.2f}"
    cv2.putText(out, label, (cx - rw, cy - rh - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, colour, 1, cv2.LINE_AA)
    return out

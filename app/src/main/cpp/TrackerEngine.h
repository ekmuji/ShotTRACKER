#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "KalmanTracker.h"

#ifdef __cplusplus
extern "C" {
#endif

// The struct we will pass back to Kotlin
typedef struct {
    int totalMakes;
    int totalShots;
    bool justMadeShot;
    bool justMissedShot;
    bool hoopTracked;
    bool ballTracked;
    float ballX, ballY, ballW, ballH;
    float hoopX, hoopY, hoopW, hoopH;
} FrameResult;

typedef struct TrackerEngine TrackerEngine;

TrackerEngine* tracker_create(float fps);
void tracker_destroy(TrackerEngine* engine);
void tracker_reset_session(TrackerEngine* engine);

FrameResult tracker_update(
    TrackerEngine* engine, long timestampMs,
    bool ballDet, float bx, float by, float bw, float bh, float bConf,
    bool hoopDet, float hx, float hy, float hw, float hh, float hConf,
    bool ballInBasketDet, bool playerShootingDet
);

#ifdef __cplusplus
}
#endif
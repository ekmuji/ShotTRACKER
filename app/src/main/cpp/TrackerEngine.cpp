#include "TrackerEngine.h"
#include "KalmanTracker.h"
#include <android/log.h>

#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, "ShotTrackr-Engine", __VA_ARGS__)

const long SHOT_COOLDOWN_MS = 1500;
const long BASKET_COOLDOWN_MS = 2000;

struct TrackerEngine {
    KalmanTracker ballTracker;

    long last_shot_time;
    long last_basket_time;
    int makes;
    int attempts;

    bool hoopLocked;
    BoundingBox currentHoop;
};

extern "C" {

TrackerEngine* tracker_create(float fps) {
    TrackerEngine* engine = new TrackerEngine();
    tracker_reset_session(engine);
    return engine;
}

void tracker_destroy(TrackerEngine* engine) {
    if (engine) delete engine;
}

void tracker_reset_session(TrackerEngine* engine) {
    if (engine) {
        engine->ballTracker = KalmanTracker();
        engine->makes = 0;
        engine->attempts = 0;
        engine->last_shot_time = -SHOT_COOLDOWN_MS;
        engine->last_basket_time = -BASKET_COOLDOWN_MS;
        engine->hoopLocked = false;
    }
}

FrameResult tracker_update(
    TrackerEngine* engine, long timestampMs,
    bool ballDet, float bx, float by, float bw, float bh, float bConf,
    bool hoopDet, float hx, float hy, float hw, float hh, float hConf,
    bool ballInBasketDet, bool playerShootingDet)
{
    FrameResult result = {0};
    if (!engine) return result;

    result.justMadeShot = false;
    result.justMissedShot = false;

    // 1. Maintain Hoop Tracking
    if (hoopDet && hConf > 0.45f) {
        engine->currentHoop = {hx, hy, hw, hh};
        engine->hoopLocked = true;
    }
    result.hoopTracked = engine->hoopLocked;

    // 2. Kalman Filter for UI Ball Drawing
    if (ballDet) {
        engine->ballTracker.update(bx, by);
    }
    BoundingBox predictedBall = engine->ballTracker.predict();
    result.ballX = ballDet ? bx : predictedBall.cx;
    result.ballY = ballDet ? by : predictedBall.cy;
    result.ballW = bw;
    result.ballH = bh;

    // 3. SwishAI Physics Rule: Shot Detected
    if (playerShootingDet) {
        if ((timestampMs - engine->last_shot_time) >= SHOT_COOLDOWN_MS) {
            engine->attempts++;
            engine->last_shot_time = timestampMs;
            LOGI("SHOT REGISTERED. Total: %d", engine->attempts);
        }
    }

    // 4. SwishAI Physics Rule: Basket Detected
    if (ballInBasketDet) {
        if ((timestampMs - engine->last_basket_time) >= BASKET_COOLDOWN_MS) {
            // Auto-add shot if AI missed the player shooting
            if ((timestampMs - engine->last_shot_time) > (SHOT_COOLDOWN_MS * 2)) {
                engine->attempts++;
                engine->last_shot_time = timestampMs;
            }
            engine->makes++;
            engine->last_basket_time = timestampMs;
            result.justMadeShot = true;
            LOGI("BASKET REGISTERED. Total: %d", engine->makes);
        }
    }

    result.totalMakes = engine->makes;
    result.totalShots = engine->attempts;

    result.ballTracked = ballDet; // Or check if Kalman is active
        if (hoopDet) {
            result.hoopX = hx;
            result.hoopY = hy;
            result.hoopW = hw;
            result.hoopH = hh;
        } else {
            result.hoopX = engine->currentHoop.x;
            result.hoopY = engine->currentHoop.y;
            result.hoopW = engine->currentHoop.width;
            result.hoopH = engine->currentHoop.height;
        }

        return result;

    return result;
}

} // extern "C"
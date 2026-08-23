#include <jni.h>
#include "TrackerEngine.h"

static jobject toKotlinFrameResult(JNIEnv* env, const FrameResult& r) {
    jclass clazz = env->FindClass("com/shottrackr/engine/FrameResult");
    if (!clazz) return nullptr;

    // Signature for (Int, Int, Boolean, Boolean, Boolean, Boolean, Floatx8)
        jmethodID ctor = env->GetMethodID(clazz, "<init>", "(IIZZZZFFFFFFFF)V");
        if (!ctor) return nullptr;

        return env->NewObject(clazz, ctor,
            (jint)r.totalMakes, (jint)r.totalShots,
            (jboolean)r.justMadeShot, (jboolean)r.justMissedShot,
            (jboolean)r.hoopTracked, (jboolean)r.ballTracked,
            (jfloat)r.ballX, (jfloat)r.ballY, (jfloat)r.ballW, (jfloat)r.ballH,
            (jfloat)r.hoopX, (jfloat)r.hoopY, (jfloat)r.hoopW, (jfloat)r.hoopH
        );
}

extern "C" JNIEXPORT jlong JNICALL
Java_com_shottrackr_engine_TrackerBridge_nativeCreate(JNIEnv*, jobject, jfloat fps) {
    return reinterpret_cast<jlong>(tracker_create(fps));
}

extern "C" JNIEXPORT void JNICALL
Java_com_shottrackr_engine_TrackerBridge_nativeDestroy(JNIEnv*, jobject, jlong handle) {
    tracker_destroy(reinterpret_cast<TrackerEngine*>(handle));
}

extern "C" JNIEXPORT void JNICALL
Java_com_shottrackr_engine_TrackerBridge_nativeResetSession(JNIEnv*, jobject, jlong handle) {
    tracker_reset_session(reinterpret_cast<TrackerEngine*>(handle));
}

extern "C" JNIEXPORT jobject JNICALL
Java_com_shottrackr_engine_TrackerBridge_nativeUpdate(
        JNIEnv* env, jobject,
        jlong handle, jlong timestampMs,
        jboolean ballDetected, jfloat ballCx, jfloat ballCy, jfloat ballW, jfloat ballH, jfloat ballConf,
        jboolean hoopDetected, jfloat hoopCx, jfloat hoopCy, jfloat hoopW, jfloat hoopH, jfloat hoopConf,
        jboolean ballInBasketDetected, jboolean playerShootingDetected) {

    auto* engine = reinterpret_cast<TrackerEngine*>(handle);

    FrameResult result = tracker_update(
        engine, timestampMs,
        ballDetected, ballCx, ballCy, ballW, ballH, ballConf,
        hoopDetected, hoopCx, hoopCy, hoopW, hoopH, hoopConf,
        ballInBasketDetected, playerShootingDetected
    );

    return toKotlinFrameResult(env, result);
}
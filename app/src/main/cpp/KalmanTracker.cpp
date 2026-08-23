#include "KalmanTracker.h"

KalmanTracker::KalmanTracker() : initialized(false), ticks(0) {
    // 4 state variables (x, y, dx, dy), 2 measurements (x, y)
    kf = cv::KalmanFilter(4, 2, 0);
    state = cv::Mat(4, 1, CV_32F);
    measurement = cv::Mat::zeros(2, 1, CV_32F);

    // Transition Matrix (F)
    kf.transitionMatrix = (cv::Mat_<float>(4, 4) <<
        1, 0, 1, 0,
        0, 1, 0, 1,
        0, 0, 1, 0,
        0, 0, 0, 1);

    // Measurement Matrix (H)
    kf.measurementMatrix = (cv::Mat_<float>(2, 4) <<
        1, 0, 0, 0,
        0, 1, 0, 0);

    // Process Noise Covariance (Q)
    cv::setIdentity(kf.processNoiseCov, cv::Scalar::all(1e-4));

    // Measurement Noise Covariance (R)
    cv::setIdentity(kf.measurementNoiseCov, cv::Scalar::all(1e-1));

    // Error Covariance (P)
    cv::setIdentity(kf.errorCovPost, cv::Scalar::all(.1));
}

void KalmanTracker::init(float x, float y) {
    kf.statePost.at<float>(0) = x;
    kf.statePost.at<float>(1) = y;
    kf.statePost.at<float>(2) = 0;
    kf.statePost.at<float>(3) = 0;
    initialized = true;
}

BoundingBox KalmanTracker::predict() {
    if (!initialized) return {0, 0, 0, 0};

    cv::Mat prediction = kf.predict();

    BoundingBox box;
    box.cx = prediction.at<float>(0);
    box.cy = prediction.at<float>(1);
    box.width = 0;  // Handled by original YOLO width if needed
    box.height = 0;

    ticks++;
    return box;
}

void KalmanTracker::update(float x, float y) {
    if (!initialized) {
        init(x, y);
        return;
    }
    measurement.at<float>(0) = x;
    measurement.at<float>(1) = y;
    kf.correct(measurement);
    ticks = 0; // Reset lost-tracking ticks
}

bool KalmanTracker::isTracking() {
    // If we haven't seen the ball in 15 frames, kill the track
    return initialized && ticks < 15;
}
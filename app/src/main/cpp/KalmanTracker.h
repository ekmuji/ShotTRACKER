#pragma once
#include <opencv2/video/tracking.hpp>
#include <vector>

struct BoundingBox {
    union { float x; float cx; };
    union { float y; float cy; };
    float width;
    float height;
};

class KalmanTracker {
private:
    cv::KalmanFilter kf;
    cv::Mat state;
    cv::Mat measurement;
    int ticks;
    bool initialized;

public:
    KalmanTracker();
    void init(float x, float y);
    BoundingBox predict();
    void update(float x, float y);
    bool isTracking();
};
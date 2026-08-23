cmake_minimum_required(VERSION 3.22.1)
project("tracker_engine")

# Define where to find the pre-compiled Android OpenCV SDK
set(OpenCV_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../../../../opencv/sdk/native/jni)
find_package(OpenCV REQUIRED)

# Define the shared library and the source files it uses
add_library(
        tracker_engine
        SHARED
        TrackerBridge_jni.cpp
        TrackerEngine.cpp
        KalmanTracker.cpp
)

# Link OpenCV and Android's native logging & JNI libraries
target_link_libraries(
        tracker_engine
        ${OpenCV_LIBS}
        android
        log
)
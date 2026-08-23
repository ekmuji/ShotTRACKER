# TensorFlow Lite — keep all model-related classes
-keep class org.tensorflow.** { *; }
-keep class org.tensorflow.lite.** { *; }
-keepclassmembers class org.tensorflow.lite.** { *; }

# Room — generated implementations must survive shrinking
-keep class * extends androidx.room.RoomDatabase
-keep @androidx.room.Entity class *
-keepclassmembers @androidx.room.Entity class * { *; }
-keep @androidx.room.Dao interface *
-keepclassmembers @androidx.room.Dao interface * { *; }

# Hilt — generated components
-keep class dagger.hilt.** { *; }
-keep class javax.inject.** { *; }
-keepclasseswithmembernames class * { @javax.inject.Inject <fields>; }
-keepclasseswithmembernames class * { @javax.inject.Inject <methods>; }

# TrackerBridge — JNI native methods must not be renamed
-keepclasseswithmembernames class com.shottrackr.engine.TrackerBridge {
    native <methods>;
}
-keepclasseswithmembernames class com.shottrackr.engine.TrackerBridge$Companion {
    native <methods>;
}

# Kotlin data classes used as LiveData values (reflection-safe)
-keepclassmembers class com.shottrackr.engine.FrameResult { *; }
-keepclassmembers class com.shottrackr.BallDetectionInput { *; }
-keepclassmembers class com.shottrackr.HoopDetectionInput { *; }

# Kotlin coroutines
-keepnames class kotlinx.coroutines.internal.MainDispatcherFactory {}
-keepnames class kotlinx.coroutines.CoroutineExceptionHandler {}
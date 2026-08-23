package com.shottrackr

import android.content.Context
import androidx.room.Room
import com.shottrackr.camera.CameraService
import com.shottrackr.data.AppDatabase
import com.shottrackr.data.WorkoutDao
import com.shottrackr.data.WorkoutRepository
import com.shottrackr.engine.TrackerBridge
import com.shottrackr.ml.ShotDetector
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides @Singleton
    fun provideDatabase(@ApplicationContext ctx: Context): AppDatabase =
        Room.databaseBuilder(ctx, AppDatabase::class.java, AppDatabase.NAME)
            .build()

    @Provides @Singleton
    fun provideDao(db: AppDatabase): WorkoutDao = db.workoutDao()

    @Provides @Singleton
    fun provideRepository(dao: WorkoutDao): WorkoutRepository = WorkoutRepository(dao)

    @Provides @Singleton
    fun provideCameraService(@ApplicationContext ctx: Context): CameraService =
        CameraService(ctx)
}

@Module
@InstallIn(SingletonComponent::class)
object EngineModule {

    @Provides @Singleton
    fun provideShotDetector(@ApplicationContext ctx: Context): ShotDetector =
        ShotDetector(ctx)

    @Provides @Singleton
    fun provideTrackerBridge(): TrackerBridge {
        val bridge = TrackerBridge()
        bridge.create(fps = 30f)
        return bridge
    }
}
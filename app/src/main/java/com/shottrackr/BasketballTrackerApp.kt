package com.shottrackr

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

/**
 * The base Application class.
 * @HiltAndroidApp triggers Hilt's code generation, including a base class
 * for your application that serves as the application-level dependency container.
 */
@HiltAndroidApp
class BasketballTrackerApp : Application()
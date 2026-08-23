package com.shottrackr.data

import androidx.room.*
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext

enum class DbShotResult { MADE, MISSED }

data class WorkoutSession(
    val id:          Long  = 0L,
    val startTimeMs:   Long,
    val endTimeMs:     Long? = null,
    val totalAttempts: Int   = 0,
    val totalMakes:    Int   = 0,
    val shootingPct:   Float = 0f,
    val hotStreakPeak: Int   = 0,
)

data class ShotEvent(
    val id:          Long = 0L,
    val sessionId:   Long,
    val result: DbShotResult,
    val timestampMs: Long,
    val confidence:  Float,
)

data class LifetimeStats(
    val shootingPct: Float,
    val bestStreak:  Int,
)

@Entity(tableName = "sessions")
data class SessionEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0L,
    val startTimeMs:   Long,
    val endTimeMs:     Long? = null,
    val totalAttempts: Int   = 0,
    val totalMakes:    Int   = 0,
    val shootingPct:   Float = 0f,
    val hotStreakPeak: Int   = 0,
) {
    fun toDomain() = WorkoutSession(id, startTimeMs, endTimeMs,
        totalAttempts, totalMakes, shootingPct, hotStreakPeak)

    companion object {
        fun from(d: WorkoutSession) = SessionEntity(d.id, d.startTimeMs, d.endTimeMs,
            d.totalAttempts, d.totalMakes, d.shootingPct, d.hotStreakPeak)
    }
}

@Entity(
    tableName    = "shots",
    foreignKeys  = [ForeignKey(
        entity        = SessionEntity::class,
        parentColumns = ["id"],
        childColumns  = ["sessionId"],
        onDelete      = ForeignKey.CASCADE,
    )],
    indices = [Index("sessionId")],
)
data class ShotEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0L,
    val sessionId:   Long,
    val result:      String,
    val timestampMs: Long,
    val confidence:  Float,
) {
    fun toDomain() = ShotEvent(id, sessionId,
        DbShotResult.valueOf(result), timestampMs, confidence)
}

@Dao
interface WorkoutDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertSession(s: SessionEntity): Long

    @Query("SELECT * FROM sessions ORDER BY startTimeMs DESC")
    fun sessionsFlow(): Flow<List<SessionEntity>>

    @Query("SELECT * FROM sessions ORDER BY startTimeMs DESC")
    suspend fun allSessions(): List<SessionEntity>

    @Query("SELECT * FROM sessions WHERE id = :id")
    suspend fun sessionById(id: Long): SessionEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertShot(s: ShotEntity): Long

    @Query("SELECT * FROM shots WHERE sessionId = :id ORDER BY timestampMs ASC")
    suspend fun shotsForSession(id: Long): List<ShotEntity>

    @Query("SELECT AVG(shootingPct) FROM sessions WHERE endTimeMs IS NOT NULL")
    suspend fun lifetimePct(): Float?

    @Query("SELECT MAX(hotStreakPeak) FROM sessions")
    suspend fun bestStreak(): Int?
}

@Database(entities = [SessionEntity::class, ShotEntity::class], version = 1, exportSchema = true)
abstract class AppDatabase : RoomDatabase() {
    abstract fun workoutDao(): WorkoutDao
    companion object { const val NAME = "basketball_tracker.db" }
}

class WorkoutRepository(
    private val dao: WorkoutDao,
    private val io:  CoroutineDispatcher = Dispatchers.IO,
) {
    val sessions: Flow<List<WorkoutSession>>
        get() = dao.sessionsFlow().map { it.map(SessionEntity::toDomain) }

    suspend fun allSessions(): List<WorkoutSession> = withContext(io) {
        dao.allSessions().map(SessionEntity::toDomain)
    }

    suspend fun saveSession(session: WorkoutSession): Long = withContext(io) {
        dao.upsertSession(SessionEntity.from(session))
    }

    suspend fun saveShot(shot: ShotEvent): Long = withContext(io) {
        dao.insertShot(
            ShotEntity(
            sessionId   = shot.sessionId,
            result      = shot.result.name,
            timestampMs = shot.timestampMs,
            confidence  = shot.confidence,
        )
        )
    }

    suspend fun shotsForSession(id: Long): List<ShotEvent> = withContext(io) {
        dao.shotsForSession(id).map(ShotEntity::toDomain)
    }

    suspend fun lifetimeStats(): LifetimeStats = withContext(io) {
        LifetimeStats(
            shootingPct = dao.lifetimePct() ?: 0f,
            bestStreak  = dao.bestStreak()  ?: 0,
        )
    }
}
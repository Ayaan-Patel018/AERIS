package com.aeris.mobile.service

import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.ServiceCompat
import com.aeris.mobile.core.filter.BaroFilter
import com.aeris.mobile.core.filter.EsEkf
import com.aeris.mobile.core.filter.MotionMode
import com.aeris.mobile.core.filter.MotionModeClassifier
import com.aeris.mobile.core.filter.ZuptDetector
import com.aeris.mobile.core.sensor.BaroCollector
import com.aeris.mobile.core.sensor.GnssCollector
import com.aeris.mobile.core.sensor.ImuCollector
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlin.math.sqrt

/**
 * Foreground service that runs the sensor-fusion pipeline.
 *
 * ## Lifecycle
 * - Started via [Context.startForegroundService] when tracking begins.
 * - Shows a persistent low-priority notification (see [TrackingNotificationHelper]).
 * - Uses [START_STICKY] so the OS restarts it if killed under memory pressure;
 *   on restart the last known position is recovered from SharedPreferences.
 * - Stopped via [stopSelf] or [Context.stopService] when the user ends tracking.
 *
 * ## Data flow
 * ```
 * ImuCollector ──→ EsEkf.predict() ──→ TrackingState ──→ UI (StateFlow)
 * GnssCollector ─→ EsEkf.updateGnss()
 * BaroCollector ─→ BaroFilter → EsEkf.updateBaroAltitude()
 *                  ZuptDetector → EsEkf.updateZupt() / updateZaru()
 *                  NHC → EsEkf.updateNhc()
 * ```
 */
class TrackingService : Service() {

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var imuJob: Job? = null
    private var gnssJob: Job? = null
    private var baroJob: Job? = null

    // ── Filter + auxiliary ──────────────────────────────────────────────
    private val ekf = EsEkf()
    private val baroFilter = BaroFilter()
    private val accelMagnitudes = mutableListOf<Double>()
    private val gyroMagnitudes = mutableListOf<Double>()

    // ── State exposed to UI ─────────────────────────────────────────────
    private val _trackingState = MutableStateFlow(TrackingState())

    // ── IMU tracking ────────────────────────────────────────────────────
    private var lastAccel = doubleArrayOf(0.0, 0.0, 0.0)
    private var lastGyro = doubleArrayOf(0.0, 0.0, 0.0)

    // ── GNSS bookkeeping ────────────────────────────────────────────────
    private var lastGnssTimeMillis: Long = 0L
    private var gnssOutageStartMillis: Long = 0L
    private var cumulativeGnssOutageSec: Long = 0L

    // ── Route / stats ───────────────────────────────────────────────────
    private val routePoints = mutableListOf<RoutePoint>()
    private var totalDistance = 0.0
    private var prevLat = 0.0
    private var prevLon = 0.0
    private var confidenceSum = 0.0
    private var confidenceCount = 0
    private var maxDrift = 0.0

    // ── Baro delta tracking ─────────────────────────────────────────────
    private var lastBaroNedDown: Double = 0.0

    // ── GNSS speed / bearing ────────────────────────────────────────────
    private var lastGnssSpeedKmh: Float = 0f
    private var lastGnssBearing: Float = 0f

    // ── Prefs for crash recovery ────────────────────────────────────────
    private val prefs: SharedPreferences by lazy {
        getSharedPreferences("aeris_tracking", Context.MODE_PRIVATE)
    }

    // ── Public companion for UI access ──────────────────────────────────

    companion object {
        /** Singleton state flow — the UI observes this. */
        private val _sharedState = MutableStateFlow(TrackingState())
        val trackingState: StateFlow<TrackingState> = _sharedState.asStateFlow()

        /** Convenience flag checked by the UI before binding. */
        @Volatile
        var isRunning: Boolean = false
            private set
    }

    // ── Service lifecycle ───────────────────────────────────────────────

    override fun onCreate() {
        super.onCreate()
        TrackingNotificationHelper.createChannel(this)
        recoverState()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val notification = TrackingNotificationHelper.buildNotification(
            this, "Aeris — starting…"
        )

        ServiceCompat.startForeground(
            this,
            TrackingNotificationHelper.NOTIFICATION_ID,
            notification,
            ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION,
        )

        isRunning = true
        startSensorCollection()

        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        isRunning = false
        serviceScope.cancel()
        persistState()
        super.onDestroy()
    }

    // ── Sensor collection ───────────────────────────────────────────────

    private fun startSensorCollection() {
        val imuCollector = ImuCollector(this)
        val gnssCollector = GnssCollector(this)
        val baroCollector = BaroCollector(this)

        // IMU loop — drives the EKF prediction at ~100 Hz.
        imuJob = serviceScope.launch {
            imuCollector.samples().collect { sample ->
                processImu(sample.accel, sample.gyro, sample.timestampNanos)
            }
        }

        // GNSS updates — measurement update when available.
        gnssJob = serviceScope.launch {
            gnssCollector.samples().collect { sample ->
                processGnss(sample)
            }
        }

        // Barometer — altitude constraint when stable.
        baroJob = serviceScope.launch {
            baroCollector.samples().collect { sample ->
                processBaro(sample.altitudeMetres.toDouble())
            }
        }
    }

    // ── IMU processing ──────────────────────────────────────────────────

    private fun processImu(accel: DoubleArray, gyro: DoubleArray, timestampNanos: Long) {
        lastAccel = accel.clone()
        lastGyro = gyro.clone()
        val lastTs = ekf.state.lastPredictTimestampNanos
        if (lastTs == 0L) {
            // First sample — initialise timestamp, don't predict yet.
            ekf.state = ekf.state.copy(lastPredictTimestampNanos = timestampNanos)
            return
        }

        val dt = (timestampNanos - lastTs) / 1_000_000_000.0
        if (dt <= 0.0 || dt > 0.5) {
            // Bad dt — skip this sample (timestamp wrap or large gap).
            ekf.state = ekf.state.copy(lastPredictTimestampNanos = timestampNanos)
            return
        }

        // Update sliding windows for ZUPT/ZARU/motion-mode detection.
        val accelNorm = ZuptDetector.norm3(accel)
        val gyroNorm = ZuptDetector.norm3(gyro)
        accelMagnitudes.add(accelNorm)
        gyroMagnitudes.add(gyroNorm)
        if (accelMagnitudes.size > ZuptDetector.WINDOW_SIZE * 2) {
            accelMagnitudes.removeAt(0)
        }
        if (gyroMagnitudes.size > ZuptDetector.WINDOW_SIZE * 2) {
            gyroMagnitudes.removeAt(0)
        }

        // Classify motion mode.
        val accelVar = if (accelMagnitudes.size >= ZuptDetector.WINDOW_SIZE) {
            ZuptDetector.variance(accelMagnitudes.takeLast(ZuptDetector.WINDOW_SIZE))
        } else 1.0
        val gyroVar = if (gyroMagnitudes.size >= ZuptDetector.WINDOW_SIZE) {
            ZuptDetector.variance(gyroMagnitudes.takeLast(ZuptDetector.WINDOW_SIZE))
        } else 1.0
        val motionMode = MotionModeClassifier.classify(
            accelVariance = accelVar,
            gyroVariance = gyroVar,
            yawRate = kotlin.math.abs(gyro[2]),
            forwardAccel = accel[1], // body Y is roughly forward on Android
        )

        // EKF predict step.
        ekf.predict(accel, gyro, dt, motionMode)
        ekf.state = ekf.state.copy(lastPredictTimestampNanos = timestampNanos)

        // ZUPT/ZARU when stationary.
        if (ZuptDetector.isStationary(accelMagnitudes)) {
            ekf.updateZupt()
        }
        if (ZuptDetector.isZeroAngularRate(gyroMagnitudes)) {
            ekf.updateZaru(gyro)
        }

        // NHC when moving.
        if (motionMode != MotionMode.STOPPED) {
            ekf.updateNhc()
        }

        // Emit state at reduced rate (~10 Hz) to avoid flooding the UI.
        if (timestampNanos % 10 == 0L || confidenceCount % 10 == 0) {
            emitTrackingState(motionMode)
        }
    }

    // ── GNSS processing ─────────────────────────────────────────────────

    private fun processGnss(sample: com.aeris.mobile.core.sensor.GnssSample) {
        val latRad = Math.toRadians(sample.latitude)
        val lonRad = Math.toRadians(sample.longitude)

        ekf.updateGnss(
            latRad = latRad,
            lonRad = lonRad,
            altM = sample.altitude,
            accuracy = sample.accuracy,
            timestampNanos = System.nanoTime(),
        )

        // Capture speed / bearing for camera heading.
        lastGnssSpeedKmh = sample.speed * 3.6f   // m/s → km/h
        lastGnssBearing  = sample.bearing

        lastGnssTimeMillis = System.currentTimeMillis()
        if (gnssOutageStartMillis > 0) {
            cumulativeGnssOutageSec += (lastGnssTimeMillis - gnssOutageStartMillis) / 1000
            gnssOutageStartMillis = 0L
        }

        emitTrackingState(ekf.currentMotionMode)
    }

    // ── Baro processing ─────────────────────────────────────────────────

    private fun processBaro(altitudeMetres: Double) {
        baroFilter.addSample(altitudeMetres)
        if (baroFilter.isStable()) {
            val delta = baroFilter.deltaAltitude()
            if (delta != null) {
                val predictedDeltaDown = ekf.state.positionNed[2] - lastBaroNedDown
                ekf.updateBaroAltitude(delta, predictedDeltaDown)
            }
            baroFilter.markAccepted()
            lastBaroNedDown = ekf.state.positionNed[2]
        }
    }

    // ── State emission ──────────────────────────────────────────────────

    private fun emitTrackingState(motionMode: MotionMode) {
        val s = ekf.state
        if (!s.originInitialised) return

        val (lat, lon, alt) = s.nedToGeodetic(s.positionNed)
        val latDeg = Math.toDegrees(lat)
        val lonDeg = Math.toDegrees(lon)
        val confidence = ekf.computeConfidence()

        // Update route
        val now = System.currentTimeMillis()
        val gnssAvailable = (now - lastGnssTimeMillis) < 5_000L
        val gnssLostSec = if (gnssAvailable) 0L else (now - lastGnssTimeMillis) / 1000

        if (!gnssAvailable && gnssOutageStartMillis == 0L) {
            gnssOutageStartMillis = lastGnssTimeMillis
        }

        // Distance accumulation.
        if (prevLat != 0.0 || prevLon != 0.0) {
            totalDistance += haversineMetres(prevLat, prevLon, latDeg, lonDeg)
        }
        prevLat = latDeg
        prevLon = lonDeg

        // Route point (throttle to ~1 per second).
        if (routePoints.isEmpty() || (now - (routePoints.lastOrNull()?.timestampMillis ?: 0)) > 1000) {
            routePoints.add(
                RoutePoint(
                    lat = latDeg, lon = lonDeg,
                    confidence = confidence,
                    isGnssLocked = gnssAvailable,
                    timestampMillis = now,
                )
            )
        }

        // Stats
        confidenceSum += confidence
        confidenceCount++
        val posTrace = s.covariance[0, 0] + s.covariance[1, 1] + s.covariance[2, 2]
        val sigma = sqrt(posTrace.coerceAtLeast(0.0))
        if (sigma > maxDrift) maxDrift = sigma

        // IMU health
        val imuStatus = if (accelMagnitudes.size > 10) SensorStatus.ACTIVE else SensorStatus.UNAVAILABLE
        val gnssStatus = if (gnssAvailable) SensorStatus.ACTIVE
            else if (lastGnssTimeMillis > 0) SensorStatus.DEGRADED
            else SensorStatus.UNAVAILABLE
        val baroStatus = if (baroFilter.isStable()) SensorStatus.ACTIVE
            else if (baroFilter.deltaAltitude() != null) SensorStatus.DEGRADED
            else SensorStatus.UNAVAILABLE

        // Mode probabilities (placeholder — active mode = 1.0)
        val probs = MotionMode.entries.associateWith {
            if (it == motionMode) 1f else 0f
        }

        val state = TrackingState(
            latitude = latDeg,
            longitude = lonDeg,
            altitude = alt,
            confidence = confidence,
            isGnssAvailable = gnssAvailable,
            gnssLostDurationSec = gnssLostSec,
            motionMode = motionMode,
            routePoints = routePoints.toList(),
            distanceTraveledMeters = totalDistance,
            isTracking = true,
            sensorHealth = SensorHealth(gnssStatus, imuStatus, baroStatus),
            modeProbabilities = probs,
            maxDriftMeters = maxDrift,
            averageConfidence = if (confidenceCount > 0) confidenceSum / confidenceCount else 100.0,
            totalGnssOutageSec = cumulativeGnssOutageSec + if (gnssOutageStartMillis > 0) {
                (now - gnssOutageStartMillis) / 1000
            } else 0,
            currentAccel = lastAccel.toList(),
            currentGyro = lastGyro.toList(),
            currentSpeedKmh = lastGnssSpeedKmh,
            currentBearing = lastGnssBearing,
        )

        _trackingState.value = state
        _sharedState.value = state

        // Update notification.
        val notifText = if (gnssAvailable) "tracking, GPS locked"
            else "estimating position (GPS lost ${gnssLostSec}s ago)"
        val notification = TrackingNotificationHelper.buildNotification(this, "Aeris — $notifText")
        val nm = getSystemService(android.app.NotificationManager::class.java)
        nm.notify(TrackingNotificationHelper.NOTIFICATION_ID, notification)
    }

    // ── State persistence for crash recovery ────────────────────────────

    private fun persistState() {
        val s = ekf.state
        prefs.edit()
            .putFloat("lat", Math.toDegrees(s.originLat).toFloat())
            .putFloat("lon", Math.toDegrees(s.originLon).toFloat())
            .putFloat("alt", s.originAlt.toFloat())
            .putBoolean("hasOrigin", s.originInitialised)
            .putFloat("posN", s.positionNed[0].toFloat())
            .putFloat("posE", s.positionNed[1].toFloat())
            .putFloat("posD", s.positionNed[2].toFloat())
            .apply()
    }

    private fun recoverState() {
        if (!prefs.getBoolean("hasOrigin", false)) return
        val lat = prefs.getFloat("lat", 0f).toDouble()
        val lon = prefs.getFloat("lon", 0f).toDouble()
        val alt = prefs.getFloat("alt", 0f).toDouble()
        ekf.state = ekf.state.copy(
            originLat = Math.toRadians(lat),
            originLon = Math.toRadians(lon),
            originAlt = alt,
            originInitialised = true,
            positionNed = doubleArrayOf(
                prefs.getFloat("posN", 0f).toDouble(),
                prefs.getFloat("posE", 0f).toDouble(),
                prefs.getFloat("posD", 0f).toDouble(),
            ),
        )
    }

    // ── Utilities ───────────────────────────────────────────────────────

    /** Haversine distance between two lat/lon points (degrees). */
    private fun haversineMetres(
        lat1: Double, lon1: Double, lat2: Double, lon2: Double
    ): Double {
        val r = 6_371_000.0
        val dLat = Math.toRadians(lat2 - lat1)
        val dLon = Math.toRadians(lon2 - lon1)
        val a = kotlin.math.sin(dLat / 2).let { it * it } +
                kotlin.math.cos(Math.toRadians(lat1)) *
                kotlin.math.cos(Math.toRadians(lat2)) *
                kotlin.math.sin(dLon / 2).let { it * it }
        return 2 * r * kotlin.math.asin(sqrt(a))
    }
}

package com.aeris.mobile.service

import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.location.GnssStatus
import android.location.Location
import android.location.LocationManager
import android.os.Build
import android.os.IBinder
import android.os.Looper
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import com.aeris.mobile.MainActivity
import com.aeris.mobile.R
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.io.BufferedWriter
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class RecordingStatus(
    val isRecording: Boolean = false,
    val elapsedSec: Long = 0L,
    val bytesWritten: Long = 0L,
    val satellitesUsed: Int = 0,
    val fixAccuracyMeters: Float? = null,
    val accelStreaming: Boolean = false,
    val gyroStreaming: Boolean = false,
    val lastLocation: Location? = null,
)

/**
 * Foreground Service that captures raw sensor events and GNSS fixes to a CSV file
 * matching backend/data_loader.py's canonical schema per M08 §2.
 */
class SensorRecorderService : Service(), SensorEventListener {

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private lateinit var sensorManager: SensorManager
    private lateinit var locationManager: LocationManager
    private lateinit var fusedLocationClient: FusedLocationProviderClient

    private var csvWriter: BufferedWriter? = null
    private var recordingDir: File? = null
    private var startTimestampMs = 0L

    private var accelSample = FloatArray(3)
    private var gyroSample = FloatArray(3)
    private var lastFix: Location? = null
    private var satellitesCount = 0

    private var isRecording = false
    private var bytesWritten = 0L

    private var gnssCallback: GnssStatus.Callback? = null
    private var locationCallback: LocationCallback? = null

    companion object {
        const val CHANNEL_ID = "aeris_sensor_recorder"
        const val NOTIFICATION_ID = 2026

        private val _status = MutableStateFlow(RecordingStatus())
        val status: StateFlow<RecordingStatus> = _status.asStateFlow()

        fun start(context: Context) {
            val intent = Intent(context, SensorRecorderService::class.java).apply {
                action = "START_RECORDING"
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            val intent = Intent(context, SensorRecorderService::class.java).apply {
                action = "STOP_RECORDING"
            }
            context.startService(intent)
        }
    }

    override fun onCreate() {
        super.onCreate()
        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        locationManager = getSystemService(Context.LOCATION_SERVICE) as LocationManager
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            "START_RECORDING" -> startRecording()
            "STOP_RECORDING" -> stopRecording()
        }
        return START_NOT_STICKY
    }

    @SuppressLint("MissingPermission")
    private fun startRecording() {
        if (isRecording) return
        isRecording = true
        startTimestampMs = System.currentTimeMillis()

        // Create folder under getExternalFilesDir("recordings")
        val timestampStr = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date(startTimestampMs))
        val baseDir = getExternalFilesDir("recordings") ?: filesDir
        recordingDir = File(baseDir, timestampStr).apply { mkdirs() }

        val csvFile = File(recordingDir, "sensor_capture.csv")
        csvWriter = BufferedWriter(FileWriter(csvFile, true))

        // Write canonical CSV header matching backend/data_loader.py
        val header = "TIME SINCE START (ms),GPS LATITUDE (degrees),GPS LONGITUDE (degrees),GPS ALTITUDE (m),GPS ACCURACY (m),GPS SPEED (Kmh),GPS ORIENTATION (°),GPS SATELLITES IN RANGE,ACCELEROMETER X (m/s²),ACCELEROMETER Y (m/s²),ACCELEROMETER Z (m/s²),GYROSCOPE X (rad/s),GYROSCOPE Y (rad/s),GYROSCOPE Z (rad/s)\n"
        csvWriter?.write(header)
        bytesWritten = header.toByteArray().size.toLong()

        // Register sensors
        sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_FASTEST)
        }
        sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_FASTEST)
        }

        // Register real GnssStatus callback for satellite count
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            gnssCallback = object : GnssStatus.Callback() {
                override fun onSatelliteStatusChanged(status: GnssStatus) {
                    var used = 0
                    for (i in 0 until status.satelliteCount) {
                        if (status.usedInFix(i)) used++
                    }
                    satellitesCount = used
                    updateStatus()
                }
            }
            try {
                locationManager.registerGnssStatusCallback(gnssCallback!!, null)
            } catch (e: SecurityException) { /* Handled */ }
        }

        // Register location request at 1 Hz
        val locationRequest = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 1000L)
            .setMinUpdateIntervalMillis(500L)
            .build()

        locationCallback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                lastFix = result.lastLocation
                updateStatus()
            }
        }
        try {
            fusedLocationClient.requestLocationUpdates(locationRequest, locationCallback!!, Looper.getMainLooper())
        } catch (e: SecurityException) { /* Handled */ }

        // Start foreground notification
        val notification = buildNotification("Recording drive — 00:00")
        ServiceCompat.startForeground(
            this,
            NOTIFICATION_ID,
            notification,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION else 0
        )

        // Elapsed time ticker
        serviceScope.launch {
            while (isRecording) {
                kotlinx.coroutines.delay(1000L)
                updateStatus()
            }
        }
    }

    private fun stopRecording() {
        if (!isRecording) return
        isRecording = false

        sensorManager.unregisterListener(this)
        gnssCallback?.let {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                locationManager.unregisterGnssStatusCallback(it)
            }
        }
        locationCallback?.let { fusedLocationClient.removeLocationUpdates(it) }

        csvWriter?.flush()
        csvWriter?.close()
        csvWriter = null

        // Write recording_info.json per M08 §2
        recordingDir?.let { dir ->
            val infoFile = File(dir, "recording_info.json")
            val json = JSONObject().apply {
                put("start_time_ms", startTimestampMs)
                put("device_model", Build.MODEL)
                put("device_manufacturer", Build.MANUFACTURER)
                put("android_version", Build.VERSION.RELEASE)
                put("bytes_written", bytesWritten)
            }
            infoFile.writeText(json.toString(2))
        }

        _status.value = RecordingStatus(isRecording = false)
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onSensorChanged(event: SensorEvent) {
        if (!isRecording) return
        when (event.sensor.type) {
            Sensor.TYPE_ACCELEROMETER -> {
                accelSample = event.values.clone()
                // Emit combined row on accelerometer event
                writeRow()
            }
            Sensor.TYPE_GYROSCOPE -> {
                gyroSample = event.values.clone()
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    private fun writeRow() {
        val now = System.currentTimeMillis()
        val timeSinceStartMs = now - startTimestampMs
        val fix = lastFix

        val lat = fix?.latitude ?: 0.0
        val lon = fix?.longitude ?: 0.0
        val alt = fix?.altitude ?: 0.0
        val acc = fix?.accuracy ?: 0.0f
        val speedKmh = (fix?.speed ?: 0.0f) * 3.6f
        val bearing = fix?.bearing ?: 0.0f
        val satStr = "$satellitesCount / 24"

        val line = "$timeSinceStartMs,$lat,$lon,$alt,$acc,$speedKmh,$bearing,$satStr,${accelSample[0]},${accelSample[1]},${accelSample[2]},${gyroSample[0]},${gyroSample[1]},${gyroSample[2]}\n"
        csvWriter?.write(line)
        bytesWritten += line.toByteArray().size
    }

    private fun updateStatus() {
        val elapsed = (System.currentTimeMillis() - startTimestampMs) / 1000L
        _status.value = RecordingStatus(
            isRecording = isRecording,
            elapsedSec = elapsed,
            bytesWritten = bytesWritten,
            satellitesUsed = satellitesCount,
            fixAccuracyMeters = lastFix?.accuracy,
            accelStreaming = true,
            gyroStreaming = true,
            lastLocation = lastFix,
        )
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "AERIS Sensor Recorder",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Foreground recording notification for sensor logs"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(text: String): android.app.Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("AERIS Drive Capture")
            .setContentText(text)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        stopRecording()
        serviceScope.cancel()
        super.onDestroy()
    }
}

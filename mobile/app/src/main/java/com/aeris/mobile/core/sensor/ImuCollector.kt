package com.aeris.mobile.core.sensor

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow

/**
 * Collects paired accelerometer + gyroscope readings from the device's
 * IMU via [SensorManager] and emits them as a [Flow] of [ImuSample].
 *
 * ## Pairing strategy
 * Accelerometer and gyroscope events arrive on separate callbacks at
 * potentially different rates. We pair them by keeping the latest
 * reading from each sensor and emitting a combined [ImuSample] every
 * time the **accelerometer** fires (it is typically the slower of the
 * two). This ensures every emit has fresh accel data, and the gyro
 * reading is the most recent one available.
 *
 * ## Timestamp
 * We use [SensorEvent.timestamp] (nanoseconds since boot), not
 * [System.currentTimeMillis], because the sensor timestamp is monotonic
 * and jitter-free.
 */
class ImuCollector(private val context: Context) {

    /**
     * Starts collecting IMU data at the device's fastest native rate.
     *
     * The returned [Flow] is cold — collection only begins when a
     * coroutine starts collecting it, and sensors are unregistered
     * when the collector is cancelled.
     */
    fun samples(): Flow<ImuSample> = callbackFlow {
        val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        val accelSensor = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        val gyroSensor = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)

        // Latest readings; guarded by single-threaded sensor callback.
        var latestAccel: FloatArray? = null
        var latestGyro: FloatArray? = null
        var latestGyroTimestamp: Long = 0

        val listener = object : SensorEventListener {
            override fun onSensorChanged(event: SensorEvent) {
                when (event.sensor.type) {
                    Sensor.TYPE_GYROSCOPE -> {
                        latestGyro = event.values.copyOf()
                        latestGyroTimestamp = event.timestamp
                    }
                    Sensor.TYPE_ACCELEROMETER -> {
                        latestAccel = event.values.copyOf()
                        val gyro = latestGyro
                        if (gyro != null) {
                            val sample = ImuSample(
                                accel = doubleArrayOf(
                                    event.values[0].toDouble(),
                                    event.values[1].toDouble(),
                                    event.values[2].toDouble(),
                                ),
                                gyro = doubleArrayOf(
                                    gyro[0].toDouble(),
                                    gyro[1].toDouble(),
                                    gyro[2].toDouble(),
                                ),
                                timestampNanos = event.timestamp,
                            )
                            trySend(sample)
                        }
                    }
                }
            }

            override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
                // Not used — accuracy changes don't affect the filter.
            }
        }

        // Register at fastest rate. On most devices this is ~100–200 Hz.
        accelSensor?.let {
            sensorManager.registerListener(listener, it, SensorManager.SENSOR_DELAY_FASTEST)
        }
        gyroSensor?.let {
            sensorManager.registerListener(listener, it, SensorManager.SENSOR_DELAY_FASTEST)
        }

        awaitClose {
            sensorManager.unregisterListener(listener)
        }
    }
}

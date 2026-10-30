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
 * Collects barometric pressure readings and converts them to approximate
 * altitude via [SensorManager.getAltitude].
 *
 * The barometer is sampled at [SensorManager.SENSOR_DELAY_NORMAL] (~5 Hz)
 * since pressure changes slowly. Higher rates would waste power without
 * improving altitude estimates.
 *
 * If the device has no barometer sensor the returned flow completes
 * immediately without emitting.
 */
class BaroCollector(private val context: Context) {

    /**
     * Starts collecting barometric samples.
     *
     * Each emission includes both the raw pressure (hPa) and the derived
     * altitude (metres above mean sea level, using standard atmosphere
     * pressure of 1013.25 hPa as the reference).
     */
    fun samples(): Flow<BaroSample> = callbackFlow {
        val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        val baroSensor = sensorManager.getDefaultSensor(Sensor.TYPE_PRESSURE)

        if (baroSensor == null) {
            // Device has no barometer — close the flow cleanly.
            close()
            return@callbackFlow
        }

        val listener = object : SensorEventListener {
            override fun onSensorChanged(event: SensorEvent) {
                val pressureHpa = event.values[0]
                val altMetres = SensorManager.getAltitude(
                    SensorManager.PRESSURE_STANDARD_ATMOSPHERE,
                    pressureHpa,
                )
                val sample = BaroSample(
                    pressureHpa = pressureHpa,
                    altitudeMetres = altMetres,
                    timestampNanos = event.timestamp,
                )
                trySend(sample)
            }

            override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
                // Barometer accuracy changes are not actionable here.
            }
        }

        sensorManager.registerListener(listener, baroSensor, SensorManager.SENSOR_DELAY_NORMAL)

        awaitClose {
            sensorManager.unregisterListener(listener)
        }
    }
}

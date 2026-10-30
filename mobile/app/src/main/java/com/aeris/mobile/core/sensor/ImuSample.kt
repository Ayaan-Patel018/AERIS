package com.aeris.mobile.core.sensor

/**
 * Timestamped IMU sample containing paired accelerometer and gyroscope readings.
 *
 * @property accel Accelerometer reading [ax, ay, az] in device body frame (m/s²).
 *                 Includes gravity — the EKF's INS mechanisation accounts for it.
 * @property gyro  Gyroscope reading [ωx, ωy, ωz] in device body frame (rad/s).
 * @property timestampNanos Monotonic event timestamp from
 *                          [android.hardware.SensorEvent.timestamp] (nanoseconds
 *                          since boot). We use this, not wall-clock time, because
 *                          it is jitter-free and consistent across sensor types.
 */
data class ImuSample(
    val accel: DoubleArray,
    val gyro: DoubleArray,
    val timestampNanos: Long,
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is ImuSample) return false
        return accel.contentEquals(other.accel) &&
                gyro.contentEquals(other.gyro) &&
                timestampNanos == other.timestampNanos
    }

    override fun hashCode(): Int {
        var result = accel.contentHashCode()
        result = 31 * result + gyro.contentHashCode()
        result = 31 * result + timestampNanos.hashCode()
        return result
    }
}

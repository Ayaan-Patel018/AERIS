package com.aeris.mobile.core.filter

import kotlin.math.abs
import kotlin.math.asin
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Unit quaternion representing a 3-D rotation.
 *
 * Uses scalar-first convention: q = [w, x, y, z] where w is the scalar
 * (real) part and (x, y, z) is the vector (imaginary) part. This matches
 * the Hamilton product convention and is consistent with Android's
 * [android.hardware.SensorManager.getQuaternionFromVector] output after
 * reordering.
 *
 * All factory methods and [normalize] return unit quaternions. The class
 * is immutable; every operation returns a new instance.
 */
data class Quaternion(
    val w: Double,
    val x: Double,
    val y: Double,
    val z: Double
) {

    /** Squared norm — avoids the sqrt when you only need a magnitude check. */
    fun normSquared(): Double = w * w + x * x + y * y + z * z

    /** Euclidean norm. */
    fun norm(): Double = sqrt(normSquared())

    /**
     * Returns this quaternion scaled to unit length.
     * If the norm is essentially zero the identity quaternion is returned
     * to avoid NaN propagation.
     */
    fun normalize(): Quaternion {
        val n = norm()
        return if (n < 1e-12) identity()
        else Quaternion(w / n, x / n, y / n, z / n)
    }

    /** Quaternion conjugate (inverse for unit quaternions). */
    fun conjugate(): Quaternion = Quaternion(w, -x, -y, -z)

    /**
     * Hamilton product: this ⊗ other.
     *
     * This composes rotations: if `this` rotates frame A→B and [other]
     * rotates frame B→C, the result rotates A→C.
     */
    operator fun times(other: Quaternion): Quaternion = Quaternion(
        w = w * other.w - x * other.x - y * other.y - z * other.z,
        x = w * other.x + x * other.w + y * other.z - z * other.y,
        y = w * other.y - x * other.z + y * other.w + z * other.x,
        z = w * other.z + x * other.y - y * other.x + z * other.w,
    )

    /**
     * Converts this unit quaternion to a 3×3 direction-cosine (rotation) matrix
     * stored in row-major order as a [Matrix].
     *
     * The resulting matrix C transforms a vector from the body frame to
     * the navigation frame: v_nav = C · v_body.
     */
    fun toRotationMatrix(): Matrix {
        val data = DoubleArray(9)
        val q0 = w; val q1 = x; val q2 = y; val q3 = z

        data[0] = 1.0 - 2.0 * (q2 * q2 + q3 * q3)
        data[1] = 2.0 * (q1 * q2 - q0 * q3)
        data[2] = 2.0 * (q1 * q3 + q0 * q2)
        data[3] = 2.0 * (q1 * q2 + q0 * q3)
        data[4] = 1.0 - 2.0 * (q1 * q1 + q3 * q3)
        data[5] = 2.0 * (q2 * q3 - q0 * q1)
        data[6] = 2.0 * (q1 * q3 - q0 * q2)
        data[7] = 2.0 * (q2 * q3 + q0 * q1)
        data[8] = 1.0 - 2.0 * (q1 * q1 + q2 * q2)

        return Matrix(3, 3, data)
    }

    /**
     * Rotates a 3-D vector by this quaternion.
     * Equivalent to C · v where C = [toRotationMatrix].
     */
    fun rotateVector(v: DoubleArray): DoubleArray {
        require(v.size == 3) { "Vector must have 3 elements" }
        val qv = Quaternion(0.0, v[0], v[1], v[2])
        val result = this * qv * conjugate()
        return doubleArrayOf(result.x, result.y, result.z)
    }

    /**
     * Extracts Euler angles (roll, pitch, yaw) in radians from this quaternion.
     * Convention: ZYX (yaw-pitch-roll), consistent with aerospace NED frames.
     */
    fun toEuler(): DoubleArray {
        val sinPitch = 2.0 * (w * y - z * x)
        val pitch = if (abs(sinPitch) >= 1.0) {
            if (sinPitch > 0) Math.PI / 2.0 else -Math.PI / 2.0
        } else {
            asin(sinPitch)
        }
        val roll = atan2(
            2.0 * (w * x + y * z),
            1.0 - 2.0 * (x * x + y * y)
        )
        val yaw = atan2(
            2.0 * (w * z + x * y),
            1.0 - 2.0 * (y * y + z * z)
        )
        return doubleArrayOf(roll, pitch, yaw)
    }

    companion object {
        /** The identity rotation (no rotation). */
        fun identity(): Quaternion = Quaternion(1.0, 0.0, 0.0, 0.0)

        /**
         * Constructs a quaternion from a rotation vector (axis × angle).
         *
         * For small angles this is the exponential map from so(3) to SO(3):
         *   q ≈ [1, θ/2]  when ‖θ‖ is small.
         *
         * @param rv Rotation vector [rx, ry, rz] in radians.
         */
        fun fromRotationVector(rv: DoubleArray): Quaternion {
            require(rv.size == 3) { "Rotation vector must have 3 elements" }
            val angle = sqrt(rv[0] * rv[0] + rv[1] * rv[1] + rv[2] * rv[2])
            return if (angle < 1e-10) {
                // First-order Taylor expansion for small angles.
                Quaternion(1.0, rv[0] / 2.0, rv[1] / 2.0, rv[2] / 2.0).normalize()
            } else {
                val halfAngle = angle / 2.0
                val s = sin(halfAngle) / angle
                Quaternion(cos(halfAngle), rv[0] * s, rv[1] * s, rv[2] * s)
            }
        }

        /**
         * Constructs a quaternion from ZYX Euler angles (yaw, pitch, roll).
         *
         * @param roll  Rotation about X axis (radians).
         * @param pitch Rotation about Y axis (radians).
         * @param yaw   Rotation about Z axis (radians).
         */
        fun fromEuler(roll: Double, pitch: Double, yaw: Double): Quaternion {
            val cr = cos(roll / 2.0);  val sr = sin(roll / 2.0)
            val cp = cos(pitch / 2.0); val sp = sin(pitch / 2.0)
            val cy = cos(yaw / 2.0);   val sy = sin(yaw / 2.0)

            return Quaternion(
                w = cr * cp * cy + sr * sp * sy,
                x = sr * cp * cy - cr * sp * sy,
                y = cr * sp * cy + sr * cp * sy,
                z = cr * cp * sy - sr * sp * cy,
            )
        }

        /**
         * Constructs a quaternion that integrates an angular velocity
         * over a time step.
         *
         * @param omega Angular velocity [ωx, ωy, ωz] in rad/s.
         * @param dt    Time step in seconds.
         */
        fun fromAngularVelocity(omega: DoubleArray, dt: Double): Quaternion {
            require(omega.size == 3) { "Angular velocity must have 3 elements" }
            return fromRotationVector(
                doubleArrayOf(omega[0] * dt, omega[1] * dt, omega[2] * dt)
            )
        }
    }
}

package com.aeris.mobile.core.filter

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Test
import kotlin.math.PI
import kotlin.math.sqrt

class QuaternionTest {

    @Test
    fun testIdentity() {
        val q = Quaternion.identity()
        assertEquals(1.0, q.w, 1e-9)
        assertEquals(0.0, q.x, 1e-9)
        assertEquals(0.0, q.y, 1e-9)
        assertEquals(0.0, q.z, 1e-9)
    }

    @Test
    fun testNorm() {
        val q = Quaternion(2.0, 0.0, 0.0, 0.0)
        assertEquals(4.0, q.normSquared(), 1e-9)
        assertEquals(2.0, q.norm(), 1e-9)
    }

    @Test
    fun testNormalize() {
        val q = Quaternion(1.0, 1.0, 1.0, 1.0)
        val qn = q.normalize()
        assertEquals(1.0, qn.norm(), 1e-9)
        assertEquals(0.5, qn.w, 1e-9)
        assertEquals(0.5, qn.x, 1e-9)
        assertEquals(0.5, qn.y, 1e-9)
        assertEquals(0.5, qn.z, 1e-9)
    }

    @Test
    fun testHamiltonProduct() {
        val q1 = Quaternion(0.5, 0.5, 0.5, 0.5)
        val q2 = Quaternion(0.5, -0.5, 0.5, -0.5)
        val p = q1 * q2
        
        // Expected: w=0.5, x=-0.5, y=0.5, z=0.5
        assertEquals(0.5, p.w, 1e-9)
        assertEquals(-0.5, p.x, 1e-9)
        assertEquals(0.5, p.y, 1e-9)
        assertEquals(0.5, p.z, 1e-9)
    }

    @Test
    fun testFromRotationVector() {
        // 90 deg rotation around X
        val rv = doubleArrayOf(PI / 2.0, 0.0, 0.0)
        val q = Quaternion.fromRotationVector(rv)
        
        // cos(45) = sin(45) ≈ 0.7071
        val expected = sqrt(2.0) / 2.0
        assertEquals(expected, q.w, 1e-9)
        assertEquals(expected, q.x, 1e-9)
        assertEquals(0.0, q.y, 1e-9)
        assertEquals(0.0, q.z, 1e-9)
    }

    @Test
    fun testRotateVector() {
        // 90 deg around Z
        val rv = doubleArrayOf(0.0, 0.0, PI / 2.0)
        val q = Quaternion.fromRotationVector(rv)
        
        // Vector [1, 0, 0] rotated 90 deg around Z becomes [0, 1, 0]
        val v = doubleArrayOf(1.0, 0.0, 0.0)
        val vr = q.rotateVector(v)
        
        assertArrayEquals(doubleArrayOf(0.0, 1.0, 0.0), vr, 1e-9)
    }
}

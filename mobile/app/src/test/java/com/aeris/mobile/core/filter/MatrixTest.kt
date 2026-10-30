package com.aeris.mobile.core.filter

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Test
import kotlin.math.abs

class MatrixTest {

    @Test
    fun testAddition() {
        val a = Matrix(2, 2, doubleArrayOf(1.0, 2.0, 3.0, 4.0))
        val b = Matrix(2, 2, doubleArrayOf(5.0, 6.0, 7.0, 8.0))
        val c = a + b
        
        assertArrayEquals(doubleArrayOf(6.0, 8.0, 10.0, 12.0), c.data, 1e-9)
    }

    @Test
    fun testMultiplication() {
        val a = Matrix(2, 3, doubleArrayOf(
            1.0, 2.0, 3.0,
            4.0, 5.0, 6.0
        ))
        val b = Matrix(3, 2, doubleArrayOf(
            7.0, 8.0,
            9.0, 10.0,
            11.0, 12.0
        ))
        
        val c = a * b
        assertEquals(2, c.rows)
        assertEquals(2, c.cols)
        
        // Row 1 x Col 1 = 1*7 + 2*9 + 3*11 = 7 + 18 + 33 = 58
        assertEquals(58.0, c[0, 0], 1e-9)
        // Row 2 x Col 2 = 4*8 + 5*10 + 6*12 = 32 + 50 + 72 = 154
        assertEquals(154.0, c[1, 1], 1e-9)
    }

    @Test
    fun testInverse() {
        // A simple 2x2 matrix
        val a = Matrix(2, 2, doubleArrayOf(
            4.0, 7.0,
            2.0, 6.0
        ))
        
        val aInv = a.inverse()
        
        // det = 24 - 14 = 10
        // Inv = [0.6, -0.7; -0.2, 0.4]
        assertEquals(0.6, aInv[0, 0], 1e-9)
        assertEquals(-0.7, aInv[0, 1], 1e-9)
        assertEquals(-0.2, aInv[1, 0], 1e-9)
        assertEquals(0.4, aInv[1, 1], 1e-9)
        
        // A * A_inv = I
        val id = a * aInv
        assertEquals(1.0, id[0, 0], 1e-9)
        assertEquals(0.0, id[0, 1], 1e-9)
        assertEquals(0.0, id[1, 0], 1e-9)
        assertEquals(1.0, id[1, 1], 1e-9)
    }
    
    @Test
    fun testSkewSymmetric() {
        val v = doubleArrayOf(1.0, 2.0, 3.0)
        val s = Matrix.skewSymmetric(v)
        
        assertEquals(0.0, s[0, 0], 1e-9)
        assertEquals(-3.0, s[0, 1], 1e-9)
        assertEquals(2.0, s[0, 2], 1e-9)
        
        assertEquals(3.0, s[1, 0], 1e-9)
        assertEquals(0.0, s[1, 1], 1e-9)
        assertEquals(-1.0, s[1, 2], 1e-9)
        
        assertEquals(-2.0, s[2, 0], 1e-9)
        assertEquals(1.0, s[2, 1], 1e-9)
        assertEquals(0.0, s[2, 2], 1e-9)
    }
}

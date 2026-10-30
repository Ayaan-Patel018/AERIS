package com.aeris.mobile.util

import org.junit.Assert.assertEquals
import org.junit.Test

class FormattersTest {

    @Test
    fun testCardinal16Boundaries() {
        // Spec requirements from R6 § 3.2:
        // Tests: 0->N, 11.24->N, 11.25->NNE, 90->E, 180->S, 270->W, 281.24->W, 281.25->WNW, 291->WNW, 348.75->N, 359.9->N, 720->N, -10->N.
        assertEquals("N", Formatters.cardinal16(0.0))
        assertEquals("N", Formatters.cardinal16(11.24))
        assertEquals("NNE", Formatters.cardinal16(11.25))
        assertEquals("E", Formatters.cardinal16(90.0))
        assertEquals("S", Formatters.cardinal16(180.0))
        assertEquals("W", Formatters.cardinal16(270.0))
        assertEquals("W", Formatters.cardinal16(281.24))
        assertEquals("WNW", Formatters.cardinal16(281.25))
        assertEquals("WNW", Formatters.cardinal16(291.0))
        assertEquals("N", Formatters.cardinal16(348.75))
        assertEquals("N", Formatters.cardinal16(359.9))
        assertEquals("N", Formatters.cardinal16(720.0))
        assertEquals("N", Formatters.cardinal16(-10.0))
    }

    @Test
    fun testFormatMeters() {
        // Spec requirements from R6 § 3.3
        assertEquals("—", Formatters.formatMeters(null))
        assertEquals("<1 m", Formatters.formatMeters(0.0))
        assertEquals("<1 m", Formatters.formatMeters(0.058))
        assertEquals("<1 m", Formatters.formatMeters(0.99))
        assertEquals("1.0 m", Formatters.formatMeters(1.0))
        assertEquals("5.4 m", Formatters.formatMeters(5.42))
        assertEquals("9.9 m", Formatters.formatMeters(9.94))
        assertEquals("10 m", Formatters.formatMeters(10.0))
        assertEquals("14 m", Formatters.formatMeters(14.2))
        assertEquals("28 m", Formatters.formatMeters(27.8))
    }

    @Test
    fun testFormatDistance() {
        assertEquals("300 m", Formatters.formatDistance(300.0))
        assertEquals("950 m", Formatters.formatDistance(950.0))
        assertEquals("1.0 km", Formatters.formatDistance(1000.0))
        assertEquals("1.4 km", Formatters.formatDistance(1400.0))
        assertEquals("3.4 km", Formatters.formatDistance(3400.0))
    }
}

package com.aeris.mobile.domain.playback

import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.model.DriveMeta
import com.aeris.mobile.domain.model.GnssStatus
import com.aeris.mobile.domain.model.TrajectoryPoint
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class PlaybackClockTest {

    private val testDispatcher = StandardTestDispatcher()
    private val testScope = TestScope(testDispatcher)

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    private fun createMockDrive(pointCount: Int = 101): Drive {
        val points = (0 until pointCount).map { i ->
            val fraction = i.toDouble() / (pointCount - 1)
            TrajectoryPoint(
                lat = 52.37 + fraction * 0.01,
                lon = -1.25 + fraction * 0.01,
                headingDeg = 291.0,
                speedMps = 10.0,
                timestampSec = fraction * 600.0, // 0 to 600 seconds
                status = GnssStatus.HEALTHY,
                sigma = 0.5,
                covXX = 0.02,
                covYY = 0.03,
                covXY = 0.0,
                distanceMeters = fraction * 3000.0 // 0 to 3000 meters
            )
        }

        val meta = DriveMeta(
            id = "Drive S3b",
            name = "Test Drive",
            durationSec = 600.0,
            totalDistanceMeters = 3000.0,
            outageCount = 0
        )

        return Drive(
            meta = meta,
            points = points,
            outages = emptyList()
        )
    }

    @Test
    fun testSingleClockConsistencyAt40Percent() {
        val clock = PlaybackClock(testScope)
        val drive = createMockDrive(101)
        clock.attachDrive(drive)

        // Seek to 40% (0.4f)
        clock.seekToFraction(0.40f)

        // 40% of 100 intervals = index 40
        assertEquals(40, clock.currentIndex.value)
        val pt = clock.currentPoint.value
        assertNotNull(pt)
        assertEquals(40, clock.currentIndex.value)

        // Assert all derived values correspond to the exact same point at index 40
        assertEquals(0.40f, clock.currentFraction.value, 1e-4f)
        assertEquals(240.0, clock.elapsedSeconds.value, 1e-3)
        assertEquals(1200.0, clock.distanceDrivenMeters.value, 1e-3)

        assertEquals(pt!!.timestampSec, clock.elapsedSeconds.value, 1e-3)
        assertEquals(pt.distanceMeters, clock.distanceDrivenMeters.value, 1e-3)
    }

    @Test
    fun testCycleSpeedValues() {
        val clock = PlaybackClock(testScope)
        assertEquals(1.0f, clock.playbackSpeed.value)
        clock.cycleSpeed()
        assertEquals(2.0f, clock.playbackSpeed.value)
        clock.cycleSpeed()
        assertEquals(4.0f, clock.playbackSpeed.value)
        clock.cycleSpeed()
        assertEquals(8.0f, clock.playbackSpeed.value)
        clock.cycleSpeed()
        assertEquals(1.0f, clock.playbackSpeed.value)
    }
}

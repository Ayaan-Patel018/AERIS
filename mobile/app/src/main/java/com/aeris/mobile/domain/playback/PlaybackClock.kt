package com.aeris.mobile.domain.playback

import com.aeris.mobile.domain.model.Drive
import com.aeris.mobile.domain.model.OutageWindow
import com.aeris.mobile.domain.model.TrajectoryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * PlaybackClock — The single source of truth for drive playback time and distance per R5 § 5 & R6 § 3.1.
 *
 * Emits current frame index, playback status, playback rate, active outage, elapsed seconds,
 * distance driven, and overall progression fraction.
 */
class PlaybackClock(
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.Main),
) {
    private var drive: Drive? = null
    private var playbackJob: Job? = null

    private val _currentIndex = MutableStateFlow(0)
    val currentIndex: StateFlow<Int> = _currentIndex.asStateFlow()

    private val _isPlaying = MutableStateFlow(false)
    val isPlaying: StateFlow<Boolean> = _isPlaying.asStateFlow()

    private val _playbackSpeed = MutableStateFlow(1.0f)
    val playbackSpeed: StateFlow<Float> = _playbackSpeed.asStateFlow()

    private val _currentPoint = MutableStateFlow<TrajectoryPoint?>(null)
    val currentPoint: StateFlow<TrajectoryPoint?> = _currentPoint.asStateFlow()

    private val _activeOutage = MutableStateFlow<OutageWindow?>(null)
    val activeOutage: StateFlow<OutageWindow?> = _activeOutage.asStateFlow()

    private val _currentFraction = MutableStateFlow(0f)
    val currentFraction: StateFlow<Float> = _currentFraction.asStateFlow()

    private val _elapsedSeconds = MutableStateFlow(0.0)
    val elapsedSeconds: StateFlow<Double> = _elapsedSeconds.asStateFlow()

    private val _distanceDrivenMeters = MutableStateFlow(0.0)
    val distanceDrivenMeters: StateFlow<Double> = _distanceDrivenMeters.asStateFlow()

    private val _totalDistanceMeters = MutableStateFlow(0.0)
    val totalDistanceMeters: StateFlow<Double> = _totalDistanceMeters.asStateFlow()

    private val _totalDurationSeconds = MutableStateFlow(0.0)
    val totalDurationSeconds: StateFlow<Double> = _totalDurationSeconds.asStateFlow()

    fun attachDrive(drive: Drive) {
        this.drive = drive
        val totalSec = drive.meta.durationSec.coerceAtLeast(0.0)
        val totalDist = drive.meta.totalDistanceMeters.coerceAtLeast(0.0)
        _totalDurationSeconds.value = totalSec
        _totalDistanceMeters.value = totalDist
        seekToIndex(0)
    }

    fun getDrive(): Drive? = drive

    fun play() {
        val d = drive ?: return
        if (d.points.isEmpty()) return
        if (_isPlaying.value) return

        _isPlaying.value = true
        playbackJob = scope.launch {
            while (isActive && _isPlaying.value) {
                val currentIdx = _currentIndex.value
                if (currentIdx >= d.points.size - 1) {
                    _isPlaying.value = false
                    break
                }

                val currPt = d.points[currentIdx]
                val nextPt = d.points[currentIdx + 1]
                val deltaSec = (nextPt.timestampSec - currPt.timestampSec).coerceIn(0.01, 1.0)
                val delayMillis = ((deltaSec * 1000.0) / _playbackSpeed.value).toLong().coerceAtLeast(10L)

                delay(delayMillis)

                val newIdx = currentIdx + 1
                updateStateForIndex(newIdx)
            }
        }
    }

    fun pause() {
        _isPlaying.value = false
        playbackJob?.cancel()
    }

    fun togglePlayPause() {
        if (_isPlaying.value) pause() else play()
    }

    fun seekToIndex(index: Int) {
        val d = drive ?: return
        if (d.points.isEmpty()) {
            _currentIndex.value = 0
            _currentPoint.value = null
            _currentFraction.value = 0f
            _elapsedSeconds.value = 0.0
            _distanceDrivenMeters.value = 0.0
            _activeOutage.value = null
            return
        }

        val clamped = index.coerceIn(0, d.points.size - 1)
        updateStateForIndex(clamped)
    }

    fun seekToFraction(fraction: Float) {
        val d = drive ?: return
        if (d.points.isEmpty()) return
        val clamped = fraction.coerceIn(0f, 1f)
        val targetIdx = (clamped * (d.points.size - 1)).toInt()
        seekToIndex(targetIdx)
    }

    fun seekToSeconds(seconds: Double) {
        val d = drive ?: return
        if (d.points.isEmpty()) return
        // Binary search or closest search for timestampSec
        var bestIdx = 0
        var minDiff = Double.MAX_VALUE
        for (i in d.points.indices) {
            val diff = kotlin.math.abs(d.points[i].timestampSec - seconds)
            if (diff < minDiff) {
                minDiff = diff
                bestIdx = i
            }
        }
        seekToIndex(bestIdx)
    }

    fun setSpeed(speed: Float) {
        _playbackSpeed.value = speed
    }

    fun cycleSpeed() {
        // Spec R5 § 3.4: tap cycles 1x, 2x, 4x, 8x
        val speeds = listOf(1.0f, 2.0f, 4.0f, 8.0f)
        val current = _playbackSpeed.value
        val nextIdx = (speeds.indexOf(current) + 1).let { if (it in speeds.indices) it else 0 }
        _playbackSpeed.value = speeds[nextIdx]
    }

    fun jumpToNextOutage() {
        val d = drive ?: return
        val currentIdx = _currentIndex.value
        val nextOutage = d.outages.firstOrNull { it.startIndex > currentIdx }
        if (nextOutage != null) {
            seekToIndex(nextOutage.startIndex)
        } else if (d.outages.isNotEmpty()) {
            seekToIndex(d.outages.first().startIndex)
        }
    }

    fun jumpToPreviousOutage() {
        val d = drive ?: return
        val currentIdx = _currentIndex.value
        val prevOutage = d.outages.lastOrNull { it.startIndex < currentIdx }
        if (prevOutage != null) {
            seekToIndex(prevOutage.startIndex)
        } else if (d.outages.isNotEmpty()) {
            seekToIndex(d.outages.last().startIndex)
        }
    }

    fun reset() {
        pause()
        seekToIndex(0)
    }

    private fun updateStateForIndex(index: Int) {
        val d = drive ?: return
        if (index !in d.points.indices) return

        val pt = d.points[index]
        _currentIndex.value = index
        _currentPoint.value = pt

        val frac = if (d.points.size > 1) index.toFloat() / (d.points.size - 1) else 0f
        _currentFraction.value = frac
        _elapsedSeconds.value = pt.timestampSec
        _distanceDrivenMeters.value = pt.distanceMeters

        _activeOutage.value = d.outages.firstOrNull { index in it.startIndex..it.endIndex }
    }
}

package com.aeris.mobile.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.aeris.mobile.MainActivity
import com.aeris.mobile.R

/**
 * Creates and manages the persistent notification shown while the
 * [TrackingService] foreground service is running.
 *
 * The notification channel is low-importance so it does not make sounds
 * or vibrate, but remains visible in the status bar and notification
 * shade to satisfy the Android foreground-service requirement.
 */
object TrackingNotificationHelper {

    /** Notification channel ID. */
    const val CHANNEL_ID = "aeris_tracking"

    /** Notification ID used for the ongoing foreground notification. */
    const val NOTIFICATION_ID = 1

    /**
     * Creates the notification channel (no-op on API < 26, but our
     * minSdk is 26 anyway).
     */
    fun createChannel(context: Context) {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Tracking",
            NotificationManager.IMPORTANCE_LOW,
        ).apply {
            description = "Shows tracking status while Aeris is navigating."
            setShowBadge(false)
        }
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(channel)
    }

    /**
     * Builds the foreground notification with the given status text.
     *
     * @param context Application or service context.
     * @param statusText One-line status string, e.g. "Aeris — tracking, GPS locked".
     */
    fun buildNotification(context: Context, statusText: String): Notification {
        val launchIntent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            context, 0, launchIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        return NotificationCompat.Builder(context, CHANNEL_ID)
            .setContentTitle("Aeris")
            .setContentText(statusText)
            .setSmallIcon(R.drawable.ic_notification)
            .setOngoing(true)
            .setContentIntent(pendingIntent)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .build()
    }
}

package nl.hes.rebirthchecker

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build

object RebirthStatusNotification {
    private const val CHANNEL_ID = "rebirth_active"
    private const val NOTIFICATION_ID = 194

    fun sync(context: Context, snapshot: RotationSnapshot) {
        if (snapshot.currentMap.equals("Rebirth Island", ignoreCase = true)) {
            show(context, snapshot.remainingSeconds)
        } else {
            hide(context)
        }
    }

    fun hide(context: Context) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager
        manager?.cancel(NOTIFICATION_ID)
    }

    private fun show(context: Context, remainingSeconds: Long) {
        if (
            Build.VERSION.SDK_INT >= 33 &&
            context.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) return

        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager
            ?: return

        val channel = NotificationChannel(
            CHANNEL_ID,
            "Rebirth Island actief",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Toont een stil statusicoon zolang Rebirth Island actief is."
            setSound(null, null)
            enableVibration(false)
            setShowBadge(false)
        }
        manager.createNotificationChannel(channel)

        val openApp = PendingIntent.getActivity(
            context,
            194,
            Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val safeRemaining = remainingSeconds.coerceIn(1L, RotationState.durationSeconds)
        val endsAt = System.currentTimeMillis() + safeRemaining * 1000L

        val builder = Notification.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_rebirth_status)
            .setContentTitle("REBIRTH ISLAND")
            .setContentText("Nu actief")
            .setContentIntent(openApp)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setCategory(Notification.CATEGORY_STATUS)
            .setVisibility(Notification.VISIBILITY_PUBLIC)
            .setWhen(endsAt)
            .setUsesChronometer(true)
            .setShowWhen(true)

        if (Build.VERSION.SDK_INT >= 24) {
            builder.setChronometerCountDown(true)
        }

        manager.notify(NOTIFICATION_ID, builder.build())
    }
}

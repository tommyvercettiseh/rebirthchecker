package nl.hes.rebirthchecker

import android.app.AlarmManager
import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Build
import android.os.SystemClock
import android.widget.RemoteViews

class RebirthWidgetProvider : AppWidgetProvider() {

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)
        when (intent.action) {
            ACTION_ROTATION_TICK,
            Intent.ACTION_BOOT_COMPLETED,
            Intent.ACTION_TIME_CHANGED,
            Intent.ACTION_TIMEZONE_CHANGED -> updateAll(context)
        }
    }

    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        ids.forEach { updateWidget(context, manager, it) }
        scheduleNext(context)
    }

    companion object {
        const val ACTION_ROTATION_TICK = "nl.hes.rebirthchecker.ROTATION_TICK"

        fun updateAll(context: Context) {
            val manager = AppWidgetManager.getInstance(context)
            val ids = manager.getAppWidgetIds(
                ComponentName(context, RebirthWidgetProvider::class.java)
            )
            ids.forEach { updateWidget(context, manager, it) }
            scheduleNext(context)
        }

        private fun updateWidget(context: Context, manager: AppWidgetManager, id: Int) {
            val views = RemoteViews(context.packageName, R.layout.widget_rebirth)

            if (!RotationState.isCalibrated(context)) {
                views.setTextViewText(R.id.widget_map, "TAP TO SET")
                views.setTextViewText(R.id.widget_next, "MAP 2")
                views.setTextViewText(R.id.widget_later, "MAP 3")
                setFallbackImages(views)
            } else {
                val s = RotationState.snapshot(context)
                val base = SystemClock.elapsedRealtime() + s.remainingSeconds * 1000L

                views.setTextViewText(R.id.widget_map, s.currentMap.uppercase())
                views.setTextColor(
                    R.id.widget_map,
                    if (s.currentMap.equals("Rebirth Island", ignoreCase = true))
                        0xFFA7F432.toInt()
                    else
                        0xFFFFFFFF.toInt()
                )
                views.setTextViewText(R.id.widget_next, s.nextMap.uppercase())
                views.setTextViewText(R.id.widget_later, s.laterMap.uppercase())

                views.setChronometer(R.id.widget_countdown, base, "%s LEFT", true)
                if (Build.VERSION.SDK_INT >= 24) {
                    views.setChronometerCountDown(R.id.widget_countdown, true)
                }

                val currentIndex = s.currentIndex
                val nextIndex = (currentIndex + 1) % 3
                val laterIndex = (currentIndex + 2) % 3

                setMapImage(context, views, R.id.map_current_image, currentIndex)
                setMapImage(context, views, R.id.map_next_image, nextIndex)
                setMapImage(context, views, R.id.map_later_image, laterIndex)
            }

            val open = PendingIntent.getActivity(
                context,
                0,
                Intent(context, MainActivity::class.java),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
            views.setOnClickPendingIntent(R.id.widget_root, open)
            manager.updateAppWidget(id, views)
        }

        private fun setFallbackImages(views: RemoteViews) {
            views.setImageViewResource(R.id.map_current_image, R.drawable.ic_launcher_foreground)
            views.setImageViewResource(R.id.map_next_image, R.drawable.ic_launcher_foreground)
            views.setImageViewResource(R.id.map_later_image, R.drawable.ic_launcher_foreground)
        }

        private fun setMapImage(
            context: Context,
            views: RemoteViews,
            viewId: Int,
            mapIndex: Int
        ) {
            val uriString = RotationState.mapImageUri(context, mapIndex)
            if (uriString.isNullOrBlank()) {
                views.setImageViewResource(viewId, R.drawable.ic_launcher_foreground)
                return
            }

            val bitmap = loadScaledBitmap(context, Uri.parse(uriString))
            if (bitmap != null) {
                views.setImageViewBitmap(viewId, bitmap)
            } else {
                views.setImageViewResource(viewId, R.drawable.ic_launcher_foreground)
            }
        }

        private fun loadScaledBitmap(context: Context, uri: Uri): Bitmap? {
            return try {
                val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                context.contentResolver.openInputStream(uri)?.use {
                    BitmapFactory.decodeStream(it, null, bounds)
                }

                var sample = 1
                while (bounds.outWidth / sample > 640 || bounds.outHeight / sample > 360) {
                    sample *= 2
                }

                val opts = BitmapFactory.Options().apply {
                    inSampleSize = sample.coerceAtLeast(1)
                }

                context.contentResolver.openInputStream(uri)?.use {
                    BitmapFactory.decodeStream(it, null, opts)
                }
            } catch (_: Exception) {
                null
            }
        }

        private fun scheduleNext(context: Context) {
            if (!RotationState.isCalibrated(context)) return

            val s = RotationState.snapshot(context)
            val trigger = System.currentTimeMillis() + s.remainingSeconds * 1000L + 250L
            val am = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
            val pi = PendingIntent.getBroadcast(
                context,
                42,
                Intent(context, RebirthWidgetProvider::class.java)
                    .setAction(ACTION_ROTATION_TICK),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )

            try {
                if (Build.VERSION.SDK_INT >= 31 && !am.canScheduleExactAlarms()) {
                    am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, trigger, pi)
                } else {
                    am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, trigger, pi)
                }
            } catch (_: SecurityException) {
                am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, trigger, pi)
            }
        }
    }
}

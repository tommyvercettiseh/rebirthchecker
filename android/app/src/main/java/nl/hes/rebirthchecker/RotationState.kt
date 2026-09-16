package nl.hes.rebirthchecker

import android.content.Context

data class RotationSnapshot(
    val currentIndex: Int,
    val currentMap: String,
    val nextMap: String,
    val laterMap: String,
    val remainingSeconds: Long
)

object RotationState {
    const val durationSeconds = 600L

    private const val PREFS = "rotation"
    private const val KEY_ANCHOR = "anchor_epoch_ms"
    private const val KEY_INDEX = "anchor_index"

    private val defaults = listOf("Rebirth Island", "Fortune's Keep", "Haven's Hollow")

    fun maps(context: Context): List<String> {
        val p = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return (0..2).map { i -> p.getString("map_name_$i", defaults[i]) ?: defaults[i] }
    }

    fun setMapName(context: Context, index: Int, name: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString("map_name_$index", name.trim().ifEmpty { defaults[index] }).apply()
    }

    fun setMapImageUri(context: Context, index: Int, uri: String?) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString("map_image_$index", uri).apply()
    }

    fun mapImageUri(context: Context, index: Int): String? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString("map_image_$index", null)

    fun calibrate(context: Context, currentIndex: Int, remainingSeconds: Long) {
        val remaining = remainingSeconds.coerceIn(0L, durationSeconds)
        val elapsedInMap = durationSeconds - remaining
        val anchor = System.currentTimeMillis() - elapsedInMap * 1000L

        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putLong(KEY_ANCHOR, anchor)
            .putInt(KEY_INDEX, currentIndex.coerceIn(0, 2))
            .apply()
    }

    fun isCalibrated(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).contains(KEY_ANCHOR)

    fun snapshot(context: Context, now: Long = System.currentTimeMillis()): RotationSnapshot {
        val maps = maps(context)
        val p = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val anchor = p.getLong(KEY_ANCHOR, now)
        val anchorIndex = p.getInt(KEY_INDEX, 0)
        val elapsed = ((now - anchor) / 1000L).coerceAtLeast(0L)
        val completed = elapsed / durationSeconds
        val intoMap = elapsed % durationSeconds
        val index = ((anchorIndex + completed) % 3).toInt()

        return RotationSnapshot(
            currentIndex = index,
            currentMap = maps[index],
            nextMap = maps[(index + 1) % 3],
            laterMap = maps[(index + 2) % 3],
            remainingSeconds = durationSeconds - intoMap
        )
    }
}

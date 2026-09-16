package nl.hes.rebirthchecker

import android.content.Context

data class RotationSnapshot(
    val currentMap: String,
    val nextMap: String,
    val remainingSeconds: Long
)

object RotationState {
    val maps = listOf("Rebirth Island", "Fortune's Keep", "Haven's Hollow")
    const val durationSeconds = 600L
    private const val PREFS = "rotation"
    private const val KEY_ANCHOR = "anchor_epoch_ms"
    private const val KEY_INDEX = "anchor_index"

    fun calibrate(context: Context, currentIndex: Int, remainingSeconds: Long) {
        val remaining = remainingSeconds.coerceIn(0L, durationSeconds)
        val elapsedInMap = durationSeconds - remaining
        val anchor = System.currentTimeMillis() - elapsedInMap * 1000L
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putLong(KEY_ANCHOR, anchor)
            .putInt(KEY_INDEX, currentIndex.coerceIn(maps.indices))
            .apply()
    }

    fun isCalibrated(context: Context) =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).contains(KEY_ANCHOR)

    fun snapshot(context: Context, now: Long = System.currentTimeMillis()): RotationSnapshot {
        val p = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val anchor = p.getLong(KEY_ANCHOR, now)
        val anchorIndex = p.getInt(KEY_INDEX, 0)
        val elapsed = ((now - anchor) / 1000L).coerceAtLeast(0L)
        val completed = elapsed / durationSeconds
        val intoMap = elapsed % durationSeconds
        val index = ((anchorIndex + completed) % maps.size).toInt()
        return RotationSnapshot(
            maps[index],
            maps[(index + 1) % maps.size],
            durationSeconds - intoMap
        )
    }
}

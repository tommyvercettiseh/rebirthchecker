package nl.hes.rebirthchecker

import android.app.AlarmManager
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.widget.*
import android.app.Activity

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val pad = (20 * resources.displayMetrics.density).toInt()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad, pad, pad, pad)
            gravity = Gravity.CENTER_HORIZONTAL
        }
        root.addView(TextView(this).apply { text = "Rebirth Checker"; textSize = 28f })
        root.addView(TextView(this).apply {
            text = "Stel één keer de actuele map en resterende tijd in. Daarna blijft de widget automatisch doorlopen via de systeemklok."
            textSize = 15f; setPadding(0, pad/2, 0, pad)
        })
        val spinner = Spinner(this).apply {
            adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item, RotationState.maps)
        }
        root.addView(spinner, LinearLayout.LayoutParams(-1, -2))
        val minutes = EditText(this).apply {
            hint = "Minuten resterend"; inputType = 2; setText("10")
        }
        root.addView(minutes, LinearLayout.LayoutParams(-1, -2))
        val seconds = EditText(this).apply {
            hint = "Seconden resterend"; inputType = 2; setText("0")
        }
        root.addView(seconds, LinearLayout.LayoutParams(-1, -2))
        root.addView(Button(this).apply {
            text = "KALIBREER & START"
            setOnClickListener {
                val remaining = ((minutes.text.toString().toLongOrNull() ?: 0L) * 60L +
                    (seconds.text.toString().toLongOrNull() ?: 0L)).coerceIn(0L, 600L)
                RotationState.calibrate(this@MainActivity, spinner.selectedItemPosition, remaining)
                RebirthWidgetProvider.updateAll(this@MainActivity)
                requestExactAlarmIfNeeded()
                Toast.makeText(this@MainActivity, "Rotatie opgeslagen en gestart.", Toast.LENGTH_LONG).show()
            }
        }, LinearLayout.LayoutParams(-1, -2))
        setContentView(root)
    }

    private fun requestExactAlarmIfNeeded() {
        if (Build.VERSION.SDK_INT >= 31) {
            val am = getSystemService(AlarmManager::class.java)
            if (!am.canScheduleExactAlarms()) {
                startActivity(Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM,
                    Uri.parse("package:" + packageName)))
            }
        }
    }
}

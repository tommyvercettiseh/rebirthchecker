package nl.hes.rebirthchecker

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.view.Gravity
import android.widget.*

class MainActivity : Activity() {

    private val imageRequestBase = 700
    private lateinit var nameFields: List<EditText>
    private lateinit var imageStatus: List<TextView>

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        try {
            buildUi()
        } catch (t: Throwable) {
            showRecoveryScreen(t)
        }
    }

    private fun buildUi() {
        val density = resources.displayMetrics.density
        val pad = (20 * density).toInt()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad, pad, pad, pad)
            gravity = Gravity.CENTER_HORIZONTAL
        }

        val scroll = ScrollView(this)
        scroll.addView(root)
        setContentView(scroll)

        root.addView(TextView(this).apply {
            text = "REBIRTH CHECKER"
            textSize = 28f
            typeface = android.graphics.Typeface.create("sans-serif-condensed", android.graphics.Typeface.BOLD)
        })

        root.addView(TextView(this).apply {
            text = "Stel je 3 maps één keer in. Kies per map een eigen afbeelding. Daarna blijft de rotatie automatisch doorlopen via de telefoontijd."
            textSize = 15f
            setPadding(0, pad / 2, 0, pad)
        })

        val savedMaps = RotationState.maps(this)
        val fields = mutableListOf<EditText>()
        val statuses = mutableListOf<TextView>()

        repeat(3) { i ->
            val card = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(0, pad / 2, 0, pad / 2)
            }

            card.addView(TextView(this).apply {
                text = "MAP " + (i + 1)
                textSize = 12f
                typeface = android.graphics.Typeface.DEFAULT_BOLD
            })

            val name = EditText(this).apply {
                setText(savedMaps[i])
                hint = "Mapnaam"
                setSingleLine(true)
            }
            fields += name
            card.addView(name, LinearLayout.LayoutParams(-1, -2))

            val status = TextView(this).apply {
                text = if (RotationState.mapImageUri(this@MainActivity, i) != null) {
                    "Afbeelding gekozen ✓"
                } else {
                    "Nog geen afbeelding"
                }
                textSize = 13f
            }
            statuses += status
            card.addView(status)

            card.addView(Button(this).apply {
                text = "KIES AFBEELDING"
                setOnClickListener { chooseImage(i) }
            }, LinearLayout.LayoutParams(-1, -2))

            root.addView(card, LinearLayout.LayoutParams(-1, -2))
        }

        nameFields = fields
        imageStatus = statuses

        root.addView(TextView(this).apply {
            text = "Welke map speelt nu?"
            textSize = 14f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            setPadding(0, pad, 0, 0)
        })

        val spinner = Spinner(this)
        fun refreshSpinner() {
            val names = nameFields.map { it.text.toString().trim().ifEmpty { "Map" } }
            spinner.adapter = ArrayAdapter(
                this,
                android.R.layout.simple_spinner_dropdown_item,
                names
            )
        }
        refreshSpinner()
        root.addView(spinner, LinearLayout.LayoutParams(-1, -2))

        root.addView(Button(this).apply {
            text = "MAPNAMEN BIJWERKEN"
            setOnClickListener {
                saveMapNames()
                refreshSpinner()
                Toast.makeText(this@MainActivity, "Mapnamen bijgewerkt.", Toast.LENGTH_SHORT).show()
            }
        }, LinearLayout.LayoutParams(-1, -2))

        val minutes = EditText(this).apply {
            hint = "Minuten resterend"
            inputType = android.text.InputType.TYPE_CLASS_NUMBER
            setText("10")
        }
        root.addView(minutes, LinearLayout.LayoutParams(-1, -2))

        val seconds = EditText(this).apply {
            hint = "Seconden resterend"
            inputType = android.text.InputType.TYPE_CLASS_NUMBER
            setText("0")
        }
        root.addView(seconds, LinearLayout.LayoutParams(-1, -2))

        root.addView(Button(this).apply {
            text = "KALIBREER & START"
            setOnClickListener {
                saveMapNames()
                val remaining = (
                    (minutes.text.toString().toLongOrNull() ?: 0L) * 60L +
                    (seconds.text.toString().toLongOrNull() ?: 0L)
                ).coerceIn(0L, RotationState.durationSeconds)

                RotationState.calibrate(
                    this@MainActivity,
                    spinner.selectedItemPosition.coerceIn(0, 2),
                    remaining
                )
                RebirthWidgetProvider.updateAll(this@MainActivity)
                Toast.makeText(
                    this@MainActivity,
                    "Klaar. De widget blijft nu automatisch doorlopen.",
                    Toast.LENGTH_LONG
                ).show()
            }
        }, LinearLayout.LayoutParams(-1, -2))
    }

    private fun showRecoveryScreen(t: Throwable) {
        val pad = (20 * resources.displayMetrics.density).toInt()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad, pad, pad, pad)
        }
        root.addView(TextView(this).apply {
            text = "REBIRTH CHECKER"
            textSize = 26f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
        })
        root.addView(TextView(this).apply {
            text = "De app kon de normale interface niet laden, maar is niet afgesloten."
            textSize = 16f
            setPadding(0, pad, 0, pad / 2)
        })
        root.addView(TextView(this).apply {
            text = "Fout: " + (t.javaClass.simpleName ?: "Onbekend") + "\n" + (t.message ?: "Geen details")
            textSize = 13f
            setTextIsSelectable(true)
        })
        root.addView(Button(this).apply {
            text = "RESET INSTELLINGEN"
            setOnClickListener {
                getSharedPreferences("rotation", MODE_PRIVATE).edit().clear().apply()
                recreate()
            }
        })
        setContentView(root)
    }

    private fun saveMapNames() {
        nameFields.forEachIndexed { index, field ->
            RotationState.setMapName(this, index, field.text.toString())
        }
    }

    private fun chooseImage(index: Int) {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            type = "image/*"
            addCategory(Intent.CATEGORY_OPENABLE)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
        }
        startActivityForResult(intent, imageRequestBase + index)
    }

    @Deprecated("Deprecated in Android API, used here for broad device compatibility.")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode != RESULT_OK) return

        val index = requestCode - imageRequestBase
        if (index !in 0..2) return

        val uri = data?.data ?: return
        try {
            contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
        } catch (_: SecurityException) {
        }

        RotationState.setMapImageUri(this, index, uri.toString())
        imageStatus[index].text = "Afbeelding gekozen ✓"
        RebirthWidgetProvider.updateAll(this)
    }

}

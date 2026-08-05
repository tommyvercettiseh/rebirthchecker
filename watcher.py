from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path.home() / ".rebirthchecker"
CONFIG_PATH = DATA_DIR / "config.json"
LOG_PATH = DATA_DIR / "watcher.log"
APP_PATH = BASE_DIR / "app.py"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

DATA_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {message}\n")


def load_config() -> dict:
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        log(f"Config lezen mislukt: {exc}")
    return {}


def config_allows_launch() -> bool:
    return bool(load_config().get("launch_with_gfn", True))


def selected_process_names() -> list[str]:
    config = load_config()
    names = config.get("gfn_process_names")
    if isinstance(names, list):
        return [str(name).strip().lower() for name in names if str(name).strip()]

    legacy = str(config.get("gfn_process_name", "")).strip().lower()
    return [legacy] if legacy else []


def powershell_output(script: str) -> str:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )
    return result.stdout.strip()


def geforce_now_running() -> bool:
    # Dit volgt dezelfde logica als Taakbeheer: alleen de zichtbare app telt,
    # niet alle losse NVIDIA-helperprocessen op de achtergrond.
    script = r"""
$gfn = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowHandle -ne 0 -and (
        $_.ProcessName -match 'GeForceNOW|GeForce Now' -or
        $_.MainWindowTitle -match 'GeForce NOW'
    )
} | Select-Object -First 1
if ($gfn) { '1' } else { '0' }
"""
    if powershell_output(script).endswith("1"):
        return True

    # Compatibiliteitsfallback voor systemen waarop MainWindowHandle tijdelijk
    # leeg blijft tijdens het openen. Alleen expliciet opgeslagen GFN-processen.
    selected = selected_process_names()
    if not selected:
        return False

    escaped = ",".join("'" + name.replace("'", "''") + "'" for name in selected)
    fallback_script = f"""
$names = @({escaped})
$p = Get-Process -ErrorAction SilentlyContinue | Where-Object {{
    $names -contains ($_.ProcessName + '.exe').ToLower() -or
    $names -contains $_.ProcessName.ToLower()
}} | Select-Object -First 1
if ($p) {{ '1' }} else {{ '0' }}
"""
    return powershell_output(fallback_script).endswith("1")


def widget_running() -> bool:
    script = (
        "$p = Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -like '*rebirthchecker*app.py*' }; "
        "if ($p) { exit 0 } else { exit 1 }"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )
    return result.returncode == 0


def start_widget() -> None:
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    executable = pythonw if pythonw.exists() else Path(sys.executable)
    subprocess.Popen([str(executable), str(APP_PATH)], cwd=BASE_DIR, creationflags=CREATE_NO_WINDOW)
    log("Rebirth Checker eenmaal gestart voor deze GeForce NOW-sessie.")


def main() -> None:
    selected = selected_process_names()
    log(f"Watcher gestart. Detectie: zichtbaar GeForce NOW-venster; fallback: {selected or 'geen'}")
    last_gfn_state: bool | None = None
    launched_for_current_session = False

    while True:
        try:
            gfn_running = geforce_now_running()

            if gfn_running != last_gfn_state:
                log(f"GeForce NOW actief: {gfn_running}")
                last_gfn_state = gfn_running

            if not gfn_running:
                launched_for_current_session = False
                time.sleep(3)
                continue

            if config_allows_launch() and not launched_for_current_session:
                if not widget_running():
                    start_widget()
                else:
                    log("Widget draaide al bij start van deze GeForce NOW-sessie.")
                launched_for_current_session = True
                time.sleep(10)
            else:
                time.sleep(3)

        except Exception as exc:
            log(f"Watcherfout: {exc}")
            time.sleep(10)


if __name__ == "__main__":
    main()

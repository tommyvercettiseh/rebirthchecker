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


def config_allows_launch() -> bool:
    try:
        if not CONFIG_PATH.exists():
            return True
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return bool(data.get("launch_with_gfn", True))
    except Exception as exc:
        log(f"Config lezen mislukt: {exc}")
        return True


def process_rows() -> list[str]:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
         "Get-CimInstance Win32_Process | Select-Object Name,ExecutablePath,CommandLine | ConvertTo-Json -Compress"],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )
    return [result.stdout.lower()]


def geforce_now_running() -> bool:
    current = "\n".join(process_rows())
    markers = (
        "geforcenow.exe",
        "geforce now",
        "geforcenowcontainer",
        "geforcenowstreamer",
        "nvidia geforce now",
    )
    return any(marker in current for marker in markers)


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
    log("Rebirth Checker gestart omdat GeForce NOW is gedetecteerd.")


def main() -> None:
    log("Watcher gestart.")
    last_gfn_state = None
    while True:
        try:
            gfn_running = geforce_now_running()
            if gfn_running != last_gfn_state:
                log(f"GeForce NOW actief: {gfn_running}")
                last_gfn_state = gfn_running
            if config_allows_launch() and gfn_running and not widget_running():
                start_widget()
                time.sleep(20)
            else:
                time.sleep(3)
        except Exception as exc:
            log(f"Watcherfout: {exc}")
            time.sleep(10)


if __name__ == "__main__":
    main()

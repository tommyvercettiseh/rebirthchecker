from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = Path.home() / ".rebirthchecker" / "config.json"
APP_PATH = BASE_DIR / "app.py"
PROCESS_NAMES = ("GeForceNOW.exe", "GeForceNOWContainer.exe", "GeForceNOWStreamer.exe")
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def config_allows_launch() -> bool:
    try:
        if not CONFIG_PATH.exists():
            return False
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return bool(data.get("launch_with_gfn", False))
    except Exception:
        return False


def process_list() -> str:
    result = subprocess.run(
        ["tasklist", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )
    return result.stdout.lower()


def geForce_now_running() -> bool:
    current = process_list()
    return any(name.lower() in current for name in PROCESS_NAMES)


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


def main() -> None:
    while True:
        try:
            should_start = config_allows_launch() and geForce_now_running() and not widget_running()
            if should_start:
                start_widget()
                time.sleep(20)
            else:
                time.sleep(3)
        except Exception:
            time.sleep(10)


if __name__ == "__main__":
    main()

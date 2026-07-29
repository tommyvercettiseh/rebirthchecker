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
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    return result.stdout.lower()


def is_running(name: str) -> bool:
    return name.lower() in process_list()


def geForce_now_running() -> bool:
    current = process_list()
    return any(name.lower() in current for name in PROCESS_NAMES)


def start_widget() -> None:
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    executable = pythonw if pythonw.exists() else Path(sys.executable)
    subprocess.Popen(
        [str(executable), str(APP_PATH)],
        cwd=BASE_DIR,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def main() -> None:
    while True:
        try:
            if config_allows_launch() and geForce_now_running() and not is_running("RebirthChecker.exe"):
                # Python-versie: voorkom dubbel starten via window title/process is niet betrouwbaar.
                # De mutex wordt praktisch afgevangen door één watcher-start en een ruime cooldown.
                start_widget()
                time.sleep(30)
            else:
                time.sleep(3)
        except Exception:
            time.sleep(10)


if __name__ == "__main__":
    main()

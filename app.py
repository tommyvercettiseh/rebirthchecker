from __future__ import annotations

import json
import logging
import threading
import time
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:  # launcher installs these
    pystray = None
    Image = None
    ImageDraw = None

APP_NAME = "Rebirth Checker"
APP_VERSION = "0.1.0"
DATA_DIR = Path.home() / ".rebirthchecker"
CONFIG_PATH = DATA_DIR / "config.json"
LOG_PATH = DATA_DIR / "rebirthchecker.log"
DEFAULT_MAPS = ["Haven's Hollow", "Rebirth Island", "Fortune's Keep"]
DEFAULT_DURATION = 10 * 60
REBIRTH_NAME = "Rebirth Island"

DATA_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


@dataclass
class Settings:
    maps: list[str]
    map_duration: int = DEFAULT_DURATION
    current_index: int = 0
    remaining_seconds: int = DEFAULT_DURATION
    always_on_top: bool = True
    compact: bool = False
    ntfy_topic: str = ""
    ntfy_server: str = "https://ntfy.sh"
    notify_rebirth: bool = True

    @classmethod
    def load(cls) -> "Settings":
        if not CONFIG_PATH.exists():
            return cls(maps=DEFAULT_MAPS.copy())
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            raw["maps"] = raw.get("maps") or DEFAULT_MAPS.copy()
            return cls(**raw)
        except Exception:
            logging.exception("Instellingen konden niet worden geladen")
            return cls(maps=DEFAULT_MAPS.copy())

    def save(self) -> None:
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


class RotationEngine:
    def __init__(self, settings: Settings, on_change: Callable[[], None]):
        self.settings = settings
        self.on_change = on_change
        self.running = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def current_map(self) -> str:
        return self.settings.maps[self.settings.current_index % len(self.settings.maps)]

    @property
    def next_map(self) -> str:
        return self.settings.maps[(self.settings.current_index + 1) % len(self.settings.maps)]

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.on_change()

    def pause(self) -> None:
        self.running = False
        self._stop.set()
        self.on_change()

    def reset(self) -> None:
        self.pause()
        self.settings.remaining_seconds = self.settings.map_duration
        self.on_change()

    def skip(self, direction: int = 1) -> None:
        self.settings.current_index = (self.settings.current_index + direction) % len(self.settings.maps)
        self.settings.remaining_seconds = self.settings.map_duration
        self.settings.save()
        self.on_change()

    def _loop(self) -> None:
        while not self._stop.wait(1):
            self.settings.remaining_seconds -= 1
            if self.settings.remaining_seconds <= 0:
                self.settings.current_index = (self.settings.current_index + 1) % len(self.settings.maps)
                self.settings.remaining_seconds = self.settings.map_duration
                self.settings.save()
                self.on_change()
                if self.current_map.lower() == REBIRTH_NAME.lower():
                    send_rebirth_notification(self.settings)
            else:
                self.on_change()


def send_ntfy(settings: Settings, title: str, body: str) -> tuple[bool, str]:
    topic = settings.ntfy_topic.strip()
    if not topic:
        return False, "Vul eerst een ntfy-topic in."
    url = f"{settings.ntfy_server.rstrip('/')}/{topic}"
    request = urllib.request.Request(
        url,
        data=body.encode("utf-8"),
        headers={"Title": title, "Priority": "high", "Tags": "video_game,green_circle"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.status < 300, f"HTTP {response.status}"
    except Exception as exc:
        logging.exception("ntfy-push mislukt")
        return False, str(exc)


def send_rebirth_notification(settings: Settings) -> None:
    if not settings.notify_rebirth:
        return
    threading.Thread(
        target=send_ntfy,
        args=(settings, "🟢 Rebirth Island beschikbaar", "Rebirth Island is nu actief voor ongeveer 10 minuten."),
        daemon=True,
    ).start()


class RebirthApp:
    BG = "#07111b"
    PANEL = "#0c1824"
    BORDER = "#17324a"
    TEXT = "#f4f8fb"
    MUTED = "#8fa2b5"
    BLUE = "#1fa2ff"
    GREEN = "#28d17c"
    RED = "#ff4d57"

    def __init__(self) -> None:
        self.settings = Settings.load()
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("980x620")
        self.root.minsize(760, 480)
        self.root.configure(bg=self.BG)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.engine = RotationEngine(self.settings, self.request_render)
        self.tray_icon = None
        self._render_pending = False
        self._build_ui()
        self.apply_window_options()
        self.render()
        self._start_tray()

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 11, "bold"), padding=9)
        style.configure("TCheckbutton", background=self.PANEL, foreground=self.TEXT)

        self.main = tk.Frame(self.root, bg=self.BG)
        self.main.pack(fill="both", expand=True, padx=18, pady=16)

        header = tk.Frame(self.main, bg=self.BG)
        header.pack(fill="x")
        tk.Label(header, text="RESURGENCE ROTATION TIMER", bg=self.BG, fg=self.TEXT,
                 font=("Segoe UI Semibold", 20)).pack(side="left")
        self.status_label = tk.Label(header, text="● GESTOPT", bg=self.BG, fg=self.MUTED,
                                     font=("Segoe UI", 10, "bold"))
        self.status_label.pack(side="right")

        body = tk.Frame(self.main, bg=self.BG)
        body.pack(fill="both", expand=True, pady=(14, 0))

        self.display_panel = tk.Frame(body, bg=self.PANEL, highlightbackground=self.BORDER,
                                      highlightthickness=1)
        self.display_panel.pack(side="left", fill="both", expand=True, padx=(0, 12))

        side = tk.Frame(body, bg=self.PANEL, width=310, highlightbackground=self.BORDER,
                        highlightthickness=1)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)

        tk.Label(self.display_panel, text="CURRENT MAP", bg=self.PANEL, fg=self.BLUE,
                 font=("Segoe UI", 11, "bold")).pack(pady=(34, 5))
        self.map_label = tk.Label(self.display_panel, bg=self.PANEL, fg=self.TEXT,
                                  font=("Segoe UI Semibold", 32))
        self.map_label.pack()
        self.timer_label = tk.Label(self.display_panel, bg=self.PANEL, fg=self.TEXT,
                                    font=("Segoe UI", 66, "bold"))
        self.timer_label.pack(pady=(22, 0))
        self.rebirth_badge = tk.Label(self.display_panel, text="REBIRTH NU BESCHIKBAAR",
                                      bg=self.GREEN, fg="#03130b", font=("Segoe UI", 12, "bold"),
                                      padx=15, pady=7)
        self.next_label = tk.Label(self.display_panel, bg=self.PANEL, fg=self.MUTED,
                                   font=("Segoe UI", 14, "bold"))
        self.next_label.pack(pady=(16, 20))

        nav = tk.Frame(self.display_panel, bg=self.PANEL)
        nav.pack()
        ttk.Button(nav, text="◀ Vorige", command=lambda: self.engine.skip(-1)).pack(side="left", padx=5)
        self.start_btn = ttk.Button(nav, text="▶ Start", command=self.toggle_timer)
        self.start_btn.pack(side="left", padx=5)
        ttk.Button(nav, text="Volgende ▶", command=lambda: self.engine.skip(1)).pack(side="left", padx=5)

        self.rotation_frame = tk.Frame(self.display_panel, bg=self.PANEL)
        self.rotation_frame.pack(fill="x", padx=26, pady=(28, 20))

        tk.Label(side, text="ROTATIE INSTELLEN", bg=self.PANEL, fg=self.BLUE,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=18, pady=(20, 8))

        form = tk.Frame(side, bg=self.PANEL)
        form.pack(fill="x", padx=18)
        tk.Label(form, text="Resterende tijd (mm:ss)", bg=self.PANEL, fg=self.MUTED).pack(anchor="w")
        self.time_entry = tk.Entry(form, font=("Segoe UI", 14), bg="#111f2d", fg=self.TEXT,
                                   insertbackground=self.TEXT, relief="flat")
        self.time_entry.pack(fill="x", pady=(5, 9), ipady=7)
        ttk.Button(form, text="Tijd toepassen", command=self.apply_time).pack(fill="x")

        tk.Label(side, text="MAPS", bg=self.PANEL, fg=self.BLUE,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=18, pady=(18, 6))
        self.maps_list = tk.Listbox(side, bg="#111f2d", fg=self.TEXT, selectbackground=self.BLUE,
                                    relief="flat", font=("Segoe UI", 11), height=6)
        self.maps_list.pack(fill="x", padx=18)
        map_buttons = tk.Frame(side, bg=self.PANEL)
        map_buttons.pack(fill="x", padx=18, pady=7)
        ttk.Button(map_buttons, text="+", width=4, command=self.add_map).pack(side="left")
        ttk.Button(map_buttons, text="−", width=4, command=self.remove_map).pack(side="left", padx=5)
        ttk.Button(map_buttons, text="↑", width=4, command=lambda: self.move_map(-1)).pack(side="left")
        ttk.Button(map_buttons, text="↓", width=4, command=lambda: self.move_map(1)).pack(side="left", padx=5)

        self.top_var = tk.BooleanVar(value=self.settings.always_on_top)
        self.compact_var = tk.BooleanVar(value=self.settings.compact)
        self.notify_var = tk.BooleanVar(value=self.settings.notify_rebirth)
        tk.Checkbutton(side, text="Altijd bovenop", variable=self.top_var, command=self.save_options,
                       bg=self.PANEL, fg=self.TEXT, selectcolor=self.PANEL, activebackground=self.PANEL).pack(anchor="w", padx=18, pady=(8, 0))
        tk.Checkbutton(side, text="Compacte modus", variable=self.compact_var, command=self.save_options,
                       bg=self.PANEL, fg=self.TEXT, selectcolor=self.PANEL, activebackground=self.PANEL).pack(anchor="w", padx=18)
        tk.Checkbutton(side, text="Push bij Rebirth", variable=self.notify_var, command=self.save_options,
                       bg=self.PANEL, fg=self.TEXT, selectcolor=self.PANEL, activebackground=self.PANEL).pack(anchor="w", padx=18)

        ttk.Button(side, text="Mobiele push instellen", command=self.configure_ntfy).pack(fill="x", padx=18, pady=(12, 5))
        ttk.Button(side, text="Test push", command=self.test_push).pack(fill="x", padx=18)

        self.footer = tk.Label(self.main, text=f"Configuratie: {CONFIG_PATH}   •   Log: {LOG_PATH}",
                               bg=self.BG, fg=self.MUTED, font=("Segoe UI", 9))
        self.footer.pack(anchor="w", pady=(8, 0))

    def apply_time(self) -> None:
        raw = self.time_entry.get().strip()
        try:
            if ":" in raw:
                minutes, seconds = raw.split(":", 1)
                total = int(minutes) * 60 + int(seconds)
            else:
                total = int(raw) * 60
            if total <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(APP_NAME, "Gebruik bijvoorbeeld 6:21 of 10:00.")
            return
        self.settings.remaining_seconds = total
        self.settings.save()
        self.render()

    def toggle_timer(self) -> None:
        self.engine.pause() if self.engine.running else self.engine.start()

    def add_map(self) -> None:
        name = simpledialog.askstring(APP_NAME, "Naam van de nieuwe map:", parent=self.root)
        if name and name.strip():
            self.settings.maps.append(name.strip())
            self.settings.save()
            self.render()

    def remove_map(self) -> None:
        selection = self.maps_list.curselection()
        if not selection or len(self.settings.maps) <= 1:
            return
        index = selection[0]
        self.settings.maps.pop(index)
        self.settings.current_index %= len(self.settings.maps)
        self.settings.save()
        self.render()

    def move_map(self, delta: int) -> None:
        selection = self.maps_list.curselection()
        if not selection:
            return
        old = selection[0]
        new = max(0, min(len(self.settings.maps) - 1, old + delta))
        if new == old:
            return
        item = self.settings.maps.pop(old)
        self.settings.maps.insert(new, item)
        self.settings.save()
        self.render()
        self.maps_list.selection_set(new)

    def save_options(self) -> None:
        self.settings.always_on_top = self.top_var.get()
        self.settings.compact = self.compact_var.get()
        self.settings.notify_rebirth = self.notify_var.get()
        self.settings.save()
        self.apply_window_options()
        self.render()

    def apply_window_options(self) -> None:
        self.root.attributes("-topmost", self.settings.always_on_top)
        if self.settings.compact:
            self.root.geometry("520x310")
            self.root.minsize(440, 260)
        else:
            self.root.minsize(760, 480)

    def configure_ntfy(self) -> None:
        topic = simpledialog.askstring(
            APP_NAME,
            "Vul je geheime ntfy-topic in. Gebruik exact hetzelfde topic in de ntfy-app:",
            initialvalue=self.settings.ntfy_topic,
            parent=self.root,
        )
        if topic is not None:
            self.settings.ntfy_topic = topic.strip()
            self.settings.save()

    def test_push(self) -> None:
        ok, detail = send_ntfy(self.settings, "🎮 Rebirth Checker test", "Je mobiele push werkt.")
        if ok:
            messagebox.showinfo(APP_NAME, "Testmelding verzonden.")
        else:
            messagebox.showerror(APP_NAME, f"Push mislukt: {detail}")

    def request_render(self) -> None:
        if self._render_pending:
            return
        self._render_pending = True
        self.root.after(0, self.render)

    def render(self) -> None:
        self._render_pending = False
        current = self.engine.current_map
        seconds = max(0, self.settings.remaining_seconds)
        minutes, secs = divmod(seconds, 60)
        is_rebirth = current.lower() == REBIRTH_NAME.lower()
        accent = self.GREEN if is_rebirth else self.BLUE

        self.map_label.config(text=current.upper(), fg=accent)
        self.timer_label.config(text=f"{minutes:02d}:{secs:02d}", fg=accent if is_rebirth else self.TEXT)
        self.next_label.config(text=f"VOLGENDE MAP: {self.engine.next_map.upper()}")
        self.status_label.config(text="● ACTIEF" if self.engine.running else "● GEPAUZEERD",
                                 fg=self.GREEN if self.engine.running else self.MUTED)
        self.start_btn.config(text="⏸ Pauze" if self.engine.running else "▶ Start")

        if is_rebirth:
            self.rebirth_badge.pack(before=self.next_label, pady=(10, 0))
        else:
            self.rebirth_badge.pack_forget()

        self.maps_list.delete(0, tk.END)
        for index, name in enumerate(self.settings.maps, start=1):
            prefix = "🟢" if name.lower() == REBIRTH_NAME.lower() else f"{index}."
            self.maps_list.insert(tk.END, f"{prefix} {name}")

        for widget in self.rotation_frame.winfo_children():
            widget.destroy()
        for index, name in enumerate(self.settings.maps):
            active = index == self.settings.current_index
            color = self.GREEN if active and name.lower() == REBIRTH_NAME.lower() else self.BLUE if active else self.MUTED
            label = tk.Label(self.rotation_frame, text=name, bg=self.PANEL, fg=color,
                             font=("Segoe UI", 10, "bold" if active else "normal"), padx=7)
            label.pack(side="left", expand=True)

        if self.settings.compact:
            self.footer.pack_forget()
        else:
            self.footer.pack(anchor="w", pady=(8, 0))

        self.root.title(f"{current} • {minutes:02d}:{secs:02d} • {APP_NAME}")

    def _create_tray_image(self):
        image = Image.new("RGB", (64, 64), self.BG)
        draw = ImageDraw.Draw(image)
        draw.ellipse((10, 10, 54, 54), fill=self.GREEN)
        draw.text((24, 18), "R", fill="#06130c")
        return image

    def _start_tray(self) -> None:
        if pystray is None:
            logging.warning("System tray niet geladen")
            return
        menu = pystray.Menu(
            pystray.MenuItem("Tonen", lambda: self.root.after(0, self.show_window)),
            pystray.MenuItem("Start/Pauze", lambda: self.root.after(0, self.toggle_timer)),
            pystray.MenuItem("Volgende map", lambda: self.root.after(0, self.engine.skip)),
            pystray.MenuItem("Afsluiten", lambda: self.root.after(0, self.quit_app)),
        )
        self.tray_icon = pystray.Icon("rebirthchecker", self._create_tray_image(), APP_NAME, menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_to_tray(self) -> None:
        if self.tray_icon:
            self.root.withdraw()
        else:
            self.quit_app()

    def show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()

    def quit_app(self) -> None:
        self.engine.pause()
        self.settings.save()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    try:
        RebirthApp().run()
    except Exception:
        logging.exception("Onverwachte fout")
        raise

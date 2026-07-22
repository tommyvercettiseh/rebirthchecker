from __future__ import annotations

import json
import logging
import threading
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageDraw, ImageEnhance, ImageTk

try:
    import pystray
except ImportError:
    pystray = None

APP_NAME = "Rebirth Checker"
APP_VERSION = "0.2.1"
DEFAULT_MAPS = ["Rebirth Island", "Fortune's Keep", "Haven's Hollow"]
DEFAULT_DURATION = 600
REBIRTH_NAME = "Rebirth Island"
DATA_DIR = Path.home() / ".rebirthchecker"
CONFIG_PATH = DATA_DIR / "config.json"
LOG_PATH = DATA_DIR / "rebirthchecker.log"
ASSET_DIR = Path(__file__).resolve().parent / "assets"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ASSET_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@dataclass
class Settings:
    maps: list[str]
    image_paths: dict[str, str]
    map_duration: int = DEFAULT_DURATION
    current_index: int = 0
    remaining_seconds: int = DEFAULT_DURATION
    always_on_top: bool = True
    ntfy_topic: str = ""
    ntfy_server: str = "https://ntfy.sh"
    notify_rebirth: bool = True

    @classmethod
    def load(cls) -> "Settings":
        defaults = {
            "Rebirth Island": str(ASSET_DIR / "rebirth-island.jpg"),
            "Fortune's Keep": str(ASSET_DIR / "fortunes-keep.jpg"),
            "Haven's Hollow": str(ASSET_DIR / "havens-hollow.jpg"),
        }
        if not CONFIG_PATH.exists():
            return cls(DEFAULT_MAPS.copy(), defaults)
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            raw.setdefault("maps", DEFAULT_MAPS.copy())
            raw.setdefault("image_paths", defaults)
            raw["current_index"] = int(raw.get("current_index", 0)) % max(1, len(raw["maps"]))
            return cls(**raw)
        except Exception:
            logging.exception("Config laden mislukt")
            return cls(DEFAULT_MAPS.copy(), defaults)

    def save(self) -> None:
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


class RotationEngine:
    def __init__(self, settings: Settings, callback: Callable[[], None]):
        self.settings = settings
        self.callback = callback
        self.running = False
        self._stop = threading.Event()

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
        threading.Thread(target=self._loop, daemon=True).start()
        self.callback()

    def pause(self) -> None:
        self.running = False
        self._stop.set()
        self.callback()

    def skip(self, direction: int = 1) -> None:
        self.settings.current_index = (self.settings.current_index + direction) % len(self.settings.maps)
        self.settings.remaining_seconds = self.settings.map_duration
        self.settings.save()
        self.callback()

    def set_current(self, index: int) -> None:
        self.settings.current_index = index % len(self.settings.maps)
        self.settings.remaining_seconds = self.settings.map_duration
        self.settings.save()
        self.callback()

    def _loop(self) -> None:
        while not self._stop.wait(1):
            self.settings.remaining_seconds -= 1
            if self.settings.remaining_seconds <= 0:
                self.settings.current_index = (self.settings.current_index + 1) % len(self.settings.maps)
                self.settings.remaining_seconds = self.settings.map_duration
                self.settings.save()
                if self.current_map.lower() == REBIRTH_NAME.lower():
                    send_rebirth_notification(self.settings)
            self.callback()


def send_ntfy(settings: Settings, title: str, body: str) -> tuple[bool, str]:
    if not settings.ntfy_topic.strip():
        return False, "Vul eerst een ntfy-topic in."
    request = urllib.request.Request(
        f"{settings.ntfy_server.rstrip('/')}/{settings.ntfy_topic.strip()}",
        data=body.encode("utf-8"),
        headers={"Title": title, "Priority": "high", "Tags": "video_game,green_circle"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.status < 300, f"HTTP {response.status}"
    except Exception as exc:
        logging.exception("Push mislukt")
        return False, str(exc)


def send_rebirth_notification(settings: Settings) -> None:
    if settings.notify_rebirth:
        threading.Thread(
            target=send_ntfy,
            args=(settings, "Rebirth Island beschikbaar", "Rebirth Island is nu actief. Tijd om te joinen."),
            daemon=True,
        ).start()


class RebirthApp:
    WIDTH = 470
    HEIGHT = 265
    SETTINGS_WIDTH = 360
    BG = "#080d11"
    PANEL = "#10171d"
    TEXT = "#f3f5f6"
    MUTED = "#a3adb4"
    GREEN = "#8be83f"
    AMBER = "#ffc538"

    def __init__(self) -> None:
        self.settings = Settings.load()
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.overrideredirect(True)
        self.root.configure(bg=self.BG)
        self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}+80+80")
        self.root.attributes("-topmost", self.settings.always_on_top)
        self.engine = RotationEngine(self.settings, self.request_render)
        self.settings_open = False
        self._render_pending = False
        self._drag_x = 0
        self._drag_y = 0
        self._photos: dict[str, ImageTk.PhotoImage] = {}
        self.tray_icon = None
        self._build_ui()
        self.render()
        self._start_tray()

    def _build_ui(self) -> None:
        self.shell = tk.Frame(self.root, bg="#29323a", bd=1)
        self.shell.pack(fill="both", expand=True)

        self.card = tk.Frame(self.shell, bg=self.BG, width=self.WIDTH, height=self.HEIGHT)
        self.card.pack(side="left", fill="both")
        self.card.pack_propagate(False)

        self.image_label = tk.Label(self.card, bg=self.BG, bd=0)
        self.image_label.place(x=0, y=0, width=self.WIDTH, height=self.HEIGHT)

        self.topbar = tk.Frame(self.card, bg="#151c21")
        self.topbar.place(x=0, y=0, width=self.WIDTH, height=34)
        self.playing_label = tk.Label(self.topbar, text="CURRENTLY PLAYING", bg="#151c21", fg=self.TEXT,
                                      font=("Segoe UI Semibold", 11))
        self.playing_label.pack(side="left", padx=10)
        self.time_label = tk.Label(self.topbar, bg="#151c21", fg=self.TEXT, font=("Segoe UI Semibold", 11))
        self.time_label.pack(side="right", padx=(4, 8))
        self.gear = tk.Button(self.topbar, text="⚙", command=self.toggle_settings, bg="#151c21", fg=self.TEXT,
                              activebackground="#202a31", activeforeground=self.GREEN, bd=0,
                              font=("Segoe UI", 12), cursor="hand2")
        self.gear.pack(side="right")
        self.close_btn = tk.Button(self.topbar, text="×", command=self.hide_to_tray, bg="#151c21", fg=self.MUTED,
                                   activebackground="#202a31", activeforeground=self.TEXT, bd=0,
                                   font=("Segoe UI", 13), cursor="hand2")
        self.close_btn.pack(side="right", padx=(0, 2))

        self.next_box = tk.Frame(self.card, bg="#11181d", highlightbackground="#51616c", highlightthickness=2)
        self.next_box.place(x=290, y=48, width=165, height=96)
        tk.Label(self.next_box, text="NEXT MAP", bg="#11181d", fg=self.TEXT,
                 font=("Segoe UI Semibold", 9)).place(x=7, y=4)
        self.next_image = tk.Label(self.next_box, bg="#11181d")
        self.next_image.place(x=6, y=24, width=151, height=48)
        self.next_name = tk.Label(self.next_box, bg="#11181d", fg=self.TEXT, anchor="w",
                                  font=("Segoe UI Semibold", 9))
        self.next_name.place(x=7, y=73, width=150, height=18)

        self.map_label = tk.Frame(self.card, bg="#05090c")
        self.map_label.place(x=0, y=213, width=self.WIDTH, height=52)
        self.status_dot = tk.Label(self.map_label, text="●", bg="#05090c", fg=self.GREEN,
                                   font=("Segoe UI", 15))
        self.status_dot.pack(side="left", padx=(14, 0))
        self.map_text = tk.Label(self.map_label, bg="#05090c", fg=self.TEXT,
                                 font=("Segoe UI Semibold", 19))
        self.map_text.pack(side="left", padx=(6, 0))

        for widget in (self.topbar, self.playing_label, self.time_label):
            widget.bind("<ButtonPress-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.do_drag)
        self.image_label.bind("<Double-Button-1>", lambda _e: self.toggle_timer())
        self.card.bind("<Button-3>", lambda _e: self.engine.skip())

        self.settings_panel = tk.Frame(self.shell, bg=self.PANEL, width=self.SETTINGS_WIDTH)
        self.settings_panel.pack_propagate(False)
        self._build_settings()

    def _build_settings(self) -> None:
        p = self.settings_panel
        tk.Label(p, text="ROTATION SETTINGS", bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI Semibold", 14)).pack(anchor="w", padx=18, pady=(16, 10))
        tk.Label(p, text="Resterende tijd", bg=self.PANEL, fg=self.MUTED).pack(anchor="w", padx=18)
        self.time_entry = tk.Entry(p, bg="#172128", fg=self.TEXT, insertbackground=self.TEXT,
                                   relief="flat", font=("Segoe UI", 13))
        self.time_entry.pack(fill="x", padx=18, pady=(5, 6), ipady=6)
        tk.Button(p, text="TIJD TOEPASSEN", command=self.apply_time, bg="#26343d", fg=self.TEXT,
                  activebackground="#31434e", activeforeground=self.TEXT, bd=0, pady=7).pack(fill="x", padx=18)

        tk.Label(p, text="Maps in rotatie", bg=self.PANEL, fg=self.MUTED).pack(anchor="w", padx=18, pady=(13, 5))
        self.maps_list = tk.Listbox(p, bg="#172128", fg=self.TEXT, selectbackground="#35511f",
                                    selectforeground=self.GREEN, relief="flat", height=4, font=("Segoe UI", 10),
                                    exportselection=False)
        self.maps_list.pack(fill="x", padx=18)
        self.maps_list.bind("<Double-Button-1>", lambda _e: self.set_current_map())

        row = tk.Frame(p, bg=self.PANEL)
        row.pack(fill="x", padx=18, pady=(7, 5))
        buttons = [
            ("+ MAP", self.add_map),
            ("VERWIJDER", self.remove_map),
            ("OMHOOG", lambda: self.move_map(-1)),
            ("OMLAAG", lambda: self.move_map(1)),
        ]
        for text, cmd in buttons:
            tk.Button(row, text=text, command=cmd, bg="#26343d", fg=self.TEXT, bd=0,
                      padx=7, pady=5).pack(side="left", padx=(0, 4))

        tk.Button(p, text="MAAK HUIDIGE MAP", command=self.set_current_map, bg="#35511f", fg=self.GREEN,
                  activebackground="#456b28", activeforeground=self.TEXT, bd=0, pady=7).pack(fill="x", padx=18, pady=(0, 5))
        tk.Button(p, text="AFBEELDING KIEZEN / WIJZIGEN", command=self.choose_image, bg="#26343d", fg=self.TEXT,
                  activebackground="#31434e", activeforeground=self.TEXT, bd=0, pady=7).pack(fill="x", padx=18, pady=(0, 9))

        self.top_var = tk.BooleanVar(value=self.settings.always_on_top)
        self.notify_var = tk.BooleanVar(value=self.settings.notify_rebirth)
        tk.Checkbutton(p, text="Altijd bovenop", variable=self.top_var, command=self.save_options,
                       bg=self.PANEL, fg=self.TEXT, activebackground=self.PANEL, activeforeground=self.TEXT,
                       selectcolor="#172128").pack(anchor="w", padx=18)
        tk.Checkbutton(p, text="Push bij Rebirth", variable=self.notify_var, command=self.save_options,
                       bg=self.PANEL, fg=self.TEXT, activebackground=self.PANEL, activeforeground=self.TEXT,
                       selectcolor="#172128").pack(anchor="w", padx=18)
        tk.Button(p, text="MOBIELE PUSH INSTELLEN", command=self.configure_ntfy, bg="#26343d", fg=self.TEXT,
                  bd=0, pady=6).pack(fill="x", padx=18, pady=(7, 4))
        tk.Button(p, text="TEST PUSH", command=self.test_push, bg="#35511f", fg=self.GREEN,
                  activebackground="#456b28", activeforeground=self.TEXT, bd=0, pady=6).pack(fill="x", padx=18)
        tk.Label(p, text="Selecteer een map en gebruik de knoppen.\nDubbelklik een map om die direct actief te maken.",
                 bg=self.PANEL, fg=self.MUTED, justify="left", font=("Segoe UI", 8)).pack(anchor="w", padx=18, pady=8)

    def start_drag(self, event) -> None:
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def do_drag(self, event) -> None:
        self.root.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def toggle_settings(self) -> None:
        self.settings_open = not self.settings_open
        if self.settings_open:
            self.settings_panel.pack(side="right", fill="y")
            self.root.geometry(f"{self.WIDTH + self.SETTINGS_WIDTH}x{self.HEIGHT}")
        else:
            self.settings_panel.pack_forget()
            self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}")

    def selected_map_index(self) -> int | None:
        selected = self.maps_list.curselection()
        return selected[0] if selected else None

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

    def add_map(self) -> None:
        name = simpledialog.askstring(APP_NAME, "Naam van de nieuwe map:", parent=self.root)
        if name and name.strip():
            self.settings.maps.append(name.strip())
            self.settings.save()
            self.refresh_maps_list(len(self.settings.maps) - 1)
            self.render()

    def remove_map(self) -> None:
        index = self.selected_map_index()
        if index is None:
            messagebox.showinfo(APP_NAME, "Selecteer eerst een map.")
            return
        if len(self.settings.maps) <= 1:
            messagebox.showinfo(APP_NAME, "Er moet minimaal één map blijven staan.")
            return
        current_name = self.engine.current_map
        removed = self.settings.maps.pop(index)
        self.settings.image_paths.pop(removed, None)
        if current_name in self.settings.maps:
            self.settings.current_index = self.settings.maps.index(current_name)
        else:
            self.settings.current_index = min(index, len(self.settings.maps) - 1)
        self.settings.save()
        self.refresh_maps_list(min(index, len(self.settings.maps) - 1))
        self.render()

    def move_map(self, delta: int) -> None:
        index = self.selected_map_index()
        if index is None:
            messagebox.showinfo(APP_NAME, "Selecteer eerst een map.")
            return
        new_index = max(0, min(len(self.settings.maps) - 1, index + delta))
        if new_index == index:
            return
        current_name = self.engine.current_map
        item = self.settings.maps.pop(index)
        self.settings.maps.insert(new_index, item)
        self.settings.current_index = self.settings.maps.index(current_name)
        self.settings.save()
        self.refresh_maps_list(new_index)
        self.render()

    def set_current_map(self) -> None:
        index = self.selected_map_index()
        if index is None:
            messagebox.showinfo(APP_NAME, "Selecteer eerst de map die nu speelt.")
            return
        self.engine.set_current(index)
        self.refresh_maps_list(index)

    def choose_image(self) -> None:
        index = self.selected_map_index()
        if index is None:
            messagebox.showinfo(APP_NAME, "Selecteer eerst een map in de lijst.")
            return
        map_name = self.settings.maps[index]
        path = filedialog.askopenfilename(
            parent=self.root,
            title=f"Kies afbeelding voor {map_name}",
            filetypes=[("Afbeeldingen", "*.png *.jpg *.jpeg *.webp *.bmp"), ("Alle bestanden", "*.*")],
        )
        if path:
            self.settings.image_paths[map_name] = path
            self.settings.save()
            self._photos.clear()
            self.refresh_maps_list(index)
            self.render()
            messagebox.showinfo(APP_NAME, f"Afbeelding voor {map_name} is opgeslagen.")

    def save_options(self) -> None:
        self.settings.always_on_top = self.top_var.get()
        self.settings.notify_rebirth = self.notify_var.get()
        self.root.attributes("-topmost", self.settings.always_on_top)
        self.settings.save()

    def configure_ntfy(self) -> None:
        topic = simpledialog.askstring(APP_NAME, "Geheim ntfy-topic:", initialvalue=self.settings.ntfy_topic, parent=self.root)
        if topic is not None:
            self.settings.ntfy_topic = topic.strip()
            self.settings.save()

    def test_push(self) -> None:
        ok, detail = send_ntfy(self.settings, "Rebirth Checker test", "Je mobiele push werkt.")
        messagebox.showinfo(APP_NAME, "Testmelding verzonden." if ok else f"Push mislukt: {detail}")

    def toggle_timer(self) -> None:
        self.engine.pause() if self.engine.running else self.engine.start()

    def request_render(self) -> None:
        if not self._render_pending:
            self._render_pending = True
            self.root.after(0, self.render)

    def refresh_maps_list(self, selected_index: int | None = None) -> None:
        if selected_index is None:
            selected_index = self.selected_map_index()
        desired = []
        for index, name in enumerate(self.settings.maps, 1):
            marker = "▶" if index - 1 == self.settings.current_index else str(index)
            desired.append(f"{marker}  {name}")
        existing = list(self.maps_list.get(0, tk.END))
        if existing != desired:
            self.maps_list.delete(0, tk.END)
            for item in desired:
                self.maps_list.insert(tk.END, item)
        if selected_index is not None and 0 <= selected_index < len(self.settings.maps):
            self.maps_list.selection_clear(0, tk.END)
            self.maps_list.selection_set(selected_index)
            self.maps_list.activate(selected_index)

    def _fallback_image(self, name: str, size: tuple[int, int]) -> Image.Image:
        image = Image.new("RGB", size, "#18242c")
        draw = ImageDraw.Draw(image)
        for y in range(size[1]):
            shade = int(30 + 35 * y / max(1, size[1]))
            draw.line((0, y, size[0], y), fill=(shade // 2, shade, shade + 12))
        draw.rectangle((0, size[1] - 70, size[0], size[1]), fill="#0a0f12")
        draw.text((16, size[1] - 48), name.upper(), fill="#dce5e9")
        return image

    def _load_photo(self, name: str, size: tuple[int, int], darken: float = 0.72) -> ImageTk.PhotoImage:
        path_value = self.settings.image_paths.get(name, "")
        key = f"{name}|{path_value}|{size}|{darken}"
        if key in self._photos:
            return self._photos[key]
        path = Path(path_value)
        try:
            image = Image.open(path).convert("RGB") if path.exists() else self._fallback_image(name, size)
        except Exception:
            logging.exception("Afbeelding laden mislukt voor %s", name)
            image = self._fallback_image(name, size)
        target_ratio = size[0] / size[1]
        ratio = image.width / image.height
        if ratio > target_ratio:
            new_width = int(image.height * target_ratio)
            left = (image.width - new_width) // 2
            image = image.crop((left, 0, left + new_width, image.height))
        else:
            new_height = int(image.width / target_ratio)
            top = (image.height - new_height) // 2
            image = image.crop((0, top, image.width, top + new_height))
        image = image.resize(size, Image.Resampling.LANCZOS)
        image = ImageEnhance.Brightness(image).enhance(darken)
        photo = ImageTk.PhotoImage(image)
        self._photos[key] = photo
        return photo

    def render(self) -> None:
        self._render_pending = False
        current = self.engine.current_map
        next_map = self.engine.next_map
        minutes, seconds = divmod(max(0, self.settings.remaining_seconds), 60)
        is_rebirth = current.lower() == REBIRTH_NAME.lower()
        accent = self.GREEN if is_rebirth else self.TEXT

        current_photo = self._load_photo(current, (self.WIDTH, self.HEIGHT), 0.74)
        next_photo = self._load_photo(next_map, (151, 48), 0.88)
        self.image_label.configure(image=current_photo)
        self.image_label.image = current_photo
        self.next_image.configure(image=next_photo)
        self.next_image.image = next_photo
        self.time_label.configure(text=f"{minutes} MIN {seconds:02d} SEC")
        self.map_text.configure(text=current.upper(), fg=accent)
        self.status_dot.configure(fg=self.GREEN if is_rebirth else self.AMBER)
        self.next_name.configure(text=next_map.upper())
        self.playing_label.configure(text="CURRENTLY PLAYING" if self.engine.running else "PAUSED • DOUBLE CLICK TO START")
        self.refresh_maps_list()
        self.root.title(f"{current} • {minutes:02d}:{seconds:02d}")

    def _tray_image(self):
        image = Image.new("RGB", (64, 64), self.BG)
        draw = ImageDraw.Draw(image)
        draw.ellipse((9, 9, 55, 55), fill=self.GREEN)
        draw.rectangle((29, 18, 35, 46), fill="#071008")
        return image

    def _start_tray(self) -> None:
        if pystray is None:
            return
        menu = pystray.Menu(
            pystray.MenuItem("Tonen", lambda: self.root.after(0, self.show_window)),
            pystray.MenuItem("Start/Pauze", lambda: self.root.after(0, self.toggle_timer)),
            pystray.MenuItem("Volgende map", lambda: self.root.after(0, self.engine.skip)),
            pystray.MenuItem("Afsluiten", lambda: self.root.after(0, self.quit_app)),
        )
        self.tray_icon = pystray.Icon("rebirthchecker", self._tray_image(), APP_NAME, menu)
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

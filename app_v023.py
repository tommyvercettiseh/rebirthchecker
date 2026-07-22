from __future__ import annotations

import ctypes
import json
import logging
import os
from pathlib import Path

import tkinter as tk

import app as base_app


base_app.APP_VERSION = "0.2.3"

APPEARANCE_PATH = base_app.DATA_DIR / "appearance.json"
DEFAULT_APPEARANCE = {
    "corner_radius": 18,
    "opacity": 96,
}


def load_appearance() -> dict[str, int]:
    try:
        if APPEARANCE_PATH.exists():
            raw = json.loads(APPEARANCE_PATH.read_text(encoding="utf-8"))
        else:
            raw = {}
    except Exception:
        logging.exception("Appearance-instellingen konden niet worden geladen")
        raw = {}

    corner_radius = max(0, min(40, int(raw.get("corner_radius", DEFAULT_APPEARANCE["corner_radius"]))))
    opacity = max(65, min(100, int(raw.get("opacity", DEFAULT_APPEARANCE["opacity"]))))
    return {"corner_radius": corner_radius, "opacity": opacity}


def save_appearance(data: dict[str, int]) -> None:
    try:
        APPEARANCE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        logging.exception("Appearance-instellingen konden niet worden opgeslagen")


class RebirthAppV023(base_app.RebirthApp):
    SETTINGS_HEIGHT = 720

    def __init__(self) -> None:
        self.appearance = load_appearance()
        super().__init__()
        self.apply_opacity()
        self.root.after(100, self.apply_corner_radius)
        self.root.bind("<Configure>", self._on_window_configure, add="+")

    def _build_settings(self) -> None:
        super()._build_settings()
        panel = self.settings_panel

        separator = tk.Frame(panel, bg="#26343d", height=1)
        separator.pack(fill="x", padx=18, pady=(13, 10))

        header = tk.Frame(panel, bg=self.PANEL)
        header.pack(fill="x", padx=18)
        tk.Label(
            header,
            text="WEERGAVE",
            bg=self.PANEL,
            fg=self.TEXT,
            font=("Segoe UI Semibold", 10),
        ).pack(side="left")

        self.corner_value = tk.Label(
            header,
            text=f"{self.appearance['corner_radius']} px",
            bg=self.PANEL,
            fg=self.GREEN,
            font=("Segoe UI Semibold", 9),
        )
        self.corner_value.pack(side="right")

        tk.Label(
            panel,
            text="Hoekafronding",
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=18, pady=(8, 0))

        self.corner_var = tk.IntVar(value=self.appearance["corner_radius"])
        self.corner_scale = tk.Scale(
            panel,
            from_=0,
            to=40,
            orient="horizontal",
            variable=self.corner_var,
            command=self.change_corner_radius,
            showvalue=False,
            resolution=1,
            bg=self.PANEL,
            fg=self.TEXT,
            troughcolor="#26343d",
            activebackground=self.GREEN,
            highlightthickness=0,
            bd=0,
            sliderlength=16,
        )
        self.corner_scale.pack(fill="x", padx=14)

        opacity_header = tk.Frame(panel, bg=self.PANEL)
        opacity_header.pack(fill="x", padx=18, pady=(4, 0))
        tk.Label(
            opacity_header,
            text="Opacity",
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Segoe UI", 9),
        ).pack(side="left")

        self.opacity_value = tk.Label(
            opacity_header,
            text=f"{self.appearance['opacity']}%",
            bg=self.PANEL,
            fg=self.GREEN,
            font=("Segoe UI Semibold", 9),
        )
        self.opacity_value.pack(side="right")

        self.opacity_var = tk.IntVar(value=self.appearance["opacity"])
        self.opacity_scale = tk.Scale(
            panel,
            from_=65,
            to=100,
            orient="horizontal",
            variable=self.opacity_var,
            command=self.change_opacity,
            showvalue=False,
            resolution=1,
            bg=self.PANEL,
            fg=self.TEXT,
            troughcolor="#26343d",
            activebackground=self.GREEN,
            highlightthickness=0,
            bd=0,
            sliderlength=16,
        )
        self.opacity_scale.pack(fill="x", padx=14)

        tk.Label(
            panel,
            text="De transparantie geldt voor de complete widget en wordt automatisch opgeslagen.",
            bg=self.PANEL,
            fg=self.MUTED,
            justify="left",
            wraplength=self.SETTINGS_WIDTH - 36,
            font=("Segoe UI", 8),
        ).pack(anchor="w", padx=18, pady=(2, 0))

    def _on_window_configure(self, _event=None) -> None:
        if not getattr(self, "_corner_job", None):
            self._corner_job = self.root.after(40, self._apply_corner_after_resize)

    def _apply_corner_after_resize(self) -> None:
        self._corner_job = None
        self.apply_corner_radius()

    def change_corner_radius(self, value: str) -> None:
        radius = max(0, min(40, int(float(value))))
        self.appearance["corner_radius"] = radius
        self.corner_value.configure(text=f"{radius} px")
        save_appearance(self.appearance)
        self.apply_corner_radius()

    def change_opacity(self, value: str) -> None:
        opacity = max(65, min(100, int(float(value))))
        self.appearance["opacity"] = opacity
        self.opacity_value.configure(text=f"{opacity}%")
        save_appearance(self.appearance)
        self.apply_opacity()

    def apply_opacity(self) -> None:
        self.root.attributes("-alpha", self.appearance["opacity"] / 100.0)

    def apply_corner_radius(self) -> None:
        if os.name != "nt":
            return
        try:
            self.root.update_idletasks()
            width = max(1, self.root.winfo_width())
            height = max(1, self.root.winfo_height())
            radius = max(0, int(self.appearance["corner_radius"]))
            hwnd = self.root.winfo_id()

            if radius <= 0:
                region = ctypes.windll.gdi32.CreateRectRgn(0, 0, width + 1, height + 1)
            else:
                diameter = radius * 2
                region = ctypes.windll.gdi32.CreateRoundRectRgn(
                    0,
                    0,
                    width + 1,
                    height + 1,
                    diameter,
                    diameter,
                )
            ctypes.windll.user32.SetWindowRgn(hwnd, region, True)
        except Exception:
            logging.exception("Hoekafronding toepassen mislukt")

    def toggle_settings(self) -> None:
        super().toggle_settings()
        self.root.after(60, self.apply_corner_radius)


if __name__ == "__main__":
    try:
        RebirthAppV023().run()
    except Exception:
        logging.exception("Onverwachte fout in v0.2.3")
        raise

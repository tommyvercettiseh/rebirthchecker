from __future__ import annotations

import csv
import io
import json
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

DATA_DIR = Path.home() / ".rebirthchecker"
CONFIG_PATH = DATA_DIR / "config.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def list_processes() -> list[tuple[str, str]]:
    result = subprocess.run(
        ["tasklist", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    rows: list[tuple[str, str]] = []
    for row in csv.reader(io.StringIO(result.stdout)):
        if len(row) >= 2:
            rows.append((row[0], row[1]))
    return sorted(rows, key=lambda item: item[0].lower())


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_process(process_name: str) -> None:
    config = load_config()
    config["launch_with_gfn"] = True
    config["gfn_process_name"] = process_name
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


class ProcessSelector:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Rebirth Checker - Kies GeForce NOW proces")
        self.root.geometry("620x520")
        self.root.minsize(560, 440)
        self.root.configure(bg="#10171d")

        tk.Label(
            self.root,
            text="KIES HET GEFORCE NOW-PROCES",
            bg="#10171d",
            fg="#f3f5f6",
            font=("Segoe UI Semibold", 16),
        ).pack(anchor="w", padx=20, pady=(18, 4))
        tk.Label(
            self.root,
            text="Laat GeForce NOW openstaan, zoek hieronder op NVIDIA of GeForce en selecteer het proces.",
            bg="#10171d",
            fg="#a3adb4",
            wraplength=570,
            justify="left",
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=20, pady=(0, 12))

        search_row = tk.Frame(self.root, bg="#10171d")
        search_row.pack(fill="x", padx=20)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        tk.Entry(
            search_row,
            textvariable=self.search_var,
            bg="#172128",
            fg="#f3f5f6",
            insertbackground="#f3f5f6",
            relief="flat",
            font=("Segoe UI", 11),
        ).pack(side="left", fill="x", expand=True, ipady=7)
        tk.Button(
            search_row,
            text="VERVERSEN",
            command=self.reload_processes,
            bg="#26343d",
            fg="#f3f5f6",
            bd=0,
            padx=14,
            pady=8,
            cursor="hand2",
        ).pack(side="left", padx=(8, 0))

        frame = tk.Frame(self.root, bg="#10171d")
        frame.pack(fill="both", expand=True, padx=20, pady=12)
        self.tree = ttk.Treeview(frame, columns=("process", "pid"), show="headings", selectmode="browse")
        self.tree.heading("process", text="Procesnaam")
        self.tree.heading("pid", text="PID")
        self.tree.column("process", width=430, anchor="w")
        self.tree.column("pid", width=100, anchor="center")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda _event: self.save_selection())

        self.status = tk.Label(self.root, bg="#10171d", fg="#8be83f", font=("Segoe UI", 10))
        self.status.pack(anchor="w", padx=20, pady=(0, 8))

        button_row = tk.Frame(self.root, bg="#10171d")
        button_row.pack(fill="x", padx=20, pady=(0, 18))
        tk.Button(
            button_row,
            text="SELECTIE OPSLAAN",
            command=self.save_selection,
            bg="#35511f",
            fg="#8be83f",
            activebackground="#456c28",
            activeforeground="#f3f5f6",
            bd=0,
            padx=14,
            pady=10,
            cursor="hand2",
        ).pack(side="right")
        tk.Button(
            button_row,
            text="ANNULEREN",
            command=self.root.destroy,
            bg="#26343d",
            fg="#f3f5f6",
            bd=0,
            padx=14,
            pady=10,
            cursor="hand2",
        ).pack(side="right", padx=(0, 8))

        self.processes: list[tuple[str, str]] = []
        self.reload_processes()

    def reload_processes(self) -> None:
        self.processes = list_processes()
        self.refresh()

    def refresh(self) -> None:
        query = self.search_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        matches = [item for item in self.processes if not query or query in item[0].lower()]
        for process, pid in matches:
            self.tree.insert("", "end", values=(process, pid))
        self.status.configure(text=f"{len(matches)} processen zichtbaar")

    def save_selection(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Rebirth Checker", "Selecteer eerst een proces.", parent=self.root)
            return
        values = self.tree.item(selected[0], "values")
        process_name = str(values[0])
        save_process(process_name)
        messagebox.showinfo(
            "Rebirth Checker",
            f"Opgeslagen proces: {process_name}\n\nDe watcher gebruikt dit proces voortaan als GeForce NOW-trigger.",
            parent=self.root,
        )
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    ProcessSelector().run()

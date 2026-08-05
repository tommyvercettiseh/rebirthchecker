from __future__ import annotations

import csv
import io
import json
import subprocess
import tkinter as tk
from collections import defaultdict
from pathlib import Path
from tkinter import messagebox, ttk

DATA_DIR = Path.home() / ".rebirthchecker"
CONFIG_PATH = DATA_DIR / "config.json"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DATA_DIR.mkdir(parents=True, exist_ok=True)

GFN_MARKERS = ("geforcenow", "geforce now", "nvidia geforce now")


def raw_processes() -> list[tuple[str, str]]:
    result = subprocess.run(
        ["tasklist", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )
    rows: list[tuple[str, str]] = []
    for row in csv.reader(io.StringIO(result.stdout)):
        if len(row) >= 2:
            rows.append((row[0], row[1]))
    return rows


def grouped_processes() -> list[dict]:
    groups: dict[str, list[str]] = defaultdict(list)
    gfn_names: set[str] = set()
    gfn_pids: list[str] = []

    for name, pid in raw_processes():
        lowered = name.lower()
        if any(marker in lowered for marker in GFN_MARKERS):
            gfn_names.add(name)
            gfn_pids.append(pid)
        else:
            groups[name].append(pid)

    rows: list[dict] = []
    if gfn_pids:
        rows.append(
            {
                "display": f"NVIDIA GeForce NOW ({len(gfn_pids)})",
                "count": len(gfn_pids),
                "pids": ", ".join(gfn_pids),
                "names": sorted(gfn_names, key=str.lower),
                "is_gfn": True,
            }
        )

    for name, pids in sorted(groups.items(), key=lambda item: item[0].lower()):
        rows.append(
            {
                "display": f"{name} ({len(pids)})" if len(pids) > 1 else name,
                "count": len(pids),
                "pids": ", ".join(pids),
                "names": [name],
                "is_gfn": False,
            }
        )
    return rows


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_gfn_group(process_names: list[str]) -> None:
    config = load_config()
    config["launch_with_gfn"] = True
    config["gfn_detection_mode"] = "visible_window"
    config["gfn_process_names"] = process_names
    config.pop("gfn_process_name", None)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


class ProcessSelector:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Rebirth Checker · GeForce NOW koppelen")
        self.root.geometry("860x610")
        self.root.minsize(720, 500)
        self.root.configure(bg="#f7f4f1")

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#202124",
            rowheight=34,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview.Heading",
            background="#fafafa",
            foreground="#50545a",
            relief="flat",
            font=("Segoe UI Semibold", 10),
        )
        style.map("Treeview", background=[("selected", "#d8efff")], foreground=[("selected", "#111111")])

        header = tk.Frame(self.root, bg="#ffffff", height=58)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text="Rebirth Checker",
            bg="#ffffff",
            fg="#202124",
            font=("Segoe UI Semibold", 12),
        ).pack(side="left", padx=20)

        content = tk.Frame(self.root, bg="#f7f4f1")
        content.pack(fill="both", expand=True, padx=24, pady=22)

        tk.Label(
            content,
            text="GeForce NOW-process kiezen",
            bg="#f7f4f1",
            fg="#202124",
            font=("Segoe UI Semibold", 17),
        ).pack(anchor="w")
        tk.Label(
            content,
            text="Processen worden gegroepeerd zoals in Taakbeheer. Kies de regel NVIDIA GeForce NOW.",
            bg="#f7f4f1",
            fg="#61656b",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 14))

        search_row = tk.Frame(content, bg="#f7f4f1")
        search_row.pack(fill="x")
        self.search_var = tk.StringVar(value="GeForce")
        self.search_var.trace_add("write", lambda *_: self.refresh())
        tk.Entry(
            search_row,
            textvariable=self.search_var,
            bg="#ffffff",
            fg="#202124",
            insertbackground="#202124",
            relief="solid",
            bd=1,
            font=("Segoe UI", 10),
        ).pack(side="left", fill="x", expand=True, ipady=8)
        tk.Button(
            search_row,
            text="Vernieuwen",
            command=self.reload_processes,
            bg="#ffffff",
            fg="#202124",
            relief="solid",
            bd=1,
            padx=16,
            pady=8,
            cursor="hand2",
        ).pack(side="left", padx=(10, 0))

        frame = tk.Frame(content, bg="#ffffff", bd=1, relief="solid")
        frame.pack(fill="both", expand=True, pady=14)
        self.tree = ttk.Treeview(frame, columns=("name", "count", "pids"), show="headings", selectmode="browse")
        self.tree.heading("name", text="Naam")
        self.tree.heading("count", text="Processen")
        self.tree.heading("pids", text="PID")
        self.tree.column("name", width=430, anchor="w")
        self.tree.column("count", width=100, anchor="center")
        self.tree.column("pids", width=230, anchor="w")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda _event: self.save_selection())

        footer = tk.Frame(content, bg="#f7f4f1")
        footer.pack(fill="x")
        self.status = tk.Label(footer, bg="#f7f4f1", fg="#61656b", font=("Segoe UI", 9))
        self.status.pack(side="left")
        tk.Button(
            footer,
            text="Koppelen",
            command=self.save_selection,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            bd=0,
            padx=22,
            pady=10,
            cursor="hand2",
            font=("Segoe UI Semibold", 10),
        ).pack(side="right")

        self.rows: list[dict] = []
        self.visible_rows: dict[str, dict] = {}
        self.reload_processes()

    def reload_processes(self) -> None:
        self.rows = grouped_processes()
        self.refresh()

    def refresh(self) -> None:
        query = self.search_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        self.visible_rows.clear()

        matches = [row for row in self.rows if not query or query in row["display"].lower()]
        gfn_item = None
        for index, row in enumerate(matches):
            item = self.tree.insert("", "end", values=(row["display"], row["count"], row["pids"]))
            self.visible_rows[item] = row
            if row["is_gfn"]:
                gfn_item = item

        if gfn_item:
            self.tree.selection_set(gfn_item)
            self.tree.focus(gfn_item)
        self.status.configure(text=f"{len(matches)} gegroepeerde processen zichtbaar")

    def save_selection(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Rebirth Checker", "Selecteer eerst NVIDIA GeForce NOW.", parent=self.root)
            return

        row = self.visible_rows.get(selected[0])
        if not row or not row["is_gfn"]:
            messagebox.showwarning(
                "Rebirth Checker",
                "Kies de gegroepeerde regel NVIDIA GeForce NOW. Andere processen zijn geen betrouwbare trigger.",
                parent=self.root,
            )
            return

        save_gfn_group(row["names"])
        messagebox.showinfo(
            "Rebirth Checker",
            f"GeForce NOW is gekoppeld als één appgroep met {row['count']} processen.\n\nDe watcher start voortaan op het zichtbare GeForce NOW-venster.",
            parent=self.root,
        )
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    ProcessSelector().run()

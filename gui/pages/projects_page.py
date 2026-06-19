"""案件管理画面。"""
import glob
import json
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import config
from gui.theme import (
    C_BG, C_PANEL, C_ACCENT, C_BORDER, C_DANGER, C_ON, C_OFF, C_SELECTED,
    FONT_NORMAL, FONT_BOLD, FONT_SMALL, FONT_LARGE,
)
from gui.widgets import ToggleSwitch

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _parse_py_config(filepath: str) -> dict:
    try:
        content = open(filepath, encoding="utf-8").read()
    except Exception:
        return {}

    def extract(varname: str) -> str:
        m = re.search(
            rf'^{varname}\s*=\s*(?:"([^"]*)"|\'([^\']*)\')',
            content, re.MULTILINE
        )
        return (m.group(1) or m.group(2)) if m else ""

    base_url = extract("BASE_URL")
    m = re.search(r"/services/(\d+)/", base_url)
    return {
        "service_name":   extract("SERVICE_NAME"),
        "service_id":     m.group(1) if m else "",
        "spreadsheet_id": extract("SPREADSHEET_ID"),
        "sheet_name":     extract("SHEET_NAME"),
        "comment":        extract("COMMENT"),
        "enabled":        True,
    }


def _slugify(name: str) -> str:
    s = re.sub(r"[^\w]", "_", name, flags=re.ASCII)
    return s.strip("_") or "project"


# ---------------------------------------------------------------------------
# インポートダイアログ
# ---------------------------------------------------------------------------

class _ImportDialog(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title(".py ファイルからインポート")
        self.geometry("600x440")
        self.resizable(False, False)
        self.configure(bg=C_BG)
        self.callback = callback
        self._parsed: list[tuple[str, dict, tk.BooleanVar]] = []
        self._build()
        self.grab_set()

    def _build(self):
        tk.Label(self, text=".py ファイルからインポート",
                 font=FONT_LARGE, bg=C_BG).pack(anchor="w", padx=16, pady=(14, 2))
        tk.Label(self, text="インポートするファイルを選択してから「インポート」を押してください。",
                 font=FONT_SMALL, bg=C_BG, fg="#555").pack(anchor="w", padx=16, pady=(0, 10))

        bf = tk.Frame(self, bg=C_BG)
        bf.pack(fill="x", padx=16)
        tk.Button(bf, text="ファイルを選択…", command=self._pick,
                  bg=C_ACCENT, fg="white", relief="flat",
                  padx=10, pady=4).pack(side="left")
        tk.Button(bf, text="archive_v1 を自動スキャン", command=self._autoscan,
                  relief="flat", padx=10, pady=4).pack(side="left", padx=(8, 0))

        wrap = tk.Frame(self, bg=C_BORDER, bd=1)
        wrap.pack(fill="both", expand=True, padx=16, pady=10)
        self._list_frame = tk.Frame(wrap, bg=C_PANEL)
        self._list_frame.pack(fill="both", expand=True)

        foot = tk.Frame(self, bg=C_BG)
        foot.pack(fill="x", padx=16, pady=(0, 14))
        tk.Button(foot, text="キャンセル", command=self.destroy,
                  relief="flat", padx=12, pady=5).pack(side="right")
        tk.Button(foot, text="インポート", command=self._do_import,
                  bg=C_ACCENT, fg="white", relief="flat",
                  padx=12, pady=5).pack(side="right", padx=(0, 8))

    def _load(self, paths):
        for w in self._list_frame.winfo_children():
            w.destroy()
        self._parsed.clear()
        for path in paths:
            data = _parse_py_config(path)
            if not data.get("service_id"):
                continue
            var = tk.BooleanVar(value=True)
            self._parsed.append((os.path.basename(path), data, var))
            row = tk.Frame(self._list_frame, bg=C_PANEL)
            row.pack(fill="x", padx=8, pady=3)
            tk.Checkbutton(row, variable=var, bg=C_PANEL).pack(side="left")
            label = (f"{data['service_name']}  [ID:{data['service_id']}]"
                     f"  シート:{data['sheet_name']}")
            tk.Label(row, text=label, bg=C_PANEL, font=FONT_SMALL).pack(side="left")
        if not self._parsed:
            tk.Label(self._list_frame,
                     text="インポート可能なファイルが見つかりませんでした。",
                     fg="gray", bg=C_PANEL, font=FONT_NORMAL).pack(pady=20)

    def _pick(self):
        paths = filedialog.askopenfilenames(
            title=".py ファイルを選択",
            filetypes=[("Python files", "*.py"), ("All", "*.*")]
        )
        if paths:
            self._load(list(paths))

    def _autoscan(self):
        scan_dir = os.path.normpath(
            os.path.join(config.resource_path(""), "..", "archive_v1", "projects")
        )
        paths = glob.glob(os.path.join(scan_dir, "*.py"))
        if not paths:
            messagebox.showinfo("スキャン結果",
                                f"archive_v1/projects/ に .py が見つかりませんでした。\nパス: {scan_dir}")
            return
        self._load(paths)

    def _do_import(self):
        selected = [(f, d) for f, d, v in self._parsed if v.get()]
        if not selected:
            messagebox.showwarning("未選択", "インポートするファイルを選択してください。")
            return
        self.callback(selected)
        self.destroy()


# ---------------------------------------------------------------------------
# 案件管理ページ本体
# ---------------------------------------------------------------------------

class ProjectsPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C_BG)
        self._app = app
        self._projects: dict[str, dict] = {}
        self._row_widgets: dict[str, dict] = {}
        self._selected: str = ""
        self._form_entries: dict[str, tk.Widget] = {}
        self._enabled_toggle: ToggleSwitch | None = None
        self._enabled_lbl: tk.Label | None = None
        os.makedirs(config.PROJECTS_DIR, exist_ok=True)
        self._load_all()
        self._build()
        self._refresh_list()
        self._set_form_editable(False)

    def on_show(self):
        pass

    def on_hide(self):
        pass

    # ── データ I/O ────────────────────────────────────────────────────

    def _load_all(self):
        self._projects.clear()
        for path in sorted(glob.glob(os.path.join(config.PROJECTS_DIR, "*.json"))):
            stem = os.path.splitext(os.path.basename(path))[0]
            try:
                with open(path, encoding="utf-8") as f:
                    p = json.load(f)
                p.setdefault("enabled", True)
                p.setdefault("comment", "")
                self._projects[stem] = p
            except Exception:
                pass

    def _save(self, stem: str):
        path = os.path.join(config.PROJECTS_DIR, f"{stem}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._projects[stem], f, ensure_ascii=False, indent=2)

    def _delete_file(self, stem: str):
        path = os.path.join(config.PROJECTS_DIR, f"{stem}.json")
        if os.path.exists(path):
            os.remove(path)

    # ── UI 構築 ───────────────────────────────────────────────────────

    def _build(self):
        # ヘッダー
        hdr = tk.Frame(self, bg=C_BG)
        hdr.pack(fill="x", padx=24, pady=(20, 0))
        tk.Label(hdr, text="案件管理", font=FONT_LARGE, bg=C_BG).pack(side="left")

        # ツールバー
        tb = tk.Frame(self, bg=C_BG)
        tb.pack(fill="x", padx=24, pady=(10, 0))
        self._btn(tb, "＋ 新規追加", self._new,    C_ACCENT,  "white").pack(side="left")
        self._btn(tb, "🗑 削除",     self._delete,  C_DANGER,  "white").pack(side="left", padx=(6, 0))
        self._btn(tb, "📥 .py インポート", self._open_import,
                  "#5f6368", "white").pack(side="left", padx=(6, 0))

        # ペイン
        pane = tk.PanedWindow(self, orient="horizontal",
                              bg=C_BG, sashwidth=5, sashrelief="flat")
        pane.pack(fill="both", expand=True, padx=24, pady=(10, 16))

        left = tk.Frame(pane, bg=C_BG)
        pane.add(left, minsize=200, width=270)
        self._build_list(left)

        right = tk.Frame(pane, bg=C_BG)
        pane.add(right, minsize=360)
        self._build_form(right)

    def _btn(self, parent, text, cmd, bg="#e8eaed", fg="#202124"):
        return tk.Button(parent, text=text, command=cmd,
                         bg=bg, fg=fg, activebackground=bg,
                         relief="flat", font=FONT_NORMAL,
                         padx=10, pady=5, cursor="hand2")

    def _build_list(self, parent):
        tk.Label(parent, text="案件一覧", bg=C_BG, font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        outer = tk.Frame(parent, bg=C_BORDER, bd=1)
        outer.pack(fill="both", expand=True)
        self._canvas = tk.Canvas(outer, bg=C_PANEL, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        self._list_inner = tk.Frame(self._canvas, bg=C_PANEL)
        cw = self._canvas.create_window((0, 0), window=self._list_inner, anchor="nw")
        self._list_inner.bind("<Configure>",
                              lambda e: self._canvas.configure(
                                  scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
                          lambda e: self._canvas.itemconfig(cw, width=e.width))
        self._canvas.bind_all("<MouseWheel>",
                              lambda e: self._canvas.yview_scroll(
                                  -1 * (e.delta // 120), "units"))

    def _build_form(self, parent):
        tk.Label(parent, text="案件の編集", bg=C_BG, font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        wrap = tk.Frame(parent, bg=C_BORDER, bd=1)
        wrap.pack(fill="both", expand=True)
        form = tk.Frame(wrap, bg=C_PANEL, padx=20, pady=16)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)

        fields = [
            ("案件名",              "service_name",   False),
            ("サービスID（6桁）",   "service_id",     False),
            ("スプレッドシートID",  "spreadsheet_id", False),
            ("シート名",            "sheet_name",     False),
            ("コメント",            "comment",        True),
        ]
        for row_i, (label, key, multi) in enumerate(fields):
            tk.Label(form, text=label, bg=C_PANEL, anchor="w",
                     font=FONT_NORMAL).grid(row=row_i, column=0, sticky="nw",
                                            padx=(0, 12), pady=(10, 0))
            if multi:
                w = tk.Text(form, height=3, relief="solid", bd=1,
                            font=FONT_NORMAL, wrap="word")
                w.grid(row=row_i, column=1, sticky="ew", pady=(10, 0))
            else:
                sv = tk.StringVar()
                w = ttk.Entry(form, textvariable=sv, font=FONT_NORMAL)
                w.grid(row=row_i, column=1, sticky="ew", ipady=4, pady=(10, 0))
                w._sv = sv  # type: ignore[attr-defined]
            self._form_entries[key] = w

        # トグル
        tog_row = tk.Frame(form, bg=C_PANEL)
        tog_row.grid(row=len(fields), column=0, columnspan=2,
                     sticky="w", pady=(16, 0))
        tk.Label(tog_row, text="有効 / 無効", bg=C_PANEL, font=FONT_NORMAL).pack(side="left")
        self._enabled_toggle = ToggleSwitch(
            tog_row, value=True, bg=C_PANEL,
            on_change=self._on_form_toggle
        )
        self._enabled_toggle.pack(side="left", padx=(12, 8))
        self._enabled_lbl = tk.Label(tog_row, text="有効", fg=C_ON,
                                     bg=C_PANEL, font=FONT_BOLD)
        self._enabled_lbl.pack(side="left")

        # 保存
        save_row = tk.Frame(form, bg=C_PANEL)
        save_row.grid(row=len(fields) + 1, column=0, columnspan=2,
                      sticky="e", pady=(20, 0))
        self._btn(save_row, "保存", self._save_form, C_ACCENT, "white").pack(side="right")

    # ── リスト ────────────────────────────────────────────────────────

    def _refresh_list(self):
        for w in self._list_inner.winfo_children():
            w.destroy()
        self._row_widgets.clear()
        for stem, proj in self._projects.items():
            self._add_row(stem, proj)
        if self._selected and self._selected not in self._projects:
            self._selected = ""
            self._set_form_editable(False)

    def _add_row(self, stem: str, proj: dict):
        frame = tk.Frame(self._list_inner, bg=C_PANEL, cursor="hand2")
        frame.pack(fill="x")
        tog = ToggleSwitch(frame, value=proj.get("enabled", True), bg=C_PANEL,
                           on_change=lambda v, s=stem: self._on_list_toggle(s, v))
        tog.pack(side="left", padx=(8, 4), pady=6)
        lbl = tk.Label(frame, text=proj.get("service_name", stem) or stem,
                       bg=C_PANEL, anchor="w", font=FONT_NORMAL, cursor="hand2")
        lbl.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Frame(self._list_inner, bg=C_BORDER, height=1).pack(fill="x")
        for widget in (frame, lbl):
            widget.bind("<Button-1>", lambda e, s=stem: self._select(s))
        self._row_widgets[stem] = {"frame": frame, "toggle": tog, "label": lbl}

    def _select(self, stem: str):
        for s, ww in self._row_widgets.items():
            bg = C_SELECTED if s == stem else C_PANEL
            ww["frame"].configure(bg=bg)
            ww["label"].configure(bg=bg)
        self._selected = stem
        self._load_form(stem)
        self._set_form_editable(True)

    # ── フォーム ─────────────────────────────────────────────────────

    def _get_entry(self, key: str) -> str:
        w = self._form_entries[key]
        if isinstance(w, tk.Text):
            return w.get("1.0", "end").strip()
        return w._sv.get().strip()  # type: ignore[attr-defined]

    def _set_entry(self, key: str, value: str):
        w = self._form_entries[key]
        if isinstance(w, tk.Text):
            w.configure(state="normal")
            w.delete("1.0", "end")
            w.insert("1.0", value)
        else:
            w._sv.set(value)  # type: ignore[attr-defined]

    def _set_form_editable(self, editable: bool):
        state = "normal" if editable else "disabled"
        for key, w in self._form_entries.items():
            if isinstance(w, tk.Text):
                w.configure(state=state)
            else:
                w.configure(state=state)
        if not editable:
            for key in self._form_entries:
                self._set_entry(key, "")

    def _load_form(self, stem: str):
        proj = self._projects[stem]
        for key in self._form_entries:
            self._set_entry(key, proj.get(key, ""))
        enabled = proj.get("enabled", True)
        if self._enabled_toggle:
            self._enabled_toggle.set(enabled)
        self._update_enabled_label(enabled)

    def _save_form(self):
        if not self._selected:
            return
        sid = self._get_entry("service_id")
        if sid and not re.fullmatch(r"\d{4,8}", sid):
            messagebox.showwarning("入力エラー", "サービスIDは数字のみ（4〜8桁）で入力してください。")
            return
        if not self._get_entry("service_name"):
            messagebox.showwarning("入力エラー", "案件名を入力してください。")
            return
        proj = self._projects[self._selected]
        for key in self._form_entries:
            proj[key] = self._get_entry(key)
        proj["enabled"] = self._enabled_toggle.get() if self._enabled_toggle else True
        self._save(self._selected)
        ww = self._row_widgets.get(self._selected)
        if ww:
            ww["label"].configure(text=proj.get("service_name", self._selected))
            ww["toggle"].set(proj["enabled"])
        messagebox.showinfo("保存完了",
                            f"「{proj.get('service_name', self._selected)}」を保存しました。")

    def _on_form_toggle(self, value: bool):
        self._update_enabled_label(value)

    def _on_list_toggle(self, stem: str, value: bool):
        self._projects[stem]["enabled"] = value
        self._save(stem)
        if self._selected == stem and self._enabled_toggle:
            self._enabled_toggle.set(value)
            self._update_enabled_label(value)

    def _update_enabled_label(self, value: bool):
        if self._enabled_lbl:
            self._enabled_lbl.configure(
                text="有効" if value else "無効",
                fg=C_ON if value else C_OFF,
            )

    # ── 新規 / 削除 / インポート ──────────────────────────────────────

    def _new(self):
        i = 1
        while f"new_project_{i}" in self._projects:
            i += 1
        stem = f"new_project_{i}"
        self._projects[stem] = {
            "service_name": "新規案件", "service_id": "",
            "spreadsheet_id": "", "sheet_name": "",
            "comment": "", "enabled": True,
        }
        self._save(stem)
        self._refresh_list()
        self._select(stem)

    def _delete(self):
        if not self._selected:
            messagebox.showwarning("未選択", "削除する案件を選択してください。")
            return
        name = self._projects[self._selected].get("service_name", self._selected)
        if not messagebox.askyesno("削除の確認",
                                   f"「{name}」を削除しますか？\nこの操作は元に戻せません。"):
            return
        self._delete_file(self._selected)
        del self._projects[self._selected]
        self._selected = ""
        self._set_form_editable(False)
        self._refresh_list()

    def _open_import(self):
        _ImportDialog(self, self._receive_import)

    def _receive_import(self, items: list[tuple[str, dict]]):
        imported, skipped = 0, []
        for fname, data in items:
            base = _slugify(data.get("service_name") or data.get("service_id") or fname)
            stem = base
            n = 1
            existing = next(
                (s for s, p in self._projects.items()
                 if p.get("service_id") == data.get("service_id")), None
            )
            if existing:
                if not messagebox.askyesno(
                    "重複確認",
                    f"「{self._projects[existing].get('service_name', existing)}」"
                    f"(ID:{data['service_id']}) は既に存在します。上書きしますか？"
                ):
                    skipped.append(data.get("service_name", fname))
                    continue
                stem = existing
            else:
                while stem in self._projects:
                    stem = f"{base}_{n}"
                    n += 1
            self._projects[stem] = data
            self._save(stem)
            imported += 1
        self._refresh_list()
        msg = f"{imported} 件をインポートしました。"
        if skipped:
            msg += f"\nスキップ: {', '.join(skipped)}"
        messagebox.showinfo("インポート完了", msg)

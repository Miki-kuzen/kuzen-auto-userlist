"""ダッシュボード画面（実行・ログ・進捗表示）。

自動化の実行を GUI から起動できる。
  - threading.Thread で非同期実行（UI をブロックしない）
  - queue.Queue でログをメインスレッドへ転送
  - threading.Event で停止要求を伝達
"""
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from core import notifier
from core.main import load_projects, run_all
from gui.theme import (
    C_BG, C_PANEL, C_ACCENT, C_BORDER,
    C_LOG_BG, C_LOG_FG, C_LOG_ERROR, C_LOG_OK, C_LOG_INFO,
    C_ON, C_DANGER, C_OFF,
    FONT_NORMAL, FONT_BOLD, FONT_SMALL, FONT_LARGE, FONT_MONO,
)

_STATE_IDLE     = "idle"
_STATE_RUNNING  = "running"
_STATE_STOPPING = "stopping"


class DashboardPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C_BG)
        self._app = app
        self._state = _STATE_IDLE
        self._log_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._run_thread: threading.Thread | None = None
        self._total = 0
        self._done = 0
        self._build()

    def on_show(self):
        self._update_project_count()

    def on_hide(self):
        pass

    # ------------------------------------------------------------------ #
    # UI 構築
    # ------------------------------------------------------------------ #

    def _build(self):
        # ヘッダー
        hdr = tk.Frame(self, bg=C_BG)
        hdr.pack(fill="x", padx=24, pady=(20, 0))
        tk.Label(hdr, text="ダッシュボード", font=FONT_LARGE, bg=C_BG).pack(side="left")

        # ── ツールバー ──────────────────────────────────────────────────
        tb = tk.Frame(self, bg=C_BG)
        tb.pack(fill="x", padx=24, pady=(12, 0))

        self._run_btn = tk.Button(
            tb, text="▶  全件実行", command=self._start,
            bg=C_ACCENT, fg="white", relief="flat",
            font=FONT_BOLD, padx=14, pady=7, cursor="hand2",
        )
        self._run_btn.pack(side="left")

        self._stop_btn = tk.Button(
            tb, text="■  停止", command=self._request_stop,
            bg=C_DANGER, fg="white", relief="flat",
            font=FONT_BOLD, padx=14, pady=7, cursor="hand2",
            state="disabled",
        )
        self._stop_btn.pack(side="left", padx=(8, 0))

        self._status_lbl = tk.Label(
            tb, text="待機中", font=FONT_SMALL,
            bg=C_BG, fg=C_OFF,
        )
        self._status_lbl.pack(side="left", padx=(16, 0))

        # ── プログレス ─────────────────────────────────────────────────
        prog_frame = tk.Frame(self, bg=C_BG)
        prog_frame.pack(fill="x", padx=24, pady=(10, 0))

        self._progress = ttk.Progressbar(
            prog_frame, orient="horizontal", mode="determinate", length=400
        )
        self._progress.pack(side="left", fill="x", expand=True)

        self._prog_lbl = tk.Label(
            prog_frame, text="", font=FONT_SMALL, bg=C_BG, width=12, anchor="e"
        )
        self._prog_lbl.pack(side="left", padx=(8, 0))

        # ── ログ ───────────────────────────────────────────────────────
        log_hdr = tk.Frame(self, bg=C_BG)
        log_hdr.pack(fill="x", padx=24, pady=(12, 4))
        tk.Label(log_hdr, text="実行ログ", font=FONT_BOLD, bg=C_BG).pack(side="left")
        tk.Button(
            log_hdr, text="クリア", command=self._clear_log,
            relief="flat", font=FONT_SMALL, padx=8, pady=2,
            bg="#e8eaed", cursor="hand2",
        ).pack(side="right")

        log_wrap = tk.Frame(self, bg=C_BORDER, bd=1)
        log_wrap.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        self._log_text = tk.Text(
            log_wrap,
            bg=C_LOG_BG, fg=C_LOG_FG,
            font=FONT_MONO,
            relief="flat", bd=0,
            padx=10, pady=8,
            wrap="word",
            state="disabled",
            cursor="arrow",
        )
        log_sb = ttk.Scrollbar(log_wrap, orient="vertical",
                               command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=log_sb.set)
        log_sb.pack(side="right", fill="y")
        self._log_text.pack(side="left", fill="both", expand=True)

        # ログカラータグ
        self._log_text.tag_configure("error", foreground=C_LOG_ERROR)
        self._log_text.tag_configure("ok",    foreground=C_LOG_OK)
        self._log_text.tag_configure("info",  foreground=C_LOG_INFO)
        self._log_text.tag_configure("body",  foreground=C_LOG_FG)

        # ── 前回結果サマリ ─────────────────────────────────────────────
        self._summary_lbl = tk.Label(
            self, text="", font=FONT_SMALL, bg=C_BG, fg="#555"
        )
        self._summary_lbl.pack(anchor="w", padx=24, pady=(0, 12))

        self._update_project_count()

    # ------------------------------------------------------------------ #
    # 案件数表示
    # ------------------------------------------------------------------ #

    def _update_project_count(self):
        try:
            projects = load_projects()
            n = len(projects)
            self._status_lbl.configure(
                text=f"有効な案件: {n} 件" if n else "有効な案件がありません",
                fg=C_OFF,
            )
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # 実行制御
    # ------------------------------------------------------------------ #

    def _start(self):
        if self._state != _STATE_IDLE:
            return
        self._set_state(_STATE_RUNNING)
        self._stop_event.clear()
        self._done = 0
        self._total = len(load_projects())
        self._progress["maximum"] = max(self._total, 1)
        self._progress["value"] = 0
        self._prog_lbl.configure(text=f"0 / {self._total}")
        self._run_thread = threading.Thread(target=self._worker, daemon=True)
        self._run_thread.start()
        self._poll()

    def _request_stop(self):
        if self._state != _STATE_RUNNING:
            return
        self._set_state(_STATE_STOPPING)
        self._stop_event.set()
        self._status_lbl.configure(text="停止中...", fg=C_DANGER)

    def _worker(self):
        """バックグラウンドスレッドで run_all() を実行する。"""
        original_log_cb = self._enqueue_log

        def per_project_log(msg: str):
            original_log_cb(msg)
            # 案件完了行を検知してプログレスを進める
            if msg and ("完了:" in msg or "[ERROR]" in msg):
                self._log_queue.put(("__progress__", None))

        try:
            result = run_all(
                log_callback=per_project_log,
                stop_event=self._stop_event,
            )
            self._log_queue.put(("__done__", result))
        except Exception as e:
            self._log_queue.put(("__error__", str(e)))

    def _enqueue_log(self, msg: str):
        self._log_queue.put(("log", msg))

    def _poll(self):
        """100ms ごとにキューを消費してログ・状態を更新する。"""
        try:
            while True:
                item = self._log_queue.get_nowait()
                kind = item[0]

                if kind == "log":
                    self._append_log(item[1])
                elif kind == "__progress__":
                    self._done += 1
                    self._progress["value"] = self._done
                    self._prog_lbl.configure(text=f"{self._done} / {self._total}")
                elif kind == "__done__":
                    self._on_done(item[1])
                    return
                elif kind == "__error__":
                    self._append_log(f"[FATAL] {item[1]}", tag="error")
                    self._on_done({"success": [], "failed": ["（予期しないエラー）"]})
                    return
        except queue.Empty:
            pass

        if self._state in (_STATE_RUNNING, _STATE_STOPPING):
            self.after(100, self._poll)

    def _on_done(self, result: dict):
        success = result.get("success", [])
        failed  = result.get("failed", [])
        self._progress["value"] = self._total
        self._prog_lbl.configure(text=f"{self._total} / {self._total}")
        self._set_state(_STATE_IDLE)

        summary = f"完了: 成功 {len(success)} 件 / 失敗 {len(failed)} 件"
        if failed:
            summary += f"  ❌ 失敗: {', '.join(failed)}"
        self._summary_lbl.configure(text=summary)

        # Slack 通知
        notifier.notify_complete(success, failed)

    # ------------------------------------------------------------------ #
    # ログ表示
    # ------------------------------------------------------------------ #

    def _append_log(self, msg: str, tag: str = ""):
        if not tag:
            if "[ERROR]" in msg or "[FATAL]" in msg:
                tag = "error"
            elif "完了:" in msg or "✅" in msg:
                tag = "ok"
            elif "処理開始:" in msg or "─" in msg:
                tag = "info"
            else:
                tag = "body"

        self._log_text.configure(state="normal")
        self._log_text.insert("end", msg + "\n", tag)
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _clear_log(self):
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")

    # ------------------------------------------------------------------ #
    # 状態管理
    # ------------------------------------------------------------------ #

    def _set_state(self, state: str):
        self._state = state
        if state == _STATE_IDLE:
            self._run_btn.configure(state="normal")
            self._stop_btn.configure(state="disabled")
            self._status_lbl.configure(text="待機中", fg=C_OFF)
        elif state == _STATE_RUNNING:
            self._run_btn.configure(state="disabled")
            self._stop_btn.configure(state="normal")
            self._status_lbl.configure(text="実行中...", fg=C_ON)
        elif state == _STATE_STOPPING:
            self._stop_btn.configure(state="disabled")

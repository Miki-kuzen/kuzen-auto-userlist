"""設定画面（Slack 連携・アップデート設定）。"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import notifier
from gui.theme import (
    C_BG, C_PANEL, C_ACCENT, C_BORDER, C_ON, C_DANGER,
    FONT_NORMAL, FONT_BOLD, FONT_SMALL, FONT_LARGE,
)
from gui.widgets import ToggleSwitch


class SettingsPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C_BG)
        self._app = app
        self._toggles: dict[str, ToggleSwitch] = {}
        self._webhook_var = tk.StringVar()
        self._share_path_var = tk.StringVar()   # 旧Google Drive方式（参照のみ保持）
        self._github_repo_var = tk.StringVar()
        self._github_token_var = tk.StringVar()
        self._github_branch_var = tk.StringVar(value="main")
        self._token_visible = False
        self._build()

    def on_show(self):
        self._load()
        self._load_history()

    def on_hide(self):
        pass

    # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #

    def _build(self):
        # ヘッダー
        hdr = tk.Frame(self, bg=C_BG)
        hdr.pack(fill="x", padx=24, pady=(20, 0))
        tk.Label(hdr, text="設定", font=FONT_LARGE, bg=C_BG).pack(side="left")

        # コンテンツ（スクロール可能：内容がウィンドウ高さを超えても全項目に到達できる）
        outer = tk.Frame(self, bg=C_BG)
        outer.pack(fill="both", expand=True, padx=24, pady=12)
        canvas = tk.Canvas(outer, bg=C_BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        scroll_outer = tk.Frame(canvas, bg=C_BG)
        _win = canvas.create_window((0, 0), window=scroll_outer, anchor="nw")
        scroll_outer.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(_win, width=e.width))
        # マウスホイールはこのページにカーソルがある間だけ有効にする（他ページと競合しない）
        def _on_wheel(e):
            canvas.yview_scroll(int(-e.delta / 120), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_wheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # ── Slack セクション ─────────────────────────────────────────
        self._section(scroll_outer, "Slack 通知")

        card = self._card(scroll_outer)

        # Webhook URL
        tk.Label(card, text="Webhook URL", font=FONT_BOLD,
                 bg=C_PANEL, anchor="w").pack(fill="x", pady=(0, 4))
        tk.Label(card,
                 text="Slack の Incoming Webhook URL を貼り付けてください。",
                 font=FONT_SMALL, bg=C_PANEL, fg="#555", anchor="w").pack(fill="x")

        entry = tk.Entry(card, textvariable=self._webhook_var,
                         font=FONT_NORMAL, relief="solid", bd=1)
        entry.pack(fill="x", ipady=5, pady=(6, 16))

        # 通知タイミング
        tk.Label(card, text="通知するタイミング", font=FONT_BOLD,
                 bg=C_PANEL, anchor="w").pack(fill="x", pady=(0, 8))

        notify_items = [
            ("slack_notify_on_complete",  "全件完了時（サマリを通知）"),
            ("slack_notify_on_error",     "エラー発生時"),
            ("slack_notify_per_project",  "案件ごとの完了時"),
        ]
        for key, label in notify_items:
            row = tk.Frame(card, bg=C_PANEL)
            row.pack(fill="x", pady=3)
            tog = ToggleSwitch(row, value=True, bg=C_PANEL)
            tog.pack(side="left")
            tk.Label(row, text=label, font=FONT_NORMAL,
                     bg=C_PANEL).pack(side="left", padx=(10, 0))
            self._toggles[key] = tog

        # テスト送信
        tk.Frame(card, bg=C_BORDER, height=1).pack(fill="x", pady=12)
        test_row = tk.Frame(card, bg=C_PANEL)
        test_row.pack(fill="x")
        tk.Button(
            test_row, text="テスト送信", command=self._test_send,
            relief="flat", font=FONT_NORMAL, padx=10, pady=4,
            bg="#e8eaed", cursor="hand2",
        ).pack(side="left")
        self._test_lbl = tk.Label(test_row, text="", font=FONT_SMALL,
                                  bg=C_PANEL, fg="#555")
        self._test_lbl.pack(side="left", padx=(10, 0))

        # ── 自動アップデートセクション（GitHub） ─────────────────────
        self._section(scroll_outer, "自動アップデート（GitHub）")

        upd_card = self._card(scroll_outer)

        # リポジトリ
        tk.Label(upd_card, text="リポジトリ", font=FONT_BOLD,
                 bg=C_PANEL, anchor="w").pack(fill="x", pady=(0, 2))
        tk.Label(upd_card, text="例: tsuyoshi-miki/userlist-bot",
                 font=FONT_SMALL, bg=C_PANEL, fg="#555", anchor="w").pack(fill="x")
        self._github_repo_var = tk.StringVar()
        tk.Entry(upd_card, textvariable=self._github_repo_var,
                 font=FONT_NORMAL, relief="solid", bd=1).pack(
            fill="x", ipady=5, pady=(4, 12))

        # ブランチ
        tk.Label(upd_card, text="ブランチ", font=FONT_BOLD,
                 bg=C_PANEL, anchor="w").pack(fill="x", pady=(0, 2))
        self._github_branch_var = tk.StringVar(value="main")
        tk.Entry(upd_card, textvariable=self._github_branch_var,
                 font=FONT_NORMAL, relief="solid", bd=1).pack(
            fill="x", ipady=5, pady=(4, 12))

        # アクセストークン
        tk.Label(upd_card, text="アクセストークン（Fine-grained PAT）", font=FONT_BOLD,
                 bg=C_PANEL, anchor="w").pack(fill="x", pady=(0, 2))
        tk.Label(upd_card,
                 text="GitHub → Settings → Developer settings → Fine-grained tokens\n"
                      "対象リポジトリのみ・Contents: Read-only で作成してください。",
                 font=FONT_SMALL, bg=C_PANEL, fg="#555", anchor="w",
                 justify="left").pack(fill="x")

        token_row = tk.Frame(upd_card, bg=C_PANEL)
        token_row.pack(fill="x", pady=(4, 0))

        self._github_token_var = tk.StringVar()
        self._token_entry = tk.Entry(
            token_row, textvariable=self._github_token_var,
            font=FONT_NORMAL, relief="solid", bd=1, show="•",
        )
        self._token_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self._token_visible = False
        tk.Button(
            token_row, text="表示", command=self._toggle_token_visibility,
            relief="flat", font=FONT_SMALL, padx=8, pady=4,
            bg="#e8eaed", cursor="hand2",
        ).pack(side="left", padx=(6, 0))

        # 接続テスト
        tk.Frame(upd_card, bg=C_BORDER, height=1).pack(fill="x", pady=12)
        test_row2 = tk.Frame(upd_card, bg=C_PANEL)
        test_row2.pack(fill="x")
        tk.Button(
            test_row2, text="接続テスト", command=self._test_github,
            relief="flat", font=FONT_NORMAL, padx=10, pady=4,
            bg="#e8eaed", cursor="hand2",
        ).pack(side="left")
        self._github_test_lbl = tk.Label(test_row2, text="", font=FONT_SMALL,
                                         bg=C_PANEL, fg="#555")
        self._github_test_lbl.pack(side="left", padx=(10, 0))

        # 更新履歴
        tk.Frame(upd_card, bg=C_BORDER, height=1).pack(fill="x", pady=12)
        hist_hdr = tk.Frame(upd_card, bg=C_PANEL)
        hist_hdr.pack(fill="x", pady=(0, 6))
        tk.Label(hist_hdr, text="更新履歴", font=FONT_BOLD,
                 bg=C_PANEL, anchor="w").pack(side="left")
        tk.Button(
            hist_hdr, text="再読み込み", command=self._load_history,
            relief="flat", font=FONT_SMALL, padx=8, pady=2,
            bg="#e8eaed", cursor="hand2",
        ).pack(side="right")

        hist_wrap = tk.Frame(upd_card, bg=C_BORDER, bd=1)
        hist_wrap.pack(fill="x")
        self._hist_text = tk.Text(
            hist_wrap, height=8, font=("Consolas", 9),
            relief="flat", bd=0, bg="#f8f9fa",
            state="disabled", cursor="arrow",
            wrap="word", padx=10, pady=8,
        )
        hist_sb = tk.Scrollbar(hist_wrap, orient="vertical",
                               command=self._hist_text.yview)
        self._hist_text.configure(yscrollcommand=hist_sb.set)
        hist_sb.pack(side="right", fill="y")
        self._hist_text.pack(fill="x")

        # 保存ボタン
        btn_row = tk.Frame(self, bg=C_BG)
        btn_row.pack(fill="x", padx=24, pady=(0, 20))
        tk.Button(
            btn_row, text="保存", command=self._save,
            bg=C_ACCENT, fg="white", relief="flat",
            font=FONT_BOLD, padx=20, pady=7, cursor="hand2",
        ).pack(side="right")

    def _section(self, parent, title: str):
        tk.Label(parent, text=title, font=FONT_BOLD,
                 bg=C_BG, fg="#444").pack(anchor="w", pady=(8, 4))

    def _card(self, parent) -> tk.Frame:
        wrap = tk.Frame(parent, bg=C_BORDER, bd=1)
        wrap.pack(fill="x", pady=(0, 16))
        inner = tk.Frame(wrap, bg=C_PANEL, padx=20, pady=16)
        inner.pack(fill="both", expand=True)
        return inner

    # ------------------------------------------------------------------ #
    # データ操作
    # ------------------------------------------------------------------ #

    def _load(self):
        s = notifier.load_settings()
        self._webhook_var.set(s.get("slack_webhook_url", ""))
        for key, tog in self._toggles.items():
            tog.set(s.get(key, True))
        self._github_repo_var.set(s.get("github_repo", ""))
        self._github_token_var.set(s.get("github_token", ""))
        self._github_branch_var.set(s.get("github_branch", "main"))

    def _save(self):
        s = notifier.load_settings()
        s["slack_webhook_url"] = self._webhook_var.get().strip()
        for key, tog in self._toggles.items():
            s[key] = tog.get()
        s["github_repo"]   = self._github_repo_var.get().strip()
        s["github_token"]  = self._github_token_var.get().strip()
        s["github_branch"] = self._github_branch_var.get().strip() or "main"
        notifier.save_settings(s)
        messagebox.showinfo("保存完了", "設定を保存しました。", parent=self)

    def _browse_share(self):
        path = filedialog.askdirectory(title="配布フォルダを選択", parent=self)
        if path:
            self._share_path_var.set(path)

    def _toggle_token_visibility(self):
        self._token_visible = not self._token_visible
        self._token_entry.configure(show="" if self._token_visible else "•")

    def _test_github(self):
        import threading
        repo   = self._github_repo_var.get().strip()
        token  = self._github_token_var.get().strip()
        branch = self._github_branch_var.get().strip() or "main"
        if not repo or not token:
            self._github_test_lbl.configure(text="❌ リポジトリとトークンを入力してください。",
                                            fg=C_DANGER)
            return
        self._github_test_lbl.configure(text="接続中...", fg="#555")
        self.update_idletasks()
        threading.Thread(
            target=self._do_github_test,
            args=(repo, token, branch),
            daemon=True,
        ).start()

    def _do_github_test(self, repo: str, token: str, branch: str):
        try:
            from core.updater import _fetch_manifest
            manifest = _fetch_manifest(repo, branch, token)
            if manifest:
                ver = manifest.get("version", "不明")
                self.after(0, lambda: self._github_test_lbl.configure(
                    text=f"✅ 接続成功（リポジトリ内バージョン: v{ver}）", fg=C_ON))
            else:
                self.after(0, lambda: self._github_test_lbl.configure(
                    text="⚠ 接続できましたが manifest.json が見つかりません。", fg="#f4a100"))
        except Exception as e:
            msg = str(e)[:60]
            self.after(0, lambda: self._github_test_lbl.configure(
                text=f"❌ 接続失敗: {msg}", fg=C_DANGER))

    def _load_history(self):
        """更新履歴を changelog.json（同梱ファイル）から表示する。

        リアルタイムで GitHub を参照せず、配布された changelog.json を読む。
        各行は "yyyy/mm/dd  コメント" 形式。
        """
        import config
        from core import changelog
        lines = changelog.format_lines()
        if not lines:
            self._set_hist_text("（更新履歴はまだありません）")
            return
        header = f"現在のバージョン: v{config.APP_VERSION}\n"
        self._set_hist_text(header + "\n".join(lines))

    def _set_hist_text(self, text: str):
        self._hist_text.configure(state="normal")
        self._hist_text.delete("1.0", "end")
        self._hist_text.insert("end", text)
        self._hist_text.configure(state="disabled")

    def _test_send(self):
        url = self._webhook_var.get().strip()
        if not url:
            self._test_lbl.configure(text="❌ Webhook URL が未入力です。", fg=C_DANGER)
            return
        self._test_lbl.configure(text="送信中...", fg="#555")
        self.update_idletasks()
        ok = notifier.send("✅ [自動転写アプリ] テスト送信です。", webhook_url=url)
        if ok:
            self._test_lbl.configure(text="✅ 送信しました！", fg=C_ON)
        else:
            self._test_lbl.configure(text="❌ 送信失敗。URL を確認してください。", fg=C_DANGER)

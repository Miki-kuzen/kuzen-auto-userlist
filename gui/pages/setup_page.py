"""初回セットアップ画面。

google_token.json が存在しないとき（初回起動時）のみ表示される。
Google OAuth 認証を完了させて on_complete コールバックを呼ぶ。
サイトログインは実行時に行うため、ここでは扱わない。
"""
import threading
import tkinter as tk
from tkinter import messagebox

from gui.theme import (
    C_BG, C_PANEL, C_ACCENT, C_ON, C_BORDER,
    FONT_TITLE, FONT_NORMAL, FONT_BOLD, FONT_SMALL,
)


class SetupPage(tk.Frame):
    def __init__(self, parent, on_complete):
        super().__init__(parent, bg=C_BG)
        self._on_complete = on_complete
        self._build()

    def _build(self):
        # 中央寄せコンテナ
        center = tk.Frame(self, bg=C_BG)
        center.place(relx=0.5, rely=0.5, anchor="center")

        # ロゴ・タイトル
        tk.Label(center, text="📊", font=("Yu Gothic UI", 48),
                 bg=C_BG).pack(pady=(0, 8))
        tk.Label(center, text="顧客数値 自動転写アプリ",
                 font=FONT_TITLE, bg=C_BG).pack()
        tk.Label(center, text="初回セットアップ",
                 font=FONT_NORMAL, bg=C_BG, fg="#555").pack(pady=(4, 24))

        # カード
        card = tk.Frame(center, bg=C_PANEL, relief="flat",
                        highlightbackground=C_BORDER, highlightthickness=1)
        card.pack(ipadx=32, ipady=24, fill="x")

        tk.Label(card, text="Google アカウントの認証が必要です",
                 font=FONT_BOLD, bg=C_PANEL).pack(pady=(0, 8))
        tk.Label(card,
                 text="「認証を開始」を押すとブラウザが開きます。\n"
                      "kuzen.io の Google アカウントで許可してください。\n"
                      "一度認証すれば次回以降は自動で使えます。",
                 font=FONT_SMALL, bg=C_PANEL, fg="#444",
                 justify="left").pack(padx=8, pady=(0, 16))

        # 状態表示
        self._status_lbl = tk.Label(card, text="", font=FONT_SMALL,
                                    bg=C_PANEL, fg="#555")
        self._status_lbl.pack(pady=(0, 8))

        # ボタン群
        btn_frame = tk.Frame(card, bg=C_PANEL)
        btn_frame.pack()

        self._auth_btn = tk.Button(
            btn_frame, text="Google 認証を開始",
            command=self._start_auth,
            bg=C_ACCENT, fg="white", relief="flat",
            font=FONT_BOLD, padx=16, pady=8, cursor="hand2",
        )
        self._auth_btn.pack(side="left", padx=(0, 8))

        self._next_btn = tk.Button(
            btn_frame, text="アプリを開始する →",
            command=self._on_complete,
            bg=C_ON, fg="white", relief="flat",
            font=FONT_BOLD, padx=16, pady=8, cursor="hand2",
            state="disabled",
        )
        self._next_btn.pack(side="left")

    # ------------------------------------------------------------------ #

    def _start_auth(self):
        self._auth_btn.configure(state="disabled", text="認証中...")
        self._status_lbl.configure(text="ブラウザが開きます。Google アカウントで許可してください。",
                                   fg="#555")
        threading.Thread(target=self._do_auth, daemon=True).start()

    def _do_auth(self):
        try:
            from core.auth_google import get_gspread_client
            get_gspread_client()
            self.after(0, self._auth_success)
        except Exception as e:
            self.after(0, lambda: self._auth_failed(str(e)))

    def _auth_success(self):
        self._status_lbl.configure(
            text="✅  認証が完了しました！", fg=C_ON)
        self._auth_btn.configure(state="disabled", text="認証済み")
        self._next_btn.configure(state="normal")

    def _auth_failed(self, msg: str):
        self._status_lbl.configure(
            text=f"❌  認証に失敗しました: {msg[:60]}", fg="#d93025")
        self._auth_btn.configure(state="normal", text="再試行")
        messagebox.showerror("認証エラー",
                             f"Google 認証に失敗しました。\n\n{msg}\n\n"
                             "oauth_client.json が正しく配置されているか確認してください。",
                             parent=self)

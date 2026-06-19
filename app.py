"""顧客数値 自動転写アプリ v2 — メインエントリーポイント。

起動方法: python app.py  または  app.exe

起動フロー:
  1. google_token.json が存在しない → セットアップ画面（OAuth 認証）
  2. 認証済み → メイン画面（サイドバー + ページ切替）
"""
import os
import sys
import tkinter as tk

import config
from gui.theme import (
    C_BG, C_HEADER, C_HEADER_TEXT,
    C_SIDEBAR, C_SIDEBAR_TEXT, C_SIDEBAR_HOVER, C_SIDEBAR_ACTIVE,
    FONT_LARGE, FONT_SMALL, FONT_BOLD,
)


class App:
    _NAV = [
        ("🏠", "ダッシュボード", "dashboard"),
        ("📋", "案件管理",       "projects"),
        ("⚙",  "設定",           "settings"),
    ]

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Userlist Automation")
        self.root.geometry("980x640")
        self.root.minsize(800, 520)
        self.root.configure(bg=C_BG)

        # ウィンドウアイコン（存在する場合のみ設定）
        icon_path = config.resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        self._pages: dict[str, tk.Frame] = {}
        self._nav_btns: dict[str, tk.Frame] = {}
        self._current: str = ""

        os.makedirs(config.APP_DATA_DIR, exist_ok=True)

        from core import updater
        updater.check_and_update(self.root)  # 新バージョンがあれば置換・再起動して終了

        if not os.path.exists(config.GOOGLE_TOKEN_FILE):
            self._build_setup()
        else:
            self._build_main()

    # ------------------------------------------------------------------ #
    # セットアップ画面
    # ------------------------------------------------------------------ #

    def _build_setup(self):
        from gui.pages.setup_page import SetupPage
        page = SetupPage(self.root, on_complete=self._on_setup_complete)
        page.pack(fill="both", expand=True)

    def _on_setup_complete(self):
        for w in self.root.winfo_children():
            w.destroy()
        self._build_main()

    # ------------------------------------------------------------------ #
    # メイン画面
    # ------------------------------------------------------------------ #

    def _build_main(self):
        # ── ヘッダー ────────────────────────────────────────────────────
        header = tk.Frame(self.root, bg=C_HEADER, height=48)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header, text="Automation Userlist",
            bg=C_HEADER, fg=C_HEADER_TEXT,
            font=FONT_LARGE,
        ).pack(side="left", padx=(8, 0))

        tk.Button(
            header, text="?  ヘルプ",
            command=self.show_help,
            bg=C_HEADER, fg=C_HEADER_TEXT,
            activebackground=C_SIDEBAR_HOVER,
            relief="flat", font=FONT_SMALL,
            padx=12, pady=4, cursor="hand2",
        ).pack(side="right", padx=8)

        # ── ボディ（サイドバー + コンテンツ）──────────────────────────
        body = tk.Frame(self.root, bg=C_BG)
        body.pack(fill="both", expand=True)

        # サイドバー
        sidebar = tk.Frame(body, bg=C_SIDEBAR, width=72)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # コンテンツエリア
        self._content = tk.Frame(body, bg=C_BG)
        self._content.pack(side="left", fill="both", expand=True)

        # ページ生成（遅延 import でスタートアップを速くする）
        from gui.pages.dashboard_page import DashboardPage
        from gui.pages.projects_page  import ProjectsPage
        from gui.pages.settings_page  import SettingsPage
        from gui.pages.help_page      import HelpPage

        self._pages = {
            "dashboard": DashboardPage(self._content, self),
            "projects":  ProjectsPage(self._content,  self),
            "settings":  SettingsPage(self._content,  self),
            "help":      HelpPage(self._content,      self),
        }
        for page in self._pages.values():
            page.place(relwidth=1, relheight=1)

        # サイドバーナビ
        for icon, label, key in self._NAV:
            btn = self._make_nav_btn(sidebar, icon, label, key)
            btn.pack(fill="x", padx=4, pady=(4, 0))
            self._nav_btns[key] = btn

        # 初期ページ
        self.navigate("dashboard")

    def _make_nav_btn(self, parent, icon: str, label: str, key: str) -> tk.Frame:
        f = tk.Frame(parent, bg=C_SIDEBAR, cursor="hand2")

        tk.Label(f, text=icon, bg=C_SIDEBAR, fg=C_SIDEBAR_TEXT,
                 font=("Yu Gothic UI", 20)).pack(pady=(10, 0))
        tk.Label(f, text=label, bg=C_SIDEBAR, fg=C_SIDEBAR_TEXT,
                 font=("Yu Gothic UI", 8)).pack(pady=(2, 10))

        def on_enter(_):
            if key != self._current:
                f.configure(bg=C_SIDEBAR_HOVER)
                for c in f.winfo_children():
                    c.configure(bg=C_SIDEBAR_HOVER)

        def on_leave(_):
            if key != self._current:
                f.configure(bg=C_SIDEBAR)
                for c in f.winfo_children():
                    c.configure(bg=C_SIDEBAR)

        for widget in [f] + list(f.winfo_children()):
            widget.bind("<Button-1>", lambda e, k=key: self.navigate(k))
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        return f

    # ------------------------------------------------------------------ #
    # ナビゲーション
    # ------------------------------------------------------------------ #

    def navigate(self, page_name: str):
        if self._current and self._current in self._pages:
            self._pages[self._current].on_hide()

        # サイドバーハイライト更新
        if self._current in self._nav_btns:
            old = self._nav_btns[self._current]
            old.configure(bg=C_SIDEBAR)
            for c in old.winfo_children():
                c.configure(bg=C_SIDEBAR)

        self._current = page_name

        if page_name in self._nav_btns:
            btn = self._nav_btns[page_name]
            btn.configure(bg=C_SIDEBAR_ACTIVE)
            for c in btn.winfo_children():
                c.configure(bg=C_SIDEBAR_ACTIVE)

        self._pages[page_name].lift()
        self._pages[page_name].on_show()

    def show_help(self):
        self.navigate("help")

    # ------------------------------------------------------------------ #

    def run(self):
        self.root.mainloop()


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()

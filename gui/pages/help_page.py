"""ヘルプ画面。

help/*.md ファイルをトグルタブで切り替えて表示する。
Markdown を tkinter.Text タグ + 埋め込みウィジェットで Notion 風にレンダリング。

対応記法:
  # ## ###         見出し
  **太字**          bold
  *斜体*            italic
  ***太字斜体***    bold+italic
  ~~打消し~~        strikethrough
  `code`            インラインコード
  [text](url)       リンク（クリックでブラウザ起動）
  ```               コードブロック
  | table |         テーブル
  ---               水平線
  > 引用            blockquote
  - item            箇条書き（ネスト: 2 スペースで 1 レベル）
  1. item           番号付きリスト（ネスト対応）
  - [ ] / - [x]    チェックボックス
"""
import glob
import os
import re
import tkinter as tk
import webbrowser
from tkinter import ttk

import config
from gui.theme import (
    C_BG, C_PANEL, C_ACCENT, C_BORDER,
    FONT_NORMAL, FONT_BOLD, FONT_SMALL, FONT_LARGE, FONT_MONO,
)

HELP_DIR = config.resource_path("help")

_BULLET_CHARS = ["• ", "◦ ", "▪ "]

# リンクタグの連番（レンダリングごとにリセット）
_link_seq = [0]


# ------------------------------------------------------------------ #
# ファイル読み込み
# ------------------------------------------------------------------ #

def _load_pages() -> list[tuple[str, str]]:
    paths = sorted(glob.glob(os.path.join(HELP_DIR, "*.md")))
    if not paths:
        return [("ヘルプ", "help/ フォルダに .md ファイルを置くとここに表示されます。")]
    pages = []
    for p in paths:
        name = os.path.splitext(os.path.basename(p))[0]
        label = re.sub(r"^\d+[_\-\s]*", "", name) or name
        try:
            content = open(p, encoding="utf-8").read()
        except Exception:
            content = f"（{p} を読み込めませんでした）"
        pages.append((label, content))
    return pages


# ------------------------------------------------------------------ #
# タグ設定
# ------------------------------------------------------------------ #

def _configure_tags(w: tk.Text):
    w.tag_configure("h1",         font=("Yu Gothic UI", 20, "bold"),       spacing3=8,  spacing1=14)
    w.tag_configure("h2",         font=("Yu Gothic UI", 15, "bold"),       spacing3=6,  spacing1=10)
    w.tag_configure("h3",         font=("Yu Gothic UI", 12, "bold"),       spacing3=4,  spacing1=8)
    w.tag_configure("bold",       font=("Yu Gothic UI", 10, "bold"))
    w.tag_configure("italic",     font=("Yu Gothic UI", 10, "italic"))
    w.tag_configure("bolditalic", font=("Yu Gothic UI", 10, "bold italic"))
    w.tag_configure("strike",     font=("Yu Gothic UI", 10, "overstrike"))
    w.tag_configure("code",       font=FONT_MONO, background="#f0f0f0")
    w.tag_configure("codeblock",  font=FONT_MONO, background="#f6f8fa",
                    lmargin1=16, lmargin2=16, spacing1=2, spacing3=2)
    w.tag_configure("blockquote", font=("Yu Gothic UI", 10, "italic"),
                    foreground="#666", lmargin1=28, lmargin2=28,
                    spacing1=3, spacing3=3)
    # 箇条書き・番号リスト（3 レベルまで）
    for lvl, (lm1, lm2) in enumerate([(20, 34), (40, 54), (60, 74)]):
        w.tag_configure(f"bullet_{lvl}",   font=FONT_NORMAL, lmargin1=lm1, lmargin2=lm2, spacing1=2)
    for lvl, (lm1, lm2) in enumerate([(20, 38), (40, 58)]):
        w.tag_configure(f"numbered_{lvl}", font=FONT_NORMAL, lmargin1=lm1, lmargin2=lm2, spacing1=2)
    w.tag_configure("body",  font=FONT_NORMAL, spacing1=2)
    w.tag_configure("blank", font=("Yu Gothic UI", 4))


# ------------------------------------------------------------------ #
# インライン記法パーサー
# ------------------------------------------------------------------ #

_INLINE_RE = re.compile(
    r'\[(?P<link_text>[^\]]+)\]\((?P<url>[^)]+)\)'  # [text](url)
    r'|\*\*\*(?P<bolditalic>.+?)\*\*\*'              # ***bold+italic***
    r'|\*\*(?P<bold>.+?)\*\*'                        # **bold**
    r'|~~(?P<strike>.+?)~~'                           # ~~strikethrough~~
    r'|\*(?P<italic>[^*\n]+?)\*'                      # *italic*
    r'|`(?P<code>.+?)`'                              # `code`
)


def _insert_inline(w: tk.Text, line: str, base_tag: str):
    pos = 0
    for m in _INLINE_RE.finditer(line):
        if m.start() > pos:
            w.insert("end", line[pos:m.start()], base_tag)

        if m.group("link_text") is not None:
            url = m.group("url")
            tag = f"_lnk_{_link_seq[0]}"
            _link_seq[0] += 1
            w.tag_configure(tag, foreground="#1a73e8", underline=True)
            w.tag_bind(tag, "<Button-1>", lambda e, u=url: webbrowser.open(u))
            w.tag_bind(tag, "<Enter>",    lambda e: w.configure(cursor="hand2"))
            w.tag_bind(tag, "<Leave>",    lambda e: w.configure(cursor="arrow"))
            w.insert("end", m.group("link_text"), (base_tag, tag))
        elif m.group("bolditalic") is not None:
            w.insert("end", m.group("bolditalic"), "bolditalic")
        elif m.group("bold") is not None:
            w.insert("end", m.group("bold"), "bold")
        elif m.group("strike") is not None:
            w.insert("end", m.group("strike"), "strike")
        elif m.group("italic") is not None:
            w.insert("end", m.group("italic"), "italic")
        elif m.group("code") is not None:
            w.insert("end", m.group("code"), "code")

        pos = m.end()

    if pos < len(line):
        w.insert("end", line[pos:], base_tag)


# ------------------------------------------------------------------ #
# 埋め込みウィジェット：水平線
# ------------------------------------------------------------------ #

def _embed_hr(w: tk.Text):
    w.insert("end", "\n")
    frame = tk.Frame(w, bg="#dadce0", height=2, bd=0)
    w.window_create("end", window=frame, stretch=True, pady=4)
    w.insert("end", "\n\n", "blank")


# ------------------------------------------------------------------ #
# 埋め込みウィジェット：テーブル
# ------------------------------------------------------------------ #

def _parse_table_rows(raw_lines: list[str]) -> list[list[str]]:
    rows = []
    for line in raw_lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.match(r'^[-:|]*$', c) for c in cells):
            continue
        rows.append(cells)
    return rows


def _embed_table(w: tk.Text, raw_lines: list[str]):
    rows = _parse_table_rows(raw_lines)
    if not rows:
        return
    ncols = max(len(r) for r in rows)
    outer = tk.Frame(w, bg="#dadce0", bd=0)
    for r_i, row in enumerate(rows):
        is_hdr = (r_i == 0)
        row_bg = "#f0f2f5" if is_hdr else ("white" if r_i % 2 == 1 else "#fafbfc")
        for c_i in range(ncols):
            cell_text = row[c_i] if c_i < len(row) else ""
            cell = tk.Frame(outer, bg=row_bg, bd=0)
            cell.grid(row=r_i, column=c_i, sticky="nsew", padx=1, pady=1)
            tk.Label(cell, text=cell_text, bg=row_bg,
                     font=FONT_BOLD if is_hdr else FONT_NORMAL,
                     padx=12, pady=7, anchor="w", justify="left",
                     ).pack(fill="both", expand=True)
    for c_i in range(ncols):
        outer.columnconfigure(c_i, weight=1, minsize=60)
    w.insert("end", "\n")
    w.window_create("end", window=outer)
    w.insert("end", "\n\n", "blank")


# ------------------------------------------------------------------ #
# メインレンダラー
# ------------------------------------------------------------------ #

def _destroy_embedded(w: tk.Text):
    for key, value, index in w.dump("1.0", "end", window=True):
        try:
            w.nametowidget(value).destroy()
        except Exception:
            pass
    # 動的リンクタグを削除（メモリリーク防止）
    for tag in list(w.tag_names()):
        if tag.startswith("_lnk_"):
            w.tag_delete(tag)


def _render_markdown(w: tk.Text, content: str):
    _destroy_embedded(w)
    _link_seq[0] = 0
    w.configure(state="normal")
    w.delete("1.0", "end")
    _configure_tags(w)

    lines     = content.split("\n")
    i         = 0
    in_code   = False
    table_buf: list[str] = []

    while i < len(lines):
        raw  = lines[i]
        line = raw.rstrip()

        # ── コードブロック ────────────────────────────────────────────
        if line.startswith("```"):
            if table_buf:
                _embed_table(w, table_buf); table_buf = []
            in_code = not in_code
            i += 1
            continue
        if in_code:
            w.insert("end", raw.rstrip("\n") + "\n", "codeblock")
            i += 1
            continue

        # ── テーブル ──────────────────────────────────────────────────
        if line.startswith("|"):
            table_buf.append(line)
            i += 1
            continue
        elif table_buf:
            _embed_table(w, table_buf); table_buf = []

        # ── 水平線 ────────────────────────────────────────────────────
        if re.match(r'^(-{3,}|\*{3,}|_{3,})$', line.strip()):
            _embed_hr(w)
            i += 1
            continue

        # ── 見出し ────────────────────────────────────────────────────
        if line.startswith("### "):
            w.insert("end", line[4:] + "\n", "h3")
        elif line.startswith("## "):
            w.insert("end", line[3:] + "\n", "h2")
        elif line.startswith("# "):
            w.insert("end", line[2:] + "\n", "h1")

        # ── 引用（blockquote） ─────────────────────────────────────────
        elif line.startswith("> "):
            _insert_inline(w, line[2:] + "\n", "blockquote")

        # ── チェックボックス ──────────────────────────────────────────
        elif re.match(r'^\s*-\s+\[[xX ]\]', line):
            indent  = len(re.match(r'^(\s*)', line).group(1))
            level   = min(indent // 2, 2)
            checked = line[line.find("[") + 1] in ("x", "X")
            text    = re.sub(r'^\s*-\s+\[[xX ]\]\s*', "", line)
            _insert_inline(w, ("☑ " if checked else "☐ ") + text + "\n",
                           f"bullet_{level}")

        # ── 番号付きリスト ────────────────────────────────────────────
        elif re.match(r'^\s*\d+\.\s', line):
            indent = len(re.match(r'^(\s*)', line).group(1))
            level  = min(indent // 2, 1)
            text   = line.lstrip()   # "1. ..." 形式のまま表示
            _insert_inline(w, text + "\n", f"numbered_{level}")

        # ── 箇条書き ──────────────────────────────────────────────────
        elif re.match(r'^\s*[-*]\s', line):
            indent = len(re.match(r'^(\s*)', line).group(1))
            level  = min(indent // 2, 2)
            text   = re.sub(r'^\s*[-*]\s', "", line)
            _insert_inline(w, _BULLET_CHARS[level] + text + "\n", f"bullet_{level}")

        # ── 空行 ──────────────────────────────────────────────────────
        elif line == "":
            w.insert("end", "\n", "blank")

        # ── 通常テキスト ──────────────────────────────────────────────
        else:
            _insert_inline(w, line + "\n", "body")

        i += 1

    if table_buf:
        _embed_table(w, table_buf)

    w.configure(state="disabled")


# ------------------------------------------------------------------ #
# HelpPage クラス
# ------------------------------------------------------------------ #

class HelpPage(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=C_BG)
        self._app      = app
        self._pages    = _load_pages()
        self._tab_btns: list[tk.Button] = []
        self._current  = 0
        self._build()

    def on_show(self):
        self._pages = _load_pages()
        self._rebuild_tabs()
        self._show_page(self._current)

    def on_hide(self):
        pass

    def _build(self):
        hdr = tk.Frame(self, bg=C_BG)
        hdr.pack(fill="x", padx=24, pady=(20, 0))
        tk.Label(hdr, text="ヘルプ", font=FONT_LARGE, bg=C_BG).pack(side="left")

        self._tab_bar = tk.Frame(self, bg=C_BG)
        self._tab_bar.pack(fill="x", padx=24, pady=(12, 0))

        content_wrap = tk.Frame(self, bg=C_BORDER, bd=1)
        content_wrap.pack(fill="both", expand=True, padx=24, pady=12)

        self._text = tk.Text(
            content_wrap,
            wrap="word", relief="flat", bd=0,
            padx=24, pady=20,
            bg=C_PANEL, font=FONT_NORMAL,
            cursor="arrow", state="disabled", spacing1=1,
        )
        sb = ttk.Scrollbar(content_wrap, orient="vertical", command=self._text.yview)
        self._text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._text.pack(side="left", fill="both", expand=True)

        self._rebuild_tabs()
        if self._pages:
            self._show_page(0)

    def _rebuild_tabs(self):
        for w in self._tab_bar.winfo_children():
            w.destroy()
        self._tab_btns.clear()
        for i, (label, _) in enumerate(self._pages):
            btn = tk.Button(
                self._tab_bar, text=label,
                relief="flat", font=FONT_NORMAL, padx=12, pady=5, cursor="hand2",
                command=lambda idx=i: self._show_page(idx),
            )
            btn.pack(side="left", padx=(0, 4))
            self._tab_btns.append(btn)
        self._update_tab_highlight(self._current)

    def _show_page(self, idx: int):
        if not self._pages:
            return
        idx = max(0, min(idx, len(self._pages) - 1))
        self._current = idx
        _, content = self._pages[idx]
        _render_markdown(self._text, content)
        self._text.yview_moveto(0)
        self._update_tab_highlight(idx)

    def _update_tab_highlight(self, active: int):
        for i, btn in enumerate(self._tab_btns):
            btn.configure(bg=C_ACCENT if i == active else "#e8eaed",
                          fg="white"  if i == active else "#202124")

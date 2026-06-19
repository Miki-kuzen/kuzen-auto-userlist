"""更新履歴（changelog.json）の読み書き。

リアルタイムで GitHub を見に行かず、リポジトリ同梱の changelog.json を表示する。
  - アプリ側  : load_entries() / format_lines() で読み取り表示
  - 管理者側  : append_entry() でリリース時に1件追記（tools/build_manifest.py --comment）

changelog.json は manifest に含まれるため、通常の自動アップデートで配布される。

フォーマット:
  {
    "entries": [
      {"date": "2026/06/19", "version": "2.0.2", "comment": "Slack通知の不具合を修正"},
      ...
    ]
  }
新しい順（先頭が最新）で保持する。
"""
import json
import os
from datetime import datetime

import config

_PATH = config.CHANGELOG_PATH


def load_entries() -> list[dict]:
    """更新履歴を新しい順で返す。ファイルが無ければ空リスト。"""
    if not os.path.exists(_PATH):
        return []
    try:
        with open(_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data.get("entries", [])
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def format_lines() -> list[str]:
    """表示用に "yyyy/mm/dd  comment" の行リストを返す。"""
    lines = []
    for e in load_entries():
        date = e.get("date", "")
        comment = e.get("comment", "")
        lines.append(f"{date}  {comment}")
    return lines


def append_entry(version: str, comment: str, date: str | None = None,
                 path: str | None = None) -> dict:
    """更新履歴の先頭に1件追記する（管理者用）。

    Args:
        version: バージョン番号（例 "2.0.2"）。
        comment: 変更内容の説明（1行）。
        date:    省略時は本日（yyyy/mm/dd）。
        path:    省略時は config の changelog.json。
    """
    target = path or _PATH
    entries = []
    if os.path.exists(target):
        try:
            with open(target, encoding="utf-8") as f:
                data = json.load(f)
            entries = data.get("entries", []) if isinstance(data, dict) else data
        except Exception:
            entries = []

    entry = {
        "date": date or datetime.now().strftime("%Y/%m/%d"),
        "version": version,
        "comment": comment,
    }
    entries.insert(0, entry)
    with open(target, "w", encoding="utf-8") as f:
        json.dump({"entries": entries}, f, ensure_ascii=False, indent=2)
    return entry

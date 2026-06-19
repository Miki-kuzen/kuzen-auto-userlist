"""自動アップデートモジュール（GitHub private repo + Fine-grained PAT 方式）。

管理者の作業:
  1. コードを編集し APP_VERSION を上げる
  2. python tools/build_manifest.py --version X.X.X  （manifest.json を更新）
  3. git add . && git commit && git push

従業員のアプリ設定:
  - github_repo:   "owner/repo-name"
  - github_token:  Fine-grained PAT（Contents: Read-only）
  - github_branch: "main"（デフォルト）

起動フロー:
  1. GitHub API で manifest.json を取得
  2. バージョン比較 → 新しければ
  3. ファイルごとに SHA256 を比較（差分のみダウンロード）
  4. ソース実行: os.execv で再起動 / exe: バッチ置換後に再起動
"""
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import messagebox
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError
from urllib.parse import quote

import config
from core import notifier


# ------------------------------------------------------------------ #
# GitHub API ユーティリティ
# ------------------------------------------------------------------ #

def _github_api(endpoint: str, token: str) -> dict:
    """GitHub REST API を呼ぶ。失敗したら例外を raise。"""
    url = f"https://api.github.com/{endpoint}"
    req = urllib_request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib_request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_manifest(repo: str, branch: str, token: str) -> dict | None:
    """リポジトリから manifest.json を取得してパースする。"""
    try:
        data = _github_api(
            f"repos/{repo}/contents/manifest.json?ref={quote(branch)}", token
        )
        return json.loads(base64.b64decode(data["content"]))
    except (HTTPError, URLError, KeyError, json.JSONDecodeError):
        return None


def _fetch_file_bytes(repo: str, branch: str, rel_path: str, token: str) -> bytes:
    """リポジトリの特定ファイルをバイト列で取得する。"""
    data = _github_api(
        f"repos/{repo}/contents/{quote(rel_path, safe='/')}?ref={quote(branch)}", token
    )
    return base64.b64decode(data["content"])


# ------------------------------------------------------------------ #
# バージョン比較・ハッシュ
# ------------------------------------------------------------------ #

def _is_newer(remote: str, local: str) -> bool:
    try:
        return (
            tuple(int(x) for x in remote.split("."))
            > tuple(int(x) for x in local.split("."))
        )
    except Exception:
        return False


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ #
# exe 配布版アップデート（バッチ置換）
# ------------------------------------------------------------------ #

def _update_exe(remote_ver: str, root: tk.Tk):
    # exe 配布版の場合、GitHub にはソースしか置かないため自動ダウンロードは行わない。
    # 管理者が tools/build_exe.bat で新しい exe をビルドして再配布する運用。
    messagebox.showinfo(
        "アップデートがあります",
        f"新しいバージョン v{remote_ver} が公開されています（現在: v{config.APP_VERSION}）。\n\n"
        "管理者から最新の UserListBot.exe を受け取り、\n"
        "現在の exe ファイルを置き換えてください。",
        parent=root,
    )


# ------------------------------------------------------------------ #
# ソース実行版アップデート（差分ダウンロード + os.execv 再起動）
# ------------------------------------------------------------------ #

def _update_source(repo: str, branch: str, token: str,
                   manifest: dict, remote_ver: str, root: tk.Tk):
    app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files_map: dict[str, str] = manifest.get("files", {})

    # SHA256 差分チェック
    changed = [
        rel for rel, remote_hash in files_map.items()
        if not os.path.exists(os.path.join(app_root, rel))
        or _sha256(os.path.join(app_root, rel)) != remote_hash
    ]

    if not changed:
        return

    ans = messagebox.askyesno(
        "アップデートがあります",
        f"新しいバージョン v{remote_ver} があります（現在: v{config.APP_VERSION}）。\n"
        f"変更ファイル: {len(changed)} 件\n\n"
        "今すぐアップデートしますか？（アプリが再起動します）",
        parent=root,
    )
    if not ans:
        return

    # ダウンロード & 上書き
    failed = []
    for rel_path in changed:
        try:
            file_bytes = _fetch_file_bytes(repo, branch, rel_path, token)
            dst = os.path.join(app_root, rel_path.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(file_bytes)
        except Exception as e:
            failed.append(f"{rel_path}: {e}")

    if failed:
        messagebox.showerror(
            "一部ダウンロード失敗",
            "以下のファイルの更新に失敗しました:\n" + "\n".join(failed[:5]),
            parent=root,
        )
        return

    # 再起動
    os.execv(sys.executable, [sys.executable] + sys.argv)


# ------------------------------------------------------------------ #
# エントリーポイント
# ------------------------------------------------------------------ #

def check_and_update(root: tk.Tk):
    """起動時に呼ぶ。新バージョンがあれば GitHub から差分をダウンロードして更新する。"""
    s = notifier.load_settings()
    repo   = s.get("github_repo", "").strip()
    token  = s.get("github_token", "").strip()
    branch = s.get("github_branch", "main").strip() or "main"

    if not repo or not token:
        return  # 未設定はスキップ

    try:
        manifest = _fetch_manifest(repo, branch, token)
    except Exception:
        return  # ネットワークエラーはサイレントにスキップ

    if not manifest:
        return

    remote_ver = manifest.get("version", "")
    if not remote_ver or not _is_newer(remote_ver, config.APP_VERSION):
        return

    if getattr(sys, "frozen", False):
        _update_exe(remote_ver, root)
    else:
        _update_source(repo, branch, token, manifest, remote_ver, root)

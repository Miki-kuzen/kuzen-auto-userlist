"""Slack 通知モジュール。

urllib.request のみ使用（外部ライブラリ不要）。
送信失敗はサイレントに処理し、本体の自動化を止めない。
"""
import json
import os
import urllib.request
import urllib.error

import config

_SETTINGS_PATH = os.path.join(config.APP_DATA_DIR, "settings.json")


# ---------------------------------------------------------------------------
# 設定 I/O
# ---------------------------------------------------------------------------

def load_settings() -> dict:
    if not os.path.exists(_SETTINGS_PATH):
        s = _defaults()
    else:
        try:
            with open(_SETTINGS_PATH, encoding="utf-8") as f:
                s = json.load(f)
            for k, v in _defaults().items():
                s.setdefault(k, v)
        except Exception:
            s = _defaults()

    # bundled_settings.json が配布物ルートにあれば空のキーを補完する
    # （管理者がトークン等を事前設定して配布するためのファイル。gitignore対象）
    bundled_path = os.path.join(config.get_base_path(), "bundled_settings.json")
    if os.path.exists(bundled_path):
        try:
            with open(bundled_path, encoding="utf-8") as f:
                bundled = json.load(f)
            for k, v in bundled.items():
                if not s.get(k):   # 未設定の項目だけ補完（ユーザー設定を上書きしない）
                    s[k] = v
        except Exception:
            pass

    return s


def save_settings(settings: dict):
    os.makedirs(config.APP_DATA_DIR, exist_ok=True)
    with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def _defaults() -> dict:
    return {
        "slack_webhook_url":        "",
        "slack_notify_on_complete": True,
        "slack_notify_on_error":    True,
        "slack_notify_per_project": False,
        "update_share_path":        "",   # 旧: Google Drive 共有フォルダ（廃止予定）
        "github_repo":              "",   # 例: "owner/repo-name"
        "github_token":             "",   # Fine-grained PAT (Contents: Read-only)
        "github_branch":            "main",
    }


# ---------------------------------------------------------------------------
# 送信
# ---------------------------------------------------------------------------

def send(text: str, webhook_url: str = "") -> bool:
    """Slack Webhook に text を POST する。成功なら True。"""
    url = webhook_url or load_settings().get("slack_webhook_url", "")
    if not url:
        return False
    try:
        payload = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


def notify_complete(success: list[str], failed: list[str]):
    """全件完了サマリを通知する。"""
    s = load_settings()
    if not s.get("slack_notify_on_complete") or not s.get("slack_webhook_url"):
        return
    emoji = "✅" if not failed else "⚠️"
    text = (f"{emoji} [自動転写] 完了  成功 {len(success)} 件 / 失敗 {len(failed)} 件")
    if failed:
        text += f"\n❌ 失敗案件: {', '.join(failed)}"
    send(text, s["slack_webhook_url"])


def notify_error(project_name: str, error_msg: str = ""):
    """案件エラーを通知する。"""
    s = load_settings()
    if not s.get("slack_notify_on_error") or not s.get("slack_webhook_url"):
        return
    text = f"❌ [自動転写] エラー: {project_name}"
    if error_msg:
        text += f"\n{error_msg[:200]}"
    send(text, s["slack_webhook_url"])


def notify_per_project(project_name: str):
    """案件ごとの完了通知（設定で有効な場合のみ）。"""
    s = load_settings()
    if not s.get("slack_notify_per_project") or not s.get("slack_webhook_url"):
        return
    send(f"✅ [自動転写] 完了: {project_name}", s["slack_webhook_url"])

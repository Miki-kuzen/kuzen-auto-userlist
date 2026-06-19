"""Googleスプレッドシートの認証（OAuth）。

サービスアカウント鍵の配布を廃止し、各従業員が自分のGoogleアカウントで認可する。
  - 同梱する oauth_client.json は desktop型クライアント（機密でない）。
  - 認可後のトークンは端末ローカル（%LOCALAPPDATA%）にのみ保存。
  - 同意画面 User Type=Internal（kuzen.io Workspace）ならトークンは無期限。
"""
import os

import gspread

import config


def get_gspread_client():
    """初回はブラウザで認可、2回目以降は保存済みトークンを自動利用。"""
    if not os.path.exists(config.OAUTH_CLIENT_PATH):
        raise FileNotFoundError(
            "oauth_client.json が見つかりません。"
            "README の手順に従い、Google desktop OAuth クライアントを配置してください。"
        )
    os.makedirs(config.APP_DATA_DIR, exist_ok=True)
    return gspread.oauth(
        credentials_filename=config.OAUTH_CLIENT_PATH,
        authorized_user_filename=config.GOOGLE_TOKEN_FILE,
        scopes=config.GOOGLE_SCOPES,
    )

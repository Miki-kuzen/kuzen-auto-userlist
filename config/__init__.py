"""非機密の設定 + 同梱データファイルをまとめる config パッケージ。

`import config` でこれまで通り使える（config.py を本ファイルに移動しただけ）。
このフォルダ（config/）には設定コードと、配布される設定/データファイルを置く:
  - config/__init__.py            このファイル（設定コード）
  - config/changelog.json         更新履歴（自動アップデートで配布）
  - config/bundled_settings.json  配布時に同梱する初期設定（PAT 等・gitignore 対象）

⚠️ パスワード・2FAシークレット・サービスアカウント鍵などの秘密は
   このフォルダにも、配布パッケージのどこにも置かない。
   秘密は各端末の %LOCALAPPDATA%\\UserListBot\\ にのみ保存される。
"""
import os
import sys


# --- アプリバージョン -------------------------------------------------------
APP_VERSION = "2.0.2"

# --- 取得元サイト ---------------------------------------------------------
# 全案件で共通。差分は services/ 配下の 6 桁 ID のみ。
BASE_URL_TEMPLATE = "https://dashboard.kuzen.io/services/{service_id}/users?type=userList"

# --- Google API スコープ --------------------------------------------------
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# --- タイムアウト ---------------------------------------------------------
WAIT_TIMEOUT = 25          # Selenium 要素待ちの基本秒数
LOGIN_WAIT_TIMEOUT = 600   # 手動ログイン完了を待つ最大秒数（10分）
CSV_GEN_RETRIES = 20       # CSV 生成完了のポーリング回数


# config/ フォルダ自身の絶対パス
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))


def get_base_path() -> str:
    """アプリのルート（app.py / projects/ / credentials/ がある場所）。

    config/ パッケージの一つ上の階層を指す。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(_CONFIG_DIR)


def resource_path(name: str) -> str:
    """配布パッケージのルート直下に同梱されたファイル/フォルダの絶対パス。"""
    return os.path.join(get_base_path(), name)


def config_path(name: str) -> str:
    """config/ フォルダ内に同梱されたファイルの絶対パス。"""
    return os.path.join(_CONFIG_DIR, name)


# --- ルート直下の同梱物（すべて非機密・公開可） --------------------------
PROJECTS_DIR = resource_path("projects")
# oauth_client.json は credentials/ フォルダに置く（.gitignore 対象）
OAUTH_CLIENT_PATH = resource_path(os.path.join("credentials", "oauth_client.json"))

# --- config/ フォルダ内の同梱物 ------------------------------------------
# 更新履歴（リポジトリ同梱・自動アップデートで配布）
CHANGELOG_PATH = config_path("changelog.json")
# 配布時に同梱する初期設定（GitHub PAT 等。gitignore 対象・自動更新の対象外）
BUNDLED_SETTINGS_PATH = config_path("bundled_settings.json")

# --- 端末ローカルの保管先（秘密はここだけ。インストール先には置かない） --
APP_DATA_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "UserListBot"
)
CHROME_PROFILE_DIR = os.path.join(APP_DATA_DIR, "chrome-profile")  # サイトのログインCookie
GOOGLE_TOKEN_FILE = os.path.join(APP_DATA_DIR, "google_token.json")  # OAuthトークン
DOWNLOAD_DIR = os.path.join(APP_DATA_DIR, "temp_download")           # 一時CSV（処理後削除）

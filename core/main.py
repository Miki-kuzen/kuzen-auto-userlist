"""顧客数値 自動転写アプリ（v2 / 秘密を配らない版）。

配布パッケージに秘密を一切含めない構成:
  - サイト認証 = 専用Chromeプロファイル（各自が手動ログイン、保存しない）
  - Google認証 = OAuth（各自のアカウントで認可）
  - 案件定義  = projects/*.json（exec せずパース）
"""
import glob
import json
import os
import traceback
from datetime import datetime

import config
from .auth_site import get_ready_driver
from .auth_google import get_gspread_client
from .scraper import download_csv
from .sheets import upload_csv


def load_projects() -> list:
    """projects/*.json を読み込み、enabled=True の案件だけ返す。"""
    projects = []
    for path in sorted(glob.glob(os.path.join(config.PROJECTS_DIR, "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            p = json.load(f)
        if not p.get("enabled", True):
            continue
        p["base_url"] = config.BASE_URL_TEMPLATE.format(service_id=p["service_id"])
        projects.append(p)
    return projects


def _cleanup_downloads():
    if not os.path.isdir(config.DOWNLOAD_DIR):
        return
    for f in glob.glob(os.path.join(config.DOWNLOAD_DIR, "*")):
        try:
            os.remove(f)
        except OSError:
            pass


def run_all(log_callback=None, stop_event=None) -> dict:
    """全案件を実行する。GUI・CLI どちらからも呼べる共通関数。

    Args:
        log_callback: GUI ログ欄へ出力する関数 (msg: str) -> None。
                      None のときは print() を使う。
        stop_event:   threading.Event。セットされたら案件ループを中断する。

    Returns:
        {"success": [...], "failed": [...]}
    """
    def log(msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        if log_callback:
            log_callback(line)
        else:
            print(line)

    os.makedirs(config.APP_DATA_DIR, exist_ok=True)

    projects = load_projects()
    if not projects:
        log("実行可能な案件が見つかりません。projects/ フォルダを確認してください。")
        return {"success": [], "failed": []}

    skipped_count = sum(
        1 for path in glob.glob(os.path.join(config.PROJECTS_DIR, "*.json"))
        if not json.load(open(path, encoding="utf-8")).get("enabled", True)
    )
    log(f"{len(projects)} 件の案件を処理します。"
        + (f"（{skipped_count} 件は無効のためスキップ）" if skipped_count else ""))

    log("Google 認証を確認中...")
    gc = get_gspread_client()

    log("サイトのログイン状態を確認中...")
    driver = get_ready_driver(projects[0]["base_url"], log_callback=log)

    success, failed = [], []
    try:
        for p in projects:
            if stop_event and stop_event.is_set():
                log("停止要求を受け付けました。")
                break

            name = p.get("service_name", p["service_id"])
            log(f"{'─' * 40}")
            log(f"処理開始: {name}")
            try:
                csv_path = download_csv(driver, p, log_callback=log)
                upload_csv(gc, csv_path, p["spreadsheet_id"], p["sheet_name"])
                log(f"完了: {name}")
                success.append(name)
            except Exception as e:
                log(f"[ERROR] {name}: {e}")
                traceback.print_exc()
                failed.append(name)
            finally:
                _cleanup_downloads()
    finally:
        driver.quit()
        _cleanup_downloads()

    log(f"{'─' * 40}")
    log(f"結果: 成功 {len(success)} 件 / 失敗 {len(failed)} 件")
    if failed:
        log(f"失敗案件: {', '.join(failed)}")

    return {"success": success, "failed": failed}


def main():
    """ターミナルから直接実行するときのエントリーポイント。"""
    result = run_all()
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc()
    finally:
        print("\n--- 全ての処理を終了しました ---")
        input("閉じるには Enter キーを押してください...")

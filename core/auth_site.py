"""取得元サイトの認証。

専用Chromeプロファイル方式：
  - パスワードもTOTPシークレットも保存しない。
  - 初回のみ従業員が画面で手動ログイン（2FAも本人実施）。
  - セッションはプロファイルに残るため、2回目以降は自動（headless）。
  - 失効していた時だけ、画面ありで再ログインを促す。
"""
import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import config
from .elements import LoginElements


def _make_options(headless: bool) -> Options:
    opts = Options()
    opts.add_argument(f"--user-data-dir={config.CHROME_PROFILE_DIR}")
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
    else:
        opts.add_argument("--start-maximized")
    opts.add_experimental_option(
        "prefs",
        {
            "download.default_directory": config.DOWNLOAD_DIR,
            "download.prompt_for_download": False,
            "directory_upgrade": True,
        },
    )
    return opts


def build_driver(headless: bool):
    os.makedirs(config.CHROME_PROFILE_DIR, exist_ok=True)
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    # Selenium Manager (Selenium 4.6+) が Chrome バージョンに合った
    # ChromeDriver を自動取得するため Service の明示指定は不要。
    return webdriver.Chrome(options=_make_options(headless))


def _on_auth_page(driver) -> bool:
    """メール入力欄または2FA入力欄が存在する間は認証フロー途中と判定する。"""
    email_present = len(driver.find_elements(By.NAME, LoginElements.EMAIL_NAME)) > 0
    otp_present   = len(driver.find_elements(By.CSS_SELECTOR, LoginElements.OTP_INPUT_CSS)) > 0
    return email_present or otp_present


def get_ready_driver(check_url: str, log_callback=None):
    """ログイン済みのdriverを返す（常にheadlessで返す）。未ログインなら画面ありで再ログインを促す。"""
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    driver = build_driver(headless=True)
    driver.get(check_url)
    time.sleep(2)
    if not _on_auth_page(driver):
        log("サイトのセッションを確認しました（ログイン済み）。")
        return driver

    driver.quit()
    driver = build_driver(headless=False)
    driver.get(check_url)
    log("サイトのセッションが切れています。")
    log("開いたブラウザでID/パスワード＋2FAを入力してください。")
    log("ログインが完了すると自動的に処理を続行します。")

    deadline = time.time() + config.LOGIN_WAIT_TIMEOUT
    while time.time() < deadline:
        time.sleep(3)
        if not _on_auth_page(driver):
            time.sleep(3)
            if not _on_auth_page(driver):
                log("ログインを確認しました。headless モードに切り替えます...")
                driver.quit()
                driver = build_driver(headless=True)
                driver.get(check_url)
                time.sleep(2)
                log("処理を続行します。")
                return driver

    driver.quit()
    raise TimeoutError("制限時間内にログインが確認できませんでした。")

"""取得元サイトから案件のCSVをダウンロードする（ログイン済みdriver前提）。"""
import glob
import os
import time
import zipfile

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import config
from .elements import DashboardElements


def _clean_download_dir():
    os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    for f in glob.glob(os.path.join(config.DOWNLOAD_DIR, "*")):
        try:
            os.remove(f)
        except OSError:
            pass


def _wait_for_csv(timeout: int = 90) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not glob.glob(os.path.join(config.DOWNLOAD_DIR, "*.crdownload")):
            zips = glob.glob(os.path.join(config.DOWNLOAD_DIR, "*.zip"))
            if zips:
                with zipfile.ZipFile(zips[0]) as z:
                    z.extractall(config.DOWNLOAD_DIR)
            csvs = glob.glob(os.path.join(config.DOWNLOAD_DIR, "*.csv"))
            if csvs:
                return csvs[0]
        time.sleep(2)
    raise FileNotFoundError("ダウンロードしたCSVが見つかりませんでした。")


def download_csv(driver, project: dict, log_callback=None) -> str:
    """1案件分のCSVを生成・ダウンロードし、CSVファイルパスを返す。"""
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    _clean_download_dir()
    wait = WebDriverWait(driver, config.WAIT_TIMEOUT)

    driver.get(project["base_url"])

    wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, DashboardElements.THREE_DOTS_CSS))).click()
    wait.until(EC.element_to_be_clickable(
        (By.XPATH, DashboardElements.CSV_DL_XPATH))).click()
    wait.until(EC.element_to_be_clickable(
        (By.XPATH, DashboardElements.FINAL_DOWNLOAD_SUBMIT_XPATH))).click()

    time.sleep(1)
    driver.refresh()
    time.sleep(3)
    wait.until(EC.element_to_be_clickable(
        (By.XPATH, DashboardElements.TAB_CSV_RESULT_XPATH))).click()

    completed = False
    for i in range(config.CSV_GEN_RETRIES):
        try:
            status = wait.until(EC.presence_of_element_located(
                (By.XPATH, DashboardElements.FIRST_ROW_STATUS_XPATH)
            )).get_attribute("textContent")
            if status and "完了" in status:
                completed = True
                break
            log(f"  CSV生成待ち ({i + 1}/{config.CSV_GEN_RETRIES}): {status}...")
        except Exception:
            pass
        time.sleep(6)
        driver.refresh()
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, DashboardElements.TAB_CSV_RESULT_XPATH))).click()

    if not completed:
        raise TimeoutError("CSV生成が完了しませんでした（タイムアウト）。")

    wait.until(EC.element_to_be_clickable(
        (By.XPATH, DashboardElements.FIRST_ROW_DL_LINK_XPATH))).click()
    return _wait_for_csv()

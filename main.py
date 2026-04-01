# --- PyInstallerにライブラリを認識させるインポート ---
import pyotp
import gspread
import oauth2client.service_account
import selenium.webdriver.chrome.webdriver
import webdriver_manager.chrome
import google.auth
import zipfile 
import glob 
import csv

# 標準ライブラリ
import time
import os
import sys
import traceback
import importlib.util

# Selenium関連
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from oauth2client.service_account import ServiceAccountCredentials

def load_external_module(module_name, file_name):
    """外部ファイルを読み込む（キャッシュを削除して最新を反映）"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    path = os.path.join(base_path, file_name)

    # 既存のキャッシュがあれば削除して強制再読み込み
    if module_name in sys.modules:
        del sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None:
        raise ImportError(f"Could not load {file_name} at {path}")
        
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# 実行ファイルパスを正確に取得する関数
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# --- 共通設定の読み込み ---
config = load_external_module("config", "config.py")
elements_mod = load_external_module("elements", "elements.py")
LoginElements = elements_mod.LoginElements
DashboardElements = elements_mod.DashboardElements

def setup_driver(headless=True):
    """ブラウザの設定と起動（ドライバの自動管理を含む）"""
    abs_download_path = os.path.join(os.getcwd(), config.DOWNLOAD_DIR_NAME)
    if not os.path.exists(abs_download_path):
        os.makedirs(abs_download_path)
    
    for f in os.listdir(abs_download_path):
        if f.endswith(".zip") or f.endswith(".csv"):
            os.remove(os.path.join(abs_download_path, f))

    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless') 
        chrome_options.add_argument('--disable-gpu')
    else:
        chrome_options.add_argument('--start-maximized') 

    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": abs_download_path,
        "download.prompt_for_download": False,
        "directory_upgrade": True
    })
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver, abs_download_path

# 案件ごとの設定（p_config）を受け取る
def upload_to_sheets(file_path, p_config):
    """CSVの内容をスプレッドシートにアップロードする"""
    try:
        print(f"スプレッドシート '{p_config.SHEET_NAME}' への書き込みを開始します")
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(config.SERVICE_ACCOUNT_FILE, scope)
        client = gspread.authorize(creds)
        
        # 案件固有のIDとシート名を使用
        spreadsheet = client.open_by_key(p_config.SPREADSHEET_ID)
        sheet = spreadsheet.worksheet(p_config.SHEET_NAME)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            data = list(reader)
        
        sheet.clear()
        # value_input_option='USER_ENTERED' は手入力操作　-> 日付の入力は日付に自動変換
        sheet.update('A1', data, value_input_option='USER_ENTERED')
        print(f"スプレッドシートの更新が完了しました。")
        
    except Exception as e:
        print(f"スプレッドシート更新中にエラーが発生しました: {e}")

# 案件1件分の処理を独立した関数
def run_project(p_config):
    """1つの案件を実行するメインロジック"""
    print(f"\n{'='*60}")
    print(f">>> 処理開始: {p_config.SERVICE_NAME}")
    print(f">>> 備考: {getattr(p_config, 'COMMENT', 'なし')}")
    print(f"{'='*60}")

    driver, download_path = setup_driver(headless=True)
    wait = WebDriverWait(driver, 25) 

    try:
        # 1. ログインフェーズ (p_config.BASE_URL を使用)
        driver.get(p_config.BASE_URL)
        print("ログイン情報を入力中...")
        wait.until(EC.visibility_of_element_located((By.NAME, LoginElements.EMAIL_NAME))).send_keys(config.USER_EMAIL)
        driver.find_element(By.NAME, LoginElements.PASS_NAME).send_keys(config.USER_PASS)
        driver.find_element(By.XPATH, LoginElements.LOGIN_SUBMIT_XPATH).click()

        # 2. 多段階認証 (2FA) フェーズ
        print("2FA認証画面の表示を待機中...")
        otp_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, LoginElements.OTP_INPUT_CSS)))
        totp = pyotp.TOTP(config.OTP_SECRET)
        otp_input.send_keys(totp.now())
        wait.until(EC.element_to_be_clickable((By.XPATH, LoginElements.OTP_SUBMIT_XPATH))).click()

        # 3. 操作フェーズ
        print("CSV作成リクエスト送信中...")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, DashboardElements.THREE_DOTS_CSS))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, DashboardElements.CSV_DL_XPATH))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, DashboardElements.FINAL_DOWNLOAD_SUBMIT_XPATH))).click()

        # 4. 画面更新 ➔ タブ遷移
        time.sleep(1)
        driver.refresh()
        time.sleep(3)
        wait.until(EC.element_to_be_clickable((By.XPATH, DashboardElements.TAB_CSV_RESULT_XPATH))).click()

        # 5. ステータス待ち
        print("CSV生成完了を待機中...")
        for i in range(20):
            try:
                status_element = wait.until(EC.presence_of_element_located((By.XPATH, DashboardElements.FIRST_ROW_STATUS_XPATH)))
                current_status = status_element.get_attribute("textContent")
                if "完了" in current_status:
                    print(f"最新ステータス: {current_status}")
                    break
                print(f"確認 {i+1}回目: {current_status}...")
            except:
                pass
            time.sleep(6)
            driver.refresh()
            wait.until(EC.element_to_be_clickable((By.XPATH, DashboardElements.TAB_CSV_RESULT_XPATH))).click()
        else:
            print("タイムアウト：CSV生成が完了しませんでした。")
            return

        # 6. ダウンロード実行
        print("ファイルをダウンロード中...")
        wait.until(EC.element_to_be_clickable((By.XPATH, DashboardElements.FIRST_ROW_DL_LINK_XPATH))).click()
        time.sleep(7) 
        
        downloaded_files = os.listdir(download_path)
        if downloaded_files:
            downloaded_file_path = os.path.join(download_path, downloaded_files[0])
            target_file_path = downloaded_file_path

            if downloaded_file_path.endswith('.zip'):
                print("ZIP解凍中...")
                with zipfile.ZipFile(downloaded_file_path, 'r') as zip_ref:
                    zip_ref.extractall(download_path)
                extracted_csvs = glob.glob(os.path.join(download_path, "*.csv"))
                if extracted_csvs: target_file_path = extracted_csvs[0]

            # 7. スプレッドシートへのアップロード
            upload_to_sheets(target_file_path, p_config)
            print(f"完了URL: https://docs.google.com/spreadsheets/d/{p_config.SPREADSHEET_ID}")
        else:
            print("エラー: ファイルが見つかりません。")

    except Exception:
        print(f"案件 [{p_config.SERVICE_NAME}] でエラーが発生しました。")
        traceback.print_exc()
    finally:
        driver.quit()

def main():
    base_path = get_base_path()
    projects_dir = os.path.join(base_path, "projects")
    
    if not os.path.exists(projects_dir):
        os.makedirs(projects_dir)
        print("projects フォルダを作成しました。案件の .py ファイルを配置してください。")
        return

    # projects フォルダ内の .py ファイルをすべて取得
    project_files = [f for f in os.listdir(projects_dir) 
                     if f.endswith('.py') and not f.startswith('_')]
    
    if not project_files:
        print("projects 内に実行可能な .py ファイルが見つかりません。")
        return

    print(f"合計 {len(project_files)} 件の案件を順次処理します。")

    for file_name in project_files:
        project_path = os.path.join(projects_dir, file_name)
        try:
            # ファイル名を識別子にして動的読み込み
            # mod_案件A_py のような名前でキャッシュを管理
            module_id = f"mod_{file_name.replace('.', '_')}"
            p_config = load_external_module(module_id, project_path)
            
            run_project(p_config)
            
        except Exception:
            print(f"\n[ERROR] ファイル '{file_name}' の処理中に致命的なエラーが発生しました。")
            traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
    finally:
        print("\n--- 全ての処理を終了しました ---")
        input("閉じるには Enter キーを押してください...")
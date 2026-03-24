import os
import time
import zipfile 
import glob 
import csv
import pyotp
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Selenium関連
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 自作モジュールのインポート
import config
from elements import LoginElements, DashboardElements

def setup_driver():
    """ブラウザの設定と起動（ドライバの自動管理を含む）"""
    abs_download_path = os.path.join(os.getcwd(), config.DOWNLOAD_DIR_NAME)
    if not os.path.exists(abs_download_path):
        os.makedirs(abs_download_path)
    
    # フォルダ内の古いCSVファイルを削除（誤動作防止）
    for f in os.listdir(abs_download_path):
        if f.endswith(".zip") or f.endswith(".csv"):
            os.remove(os.path.join(abs_download_path, f))

    chrome_options = Options()
    
    # --- 画面を最大化する設定 ---
    chrome_options.add_argument('--start-maximized') 
    
    # ダウンロード先を指定し、確認ダイアログを無効化
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": abs_download_path,
        "download.prompt_for_download": False,
        "directory_upgrade": True
    })
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 念のため、起動直後にも最大化コマンドを送る（環境による不安定さを解消）
    driver.maximize_window()
    
    return driver, abs_download_path

def upload_to_sheets(file_path):
    """CSVの内容をスプレッドシートにアップロードする"""
    try:
        print(f"スプレッドシートへの書き込みを開始します: {file_path}")
        
        # 認証設定
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(config.SERVICE_ACCOUNT_FILE, scope)
        client = gspread.authorize(creds)
        
        # スプレッドシートとシートを開く
        spreadsheet = client.open_by_key(config.SPREADSHEET_ID)
        sheet = spreadsheet.worksheet(config.SHEET_NAME)
        
        # CSVファイルを読み込む（文字化けする場合は encoding='cp932' を試してください）
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            data = list(reader)
        
        # シートの内容をすべて消去してから、CSVデータを書き込む
        sheet.clear()
        sheet.update('A1', data)
        print(f"スプレッドシート '{config.SHEET_NAME}' の更新が完了しました。")
        
    except Exception as e:
        print(f"スプレッドシート更新中にエラーが発生しました: {e}")

def main():
    driver, download_path = setup_driver()
    wait = WebDriverWait(driver, 25) 

    try:
        # 1. ログインフェーズ
        driver.get(config.BASE_URL)
        print("ログイン情報を入力中...")
        wait.until(EC.visibility_of_element_located((By.NAME, LoginElements.EMAIL_NAME))).send_keys(config.USER_EMAIL)

        driver.find_element(By.NAME, LoginElements.PASS_NAME).send_keys(config.USER_PASS)
        driver.find_element(By.XPATH, LoginElements.LOGIN_SUBMIT_XPATH).click()

        # 2. 多段階認証 (2FA) フェーズ
        print("2FA認証画面の表示を待機中...")
        otp_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, LoginElements.OTP_INPUT_CSS)))
        
        totp = pyotp.TOTP(config.OTP_SECRET)
        otp_code = totp.now()
        otp_input.send_keys(otp_code)
        
        otp_submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, LoginElements.OTP_SUBMIT_XPATH)))
        otp_submit_btn.click()

        # 3. 操作フェーズ（三点リーダー ➔ CSVダウンロード）
        print("CSV作成リクエスト送信中...")
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, DashboardElements.THREE_DOTS_CSS))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, DashboardElements.CSV_DL_XPATH))).click()

        final_dl_btn = wait.until(EC.element_to_be_clickable((By.XPATH, DashboardElements.FINAL_DOWNLOAD_SUBMIT_XPATH)))
        final_dl_btn.click()

        # 4. 画面更新 ➔ タブ遷移
        time.sleep(1)
        driver.refresh()
        time.sleep(3)
        wait.until(EC.element_to_be_clickable((By.XPATH, DashboardElements.TAB_CSV_RESULT_XPATH))).click()

        # 5. ステータス「完了」待ち（ポーリング）
        print("最新（1行目）のCSV生成完了を待機しています...")
        max_retries = 20
        
        for i in range(max_retries):
            try:
                # 1行目のステータス文字を取得
                status_element = wait.until(EC.visibility_of_element_located((By.XPATH, DashboardElements.FIRST_ROW_STATUS_XPATH)))
                current_status = status_element.text
                
                if "完了" in current_status:
                    print(f"最新のステータスが「{current_status}」になりました。")
                    break
                else:
                    print(f"確認 {i+1}回目: ステータスは「{current_status}」です。生成を待っています...")
            
            except Exception as e:
                print("待機中に要素を再検索します...")

            time.sleep(6)
            driver.refresh()
            # ページ更新後は必ずタブを再クリック
            wait.until(EC.element_to_be_clickable((By.XPATH, DashboardElements.TAB_CSV_RESULT_XPATH))).click()
            
        else:
            print("タイムアウト：CSVの生成が完了しませんでした。")
            return

        # 6. ファイルダウンロード実行
        print("ファイルをダウンロードします...")
        dl_btn = wait.until(EC.element_to_be_clickable((By.XPATH, DashboardElements.FIRST_ROW_DL_LINK_XPATH)))
        dl_btn.click()

        # ダウンロード完了（ファイル出現）を待機
        time.sleep(7) 
        downloaded_files = os.listdir(download_path)
        
        if downloaded_files:
            # フォルダ内の最初のファイルパスを取得
            downloaded_file_path = os.path.join(download_path, downloaded_files[0])
            print(f"ダウンロード成功: {downloaded_file_path}")

            # --- [追加] ZIP解凍ロジック ---
            target_file_path = downloaded_file_path # デフォルトはそのまま

            if downloaded_file_path.endswith('.zip'):
                print("ZIPファイルを解凍中...")
                with zipfile.ZipFile(downloaded_file_path, 'r') as zip_ref:
                    # ダウンロードフォルダ直下に解凍
                    zip_ref.extractall(download_path)
                
                # 解凍されたファイルの中からCSVを探す
                extracted_csvs = glob.glob(os.path.join(download_path, "*.csv"))
                if extracted_csvs:
                    target_file_path = extracted_csvs[0]
                    print(f"CSVを抽出しました: {target_file_path}")
                else:
                    print("エラー: ZIP内にCSVが見つかりませんでした。")
                    return

            # --- 7. Googleスプレッドシートへのアップロードを実行 ---
            # 解凍されたCSV（または直接降ってきたCSV）のパスを渡す
            upload_to_sheets(target_file_path)

        else:
            print("エラー: ダウンロードフォルダにファイルが見つかりませんでした。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
    
    finally:
        print("ブラウザを終了します。")
        driver.quit()

if __name__ == "__main__":
    main()
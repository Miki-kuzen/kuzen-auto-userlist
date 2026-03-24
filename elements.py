class LoginElements:
    EMAIL_NAME = "email"
    PASS_NAME = "password"
    LOGIN_SUBMIT_XPATH = "//div[contains(text(), 'ログイン')]"
    OTP_INPUT_CSS = "input.input.css-1s19k5j"
    OTP_SUBMIT_XPATH = "//button[contains(., '認証する')]"

class DashboardElements:
    # 三点リーダー
    THREE_DOTS_CSS = "[data-testid='show-more-button']"
    # CSVダウンロードボタン
    CSV_DL_XPATH = "//div[contains(@class, 'text') and text()='CSVダウンロード']"
    # [追加] 「ダウンロード」というテキストを含むボタンを特定
    FINAL_DOWNLOAD_SUBMIT_XPATH = "//button[contains(., 'ダウンロード')]"
    # タブ切り替え
    TAB_CSV_RESULT_XPATH = "//div[contains(text(), 'CSV操作結果')]"
    # 「完了」か「生成中」のどちらかの文字が入る場所を狙います
    FIRST_ROW_STATUS_XPATH = "(//div[@class='tableBody']/div[contains(@class, 'css-1mq5aov')])[1]//div[@class='css-5nu4ed']"
    # 1行目の「ダウンロード」ボタン
    FIRST_ROW_DL_LINK_XPATH = "(//div[@class='tableBody']/div[contains(@class, 'css-1mq5aov')])[1]//div[@class='css-6fe6ry']"
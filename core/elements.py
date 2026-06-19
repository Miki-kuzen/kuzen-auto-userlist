"""画面要素のセレクタ定義（サイトのUI変更時はここだけ直す）。"""


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
    # 確定ダウンロードボタン
    FINAL_DOWNLOAD_SUBMIT_XPATH = "//button[contains(., 'ダウンロード')]"
    # タブ切り替え（CSV操作結果）
    TAB_CSV_RESULT_XPATH = "//div[contains(text(), 'CSV操作結果')]"
    # 1行目のステータス（「完了」「生成中」）
    FIRST_ROW_STATUS_XPATH = (
        "(//div[@class='tableBody']/div[contains(@class, 'css-1mq5aov')])[1]"
        "//div[@class='css-5nu4ed']"
    )
    # 1行目のダウンロードリンク
    FIRST_ROW_DL_LINK_XPATH = (
        "(//div[@class='tableBody']/div[contains(@class, 'css-1mq5aov')])[1]"
        "//div[@class='css-6fe6ry']"
    )

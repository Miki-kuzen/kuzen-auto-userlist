"""CSVをGoogleスプレッドシートへ転写する。"""
import csv


def upload_csv(gc, csv_path: str, spreadsheet_id: str, sheet_name: str):
    """CSVの内容でシートを置き換える。

    value_input_option='USER_ENTERED' により、ユーザーがUIに手入力したときと
    同じ解釈で値が格納される（日付は日付、数値は数値として認識される）。
    'RAW' では日付が文字列扱いになり先頭に ' が付いてしまうため、こちらを使う。

    注意: USER_ENTERED では '=' や '+' で始まるセルが数式として評価される
    （Formula/CSV Injection の余地が戻る）。取得元は自社ダッシュボードのため許容。
    """
    sheet = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)

    with open(csv_path, "r", encoding="utf-8") as f:
        data = list(csv.reader(f))

    sheet.clear()
    if data:
        sheet.update(values=data, range_name="A1",
                     value_input_option="USER_ENTERED")

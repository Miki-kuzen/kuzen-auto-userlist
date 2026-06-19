"""CSVをGoogleスプレッドシートへ転写する。"""
import csv


def upload_csv(gc, csv_path: str, spreadsheet_id: str, sheet_name: str):
    """CSVの内容でシートを置き換える。

    value_input_option='RAW' により、'=' や '+' で始まるセルが数式として
    評価されない（Formula/CSV Injection を防止）。
    """
    sheet = gc.open_by_key(spreadsheet_id).worksheet(sheet_name)

    with open(csv_path, "r", encoding="utf-8") as f:
        data = list(csv.reader(f))

    sheet.clear()
    if data:
        sheet.update(values=data, range_name="A1", value_input_option="RAW")

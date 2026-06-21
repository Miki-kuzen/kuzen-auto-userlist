"""管理者用ビルドツール：manifest.json の生成。

--- GitHub private repo 方式（推奨）---
使い方:
  python tools/build_manifest.py --version 2.0.1

実行すると:
  1. プロジェクトルートの .py / .json / .md ファイルを走査
  2. 各ファイルの SHA256 を計算
  3. manifest.json をプロジェクトルートに書き込む（git push の対象になる）

管理者の作業フロー:
  1. コードを編集
  2. config.py の APP_VERSION を上げる
  3. python tools/build_manifest.py --version 2.0.1
  4. git add . && git commit -m "Release v2.0.1" && git push

--- Google Drive 共有フォルダ方式（旧）---
  python tools/build_manifest.py --version 2.0.1 --output /path/to/share
  ※ ファイルも --output フォルダにコピーされる
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

# このスクリプトは Automation-Userlist/ を基準にする
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT   = os.path.dirname(SCRIPT_DIR)

INCLUDE_EXTS = {".py", ".json", ".md"}
EXCLUDE_DIRS = {
    "__pycache__", ".git", "tools", "archive_v1",
    "dist", "dist_portable", "dist_launcher",
    "build", "build_launcher", "runtime",
    "credentials",          # 秘密: OAuth クライアント（配布物に手動同梱・リポジトリには入れない）
    "projects",             # 案件定義: git 管理外（端末/配布ごとに管理・自動更新の対象外）
}
EXCLUDE_FILES = {
    "manifest.json",
    "bundled_settings.json",           # 秘密: GitHub PAT を含む。絶対に manifest/リポジトリに載せない
    "bundled_settings_template.json",  # 配布・自動更新の対象外
}


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _collect_files() -> dict[str, str]:
    """対象ファイルを走査し {相対パス: sha256} を返す。"""
    result = {}
    for dirpath, dirnames, filenames in os.walk(APP_ROOT):
        # 除外ディレクトリをスキップ（in-place で変更する必要がある）
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDE_DIRS and not d.startswith(".")
        ]
        for fname in filenames:
            if fname in EXCLUDE_FILES:
                continue
            _, ext = os.path.splitext(fname)
            if ext not in INCLUDE_EXTS:
                continue
            abs_path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(abs_path, APP_ROOT).replace("\\", "/")
            result[rel_path] = _sha256(abs_path)
    return result


def main():
    parser = argparse.ArgumentParser(description="manifest.json を生成します。")
    parser.add_argument("--version", required=True, help="新しいバージョン番号（例: 2.0.1）")
    parser.add_argument("--comment", default=None,
                        help="更新内容（1行）。指定すると changelog.json に "
                             "「本日の日付 + バージョン + コメント」を1件追記する。")
    parser.add_argument("--output",  default=None,
                        help="指定するとファイルをそのフォルダにもコピー（Google Drive方式）。"
                             "省略時はプロジェクトルートに manifest.json だけ生成（GitHub方式）。")
    args = parser.parse_args()

    # --comment 指定時は changelog.json に追記（manifest 生成前に行い、ハッシュへ反映）
    if args.comment:
        sys.path.insert(0, APP_ROOT)
        from core import changelog
        entry = changelog.append_entry(args.version, args.comment)
        print(f"changelog.json に追記: {entry['date']}  v{entry['version']}  {entry['comment']}")

    print(f"スキャン中: {APP_ROOT}")
    files_map = _collect_files()
    print(f"  {len(files_map)} ファイルを検出しました。")

    manifest = {
        "version": args.version,
        "files":   files_map,
    }

    if args.output:
        # ── Google Drive 共有フォルダ方式 ──
        os.makedirs(args.output, exist_ok=True)
        manifest_path = os.path.join(args.output, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"manifest.json を書き込みました: {manifest_path}")

        copied = 0
        for rel_path in files_map:
            src = os.path.join(APP_ROOT, rel_path.replace("/", os.sep))
            dst = os.path.join(args.output, rel_path.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        print(f"ファイルをコピーしました: {copied} 件 → {args.output}")
    else:
        # ── GitHub 方式: プロジェクトルートに manifest.json だけ生成 ──
        manifest_path = os.path.join(APP_ROOT, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"manifest.json を書き込みました: {manifest_path}")
        print("次のステップ: git add . && git commit && git push")

    print("完了！")


if __name__ == "__main__":
    main()

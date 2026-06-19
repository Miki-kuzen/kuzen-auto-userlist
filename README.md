# 顧客数値 自動転写アプリ（Automation-Userlist）

取得元サイト（`dashboard.kuzen.io`）から案件ごとのユーザーリスト CSV を取得し、
Google スプレッドシートへ自動転写するローカル GUI アプリ。

**設計の核 — 配布パッケージに秘密を一切含めない。**

| 認証対象 | v2 の方式 | 旧 v1 の問題 |
|---|---|---|
| サイト認証 | 各自が専用 Chrome プロファイルで手動ログイン（パスワード/2FA は保存しない） | 平文の ID/PW/2FA を全員に同梱 |
| Google 認証 | 各自の kuzen.io アカウントで OAuth 認可 | サービスアカウント鍵を同梱 |
| 案件定義 | `projects/*.json`（コードではなくデータ） | `.py` を動的 import |

> 旧版（`archive_v1/`）はパスワード・2FA シークレット・サービスアカウント鍵を平文同梱していたため、
> これらは **無効化・ローテーション対象**。

---

## フォルダ構成

```
Automation-Userlist/            ← このリポジトリ（git 管理対象）
├─ app.py                       # エントリーポイント
├─ config.py                    # 非機密の設定（バージョン・URL）
├─ core/                        # 自動化ロジック
│   ├─ main.py                  #   全案件の実行制御
│   ├─ auth_site.py             #   サイト認証（Chrome プロファイル）
│   ├─ auth_google.py           #   Google OAuth
│   ├─ scraper.py               #   CSV ダウンロード
│   ├─ sheets.py                #   スプレッドシート転写
│   ├─ notifier.py              #   Slack 通知
│   └─ updater.py               #   GitHub 自動アップデート
├─ gui/                         # tkinter GUI（ダッシュボード/案件管理/設定/ヘルプ）
├─ help/                        # アプリ内ヘルプ（*.md）
├─ projects/                    # 案件定義（6桁IDなどのデータのみ）
├─ tools/                       # 管理者用ビルドツール（配布物には含めない）
│   ├─ build_manifest.py        #   manifest.json 生成
│   ├─ launcher.py              #   ポータブル起動スタブ
│   ├─ setup_runtime.bat        #   Python 埋め込みランタイム構築
│   └─ build_launcher.bat       #   launcher.exe ビルド
├─ build_portable.bat           # ポータブル配布ビルド
├─ manifest.json                # 自動アップデート用のファイル一覧+ハッシュ
└─ requirements.txt

credentials/                    ← 秘密。git 無視・配布時に手動同梱
└─ oauth_client.json            #   Google desktop OAuth クライアント

bundled_settings.json           ← 秘密。git 無視・配布時に同梱（GitHub PAT 等）

%LOCALAPPDATA%\UserListBot\     ← 端末ローカル。秘密はここだけに生成される
├─ chrome-profile/              #   サイトのログインセッション
├─ google_token.json            #   Google OAuth トークン
├─ settings.json                #   各端末の設定（Webhook/PAT 等）
└─ temp_download/               #   一時CSV（処理後に自動削除）
```

> `.venv` は **このフォルダの一つ上**（`user_list/.venv`）に作成する。ビルドスクリプトは `..\.venv` を参照する。

---

## 管理者の初期準備（1回だけ）

### 1. Google console 側
1. GCP プロジェクトで **Google Sheets API** と **Google Drive API** を有効化。
2. OAuth 同意画面の **User Type = Internal**（kuzen.io Workspace）に設定。
   → トークンが無期限になり再認可が実質不要。
3. **Desktop 型** の OAuth クライアントを作成し JSON をダウンロード。
4. その JSON を `credentials/oauth_client.json` という名前で配置する。
   - Desktop 型の client_secret は Google の仕様上「機密でない」ため同梱・配布可。

### 2. スプレッドシートのアクセス権
サービスアカウント `kuzen-bot@...` への編集者登録は **廃止**。
代わりに、利用する従業員の kuzen.io アカウントが対象スプレッドシートを編集できる状態にする（推奨順）:

1. **共有ドライブ** に対象スプレッドシートを置く
2. **Google グループ**（例 `userlist-team@kuzen.io`）を各スプシの編集者にする
3. 個別に各従業員へ編集共有

### 3. GitHub 自動アップデートの準備
1. private リポジトリにコードを push（`manifest.json` を含める）。
2. **Fine-grained PAT** を発行（対象リポジトリのみ・**Contents: Read-only**）。
3. `bundled_settings_template.json` をコピーして `bundled_settings.json` を作成し、
   リポジトリ名・PAT・ブランチを記入（このファイルは git 無視・配布物にのみ同梱）。

詳細は アプリ内ヘルプ `help/05_アップデート管理.md` 参照。

---

## ビルドと配布

### 推奨：ポータブル配布（`build_portable.bat`）
```
build_portable.bat
```
- `UserListBot.exe`（軽量ランチャー）+ `runtime/`（Python 埋め込み）+ ソース一式を
  `dist_portable/UserListBot/` に生成する。
- ソースは外部ファイルのまま同梱されるため、**GitHub 自動アップデートが効く**
  （`git push` だけで従業員のアプリが次回起動時に差分取得・再起動）。
- 配布は `dist_portable/UserListBot/` を zip にして共有するだけ。

### 旧方式：単一フォルダ exe（`tools/build_exe.bat`）
```
tools\build_exe.bat
```
- PyInstaller `--onedir`（`app.spec`）で `dist/UserListBot/` を生成。
- exe に固めるため自動アップデートは「管理者が新 exe を再配布」する運用になる。

---

## 管理者の更新フロー（リリースのたびに）

```
# 1. コードを編集
# 2. config.py の APP_VERSION を上げる（例: 2.0.2）
python tools\build_manifest.py --version 2.0.2
git add .
git commit -m "Release v2.0.2"
git push
```
→ 次回従業員がアプリを起動すると自動でアップデートダイアログが表示される。

---

## 従業員の使い方

### 初回のみ
1. 配布フォルダを任意の場所に展開し `UserListBot.exe` を起動。
2. **Google 認可** … ブラウザが開くので自分の kuzen.io アカウントで許可。
3. **サイトログイン** … 実行時に Chrome が開いたら ID/パスワード＋2FA を入力。完了後、自動で処理続行。

### 2回目以降
- `UserListBot.exe` を起動して **「▶ 全件実行」** を押すだけ。
- サイトのセッションが切れていたときだけ、再ログイン画面が出る。

---

## セキュリティ要点

- 配布物に秘密ゼロ（パスワード/2FA/サービスアカウント鍵を持たない）。
- 各端末には「その従業員自身の権限・認証情報」だけが存在。退職者は本人アカウント無効化で完結。
- スプレッドシート書き込みは `value_input_option='RAW'`（数式インジェクション対策）。
- 個人情報を含む一時 CSV は案件ごと・終了時に削除。
- `credentials/`・`bundled_settings.json` は `.gitignore` 済み（リポジトリに入らない）。

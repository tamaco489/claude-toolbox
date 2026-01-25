---
name: report-email
description: テンプレートに基づきPDFファイルを添付してメールを送信する
allowed-tools: Bash, Read, Write, Glob, AskUserQuestion
---

# レポートメール送信スキル

このスキルは、指定したテンプレートに基づいてファイルを添付し、指定した送信元から宛先へメールを送信します。

## 前提条件

### Gmail アプリパスワードの設定

Gmail SMTPを使用するには、Googleアカウントでアプリパスワードを生成する必要があります：

1. [Googleアカウント](https://myaccount.google.com/) にアクセス
2. 「セキュリティ」→「2段階認証プロセス」を有効化
3. 「アプリパスワード」を選択し、新しいパスワードを生成
4. 生成された16桁のパスワードを `config/secrets.json` に設定

**注意**: 通常のGoogleパスワードではSMTP認証はできません。必ずアプリパスワードを使用してください。

---

## 実行手順

### 1. 添付ファイルのヒアリング

ユーザーに添付するファイルを確認します。

**手順:**
1. Globツールで `output/*` などを検索し、利用可能なファイルを一覧表示
2. AskUserQuestionツールで添付するファイルを選択してもらう

**確認例:**
```
以下のファイルが見つかりました。添付するファイルを選択してください（最大5ファイル）:

1. output/ai-news-2026-01-24.pdf
2. output/report.xlsx
3. output/data.csv
```

**対応ファイル形式:**
- PDF (.pdf)
- Excel (.xlsx, .xls)
- CSV (.csv)
- PowerPoint (.pptx, .ppt)
- Word (.docx, .doc)
- 画像 (.jpg, .jpeg, .png, .gif)
- テキスト (.txt)
- ZIP (.zip)
- その他（application/octet-streamとして送信）

**制限事項:**
- 添付ファイルは最大5つまで
- 各ファイルは25MB以下（Gmail制限）

### 2. メール送信の実行

ヒアリングで確認したファイルを添付してメールを送信します：

```bash
python .claude/skills/report-email/scripts/send_email.py <file_paths> [to_email] [subject] [body]
```

**引数:**
- `file_paths`: 添付するファイルのパス（カンマ区切りで複数指定可、最大5ファイル）
- `to_email`: 送信先メールアドレス（省略時はデフォルト設定を使用）
- `subject`: メール件名（省略時はテンプレートから生成）
- `body`: メール本文（省略時はテンプレートから生成）

**例:**
```bash
# 単一ファイル送信（デフォルト宛先）
python .claude/skills/report-email/scripts/send_email.py output/report.pdf

# 複数ファイル送信（最大5ファイル、異なる形式も可）
python .claude/skills/report-email/scripts/send_email.py "output/report.pdf,output/data.xlsx,output/image.png"

# 宛先と件名を指定
python .claude/skills/report-email/scripts/send_email.py "output/report.pdf" user@example.com "週次レポート"
```

---

## 設定リファレンス

### config/secrets.json

| キー | 説明 |
|------|------|
| `smtp_server` | SMTPサーバーアドレス（Gmail: smtp.gmail.com） |
| `smtp_port` | SMTPポート（Gmail: 587） |
| `sender_email` | 送信元メールアドレス |
| `sender_password` | アプリパスワード |
| `sender_name` | 送信者名（省略可） |
| `default_recipient` | デフォルト送信先（省略可） |

### templates/email_template.json

| キー | 説明 |
|------|------|
| `subject` | メール件名テンプレート |
| `body` | メール本文テンプレート |
| `signature` | 署名（本文末尾に追加） |

**テンプレート変数:**
- `{date}` - 送信日（YYYY年MM月DD日形式）
- `{date_compact}` - 送信日（YYYYMMDD形式）
- `{filenames}` - 添付ファイル名一覧
- `{recipient}` - 宛先メールアドレス

---

## トラブルシューティング

### 認証エラーが発生する場合

- アプリパスワードが正しく設定されているか確認
- 2段階認証が有効になっているか確認

### 送信がタイムアウトする場合

- ネットワーク接続を確認
- ファイアウォールでポート587がブロックされていないか確認

### ファイルが添付されない場合

- ファイルのパスが正しいか確認
- ファイルサイズが25MB以下か確認（Gmailの添付ファイル制限）
- 添付ファイル数が5以下か確認

## セキュリティ上の注意

- `secrets.json` はGitにコミットしないでください（`.gitignore` に追加推奨）
- アプリパスワードは定期的に更新することを推奨します

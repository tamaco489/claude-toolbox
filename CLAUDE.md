# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ニュース収集・要約・PDF生成・配信を自動化するClaude Codeスキル集。各スキルの詳細は `SKILL.md` を参照。

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

`secrets/settings.json` に認証情報を設定 (`settings.example.json` を参照、gitignore 対象)。

## Structure

```text
.claude/skills/{skill-name}/
├── SKILL.md       # 実行手順・制約（スキル実行時はこれに従う）
├── scripts/       # Python スクリプト群
├── templates/     # カテゴリ定義、PDF/Slack/メールテンプレート
secrets/                       # 認証情報・OAuth トークン等（gitignore 対象）
├── settings.json              # 全スキル共通の設定ファイル
├── client_secret_xxx.json     # GCP OAuth クライアントシークレット
└── gdrive_token.json          # Google Drive トークン
```

## Skills

| コマンド              | 説明                                       |
| --------------------- | ------------------------------------------ |
| `/ai-news-summary`    | AIニュースを収集・要約・PDF・Slack投稿     |
| `/aws-blog-summary`   | AWSブログを収集・要約・PDF・Slack投稿      |
| `/jp-it-news-summary` | 国内ITニュースを収集・要約・PDF・Slack投稿 |
| `/report-email`       | PDFを添付してメール送信                    |

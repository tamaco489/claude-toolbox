# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ニュース収集・要約・PDF生成・配信を自動化するClaude Codeスキル集。各スキルの詳細は `SKILL.md` を参照。

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

各スキルの `config/secrets.json` にSlack/SMTP認証情報を設定（`secrets.example.json` を参照）。

## Structure

```text
secret/                        # GCP OAuth クライアントシークレット等（gitignore対象）
.claude/skills/{skill-name}/
├── SKILL.md       # 実行手順・制約（スキル実行時はこれに従う）
├── config/        # secrets.json（gitignore対象）
├── scripts/       # Python スクリプト群
└── templates/     # カテゴリ定義、PDF/Slack/メールテンプレート
```

## Skills

| コマンド              | 説明                                       |
| --------------------- | ------------------------------------------ |
| `/ai-news-summary`    | AIニュースを収集・要約・PDF・Slack投稿     |
| `/aws-blog-summary`   | AWSブログを収集・要約・PDF・Slack投稿      |
| `/jp-it-news-summary` | 国内ITニュースを収集・要約・PDF・Slack投稿 |
| `/report-email`       | PDFを添付してメール送信                    |

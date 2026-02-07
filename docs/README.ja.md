[English](README.md)

# Claude Code スキル集

ニュース収集・レポート作成を自動化する Claude Code 用カスタムスキル。

## スキル一覧

| コマンド              | 説明                                       |
| --------------------- | ------------------------------------------ |
| `/ai-news-summary`    | AIニュースを収集・要約・PDF・Slack投稿     |
| `/aws-blog-summary`   | AWSブログを収集・要約・PDF・Slack投稿      |
| `/jp-it-news-summary` | 国内ITニュースを収集・要約・PDF・Slack投稿 |
| `/report-email`       | PDFを添付してメール送信                    |

## セットアップ

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

各スキルの `config/secrets.json` に認証情報を設定（`secrets.example.json` を参照）。

## ライセンス

Private

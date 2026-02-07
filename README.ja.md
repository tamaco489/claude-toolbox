# Claude Code スキル集

ニュース収集・レポート作成を自動化する Claude Code 用カスタムスキル。

## スキル一覧

| スキル               | 説明                                             |
| -------------------- | ------------------------------------------------ |
| `ai-news-summary`    | AIニュースを収集・要約し、PDF生成・Slack投稿     |
| `aws-blog-summary`   | AWSブログ記事を収集・要約し、PDF生成・Slack投稿  |
| `jp-it-news-summary` | 国内ITニュースを収集・要約し、PDF生成・Slack投稿 |
| `report-email`       | PDFを添付してメール送信                          |

## セットアップ

```bash
# 仮想環境を作成
python3 -m venv .venv

# 依存パッケージをインストール
source .venv/bin/activate
pip install requests beautifulsoup4 feedparser reportlab fake-useragent
```

## 設定

各スキルディレクトリに `config/secrets.json` を作成:

```json
{
  "slack_token": "xoxb-...",
  "slack_channel": "#channel-name"
}
```

## 使い方

Claude Code でスキルを実行:

```
/ai-news-summary
/aws-blog-summary
/jp-it-news-summary
```

## ライセンス

Private

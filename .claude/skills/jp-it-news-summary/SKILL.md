---
name: jp-it-news-summary
description: 国内ITニュースを収集・要約してPDF生成・Slack投稿する
---

# 国内ITニュース要約・PDF・Slack投稿スキル

このスキルは、国内の主要ITニュースサイトから最新記事を取得し、日本語で要約・カテゴリー分類した後、PDFを生成してSlackに投稿します。

## ⚠️ 実行上の注意事項

このスキルを実行する際は、以下のルールを必ず遵守してください。

### 要約フェーズにおける原則

1. **正確性 > 即時性**
   - 速度よりも正確さを優先すること
   - 不明な点があれば原文を再確認し、推測で補完しない

2. **原文への忠実性**
   - 記事に書かれていない情報を追加しない
   - 著者の主張を歪曲・誇張しない
   - 技術用語は正確に使用する

3. **ハルシネーションの禁止**
   - 存在しない事実、数値、引用を生成しない
   - 確認できない情報は要約に含めない

4. **出典の明記**
   - 各記事の出典元とURLを必ず保持する
   - 複数ソースの情報を混同しない

### カテゴリ分類における原則

1. **定義されたカテゴリのみ使用**
   - `categories.csv` に定義されたカテゴリから選択する
   - 該当なしの場合は「その他」を使用

2. **主題に基づく分類**
   - 記事の主要なトピックで分類する
   - 複数カテゴリに該当する場合は最も関連性の高いものを選択

### 品質チェック

- 要約が日本語として自然か確認する
- 専門用語の誤訳がないか確認する
- 重複記事がないか確認する

---

## 実行手順

### 1. 一時ファイルのクリーンアップ

前回実行時の一時ファイルが残っている場合に備え、最初に削除してください：

```bash
rm -f tmp/jp_raw_articles.json tmp/jp_summarized_articles.json
```

### 2. Pythonパッケージの確認

まず、必要なパッケージがインストールされているか確認してください：

```bash
pip install requests beautifulsoup4 feedparser reportlab fake-useragent google-api-python-client google-auth google-auth-oauthlib
```

### 3. ニュースソースの読み込み

テンプレートCSVファイルを読み込んでください：

- `.claude/skills/jp-it-news-summary/templates/news_sources.csv` - ニュースソースURL
- `.claude/skills/jp-it-news-summary/templates/categories.csv` - カテゴリ分類

### 4. ニュース取得

以下のスクリプトを実行してニュースを取得してください：

```bash
./.claude/skills/jp-it-news-summary/scripts/fetch_news.py
```

スクリプトはJSON形式で記事一覧を標準出力します。出力を `tmp/jp_raw_articles.json` に保存してください。

### 5. 記事の要約・カテゴリー分類

取得した記事を読み、以下の作業を行ってください：

1. 各記事を日本語で要約（100-200文字程度）
2. `categories.csv` に基づいてカテゴリーを割り当て
3. 要約結果を以下のJSON形式で `tmp/jp_summarized_articles.json` に保存：

```json
{
  "date": "YYYY-MM-DD",
  "articles": [
    {
      "title": "記事タイトル",
      "source": "ソース名",
      "url": "記事URL",
      "category": "カテゴリ名",
      "summary": "日本語要約"
    }
  ]
}
```

### 6. PDF生成

要約データをPDFに変換してください：

```bash
cat tmp/jp_summarized_articles.json | ./.claude/skills/jp-it-news-summary/scripts/generate_pdf.py
```

PDFは `output/jp-it-news-YYYY-MM-DD.pdf` に出力されます。

### 7. Slack投稿

PDFファイルのパスとサマリーをSlackに投稿してください：

```bash
./.claude/skills/jp-it-news-summary/scripts/post_slack.py output/jp-it-news-YYYY-MM-DD.pdf "本日の国内ITニュース要約です"
```

### 8. Google Driveアップロード

PDFファイルを Google Drive の指定フォルダにアップロードしてください：

```bash
./.claude/skills/jp-it-news-summary/scripts/upload_gdrive.py output/jp-it-news-YYYY-MM-DD.pdf
```

**注意**: Google Drive の認証情報 (OAuth クライアントシークレットのパス、フォルダ ID) は `secrets/settings.json` または環境変数で設定してください。初回実行時はブラウザで Google アカウント認証が必要です。同名ファイルが既に存在する場合は上書きされます。

## 出力

- **PDF**: `output/jp-it-news-YYYY-MM-DD.pdf`
- **一時ファイル**: `tmp/jp_raw_articles.json`, `tmp/jp_summarized_articles.json`

## トラブルシューティング

- PDFのフォントが表示されない場合: macOS以外の環境では `generate_pdf.py` 内のフォントパスを変更してください
- Slack投稿が失敗する場合: `secrets/settings.json` の設定を確認してください

## 補足事項

### ニュースソース・カテゴリの追加・変更

運用する中で、新たに取得したいニュースサイトや記事ソースが出てきた場合は、以下のテンプレートファイルを更新してください：

| 変更内容                   | 対象ファイル                                                   |
| -------------------------- | -------------------------------------------------------------- |
| ニュースソースの追加・削除 | `.claude/skills/jp-it-news-summary/templates/news_sources.csv` |
| カテゴリの追加・変更       | `.claude/skills/jp-it-news-summary/templates/categories.csv`   |

**注意**: 新しいサイトを追加する際、サイトの構造によっては `fetch_news.py` に専用のフェッチャー関数を追加する必要がある場合があります。

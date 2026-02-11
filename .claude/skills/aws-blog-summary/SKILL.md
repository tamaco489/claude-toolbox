---
name: aws-blog-summary
description: AWSブログの最新記事を収集・要約してPDF生成・Slack投稿する
---

# AWSブログ要約・PDF・Slack投稿スキル

このスキルは、AWS公式ブログ（日本語版）から最新の記事5件を取得し、日本語で要約した後、PDFを生成してSlackに投稿します。

## 実行上の注意事項

このスキルを実行する際は、以下のルールを必ず遵守してください。

### 要約フェーズにおける原則

1. **正確性 > 即時性**
   - 速度よりも正確さを優先すること
   - 不明な点があれば原文を再確認し、推測で補完しない

2. **原文への忠実性**
   - 記事に書かれていない情報を追加しない
   - 著者の主張を歪曲・誇張しない
   - 技術用語・サービス名は正確に使用する

3. **ハルシネーションの禁止**
   - 存在しない事実、数値、引用を生成しない
   - 確認できない情報は要約に含めない

4. **出典の明記**
   - 各記事の出典元とURLを必ず保持する

### カテゴリ分類における原則

1. **定義されたカテゴリのみ使用**
   - `categories.csv` に定義されたカテゴリから選択する
   - 該当なしの場合は「その他」を使用

2. **主題に基づく分類**
   - 記事の主要なトピックで分類する
   - 複数カテゴリに該当する場合は最も関連性の高いものを選択

### 品質チェック

- 要約が日本語として自然か確認する
- AWSサービス名の誤訳がないか確認する
- 重複記事がないか確認する

---

## 実行手順

### 1. 一時ファイルのクリーンアップ

前回実行時の一時ファイルが残っている場合に備え、最初に削除してください：

```bash
rm -f tmp/aws_raw_articles.json tmp/aws_summarized_articles.json
```

### 2. Pythonパッケージの確認

まず、必要なパッケージがインストールされているか確認してください：

```bash
pip install requests beautifulsoup4 feedparser reportlab fake-useragent google-api-python-client google-auth google-auth-oauthlib
```

### 3. ニュース取得

以下のスクリプトを実行してAWSブログの最新記事を取得してください：

```bash
./.claude/skills/aws-blog-summary/scripts/fetch_news.py
```

スクリプトはJSON形式で記事一覧を標準出力します。出力を `tmp/aws_raw_articles.json` に保存してください。

### 4. 記事の要約・カテゴリー分類

取得した記事を読み、以下の作業を行ってください：

1. 各記事を日本語で要約（150-250文字程度）
2. `categories.csv` に基づいてカテゴリーを割り当て
3. 要約結果を以下のJSON形式で `tmp/aws_summarized_articles.json` に保存：

```json
{
  "date": "YYYY-MM-DD",
  "articles": [
    {
      "title": "記事タイトル",
      "source": "AWS Blog",
      "url": "記事URL",
      "category": "カテゴリ名",
      "summary": "日本語要約"
    }
  ]
}
```

### 5. PDF生成

要約データをPDFに変換してください：

```bash
cat tmp/aws_summarized_articles.json | ./.claude/skills/aws-blog-summary/scripts/generate_pdf.py
```

PDFは `output/aws-blog-YYYY-MM-DD.pdf` に出力されます。

### 6. Slack投稿

PDFファイルとサマリーをSlackに投稿してください：

```bash
./.claude/skills/aws-blog-summary/scripts/post_slack.py output/aws-blog-YYYY-MM-DD.pdf "本日のAWSブログ要約です" tmp/aws_summarized_articles.json
```

**注意**: Slack 認証情報は `secrets/settings.json` または環境変数で設定してください。

### 7. Google Driveアップロード

PDFファイルを Google Drive の指定フォルダにアップロードしてください：

```bash
./.claude/skills/aws-blog-summary/scripts/upload_gdrive.py output/aws-blog-YYYY-MM-DD.pdf
```

**注意**: Google Drive の認証情報 (OAuth クライアントシークレットのパス、フォルダ ID) は `secrets/settings.json` または環境変数で設定してください。初回実行時はブラウザで Google アカウント認証が必要です。同名ファイルが既に存在する場合は上書きされます。

## 出力

- **PDF**: `output/aws-blog-YYYY-MM-DD.pdf`
- **一時ファイル**: `tmp/aws_raw_articles.json`, `tmp/aws_summarized_articles.json`

## トラブルシューティング

- PDFのフォントが表示されない場合: macOS以外の環境では `generate_pdf.py` 内のフォントパスを変更してください
- Slack投稿が失敗する場合: `secrets/settings.json` の設定を確認してください
- 記事が取得できない場合: AWSブログのRSSフィードが変更された可能性があります

## 補足事項

### カテゴリの追加・変更

運用する中で、カテゴリを変更したい場合は以下のファイルを更新してください：

| 変更内容             | 対象ファイル                                               |
| -------------------- | ---------------------------------------------------------- |
| カテゴリの追加・変更 | `.claude/skills/aws-blog-summary/templates/categories.csv` |

#!/usr/bin/env python3
"""PDF生成スクリプト（AWSブログ用）"""

import json
import sys
import os
from datetime import datetime
from collections import defaultdict

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# パス設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
TEMPLATE_PATH = os.path.join(SKILL_DIR, 'templates', 'pdf_template.json')

# フォント
JP_FONT = 'HeiseiKakuGo-W5'

# デフォルトテンプレート
DEFAULT_TPL = {
    "title": "AWSブログ要約レポート",
    "date_format": "作成日: {date}",
    "category_format": "{category}",
    "source_format": "出典: {source} | {url}",
    "no_articles_message": "取得した記事はありません。",
    "styles": {
        "title": {"font_size": 18, "color": "#232f3e", "leading": 24, "space_after": 12},
        "date": {"font_size": 10, "color": "#6b7280", "leading": 12, "space_after": 20},
        "category_header": {"font_size": 14, "color": "#ff9900", "leading": 18, "space_before": 16, "space_after": 8},
        "article_title": {"font_size": 11, "color": "#232f3e", "leading": 14, "space_before": 8, "space_after": 2},
        "article_body": {"font_size": 10, "color": "#374151", "leading": 14, "space_after": 4},
        "article_meta": {"font_size": 8, "color": "#6b7280", "leading": 10, "space_after": 8}
    },
    "page": {"size": "A4", "margin_top": 20, "margin_bottom": 20, "margin_left": 20, "margin_right": 20},
    "url_settings": {"max_display_length": 60, "truncate_suffix": "...", "make_clickable": True}
}

# スタイル定義（name, font, 追加属性）
STYLE_DEFS = [
    ('JapaneseTitle', 'title', True, {}),
    ('DateStyle', 'date', False, {}),
    ('CategoryHeader', 'category_header', True, {}),
    ('ArticleTitle', 'article_title', True, {}),
    ('ArticleBody', 'article_body', False, {}),
    ('ArticleMeta', 'article_meta', False, {'linkUnderline': True}),
]


def _deep_merge(base, override):
    """辞書を深くマージ"""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def _escape(text):
    """HTMLエスケープ"""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _load_json(path, default=None):
    """JSONファイルを読み込む"""
    if not os.path.exists(path):
        return default or {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: {path}: {e}", file=sys.stderr)
        return default or {}


def load_template():
    """テンプレート読み込み"""
    tpl = _load_json(TEMPLATE_PATH)
    if not tpl:
        return DEFAULT_TPL.copy()
    return _deep_merge(DEFAULT_TPL.copy(), tpl)


def register_fonts():
    """日本語CIDフォント登録"""
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(JP_FONT))
        return True
    except Exception as e:
        print(f"Warning: Font registration failed: {e}", file=sys.stderr)
        return False


def create_styles(tpl):
    """テンプレートに基づいてスタイル作成"""
    styles = getSampleStyleSheet()
    cfg = tpl.get('styles', {})

    for name, key, bold, extra in STYLE_DEFS:
        s = cfg.get(key, {})
        props = {
            'name': name,
            'fontName': JP_FONT,
            'fontSize': s.get('font_size', 10),
            'leading': s.get('leading', 12),
            'textColor': HexColor(s.get('color', '#1a1a1a')),
            **extra
        }
        if 'space_after' in s:
            props['spaceAfter'] = s['space_after']
        if 'space_before' in s:
            props['spaceBefore'] = s['space_before']
        styles.add(ParagraphStyle(**props))

    return styles


def _build_content(data, tpl, styles):
    """PDFコンテンツ構築"""
    content = []
    url_cfg = tpl.get('url_settings', {})
    max_len = url_cfg.get('max_display_length', 60)
    suffix = url_cfg.get('truncate_suffix', '...')
    clickable = url_cfg.get('make_clickable', True)

    # タイトル・日付
    content.append(Paragraph(tpl.get('title', 'AWSブログ要約レポート'), styles['JapaneseTitle']))
    date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    content.append(Paragraph(tpl.get('date_format', '作成日: {date}').format(date=date), styles['DateStyle']))

    # 記事なし
    articles = data.get('articles', [])
    if not articles:
        content.append(Paragraph(tpl.get('no_articles_message', '取得した記事はありません。'), styles['ArticleBody']))
        return content

    # カテゴリ別グループ化
    by_cat = defaultdict(list)
    for art in articles:
        by_cat[art.get('category', '未分類')].append(art)

    cat_fmt = tpl.get('category_format', '{category}')
    src_fmt = tpl.get('source_format', '出典: {source} | {url}')

    for cat, arts in by_cat.items():
        content.append(Paragraph(cat_fmt.format(category=cat), styles['CategoryHeader']))

        for art in arts:
            # タイトル
            title = _escape(art.get('title', '(タイトルなし)'))
            content.append(Paragraph(title, styles['ArticleTitle']))

            # 要約
            summary = art.get('summary', '')
            if summary:
                content.append(Paragraph(_escape(summary), styles['ArticleBody']))

            # メタ情報
            src, url = art.get('source', ''), art.get('url', '')
            if url:
                disp = url[:max_len] + suffix if len(url) > max_len else url
                url_txt = f'<link href="{url}"><u>{disp}</u></link>' if clickable else disp
                meta = src_fmt.format(source=src, url=url_txt)
            else:
                meta = f'出典: {src}'
            content.append(Paragraph(meta, styles['ArticleMeta']))
            content.append(Spacer(1, 4 * mm))

    # URL一覧セクション
    urls = [art.get('url') for art in articles if art.get('url')]
    if urls:
        content.append(Spacer(1, 8 * mm))
        content.append(Paragraph('記事URL一覧', styles['CategoryHeader']))
        for url in urls:
            content.append(Paragraph(url, styles['ArticleMeta']))

    return content


def generate_pdf(data, path, tpl):
    """PDF生成"""
    register_fonts()
    styles = create_styles(tpl)

    page = tpl.get('page', {})
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        rightMargin=page.get('margin_right', 20) * mm,
        leftMargin=page.get('margin_left', 20) * mm,
        topMargin=page.get('margin_top', 20) * mm,
        bottomMargin=page.get('margin_bottom', 20) * mm
    )

    doc.build(_build_content(data, tpl, styles))
    return path


def main():
    tpl = load_template()

    # JSON入力
    try:
        data = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # 出力パス
    date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    root = os.path.dirname(os.path.dirname(os.path.dirname(SKILL_DIR)))
    out_dir = os.path.join(root, 'output')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'aws-blog-{date}.pdf')

    try:
        result = generate_pdf(data, out_path, tpl)
        print(f"PDF generated: {result}")
    except Exception as e:
        print(f"Error generating PDF: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

#!/Users/tamaco/Desktop/work/general/.venv/bin/python3
"""ニュース取得スクリプト"""

import csv
import json
import sys
import os
import re
from urllib.parse import urljoin
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import feedparser

TIMEOUT = 30
HEADERS = {'User-Agent': UserAgent().chrome}
MAX_ARTICLES = 5


def _get_soup(url):
    """URLからBeautifulSoupオブジェクトを取得"""
    res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    res.raise_for_status()
    return BeautifulSoup(res.text, 'html.parser')


def _make_article(title, url, source):
    """記事dictを生成"""
    return {'title': title, 'url': url, 'source': source, 'content': ''}


def _extract_content(soup):
    """HTMLから本文を抽出"""
    # 不要要素を削除
    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']):
        tag.decompose()

    # 優先順位順に本文を探す
    for finder in [
        lambda: soup.find('article'),
        lambda: soup.find('main'),
        lambda: next((soup.find('div', class_=lambda x: x and c in str(x).lower())
                        for c in ['content', 'post-content', 'article-content', 'entry-content']
                        if soup.find('div', class_=lambda x: x and c in str(x).lower())), None),
    ]:
        elem = finder()
        if elem:
            return elem.get_text(separator='\n', strip=True)

    # フォールバック: 段落から抽出
    return '\n'.join(p.get_text(strip=True) for p in soup.find_all('p') if len(p.get_text(strip=True)) > 50)


def fetch_content(url, max_len=3000):
    """記事ページから本文を取得"""
    try:
        content = _extract_content(_get_soup(url))
        if not content:
            return ""
        # クリーンアップ
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r' {2,}', ' ', content).strip()
        return content[:max_len] + "..." if len(content) > max_len else content
    except Exception as e:
        print(f"  Warning: {url}: {e}", file=sys.stderr)
        return ""


def load_sources(path):
    """CSVからニュースソースを読み込む"""
    with open(path, 'r', encoding='utf-8') as f:
        return [
            {'name': r['サイト名'], 'url': r['URL']}
            for r in csv.DictReader(f)
            if r.get('有効', '').lower() == 'true'
        ]


def _fetch_by_pattern(url, name, link_filter, title_min_len=10):
    """パターンに基づいて記事を取得"""
    articles = []
    seen = set()
    try:
        soup = _get_soup(url)
        for link in soup.find_all('a', href=True):
            href, title = link.get('href', ''), link.get_text(strip=True)
            if not (title and len(title) > title_min_len and link_filter(href)):
                continue
            full_url = urljoin(url, href)
            if full_url in seen:
                continue
            seen.add(full_url)
            articles.append(_make_article(title, full_url, name))
            if len(articles) >= MAX_ARTICLES:
                break
    except Exception as e:
        print(f"Error fetching {name}: {e}", file=sys.stderr)
    return articles


def fetch_buttondown(url, name):
    return _fetch_by_pattern(url, name, lambda h: '/archive/' in h)


def fetch_deeplearn(url, name):
    articles = _fetch_by_pattern(url, name, lambda h: h.startswith('http'), title_min_len=20)
    if articles:
        return articles
    # フォールバック: article/div要素から探索
    try:
        soup = _get_soup(url)
        for item in soup.find_all(['article', 'div'], class_=lambda x: x and ('post' in str(x).lower() or 'article' in str(x).lower()))[:10]:
            link = item.find('a', href=True)
            if link and len(link.get_text(strip=True)) > 5:
                articles.append(_make_article(link.get_text(strip=True), urljoin(url, link['href']), name))
                if len(articles) >= MAX_ARTICLES:
                    break
    except Exception:
        pass
    return articles


def fetch_huggingface(url, name):
    return _fetch_by_pattern(
        url, name,
        lambda h: '/papers/' in h and h != '/papers' and '/papers/trending' not in h
    )


def fetch_deeplearning_ai(url, name):
    return _fetch_by_pattern(url, name, lambda h: '/the-batch/' in h, title_min_len=15)


def fetch_generic(url, name):
    """汎用取得（RSS優先）"""
    # RSS試行
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            return [
                {**_make_article(e.get('title', ''), e.get('link', ''), name),
                    'content': (e.get('summary', '') or '')[:500]}
                for e in feed.entries[:MAX_ARTICLES]
            ]
    except Exception:
        pass
    return _fetch_by_pattern(url, name, lambda h: bool(h), title_min_len=20)


# ソースURLとフェッチ関数のマッピング
FETCHERS = [
    ('buttondown.com', fetch_buttondown),
    ('deeplearn.org', fetch_deeplearn),
    ('huggingface.co/papers', fetch_huggingface),
    ('deeplearning.ai/the-batch', fetch_deeplearning_ai),
]


def fetch_articles(source, with_content=True):
    """ソースから記事を取得"""
    url, name = source['url'], source['name']

    # 適切なフェッチャーを選択
    fetcher = next((f for pattern, f in FETCHERS if pattern in url), fetch_generic)
    articles = fetcher(url, name)

    # 本文取得
    if with_content:
        for i, art in enumerate(articles):
            if art['url'] and not art.get('content'):
                print(f"    Fetching {i+1}/{len(articles)}...", file=sys.stderr)
                art['content'] = fetch_content(art['url'])

    return articles


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(os.path.dirname(script_dir), 'templates', 'news_sources.csv')

    sources = load_sources(csv_path)
    all_articles = []

    for src in sources:
        print(f"Fetching from {src['name']}...", file=sys.stderr)
        arts = fetch_articles(src)
        all_articles.extend(arts)
        print(f"  Found {len(arts)} articles", file=sys.stderr)

    print(json.dumps({
        'date': datetime.now().strftime('%Y-%m-%d'),
        'sources': [s['name'] for s in sources],
        'articles': all_articles
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

#!/Users/tamaco/Desktop/work/general/.venv/bin/python3
"""国内ITニュース取得スクリプト"""

import csv
import json
import sys
import os
import re
import time
from urllib.parse import urljoin
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import feedparser

TIMEOUT = 30
HEADERS = {'User-Agent': UserAgent().chrome}
MAX_ARTICLES = 5
MAX_RETRIES = 3
RETRY_DELAY = 2


def _get_soup(url, retries=MAX_RETRIES):
    """URLからBeautifulSoupオブジェクトを取得（リトライ付き）"""
    for attempt in range(retries):
        try:
            res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            res.raise_for_status()
            # res.content（バイト列）を渡すことでBeautifulSoupが文字コードを自動検出
            return BeautifulSoup(res.content, 'html.parser')
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                print(f"  Retry {attempt + 1}/{retries - 1}: {url}", file=sys.stderr)
                time.sleep(RETRY_DELAY)
            else:
                raise e
    return None


def _make_article(title, url, source):
    """記事dictを生成"""
    return {'title': title, 'url': url, 'source': source, 'content': ''}


def _extract_content(soup):
    """HTMLから本文を抽出"""
    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']):
        tag.decompose()

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

    return '\n'.join(p.get_text(strip=True) for p in soup.find_all('p') if len(p.get_text(strip=True)) > 50)


def fetch_content(url, max_len=3000):
    """記事ページから本文を取得"""
    try:
        content = _extract_content(_get_soup(url))
        if not content:
            return ""
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
            {'name': r['サイト名'], 'url': r['URL'], 'domain': r['ドメイン名']}
            for r in csv.DictReader(f)
            if r.get('有効', '').lower() == 'true'
        ]


def _fetch_by_pattern(url, name, link_filter, title_min_len=10):
    """パターンに基づいて記事を取得"""
    articles, seen = [], set()
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


def fetch_gigazine(url, name):
    """Gigazineから記事を取得"""
    articles, seen = [], set()
    try:
        soup = _get_soup(url)
        for item in soup.select('div.card h2 a, article h2 a, .content h2 a'):
            href = item.get('href', '')
            title = item.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            full_url = urljoin(url, href)
            if full_url in seen or '/news/' not in full_url:
                continue
            seen.add(full_url)
            articles.append(_make_article(title, full_url, name))
            if len(articles) >= MAX_ARTICLES:
                break
    except Exception as e:
        print(f"Error fetching {name}: {e}", file=sys.stderr)
    if not articles:
        return _fetch_by_pattern(url, name, lambda h: '/news/' in h and h.endswith('.html'))
    return articles


def fetch_publickey(url, name):
    """Publickeyから記事を取得"""
    articles, seen = [], set()
    try:
        soup = _get_soup(url)
        for item in soup.select('article h2 a, .post-title a, h2.title a'):
            href = item.get('href', '')
            title = item.get_text(strip=True)
            if not title or len(title) < 10:
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
    if not articles:
        return _fetch_by_pattern(url, name, lambda h: '/blog/' in h or '/archives/' in h)
    return articles


def fetch_ascii(url, name):
    """ASCII.jpから記事を取得"""
    articles, seen = [], set()
    try:
        soup = _get_soup(url)
        for item in soup.select('article a, .article-list a, h3 a, h2 a'):
            href = item.get('href', '')
            title = item.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            full_url = urljoin(url, href)
            if full_url in seen or not re.search(r'/\d+/', full_url):
                continue
            seen.add(full_url)
            articles.append(_make_article(title, full_url, name))
            if len(articles) >= MAX_ARTICLES:
                break
    except Exception as e:
        print(f"Error fetching {name}: {e}", file=sys.stderr)
    if not articles:
        return _fetch_by_pattern(url, name, lambda h: re.search(r'/\d+/', h) is not None)
    return articles


def fetch_itmedia(url, name):
    """ITmediaから記事を取得"""
    articles, seen = [], set()
    try:
        soup = _get_soup(url)
        for item in soup.select('article a, .colBoxIndex a, h3 a'):
            href = item.get('href', '')
            title = item.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            full_url = urljoin('https://www.itmedia.co.jp', href)
            if full_url in seen or '/articles/' not in full_url:
                continue
            seen.add(full_url)
            articles.append(_make_article(title, full_url, name))
            if len(articles) >= MAX_ARTICLES:
                break
    except Exception as e:
        print(f"Error fetching {name}: {e}", file=sys.stderr)
    if not articles:
        return _fetch_by_pattern(url, name, lambda h: '/articles/' in h)
    return articles


def fetch_generic(url, name):
    """汎用取得（RSS優先）"""
    rss_urls = [
        url.rstrip('/') + '/feed',
        url.rstrip('/') + '/rss',
        url.rstrip('/') + '/index.xml',
    ]
    for rss_url in rss_urls:
        try:
            feed = feedparser.parse(rss_url)
            if feed.entries:
                return [
                    {**_make_article(e.get('title', ''), e.get('link', ''), name),
                     'content': (e.get('summary', '') or '')[:500]}
                    for e in feed.entries[:MAX_ARTICLES]
                ]
        except Exception:
            pass
    return _fetch_by_pattern(url, name, lambda h: bool(h), title_min_len=15)


# ソースURLとフェッチ関数のマッピング
FETCHERS = [
    ('gigazine.net', fetch_gigazine),
    ('publickey1.jp', fetch_publickey),
    ('ascii.jp', fetch_ascii),
    ('itmedia.co.jp', fetch_itmedia),
]


def fetch_articles(source, with_content=True):
    """ソースから記事を取得"""
    url, name, domain = source['url'], source['name'], source.get('domain', '')

    fetcher = next((f for pattern, f in FETCHERS if pattern in domain or pattern in url), fetch_generic)
    articles = fetcher(url, name)

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

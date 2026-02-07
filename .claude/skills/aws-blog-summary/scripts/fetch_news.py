#!/Users/tamaco/Desktop/work/general/.venv/bin/python3
"""AWSブログ記事取得スクリプト"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import feedparser

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

TIMEOUT = 30
HEADERS = {'User-Agent': UserAgent().chrome}
MAX_ARTICLES = 5
MAX_RETRIES = 3
RETRY_DELAY = 2

# AWSブログ日本語版RSSフィード
AWS_BLOG_RSS = 'https://aws.amazon.com/jp/blogs/aws/feed/'
SOURCE_NAME = 'AWS Blog'


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
                logger.warning(f"Retry {attempt + 1}/{retries - 1}: {url}")
                time.sleep(RETRY_DELAY)
            else:
                raise e
    return None


def _make_article(title, url, source, content=''):
    """記事dictを生成"""
    return {'title': title, 'url': url, 'source': source, 'content': content}


def _extract_content(soup):
    """HTMLから本文を抽出"""
    # 不要要素を削除
    for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']):
        tag.decompose()

    # 優先順位順に本文を探す
    for finder in [
        lambda: soup.find('article'),
        lambda: soup.find('main'),
        lambda: soup.find('div', class_=lambda x: x and 'blog-post' in str(x).lower()),
        lambda: soup.find('div', class_=lambda x: x and 'content' in str(x).lower()),
    ]:
        elem = finder()
        if elem:
            return elem.get_text(separator='\n', strip=True)

    # フォールバック: 段落から抽出
    return '\n'.join(p.get_text(strip=True) for p in soup.find_all('p') if len(p.get_text(strip=True)) > 50)


def fetch_content(url, max_len=5000):
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
        logger.warning(f"{url}: {e}")
        return ""


def fetch_aws_blog():
    """AWSブログからRSSで記事を取得"""
    articles = []

    try:
        logger.info(f"Fetching from {AWS_BLOG_RSS}...")
        feed = feedparser.parse(AWS_BLOG_RSS)

        if not feed.entries:
            logger.warning("No entries found in RSS feed")
            return articles

        for entry in feed.entries[:MAX_ARTICLES]:
            title = entry.get('title', '')
            link = entry.get('link', '')

            # RSSからの要約を取得（あれば）
            summary = entry.get('summary', '') or entry.get('description', '')
            # HTMLタグを除去
            if summary:
                summary = BeautifulSoup(summary, 'html.parser').get_text(strip=True)
                summary = summary[:500] if len(summary) > 500 else summary

            article = _make_article(title, link, SOURCE_NAME, summary)
            articles.append(article)

        logger.info(f"Found {len(articles)} articles from RSS")

    except Exception as e:
        logger.error(f"Fetching RSS: {e}")

    return articles


def fetch_full_content(articles):
    """各記事の全文を取得"""
    for i, art in enumerate(articles):
        if art['url']:
            logger.info(f"Fetching full content {i+1}/{len(articles)}...")
            content = fetch_content(art['url'])
            if content:
                art['content'] = content
    return articles


def main():
    # 記事取得
    articles = fetch_aws_blog()

    # 全文取得
    if articles:
        articles = fetch_full_content(articles)

    # JSON出力
    print(json.dumps({
        'date': datetime.now().strftime('%Y-%m-%d'),
        'source': SOURCE_NAME,
        'source_url': AWS_BLOG_RSS,
        'articles': articles
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

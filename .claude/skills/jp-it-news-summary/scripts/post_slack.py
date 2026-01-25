#!/usr/bin/env python3
"""Slack投稿スクリプト"""

import sys
import os
import json
from datetime import datetime
from collections import defaultdict

import requests

# パス設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
TEMPLATE_PATH = os.path.join(SKILL_DIR, 'templates', 'slack_template.json')
SECRETS_PATH = os.path.join(SKILL_DIR, 'config', 'secrets.json')

# デフォルトテンプレート
DEFAULT_TEMPLATE = {
    "header": ":newspaper: 国内ITニュース要約 - {date}",
    "message_format": "{message}",
    "category_format": "*{category}*\n",
    "article_format": "• {title}\n",
    "max_articles_per_category": 3,
    "max_title_length": 50,
    "footer": "",
    "settings": {"show_categories": True, "show_article_list": True, "truncate_suffix": "..."}
}


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


def _get_env_or(key, default=''):
    """環境変数を取得、なければデフォルト"""
    return os.environ.get(key) or default


def load_secrets():
    """秘匿情報を読み込む（環境変数優先）"""
    secrets = _load_json(SECRETS_PATH, {
        'slack_bot_token': '',
        'slack_webhook_url': '',
        'slack_channel_id': ''
    })
    return {
        'token': _get_env_or('SLACK_BOT_TOKEN', secrets.get('slack_bot_token', '')),
        'webhook': _get_env_or('SLACK_WEBHOOK_URL', secrets.get('slack_webhook_url', '')),
        'channel': _get_env_or('SLACK_CHANNEL_ID', secrets.get('slack_channel_id', ''))
    }


def load_template():
    """テンプレートを読み込む"""
    tpl = _load_json(TEMPLATE_PATH, DEFAULT_TEMPLATE.copy())
    for k, v in DEFAULT_TEMPLATE.items():
        tpl.setdefault(k, v)
    return tpl


def _truncate(text, max_len, suffix='...'):
    """テキストを切り詰める"""
    return text[:max_len] + suffix if len(text) > max_len else text


def _build_category_text(tpl, category, articles):
    """カテゴリテキストを構築"""
    cfg = tpl.get('settings', {})
    max_arts = tpl.get('max_articles_per_category', 3)
    max_len = tpl.get('max_title_length', 50)
    suffix = cfg.get('truncate_suffix', '...')

    text = tpl.get('category_format', '*{category}*\n').format(category=category)
    if cfg.get('show_article_list', True):
        for art in articles[:max_arts]:
            title = _truncate(art.get('title', ''), max_len, suffix)
            text += tpl.get('article_format', '• {title}\n').format(title=title)
    return text


def format_summary(tpl, msg, summary, date):
    """サマリーテキストを作成"""
    header = tpl.get('header', DEFAULT_TEMPLATE['header']).format(date=date)
    text = f"*{header}*\n\n{tpl.get('message_format', '{message}').format(message=msg)}"

    if summary and tpl.get('settings', {}).get('show_categories', True):
        text += "\n"
        for cat, arts in summary.items():
            text += f"\n{_build_category_text(tpl, cat, arts)}"

    if tpl.get('footer'):
        text += f"\n{tpl['footer']}"
    return text


def upload_file(path, channel, comment, token):
    """Slack APIでファイルをアップロード"""
    if not token:
        print("Error: SLACK_BOT_TOKEN is not set.", file=sys.stderr)
        return False
    if not os.path.exists(path):
        print(f"Error: File not found: {path}", file=sys.stderr)
        return False

    name = os.path.basename(path)
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: アップロードURL取得
    res = requests.post(
        "https://slack.com/api/files.getUploadURLExternal",
        headers=headers,
        data={"filename": name, "length": os.path.getsize(path)},
        timeout=30
    ).json()

    if not res.get("ok"):
        print(f"Error: {res.get('error', 'Unknown')}", file=sys.stderr)
        return False

    # Step 2: ファイルアップロード
    with open(path, "rb") as f:
        upload_res = requests.post(res["upload_url"], files={"file": (name, f, "application/pdf")}, timeout=60)
    if upload_res.status_code != 200:
        print(f"Error uploading: {upload_res.status_code}", file=sys.stderr)
        return False

    # Step 3: アップロード完了
    complete_res = requests.post(
        "https://slack.com/api/files.completeUploadExternal",
        headers={**headers, "Content-Type": "application/json"},
        json={"files": [{"id": res["file_id"], "title": name}], "channel_id": channel, "initial_comment": comment},
        timeout=30
    ).json()

    if not complete_res.get("ok"):
        print(f"Error: {complete_res.get('error', 'Unknown')}", file=sys.stderr)
        return False

    print(f"Uploaded {name} to Slack!")
    return True


def post_webhook(tpl, msg, summary, date, webhook):
    """Webhookでメッセージ投稿"""
    if not webhook:
        print("Error: SLACK_WEBHOOK_URL is not set.", file=sys.stderr)
        return False

    header = tpl.get('header', DEFAULT_TEMPLATE['header']).format(date=date)
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": header, "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": msg}}
    ]

    if summary and tpl.get('settings', {}).get('show_categories', True):
        blocks.append({"type": "divider"})
        for cat, arts in summary.items():
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": _build_category_text(tpl, cat, arts)}})

    try:
        requests.post(webhook, json={"blocks": blocks, "text": header}, headers={'Content-Type': 'application/json'}, timeout=30).raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def load_summary(path):
    """要約JSONを読み込んでカテゴリ別に整理"""
    if not path or not os.path.exists(path):
        return None
    try:
        data = _load_json(path)
        summary = defaultdict(list)
        for art in data.get('articles', []):
            summary[art.get('category', '未分類')].append(art)
        return dict(summary)
    except Exception as e:
        print(f"Warning: {e}", file=sys.stderr)
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: post_slack.py <pdf> [message] [json] [channel]", file=sys.stderr)
        sys.exit(1)

    pdf = sys.argv[1]
    msg = sys.argv[2] if len(sys.argv) > 2 else '本日の国内ITニュース要約です'
    json_path = sys.argv[3] if len(sys.argv) > 3 else None
    secrets = load_secrets()
    channel = sys.argv[4] if len(sys.argv) > 4 else secrets['channel']

    tpl = load_template()
    summary = load_summary(json_path)
    date = datetime.now().strftime('%Y年%m月%d日')
    text = format_summary(tpl, msg, summary, date)

    # PDF アップロード試行
    if os.path.exists(pdf) and upload_file(pdf, channel, text, secrets['token']):
        print("Success!")
        sys.exit(0)

    # フォールバック: Webhook
    print("Falling back to webhook...", file=sys.stderr)
    ok = post_webhook(tpl, msg, summary, date, secrets['webhook'])
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()

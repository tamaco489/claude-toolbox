#!/usr/bin/env python3
"""メール送信スクリプト - ファイルを添付してメールを送信（最大5ファイル）"""

import sys
import os
import json
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.header import Header
from email.utils import formataddr
from email import encoders
from datetime import datetime

# MIMEタイプのフォールバック（mimetypesで取得できない場合）
MIME_TYPES_FALLBACK = {
    '.xlsx': ('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    '.xls': ('application', 'vnd.ms-excel'),
    '.pptx': ('application', 'vnd.openxmlformats-officedocument.presentationml.presentation'),
    '.ppt': ('application', 'vnd.ms-powerpoint'),
    '.docx': ('application', 'vnd.openxmlformats-officedocument.wordprocessingml.document'),
    '.doc': ('application', 'msword'),
}

# パス設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
TEMPLATE_PATH = os.path.join(SKILL_DIR, 'templates', 'email_template.json')
SECRETS_PATH = os.path.join(SKILL_DIR, 'config', 'secrets.json')

# 制限
MAX_ATTACHMENTS = 5
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB（Gmail制限）

# デフォルトテンプレート
DEFAULT_TEMPLATE = {
    "subject": "レポート送付 - {date}",
    "body": "レポートを添付いたします。\n\n添付ファイル:\n{filenames}",
    "signature": ""
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
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'sender_email': '',
        'sender_password': '',
        'sender_name': '',
        'default_recipient': ''
    })
    return {
        'server': _get_env_or('SMTP_SERVER', secrets.get('smtp_server', 'smtp.gmail.com')),
        'port': int(_get_env_or('SMTP_PORT', secrets.get('smtp_port', 587))),
        'email': _get_env_or('SENDER_EMAIL', secrets.get('sender_email', '')),
        'password': _get_env_or('SENDER_PASSWORD', secrets.get('sender_password', '')),
        'name': _get_env_or('SENDER_NAME', secrets.get('sender_name', '')),
        'default_recipient': _get_env_or('DEFAULT_RECIPIENT', secrets.get('default_recipient', ''))
    }


def load_template():
    """テンプレートを読み込む"""
    tpl = _load_json(TEMPLATE_PATH, DEFAULT_TEMPLATE.copy())
    for k, v in DEFAULT_TEMPLATE.items():
        tpl.setdefault(k, v)
    return tpl


def format_message(tpl, recipient, filenames, date, date_compact):
    """テンプレートからメッセージを生成"""
    filenames_str = '\n'.join(f'- {f}' for f in filenames)
    subject = tpl.get('subject', DEFAULT_TEMPLATE['subject']).format(
        date=date, date_compact=date_compact, filenames=filenames_str, recipient=recipient
    )
    body = tpl.get('body', DEFAULT_TEMPLATE['body']).format(
        date=date, date_compact=date_compact, filenames=filenames_str, recipient=recipient
    )
    signature = tpl.get('signature', '')
    return subject, body + signature


def get_mime_type(file_path):
    """ファイル拡張子からMIMEタイプを取得"""
    # mimetypesモジュールで取得（標準的な方法を優先）
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        main_type, sub_type = mime_type.split('/', 1)
        return (main_type, sub_type)

    # フォールバック（Office形式など環境によって取得できない場合）
    ext = os.path.splitext(file_path)[1].lower()
    if ext in MIME_TYPES_FALLBACK:
        return MIME_TYPES_FALLBACK[ext]

    # デフォルト
    return ('application', 'octet-stream')


def attach_file(msg, file_path):
    """ファイルを添付（各種形式対応）"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # ファイルサイズ検証
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {file_path} ({file_size // (1024*1024)}MB > 25MB limit)")

    filename = os.path.basename(file_path)
    main_type, sub_type = get_mime_type(file_path)

    with open(file_path, 'rb') as f:
        part = MIMEBase(main_type, sub_type)
        part.set_payload(f.read())

    encoders.encode_base64(part)
    # RFC 2231準拠のファイル名エンコーディング（日本語・特殊文字対応）
    part.add_header('Content-Disposition', 'attachment',
                    filename=('utf-8', '', filename))
    msg.attach(part)
    return filename


def send_email(secrets, to_emails, subject, body, file_paths):
    """メールを送信（複数ファイル対応）"""
    if not secrets['email']:
        print("Error: SENDER_EMAIL is not set.", file=sys.stderr)
        return False

    if not secrets['password']:
        print("Error: SENDER_PASSWORD is not set.", file=sys.stderr)
        return False

    # 宛先をリストに変換
    if isinstance(to_emails, str):
        to_emails = [e.strip() for e in to_emails.split(',')]

    # メール作成
    msg = MIMEMultipart()

    # 送信者設定（日本語名対応）
    if secrets['name']:
        msg['From'] = formataddr((str(Header(secrets['name'], 'utf-8')), secrets['email']))
    else:
        msg['From'] = secrets['email']

    msg['To'] = ', '.join(to_emails)
    msg['Subject'] = subject

    # 本文
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # ファイル添付（複数対応）
    attached_files = []
    for file_path in file_paths:
        try:
            filename = attach_file(msg, file_path)
            attached_files.append(filename)
            print(f"Attached: {filename}")
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return False

    # SMTP送信
    try:
        print(f"Connecting to {secrets['server']}:{secrets['port']}...")
        with smtplib.SMTP(secrets['server'], secrets['port'], timeout=30) as server:
            server.starttls()
            server.login(secrets['email'], secrets['password'])
            server.sendmail(secrets['email'], to_emails, msg.as_string())

        print(f"Email sent successfully to: {', '.join(to_emails)}")
        print(f"Attached files: {len(attached_files)}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("Error: Authentication failed. Check your email and app password.", file=sys.stderr)
        return False
    except smtplib.SMTPException as e:
        print(f"Error: SMTP error - {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: send_email.py <file_paths> [to_email] [subject] [body]", file=sys.stderr)
        print("  file_paths: File path(s), comma-separated for multiple (max 5)", file=sys.stderr)
        print("  to_email:   Recipient email address(es) (optional if default set)", file=sys.stderr)
        print("  subject:    Email subject (optional, uses template if omitted)", file=sys.stderr)
        print("  body:       Email body (optional, uses template if omitted)", file=sys.stderr)
        print("", file=sys.stderr)
        print("Supported formats: PDF, Excel, CSV, PowerPoint, Word, images, etc.", file=sys.stderr)
        sys.exit(1)

    # ファイルパスをパース（カンマ区切り）
    file_paths = [p.strip() for p in sys.argv[1].split(',')]

    # 最大5ファイルまで
    if len(file_paths) > MAX_ATTACHMENTS:
        print(f"Error: Maximum {MAX_ATTACHMENTS} attachments allowed. Got {len(file_paths)}.", file=sys.stderr)
        sys.exit(1)

    secrets = load_secrets()

    # 宛先: 引数 > デフォルト設定
    to_email = sys.argv[2] if len(sys.argv) > 2 else secrets['default_recipient']
    if not to_email:
        print("Error: No recipient specified. Provide to_email or set default_recipient.", file=sys.stderr)
        sys.exit(1)

    tpl = load_template()
    now = datetime.now()
    date = now.strftime('%Y年%m月%d日')
    date_compact = now.strftime('%Y%m%d')
    filenames = [os.path.basename(p) for p in file_paths]

    # 件名と本文（テンプレートから生成し、引数があれば上書き）
    subject, body = format_message(tpl, to_email, filenames, date, date_compact)
    if len(sys.argv) > 3:
        subject = sys.argv[3]
    if len(sys.argv) > 4:
        body = sys.argv[4]

    success = send_email(secrets, to_email, subject, body, file_paths)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

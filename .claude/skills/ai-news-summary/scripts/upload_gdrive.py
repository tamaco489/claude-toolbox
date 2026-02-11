#!/Users/tamaco/Desktop/work/general/.venv/bin/python3
"""Google Driveアップロードスクリプト（AWSブログ用）"""

import json
import logging
import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# パス設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
SECRETS_PATH = os.path.join(SKILL_DIR, 'config', 'secrets.json')

SCOPES = ['https://www.googleapis.com/auth/drive.file']


def _load_json(path, default=None):
    """JSONファイルを読み込む"""
    if not os.path.exists(path):
        return default or {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"{path}: {e}")
        return default or {}


def _get_env_or(key, default=''):
    """環境変数を取得、なければデフォルト"""
    return os.environ.get(key) or default


def load_secrets():
    """秘匿情報を読み込む（環境変数優先）"""
    if not os.path.exists(SECRETS_PATH):
        logger.warning(f"{SECRETS_PATH} not found. Using environment variables.")
    secrets = _load_json(SECRETS_PATH)
    result = {
        'client_secret': _get_env_or(
            'GDRIVE_CLIENT_SECRET',
            secrets.get('gdrive_client_secret', '')
        ),
        'folder_id': _get_env_or(
            'GDRIVE_FOLDER_ID',
            secrets.get('gdrive_folder_id', '')
        ),
    }
    if not result['client_secret']:
        logger.error("Google Drive OAuth client secret is not configured.")
        logger.error(f"  Set GDRIVE_CLIENT_SECRET env var or")
        logger.error(f"  add gdrive_client_secret to {SECRETS_PATH}")
    if not result['folder_id']:
        logger.error("Google Drive folder ID is not configured.")
        logger.error(f"  Set GDRIVE_FOLDER_ID env var or")
        logger.error(f"  add gdrive_folder_id to {SECRETS_PATH}")
    return result


def get_drive_service(client_secret_path):
    """OAuth 2.0認証でGoogle Drive APIサービスを構築"""
    token_path = os.path.join(os.path.dirname(client_secret_path), 'gdrive_token.json')
    creds = None

    # 保存済みトークンがあれば読み込む
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # トークンがない or 期限切れの場合
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing access token...")
            creds.refresh(Request())
        else:
            logger.info("Opening browser for authorization...")
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # トークンを保存
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
        logger.info(f"Token saved to {token_path}")

    return build('drive', 'v3', credentials=creds)


def find_existing_file(service, name, folder_id):
    """フォルダ内の同名ファイルを検索"""
    query = (
        f"name = '{name}' and '{folder_id}' in parents and trashed = false"
    )
    results = service.files().list(
        q=query, fields='files(id, name)', pageSize=1
    ).execute()
    files = results.get('files', [])
    return files[0]['id'] if files else None


def upload_file(service, path, folder_id):
    """ファイルをGoogle Driveにアップロード（同名ファイルがあれば上書き）"""
    name = os.path.basename(path)
    media = MediaFileUpload(path, mimetype='application/pdf', resumable=True)

    existing_id = find_existing_file(service, name, folder_id)

    if existing_id:
        logger.info(f"Updating existing file: {name} (id: {existing_id})")
        file = service.files().update(
            fileId=existing_id,
            media_body=media,
        ).execute()
    else:
        logger.info(f"Uploading new file: {name}")
        metadata = {
            'name': name,
            'parents': [folder_id],
        }
        file = service.files().create(
            body=metadata,
            media_body=media,
            fields='id, name, webViewLink',
        ).execute()

    logger.info(f"Done! File ID: {file.get('id')}")
    web_link = file.get('webViewLink')
    if web_link:
        logger.info(f"Link: {web_link}")
    return file


def main():
    if len(sys.argv) < 2:
        logger.error("Usage: upload_gdrive.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        sys.exit(1)

    secrets = load_secrets()
    if not secrets['client_secret'] or not secrets['folder_id']:
        sys.exit(1)

    service = get_drive_service(secrets['client_secret'])
    upload_file(service, pdf_path, secrets['folder_id'])
    logger.info("Success!")


if __name__ == '__main__':
    main()

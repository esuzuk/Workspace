"""
ユーティリティ関数
"""
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config():
    """
    環境変数から設定を読み込み
    
    Returns:
        dict: 設定辞書
    """
    load_dotenv()
    
    config = {
        'spreadsheet_id': os.getenv('GOOGLE_SPREADSHEET_ID', ''),
        'credentials_path': os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
    }
    
    if not config['spreadsheet_id']:
        logger.warning("GOOGLE_SPREADSHEET_IDが設定されていません")
    
    if not os.path.exists(config['credentials_path']):
        logger.warning(f"認証情報ファイルが見つかりません: {config['credentials_path']}")
    
    return config
